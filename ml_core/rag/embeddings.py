"""
ml_core/rag/embeddings.py

Turns Chunk objects (from chunker.py) into vectors, ready for storage in
ChromaDB. This is the "embedding" stage of the RAG pipeline:

    ingest.py -> chunk_text() -> [embeddings.py] -> ChromaDB -> retriever.py

Why Voyage AI, not Claude or OpenAI:
Anthropic's API has no embeddings endpoint — Claude is a generation model,
not an embedding model. Anthropic's own docs recommend Voyage AI as the
embedding provider for Claude-stack RAG applications, so this module is a
thin wrapper around voyageai's official SDK rather than a raw HTTP client.

Two distinct entry points, not one:
Voyage's API distinguishes input_type="document" (text being stored/indexed)
from input_type="query" (text used to search). Using the wrong one for a
given direction measurably hurts retrieval quality per Voyage's own
documentation, so embed_chunks() and embed_query() are kept as separate
functions rather than one function with a type flag that's easy to get
backwards by accident at a call site.

Model choice:
Defaults to voyage-3-lite (512 dims) rather than voyage-3 (1024 dims). At
MVP scale — one document's worth of chunks per learning session, not a
shared corpus — the storage and retrieval-speed savings from the smaller
vector outweigh the marginal quality difference. This is a config constant,
not hardcoded inline, specifically so it's a one-line change later if
retrieval quality on real documents turns out to need the larger model.

Retry behavior:
RateLimitError and APIConnectionError are retried with exponential backoff,
since both are transient by nature. AuthenticationError and
InvalidRequestError are NOT retried — retrying a bad API key five times
just burns five timeouts before failing anyway, and hides the real problem
(misconfigured .env, malformed input) behind a slow, confusing failure.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

try:
    import voyageai
    from voyageai.error import (
        VoyageError,
        RateLimitError,
        APIConnectionError,
        AuthenticationError,
        InvalidRequestError,
    )
except ImportError:
    voyageai = None

from ml_core.rag.chunker import Chunk

DEFAULT_MODEL = "voyage-3-lite"
EXPECTED_DIMENSIONS = {"voyage-3-lite": 512, "voyage-3": 1024, "voyage-3-large": 1024}

# Voyage's per-request batch limit is generous, but we cap well below it so
# one oversized batch never becomes a single point of failure for an entire
# document's worth of chunks — if a 200-chunk PDF fails embedding partway
# through, we want to know it failed on batch 3 of 5, not "the whole thing
# failed" with no indication of how much actually succeeded.
DEFAULT_BATCH_SIZE = 64

MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.5


class EmbeddingError(Exception):
    """Raised for embedding failures that are NOT worth retrying — bad API
    key, malformed input, or retries exhausted. Always carries a specific
    reason so callers don't need to inspect the underlying Voyage exception
    to know what to do about it."""


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    vector: list[float]
    model: str


def _get_client() -> "voyageai.Client":
    if voyageai is None:
        raise EmbeddingError(
            "voyageai package is not installed. Run `pip install voyageai` to enable embeddings."
        )
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise EmbeddingError(
            "VOYAGE_API_KEY is not set. Add it to your .env — embeddings cannot run without it."
        )
    return voyageai.Client(api_key=api_key, max_retries=0)  # we handle retries ourselves, deliberately


def _batched(items: list, batch_size: int):
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def _embed_with_retry(client, texts: list[str], model: str, input_type: str) -> list[list[float]]:
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            result = client.embed(texts=texts, model=model, input_type=input_type)
            return result.embeddings
        except (RateLimitError, APIConnectionError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                backoff = BASE_BACKOFF_SECONDS * (2 ** attempt)
                time.sleep(backoff)
            continue
        except AuthenticationError as e:
            raise EmbeddingError(
                f"Voyage API authentication failed — check VOYAGE_API_KEY. Details: {e}"
            ) from e
        except InvalidRequestError as e:
            raise EmbeddingError(f"Voyage API rejected the request as invalid: {e}") from e
        except VoyageError as e:
            # any other Voyage-side error: don't blindly retry an unknown
            # failure mode, surface it immediately
            raise EmbeddingError(f"Voyage API error: {e}") from e

    raise EmbeddingError(
        f"Embedding failed after {MAX_RETRIES} retries (rate limit or connection issue). "
        f"Last error: {last_error}"
    )


# ── Public API ────────────────────────────────────────────────────────────

def embed_chunks(
    chunks: list[Chunk],
    model: str = DEFAULT_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[EmbeddedChunk]:
    """
    Embeds a list of Chunks for STORAGE (input_type="document"). Use this
    when ingesting a new source, never at query time.

    Batches internally so a large document's chunk list never goes out in
    a single oversized request, and so a failure can be attributed to a
    specific batch rather than the whole call.
    """
    if not chunks:
        return []

    client = _get_client()
    results: list[EmbeddedChunk] = []

    for batch_num, batch in enumerate(_batched(chunks, batch_size)):
        texts = [c.text for c in batch]
        try:
            vectors = _embed_with_retry(client, texts, model=model, input_type="document")
        except EmbeddingError as e:
            raise EmbeddingError(
                f"Failed on batch {batch_num + 1} "
                f"(chunks {batch[0].index}-{batch[-1].index}): {e}"
            ) from e

        if len(vectors) != len(batch):
            raise EmbeddingError(
                f"Voyage returned {len(vectors)} vectors for {len(batch)} input chunks "
                f"in batch {batch_num + 1} — response/request count mismatch."
            )

        for chunk, vector in zip(batch, vectors):
            results.append(EmbeddedChunk(chunk=chunk, vector=vector, model=model))

    return results


def embed_query(query: str, model: str = DEFAULT_MODEL) -> list[float]:
    """
    Embeds a single piece of text for SEARCH (input_type="query"). Use this
    at retrieval time — every turn of a live learning session — never for
    the chunks being stored.
    """
    if not query or not query.strip():
        raise EmbeddingError("Cannot embed an empty query.")

    client = _get_client()
    vectors = _embed_with_retry(client, [query], model=model, input_type="query")
    if not vectors:
        raise EmbeddingError("Voyage returned no vector for the query.")
    return vectors[0]


def expected_dimensions(model: str = DEFAULT_MODEL) -> int:
    """Lets callers (e.g. the Chroma collection setup) validate vector size
    without making a network call just to find out how many dimensions a
    model produces."""
    if model not in EXPECTED_DIMENSIONS:
        raise EmbeddingError(
            f"Unknown model {model!r}. Expected one of {list(EXPECTED_DIMENSIONS)}."
        )
    return EXPECTED_DIMENSIONS[model]
