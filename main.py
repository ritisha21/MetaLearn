from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import openai
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="MetaLearn API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ────────────────────────────────────────────────────────────────────

class PreLearnRequest(BaseModel):
    topic: str
    mode: str = "academic"
    confidence: int          # 0-100
    prior_knowledge: str = ""

class ChatMessage(BaseModel):
    role: str                # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    topic: str
    mode: str
    prior_knowledge: str
    confidence: int
    history: list[ChatMessage]
    user_message: str

class FeynmanRequest(BaseModel):
    topic: str
    explanation: str

class QuizRequest(BaseModel):
    topic: str
    history: list[ChatMessage]  # session transcript for context

class QuizSubmitRequest(BaseModel):
    topic: str
    questions: list[dict]
    answers: list[str]          # ["A", "C", "B", "D"]
    pre_confidence: int

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_client(api_key: str | None = None) -> openai.OpenAI:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=401, detail="OPENAI_API_KEY not set")
    return openai.OpenAI(api_key=key)


TUTOR_SYSTEM = """\
You are MetaLearn, an AI metacognitive tutor. Your job is NOT just to explain — \
you must build the learner's self-awareness about their own understanding.

Topic: "{topic}"
Mode: {mode}
Learner's prior knowledge: "{prior}"
Learner's starting confidence: {confidence}%

STRICT RULES:
1. Keep each response to 2–3 short paragraphs maximum. Dense walls of text destroy learning.
2. Every 2 exchanges, insert exactly ONE metacognitive prompt using this format on its own line:
   [META]: Your question here
   Good meta questions: "What surprised you?", "Where are you still fuzzy?", \
"How does this connect to something you already know?", "Predict what comes next."
3. If you detect a misconception in what the learner says, flag it on its own line:
   [MISCONCEPTION]: Brief one-sentence description
4. Never just give answers — make the learner reason first.
5. Use concrete examples and analogies, not abstract definitions.
"""


def parse_ai_response(raw: str) -> dict:
    """Split raw LLM text into main content, meta prompts, and misconceptions."""
    meta_prompts = re.findall(r"\[META\]:\s*(.+?)(?=\n|$)", raw)
    misconceptions = re.findall(r"\[MISCONCEPTION\]:\s*(.+?)(?=\n|$)", raw)
    clean = re.sub(r"\[(META|MISCONCEPTION)\]:.+?(?=\n|$)", "", raw).strip()
    return {
        "content": clean,
        "meta_prompts": meta_prompts,
        "misconceptions": misconceptions,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "MetaLearn API"}


@app.post("/session/start")
def session_start(req: PreLearnRequest):
    """
    Returns a structured pre-learn analysis: detected knowledge gaps,
    likely misconceptions based on stated prior knowledge, and a learning plan.
    """
    client = get_client()

    prompt = f"""A learner wants to learn about "{req.topic}".
Their stated prior knowledge: "{req.prior_knowledge or 'None'}"
Their confidence level: {req.confidence}%

Analyse this and return ONLY valid JSON with this shape:
{{
  "knowledge_gaps": ["gap 1", "gap 2", "gap 3"],
  "likely_misconceptions": ["possible misconception 1", "possible misconception 2"],
  "learning_plan": ["step 1", "step 2", "step 3", "step 4"],
  "opening_message": "A warm 2-sentence message to start the session that acknowledges their starting point"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    data = json.loads(response.choices[0].message.content)
    return data


@app.post("/session/chat")
def session_chat(req: ChatRequest):
    """
    Main learning exchange. Returns structured response with content,
    meta prompts, and any detected misconceptions. Streams the response.
    """
    client = get_client()

    system = TUTOR_SYSTEM.format(
        topic=req.topic,
        mode=req.mode,
        prior=req.prior_knowledge or "None stated",
        confidence=req.confidence,
    )

    messages = [{"role": "system", "content": system}]
    for msg in req.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.user_message})

    def stream():
        buffer = ""
        with client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
            temperature=0.7,
        ) as stream_resp:
            for chunk in stream_resp:
                delta = chunk.choices[0].delta.content or ""
                buffer += delta
                # Stream raw text token by token
                if delta:
                    yield f"data: {json.dumps({'token': delta})}\n\n"

        # After streaming, send parsed metadata as final event
        parsed = parse_ai_response(buffer)
        yield f"data: {json.dumps({'done': True, 'meta': parsed})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/session/feynman")
def evaluate_feynman(req: FeynmanRequest):
    """
    Evaluates a Feynman explanation on 4 dimensions.
    Returns score (0-1) and structured feedback.
    """
    client = get_client()

    prompt = f"""Evaluate this Feynman explanation of "{req.topic}".

