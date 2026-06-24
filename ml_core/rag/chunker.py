"""
ml_core/rag/chunker.py

Splits extracted text into overlapping, token-bounded chunks for embedding.

Design notes:
- Chunk size is measured in tokens (not characters) because embedding models
  and the tutor agent's context budget both think in tokens.
- We never split mid-sentence. A sentence that would overflow a chunk gets
  pushed entirely into the next chunk instead of being cut in half — a
  half-sentence is useless context for both retrieval and the LLM judge.
- Overlap exists so a sentence near a chunk boundary is never the ONLY
  copy of that sentence available to the retriever from just one side.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_CHUNK_TOKENS = 800
DEFAULT_OVERLAP_TOKENS = 100

# tiktoken downloads its vocab file from a remote blob on first use. In
# network-restricted environments (CI, sandboxed dev containers, offline
# machines) that download can fail outright. We try tiktoken first since
# it's the more accurate proxy for real token counts, but fall back to a
# cheap character-based estimate (~4 chars/token for English text) so the
# chunker never hard-fails just because token counting is approximate —
# approximate sizing is all we actually need here, exact parity is not.
try:
    import tiktoken

    _ENCODING = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_ENCODING.encode(text))

except Exception:
    _ENCODING = None

    def count_tokens(text: str) -> int:
        # Rough heuristic: English averages ~4 characters per token.
        return max(1, len(text) // 4)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


@dataclass
class Chunk:
    text: str
    index: int
    token_count: int
    char_start: int
    char_end: int


def split_into_sentences(text: str) -> list[str]:
    """
    Lightweight sentence splitter. Not linguistically perfect (abbreviations
    like 'e.g.' will sometimes split early) but good enough for chunk
    boundaries — a slightly-off sentence boundary costs nothing here, unlike
    in the Feynman scorer where wording precision matters.
    """
    text = text.strip()
    if not text:
        return []
    raw_sentences = _SENTENCE_SPLIT_RE.split(text)
    return [s.strip() for s in raw_sentences if s.strip()]


def chunk_text(
    text: str,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[Chunk]:
    """
    Greedily packs sentences into chunks up to `chunk_tokens`, then starts
    the next chunk `overlap_tokens` worth of trailing sentences back from
    where the previous one ended.

    IMPORTANT: overlap is sentence-granular and best-effort, not exact.
    Because we never split mid-sentence, `overlap_tokens` rounds UP to the
    nearest whole sentence boundary. If `overlap_tokens` is smaller than a
    single typical sentence in your text, overlap will silently collapse
    to zero for that chunk pair — this is expected, not a bug, but it means
    overlap_tokens should be set well above your text's average sentence
    length (a few hundred tokens of overlap on ~800-token chunks of normal
    prose is a safe ratio; 10 tokens of overlap is not).
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return []

    sentence_tokens = [count_tokens(s) for s in sentences]

    chunks: list[Chunk] = []
    start_idx = 0
    char_cursor = 0
    chunk_index = 0

    while start_idx < len(sentences):
        cur_tokens = 0
        end_idx = start_idx
        while end_idx < len(sentences) and cur_tokens + sentence_tokens[end_idx] <= chunk_tokens:
            cur_tokens += sentence_tokens[end_idx]
            end_idx += 1

        # Guarantee progress even if a single sentence exceeds chunk_tokens
        if end_idx == start_idx:
            end_idx = start_idx + 1
            cur_tokens = sentence_tokens[start_idx]

        chunk_sentences = sentences[start_idx:end_idx]
        chunk_str = " ".join(chunk_sentences)
        char_start = char_cursor
        char_end = char_start + len(chunk_str)

        chunks.append(
            Chunk(
                text=chunk_str,
                index=chunk_index,
                token_count=cur_tokens,
                char_start=char_start,
                char_end=char_end,
            )
        )
        chunk_index += 1
        char_cursor = char_end + 1

        if end_idx >= len(sentences):
            break

        # Walk back from end_idx to build the overlap for the next chunk.
        # Constraint: the next start_idx must strictly exceed the CURRENT
        # start_idx, or we re-emit the same chunk forever. Overlap is a
        # best-effort optimization, not a guarantee — if even one sentence
        # blows past the overlap budget, we simply can't overlap and must
        # advance past it.
        overlap_count = 0
        back_idx = end_idx
        while back_idx > start_idx + 1 and overlap_count < overlap_tokens:
            back_idx -= 1
            overlap_count += sentence_tokens[back_idx]

        next_start_idx = min(back_idx, end_idx - 1)
        start_idx = max(next_start_idx, start_idx + 1)

    return chunks