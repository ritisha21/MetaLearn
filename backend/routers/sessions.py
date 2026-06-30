"""
backend/routers/sessions.py

The learning session flow — this is where ml_core gets called from.
Endpoints map directly to the wireframe's phases:
  POST /sessions/start       -> pre-assessment, RAG ingestion, learning plan
  POST /sessions/{id}/chat   -> tutor agent streaming
  POST /sessions/{id}/feynman -> Feynman scorer
  POST /sessions/{id}/quiz   -> quiz generator (stub, next to build)
  POST /sessions/{id}/submit -> calibration engine, final results

All heavy lifting is in ml_core/. This file is intentionally thin:
validate input, call ml_core, return result.
"""

import os
import uuid
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ml_core.rag.ingest import ingest, IngestError
from ml_core.rag.chunker import chunk_text
from ml_core.rag.embeddings import embed_chunks, EmbeddingError
from ml_core.rag.retriever import store_embedded_chunks, retrieve, format_context_for_prompt, RetrieverError
from ml_core.tutor.session_agent import SessionAgent, TutorAgentError
from ml_core.scoring.feynman_scorer import score_feynman_explanation, ScoringError

router = APIRouter()

# In-memory session store for MVP — replace with Supabase in V1.
# Keyed by session_id -> dict of session state.
_sessions: dict[str, dict] = {}


# ── Request / Response models ─────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    topic: str
    mode: str = "academic"           # academic | career | self
    prior_knowledge: str = ""
    confidence: int = 50             # 0-100
    source_type: str = "topic"       # topic | text | pdf
    raw_text: Optional[str] = None   # for source_type="text"


class ChatRequest(BaseModel):
    message: str


class FeynmanRequest(BaseModel):
    explanation: str


class QuizSubmitRequest(BaseModel):
    answers: list[str]          # one letter per question e.g. ["A","C","B","D"]
    post_confidence: int        # 0-100, recalibrated after quiz


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/start")
async def start_session(req: StartSessionRequest):
    """
    Ingests source material (if any), runs RAG, creates a SessionAgent,
    and returns the agent's opening message.
    """
    session_id = str(uuid.uuid4())

    # --- Ingest + RAG ---
    retrieved_context = ""
    try:
        if req.source_type == "topic":
            ingest_result = ingest("topic", topic=req.topic)
        elif req.source_type == "text" and req.raw_text:
            ingest_result = ingest("text", raw_text=req.raw_text)
            chunks = chunk_text(ingest_result.full_text)
            embedded = embed_chunks(chunks)
            store_embedded_chunks(session_id, embedded)
            retrieved = retrieve(session_id, req.topic)
            retrieved_context = format_context_for_prompt(retrieved)
        else:
            ingest_result = ingest("topic", topic=req.topic)
    except (IngestError, EmbeddingError, RetrieverError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    # --- Build agent ---
    agent = SessionAgent(
        topic=req.topic,
        prior_knowledge=req.prior_knowledge,
        confidence=req.confidence,
        retrieved_context=retrieved_context,
    )
    history = agent.build_opening_history(prior_knowledge=req.prior_knowledge)

    # --- Get opening message (non-streaming for session start) ---
    try:
        turn = agent.send_message(history)
    except TutorAgentError as e:
        raise HTTPException(status_code=502, detail=str(e))

    history.append({"role": "assistant", "content": turn.raw_text})

    # Store session state
    _sessions[session_id] = {
        "topic": req.topic,
        "mode": req.mode,
        "pre_confidence": req.confidence,
        "history": history,
        "retrieved_context": retrieved_context,
        "misconceptions": turn.parsed.misconceptions,
        "meta_prompt_count": len(turn.parsed.meta_prompts),
    }

    return {
        "session_id": session_id,
        "clean_text": turn.parsed.clean_text,
        "meta_prompts": turn.parsed.meta_prompts,
        "misconceptions": turn.parsed.misconceptions,
        "warnings": ingest_result.warnings,
    }


@router.post("/{session_id}/chat")
async def chat(session_id: str, req: ChatRequest):
    """
    Streams a tutor response. Returns SSE.
    The client accumulates tokens and calls /parse after stream ends
    to get structured meta-prompts and misconceptions.
    """
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")

    history = session["history"]
    history.append({"role": "user", "content": req.message})

    agent = SessionAgent(
        topic=session["topic"],
        confidence=session["pre_confidence"],
        retrieved_context=session["retrieved_context"],
    )

    accumulated: list[str] = []

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            for token in agent.stream_message(history):
                accumulated.append(token)
                yield f"data: {token}\n\n"
        except TutorAgentError as e:
            yield f"event: error\ndata: {e}\n\n"
            return

        full = "".join(accumulated)
        from ml_core.tutor.response_parser import parse_tutor_response
        parsed = parse_tutor_response(full)

        history.append({"role": "assistant", "content": full})
        session["misconceptions"].extend(parsed.misconceptions)
        session["meta_prompt_count"] += len(parsed.meta_prompts)

        import json
        meta_json = json.dumps({
            "meta_prompts": parsed.meta_prompts,
            "misconceptions": parsed.misconceptions,
        })
        yield f"event: meta\ndata: {meta_json}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{session_id}/feynman")