The learner wrote:
\"\"\"{req.explanation}\"\"\"

Score it on 4 dimensions, each 0.00–1.00:
- accuracy: factual correctness
- clarity: would a non-expert understand this?
- depth: does it explain WHY, not just WHAT?
- transfer: does it use analogies or novel examples showing real understanding?

Return ONLY valid JSON:
{{
  "scores": {{
    "accuracy": 0.00,
    "clarity": 0.00,
    "depth": 0.00,
    "transfer": 0.00
  }},
  "overall": 0.00,
  "strengths": "1-2 sentences on what they got right",
  "gaps": "1-2 sentences on what's missing or wrong",
  "next_step": "One concrete thing to do to deepen understanding"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    return json.loads(response.choices[0].message.content)


@app.post("/session/quiz/generate")
def generate_quiz(req: QuizRequest):
    """
    Generates 4 MCQ questions from the session transcript.
    Questions test understanding, not memorisation.
    """
    client = get_client()

    transcript_summary = "\n".join(
        f"{m.role.upper()}: {m.content[:300]}" for m in req.history[-12:]
    )

    prompt = f"""Based on this learning session about "{req.topic}", generate exactly 4 multiple-choice questions.

Session transcript (last exchanges):
{transcript_summary}

Rules:
- Test UNDERSTANDING and ability to apply, not memorisation of facts
- Each question has exactly 4 options (A, B, C, D)
- One correct answer per question
- Wrong options should be plausible (common misconceptions), not obviously wrong
- Vary difficulty: 1 easy, 2 medium, 1 hard

Return ONLY valid JSON:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Question text",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "A",
      "explanation": "Brief explanation of why this is correct",
      "difficulty": "easy"
    }}
  ]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.5,
    )

    return json.loads(response.choices[0].message.content)


@app.post("/session/quiz/submit")
def submit_quiz(req: QuizSubmitRequest):
    """
    Scores the quiz, calculates calibration error, returns metacognitive analysis.
    """
    questions = req.questions
    answers = req.answers

    correct_count = 0
    results = []
    for i, (q, user_ans) in enumerate(zip(questions, answers)):
        is_correct = user_ans == q["correct"]
        if is_correct:
            correct_count += 1
        results.append({
            "question_id": q["id"],
            "user_answer": user_ans,
            "correct_answer": q["correct"],
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    quiz_score_pct = round((correct_count / len(questions)) * 100)
    calibration_error = req.pre_confidence - quiz_score_pct

    # Calibration interpretation
    if abs(calibration_error) <= 10:
        calibration_label = "well_calibrated"
        calibration_message = (
            f"Excellent calibration. Your confidence ({req.pre_confidence}%) closely matched "
            f"your actual score ({quiz_score_pct}%). This is rare — most learners are significantly overconfident."
        )
    elif calibration_error > 10:
        calibration_label = "overconfident"
        calibration_message = (
            f"You were overconfident by {calibration_error} points. "
            f"You expected {req.pre_confidence}% but scored {quiz_score_pct}%. "
            "This is the most common metacognitive failure — familiarity feels like understanding. "
            "Focus on testing yourself more aggressively during study."
        )
    else:
        calibration_label = "underconfident"
        calibration_message = (
            f"You were underconfident by {abs(calibration_error)} points. "
            f"You expected {req.pre_confidence}% but scored {quiz_score_pct}%. "
            "You know more than you think. Classic imposter syndrome pattern."
        )

    return {
        "quiz_score": quiz_score_pct,
        "correct_count": correct_count,
        "total": len(questions),
        "results": results,
        "calibration": {
            "pre_confidence": req.pre_confidence,
            "actual_score": quiz_score_pct,
            "error": calibration_error,
            "label": calibration_label,
            "message": calibration_message,
        },
    }