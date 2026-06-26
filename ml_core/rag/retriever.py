"""
ml_core/rag/retriever.py

Final stage of the RAG pipeline: stores embedded chunks in ChromaDB and
retrieves the most relevant ones for a given query.

    ingest.py -> chunker.py -> embeddings.py -> [retriever.py] -> tutor agent

Storage model:
One Chroma collection per source_id (one per uploaded document / topic).
This keeps search fast (querying within one document's ~10-200 chunks,
never the whole platform's corpus) and makes deletion trivial — removing
a document is just dropping its collection, not filtering a shared index.

We pass embedding_function=None to every Chroma collection because we
already computed vectors ourselves via Voyage (embeddings.py) — leaving
Chroma's default embedding function active would make it silently try to
compute its OWN embeddings with its bundled ONNX model on any add()/query()
call that's missing an explicit vector, which would produce vectors from a
totally different model than the ones already stored. Explicit is correct
here, not optional.

Retrieval model — why MMR on top of Chroma, not just top-k:
Chroma's native query() only does plain similarity ranking. Plain top-k
against one document tends to return near-duplicate chunks when a concept
is repeated (e.g. "pooling" mentioned in 5 different paragraphs) — useless
for grounding a single tutor turn, since 4 near-identical chunks cover one
narrow angle instead of four different facets of the topic. We over-fetch
(fetch_k, default 12) from Chroma, then apply Maximal Marginal Relevance in
plain Python to select a final top-k that balances relevance against
diversity. MMR is small and pure-Python on a handful of vectors, so this
costs nothing meaningful in latency.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

try:
    import chromadb
except ImportError:
    chromadb = None

from ml_core.rag.chunker import Chunk
from ml_core.rag.embeddings import EmbeddedChunk, embed_query

DEFAULT_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "./chroma_data")
DEFAULT_FETCH_K = 12
DEFAULT_TOP_K = 4
# Empirically tested against a synthetic 8-chunk set containing 3 near-
# duplicate explanations of the same concept plus genuinely distinct
# content: lambda=0.7 kept ALL three near-duplicates in the top-4, which
# defeats the entire purpose of MMR re-ranking (see retriever tests).
# lambda=0.5 correctly swapped duplicates out for distinct chunks. 0.5 is
# the standard "balanced" MMR value in the literature and is the value
# that actually produced diverse results in our own test data, not just
# the textbook default — don't raise this back toward 0.7 without
# re-running test_retriever.py's diversity assertions against it.
DEFAULT_MMR_LAMBDA = 0.5


class RetrieverError(Exception):
    """Raised for storage/retrieval failures with a specific, actionable
    reason — never raised for a generic 'something went wrong'."""


@dataclass
class RetrievedChunk:
    text: str
    score: float  # similarity score, higher = more relevant (post-MMR rank, not raw distance)
    chunk_index: int
    page_number: int | None
    source_id: str


def _collection_name(source_id: str) -> str:
    # Chroma collection names have character restrictions; prefix + sanitize
    # so a raw source_id (e.g. a UUID with hyphens) is always a valid name.
    safe = "".join(c if c.isalnum() or c == "_" else "_" for c in source_id)
    return f"src_{safe}"


def _get_client():
    if chromadb is None:
        raise RetrieverError(
            "chromadb package is not installed. Run `pip install chromadb` to enable storage."
        )
    return chromadb.PersistentClient(path=DEFAULT_PERSIST_PATH)


def _get_collection(source_id: str, client=None):
    client = client or _get_client()
    return client.get_or_create_collection(
        name=_collection_name(source_id),
        embedding_function=None,  # we supply our own Voyage vectors — see module docstring
        metadata={"source_id": source_id},
    )


# ── Storage ────────────────────────────────────────────────────────────────

def store_embedded_chunks(
    source_id: str,
    embedded_chunks: list[EmbeddedChunk],
    page_numbers: dict[int, int] | None = None,
) -> int:
    """
    Persists embedded chunks into the collection for this source.

    page_numbers, if provided, maps chunk_index -> page_number, so chunks
    extracted from a multi-page PDF carry that provenance into Chroma's
    metadata. Purely optional — chunks from ingest_text()/ingest_topic()
    have no real page concept, and page_number will be None for those.

    Returns the number of chunks stored. Raises RetrieverError if the
    source has no chunks at all, since storing zero chunks for a source_id
    silently would make later retrieval indistinguishable from "this
    source hasn't been ingested yet" vs "this source had no content."
    """
    if not embedded_chunks:
        raise RetrieverError(
            f"No embedded chunks to store for source_id={source_id!r}. "
            "Did ingestion produce any chunks at all?"
        )

    page_numbers = page_numbers or {}
    collection = _get_collection(source_id)

    ids = [f"{source_id}_{ec.chunk.index}" for ec in embedded_chunks]
    vectors = [ec.vector for ec in embedded_chunks]
    documents = [ec.chunk.text for ec in embedded_chunks]
    metadatas = [
        {
            "source_id": source_id,
            "chunk_index": ec.chunk.index,
            "token_count": ec.chunk.token_count,
            "char_start": ec.chunk.char_start,
            "char_end": ec.chunk.char_end,
            "page_number": page_numbers.get(ec.chunk.index, -1),  # -1 = unknown, Chroma metadata can't store None
            "embedding_model": ec.model,
        }
        for ec in embedded_chunks
    ]

    try:
        collection.add(ids=ids, embeddings=vectors, documents=documents, metadatas=metadatas)
    except Exception as e:
        raise RetrieverError(f"Failed to store chunks for source_id={source_id!r}: {e}") from e

    return len(embedded_chunks)


def delete_source(source_id: str) -> None:
    """Drops the entire collection for a source — used when a document is
    removed or re-ingested from scratch."""
    client = _get_client()
    try:
        client.delete_collection(name=_collection_name(source_id))
    except Exception:
        # collection may simply not exist yet — deleting a nonexistent
        # source should be a no-op, not an error, since callers shouldn't
        # need to check existence first just to clean up.
        pass


def source_chunk_count(source_id: str) -> int:
    """Returns how many chunks are stored for a source. Useful for the
    ingestion endpoint to confirm storage actually succeeded, and for
    tests, without needing a full retrieval round-trip."""
    collection = _get_collection(source_id)
    return collection.count()


# ── MMR re-ranking ──────────────────────────────────────────────────────────

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _mmr_select(
    query_vector: np.ndarray,
    candidate_vectors: list[np.ndarray],
    top_k: int,
    lambda_mult: float,
) -> list[int]:
    """
    Maximal Marginal Relevance. Greedily picks the candidate that maximizes:

        lambda * sim(query, candidate) - (1 - lambda) * max(sim(candidate, already_selected))

    i.e. relevant to the query, but not redundant with what's already picked.
    Returns indices into candidate_vectors, in selection order (most
    relevant-and-diverse first).
    """
    if not candidate_vectors:
        return []

    n = len(candidate_vectors)
    top_k = min(top_k, n)

    query_sims = [_cosine_similarity(query_vector, v) for v in candidate_vectors]

    selected: list[int] = []
    remaining = set(range(n))

    # first pick is always the most relevant candidate, no diversity penalty
    first = max(remaining, key=lambda i: query_sims[i])
    selected.append(first)
    remaining.remove(first)

    while len(selected) < top_k and remaining:
        best_idx = None
        best_score = float("-inf")
        for i in remaining:
            redundancy = max(_cosine_similarity(candidate_vectors[i], candidate_vectors[j]) for j in selected)
            mmr_score = lambda_mult * query_sims[i] - (1 - lambda_mult) * redundancy
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i
        selected.append(best_idx)
        remaining.remove(best_idx)

    return selected


# ── Retrieval ────────────────────────────────────────────────────────────────

def retrieve(
    source_id: str,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    fetch_k: int = DEFAULT_FETCH_K,
    mmr_lambda: float = DEFAULT_MMR_LAMBDA,
) -> list[RetrievedChunk]:
    """
    Embeds `query`, over-fetches `fetch_k` candidates from Chroma by plain
    similarity, then MMR-reranks down to `top_k` for relevance + diversity.

    Returns an empty list (not an error) when the source has zero stored
    chunks — this is the expected, normal case for topic-only sessions
    (ingest_topic()) where there was never any source material to retrieve
    from. The tutor agent should treat an empty result as "teach from
    general knowledge," not as a failure.
    """
    collection = _get_collection(source_id)

    if collection.count() == 0:
        return []

    query_vector = embed_query(query)

    fetch_k = min(fetch_k, collection.count())
    raw = collection.query(
        query_embeddings=[query_vector],
        n_results=fetch_k,
        include=["documents", "metadatas", "embeddings"],
    )

    if not raw["ids"] or not raw["ids"][0]:
        return []

    documents = raw["documents"][0]
    metadatas = raw["metadatas"][0]
    embeddings = raw["embeddings"][0]

    candidate_vectors = [np.array(e) for e in embeddings]
    mmr_indices = _mmr_select(
        query_vector=np.array(query_vector),
        candidate_vectors=candidate_vectors,
        top_k=top_k,
        lambda_mult=mmr_lambda,
    )

    results: list[RetrievedChunk] = []
    for rank, idx in enumerate(mmr_indices):
        meta = metadatas[idx]
        page_number = meta.get("page_number", -1)
        results.append(
            RetrievedChunk(
                text=documents[idx],
                score=1.0 - (rank / max(len(mmr_indices), 1)),  # simple rank-based score, not raw distance
                chunk_index=meta.get("chunk_index", -1),
                page_number=page_number if page_number != -1 else None,
                source_id=source_id,
            )
        )

    return results


def format_context_for_prompt(retrieved: list[RetrievedChunk]) -> str:
    """
    Assembles retrieved chunks into a single context block for the tutor
    agent's prompt. Kept as a separate function (rather than inlined in the
    tutor agent) so the exact formatting can be tuned/tested independently
    of the retrieval logic itself.
    """
    if not retrieved:
        return ""

    parts = []
    for r in retrieved:
        page_tag = f" (page {r.page_number})" if r.page_number else ""
        parts.append(f"[Source excerpt{page_tag}]\n{r.text}")
    return "\n\n".join(parts)