async def feynman(session_id: str, req: FeynmanRequest):
    """Scores the learner's Feynman explanation."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")

    try:
        result = score_feynman_explanation(
            topic=session["topic"],
            explanation=req.explanation,
        )
    except ScoringError as e:
        raise HTTPException(status_code=422, detail=str(e))

    session["feynman_result"] = result
    return {
        "overall": result.overall,
        "band": result.band,
        "dimensions": result.dimensions,
        "rubric_version": result.rubric_version,
    }


@router.post("/{session_id}/submit")
async def submit(session_id: str, req: QuizSubmitRequest):
    """
    Final step: calibration computation + full session results.
    Quiz scoring is a stub until quiz_generator.py is built.
    """
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")

    pre = session["pre_confidence"]
    post = req.post_confidence
    calibration_error = pre - post          # positive = overconfident
    feynman = session.get("feynman_result")

    return {
        "topic": session["topic"],
        "pre_confidence": pre,
        "post_confidence": post,
        "calibration_error": calibration_error,
        "calibration_label": (
            "well_calibrated" if abs(calibration_error) <= 10
            else "overconfident" if calibration_error > 10
            else "underconfident"
        ),
        "feynman_overall": feynman.overall if feynman else None,
        "feynman_band": feynman.band if feynman else None,
        "feynman_dimensions": feynman.dimensions if feynman else None,
        "misconceptions": session["misconceptions"],
        "meta_prompt_count": session["meta_prompt_count"],
    }


@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Accepts a PDF upload, ingests it, chunks it, embeds it, stores it in
    Chroma. Returns a source_id to reference in a subsequent /start call.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted.")

    import tempfile, shutil
    source_id = str(uuid.uuid4())

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        from ml_core.rag.ingest import ingest_pdf
        result = ingest_pdf(tmp_path)
        chunks = chunk_text(result.full_text)
        embedded = embed_chunks(chunks)

        page_numbers = {}
        char_to_page = {}
        for page in result.pages:
            for i in range(page.char_start if hasattr(page, 'char_start') else 0,
                           page.char_end if hasattr(page, 'char_end') else len(result.full_text)):
                char_to_page[i] = page.page_number

        for chunk in chunks:
            page_num = char_to_page.get(chunk.char_start, 1)
            page_numbers[chunk.index] = page_num

        store_embedded_chunks(source_id, embedded, page_numbers=page_numbers)
    except (IngestError, EmbeddingError, RetrieverError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.unlink(tmp_path)

    return {
        "source_id": source_id,
        "pages": len(result.pages),
        "chunks": len(chunks),
        "warnings": result.warnings,
    }
