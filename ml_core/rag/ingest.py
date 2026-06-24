"""
ml_core/rag/ingest.py

Normalizes raw uploads (PDF, plain text, bare topic strings) into clean text
ready for chunk_text(). This is the "extraction" stage of the RAG pipeline:

    source input -> [ingest.py] -> chunk_text() -> embeddings -> ChromaDB

Design notes:
- Every extractor returns a list of PageText, never a single blob of text.
  Page boundaries matter: they're the only provenance we get for free, and
  the retriever's metadata (page number) depends on them surviving through
  to chunking.
- PDF extraction strips the most common noise (page numbers, repeated
  headers/footers, broken hyphenation across line wraps) but this is NOT
  OCR. Scanned/image-only PDFs will extract empty or garbage text — we
  detect that case and raise rather than silently returning nothing, since
  a silent empty-text result downstream just shows up as "zero chunks were
  created" with no clue why.
- YouTube and raw-notes ingestion are stubbed with a stable interface so
  the rest of the pipeline (chunker, embeddings, retriever) never needs to
  know which source type it came from — they only ever see PageText.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class IngestError(Exception):
    """Raised when a source can't be turned into usable text. Always carries
    a specific, user-facing reason — never raised for a vague 'something
    went wrong' case."""


@dataclass
class PageText:
    """One page (or page-equivalent unit) of extracted text."""
    page_number: int  # 1-indexed
    text: str


@dataclass
class IngestResult:
    source_type: str  # "pdf" | "text" | "topic" | "youtube"
    pages: list[PageText]
    full_text: str  # pages joined, convenience for chunk_text()
    warnings: list[str]


# ── Shared cleanup helpers ───────────────────────────────────────────────

_HYPHEN_LINEBREAK_RE = re.compile(r"(\w+)-\n(\w+)")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_TRAILING_WS_RE = re.compile(r"[ \t]+\n")


def _dehyphenate(text: str) -> str:
    """Rejoins words that were broken across a line wrap with a hyphen,
    e.g. 'back-\npropagation' -> 'backpropagation'. This is extremely
    common in PDF-extracted text and, left unfixed, corrupts both token
    counts and the literal words the LLM sees."""
    return _HYPHEN_LINEBREAK_RE.sub(r"\1\2", text)


def _normalize_whitespace(text: str) -> str:
    text = _TRAILING_WS_RE.sub("\n", text)
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip()


def _strip_repeated_lines(page_texts: list[str], min_repeat_frac: float = 0.6) -> list[str]:
    """
    Detects lines (typically headers/footers/page numbers) that repeat
    near-verbatim across most pages, and removes them. A line that appears
    on >= min_repeat_frac of pages is treated as boilerplate, not content.

    Only applied when there are enough pages for "repeated across pages" to
    be a meaningful signal — skipped for very short documents where it would
    just delete real, non-repeated content that happens to coincide once.
    """
    if len(page_texts) < 4:
        return page_texts

    line_page_count: dict[str, int] = {}
    per_page_lines = []
    for pt in page_texts:
        lines = [l.strip() for l in pt.split("\n")]
        per_page_lines.append(lines)
        seen_this_page = set()
        for l in lines:
            if not l or l in seen_this_page:
                continue
            seen_this_page.add(l)
            line_page_count[l] = line_page_count.get(l, 0) + 1

    threshold = max(2, int(len(page_texts) * min_repeat_frac))
    boilerplate = {l for l, count in line_page_count.items() if count >= threshold}

    cleaned_pages = []
    for lines in per_page_lines:
        kept = [l for l in lines if l not in boilerplate]
        cleaned_pages.append("\n".join(kept))
    return cleaned_pages


# ── PDF extraction ───────────────────────────────────────────────────────

# Heuristic: real body text averages well above this many alphabetic
# characters per page. A PDF that extracts far less than this on most pages
# is almost certainly scanned/image-only and needs OCR, which we don't do.
_MIN_ALPHA_CHARS_PER_PAGE = 40


def ingest_pdf(file_path: str | Path) -> IngestResult:
    if fitz is None:
        raise IngestError(
            "PyMuPDF is not installed. Run `pip install pymupdf` to enable PDF ingestion."
        )

    file_path = Path(file_path)
    if not file_path.exists():
        raise IngestError(f"File not found: {file_path}")

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise IngestError(f"Could not open PDF (corrupt or password-protected?): {e}") from e

    if doc.is_encrypted:
        raise IngestError("This PDF is password-protected. Remove the password and re-upload.")

    if doc.page_count == 0:
        raise IngestError("This PDF has no pages.")

    raw_pages: list[str] = []
    for page in doc:
        raw_pages.append(page.get_text("text"))
    doc.close()

    alpha_counts = [sum(c.isalpha() for c in p) for p in raw_pages]
    pages_with_real_text = sum(1 for c in alpha_counts if c >= _MIN_ALPHA_CHARS_PER_PAGE)
    warnings: list[str] = []

    if pages_with_real_text == 0:
        raise IngestError(
            "No extractable text found. This PDF appears to be scanned images rather than "
            "real text — MetaLearn doesn't support OCR yet. Try a text-based PDF instead."
        )
    if pages_with_real_text < len(raw_pages) * 0.5:
        warnings.append(
            f"Only {pages_with_real_text}/{len(raw_pages)} pages had extractable text. "
            "Some pages may be scanned images and were skipped."
        )

    cleaned_pages = _strip_repeated_lines(raw_pages)
    cleaned_pages = [_normalize_whitespace(_dehyphenate(p)) for p in cleaned_pages]

    pages = [
        PageText(page_number=i + 1, text=p)
        for i, p in enumerate(cleaned_pages)
        if p.strip()
    ]

    if not pages:
        raise IngestError("PDF text extraction produced no usable content after cleanup.")

    full_text = "\n\n".join(p.text for p in pages)
    return IngestResult(source_type="pdf", pages=pages, full_text=full_text, warnings=warnings)


# ── Plain text / pasted notes ────────────────────────────────────────────

def ingest_text(raw_text: str) -> IngestResult:
    """For pasted notes, lecture transcripts, or any plain-text source.
    Treated as a single 'page' since there's no real page concept."""
    if not raw_text or not raw_text.strip():
        raise IngestError("No text provided.")

    cleaned = _normalize_whitespace(raw_text)
    pages = [PageText(page_number=1, text=cleaned)]
    return IngestResult(source_type="text", pages=pages, full_text=cleaned, warnings=[])


# ── Bare topic string (no source material at all) ───────────────────────

def ingest_topic(topic: str) -> IngestResult:
    """
    Handles the 'Teach me CNNs' case from the wireframe — no uploaded
    material, just a topic name. There is deliberately no text to chunk
    or embed here: the tutor agent will teach from its own knowledge
    instead of RAG-grounded retrieval. We still return an IngestResult
    (with empty pages) so callers don't need a separate code path —
    the chunker and retriever simply see zero chunks for this source.
    """
    if not topic or not topic.strip():
        raise IngestError("No topic provided.")

    return IngestResult(
        source_type="topic",
        pages=[],
        full_text="",
        warnings=["No source material provided — the tutor will teach from general knowledge, not RAG retrieval."],
    )


# ── YouTube (stubbed — not implemented at MVP) ───────────────────────────

def ingest_youtube(url: str) -> IngestResult:
    """
    Stub. Real implementation needs a transcript-fetching service (e.g.
    youtube-transcript-api or a captions API) which is explicitly deferred
    past MVP per the build phasing. Raising here — rather than returning
    an empty IngestResult — is intentional: a YouTube URL silently producing
    zero chunks would look identical to a successful-but-empty video, which
    is a much more confusing failure mode for whoever's debugging it.
    """
    raise IngestError(
        "YouTube ingestion isn't implemented yet. Paste a transcript as text instead, "
        "or upload a PDF."
    )


# ── Single entry point ────────────────────────────────────────────────────

def ingest(source_type: str, **kwargs) -> IngestResult:
    """
    Dispatch by source_type so callers (e.g. the FastAPI router) don't need
    to import each extractor individually.

        ingest("pdf", file_path="/tmp/upload.pdf")
        ingest("text", raw_text="...")
        ingest("topic", topic="CNNs")
        ingest("youtube", url="...")
    """
    dispatch = {
        "pdf": lambda: ingest_pdf(kwargs["file_path"]),
        "text": lambda: ingest_text(kwargs["raw_text"]),
        "topic": lambda: ingest_topic(kwargs["topic"]),
        "youtube": lambda: ingest_youtube(kwargs["url"]),
    }
    if source_type not in dispatch:
        raise IngestError(f"Unknown source_type: {source_type!r}. Expected one of {list(dispatch)}.")
    return dispatch[source_type]()