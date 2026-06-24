"""
ml_core/tests/test_ingest.py

Run with: python3 -m pytest ml_core/tests/test_ingest.py -v

Uses synthetic PDFs generated on the fly with PyMuPDF rather than checked-in
binary fixtures, so the test suite has no binary assets to go stale.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
import fitz

from ml_core.rag.ingest import (
    ingest,
    ingest_pdf,
    ingest_text,
    ingest_topic,
    ingest_youtube,
    IngestError,
)


# ── Fixtures: synthetic PDFs built on the fly ────────────────────────────

@pytest.fixture
def pdf_with_repeated_header_footer(tmp_path):
    """
    6 pages (above the >=4 page threshold for boilerplate stripping) with a
    header and footer repeated on every page, plus one hyphenated line break
    to verify dehyphenation. This is the exact case that silently failed in
    manual testing when only 3 pages were generated — the page count must
    stay >= 4 for this fixture to mean anything.
    """
    doc = fitz.open()
    header = "CS229: Machine Learning Notes\n\n"
    footer = "\n\nPage continues below"
    bodies = [
        "Convolutional neural networks process images using a sliding filter called a ker-\nnel.",
        "Each kernel detects a specific pattern, like an edge or a texture.",
        "This operation is called convolution, and it produces a feature map.",
        "After convolution, a pooling layer typically reduces the spatial size.",
        "Max pooling makes the network more robust to small translations.",
        "Backpropagation is then used to adjust the kernel weights.",
    ]
    for i, body in enumerate(bodies):
        page = doc.new_page()
        has_footer = i < len(bodies) - 1
        content = header + body + (footer if has_footer else "")
        page.insert_textbox(fitz.Rect(50, 50, 550, 750), content, fontsize=11)
    path = tmp_path / "lecture_6page.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture
def pdf_short_three_pages(tmp_path):
    """Below the boilerplate-stripping page threshold — header/footer should
    survive untouched here, since 3 pages isn't a reliable repetition signal."""
    doc = fitz.open()
    header = "CS229: Machine Learning Notes\n\n"
    bodies = ["First page body text here.", "Second page body text here.", "Third page body text here."]
    for body in bodies:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(50, 50, 550, 750), header + body, fontsize=11)
    path = tmp_path / "lecture_3page.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture
def pdf_encrypted(tmp_path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 550, 750), "secret content", fontsize=11)
    path = tmp_path / "encrypted.pdf"
    doc.save(str(path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret123", owner_pw="owner456")
    doc.close()
    return str(path)


@pytest.fixture
def pdf_image_only(tmp_path):
    """Simulates a scanned PDF: a page with a drawn shape but zero real text."""
    doc = fitz.open()
    page = doc.new_page()
    page.draw_rect(fitz.Rect(100, 100, 400, 400))
    path = tmp_path / "scanned.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture
def pdf_corrupt(tmp_path):
    path = tmp_path / "corrupt.pdf"
    path.write_text("this is not a real pdf file, just garbage bytes %%%%")
    return str(path)


# ── PDF ingestion tests ───────────────────────────────────────────────────

def test_strips_repeated_header_and_footer_above_page_threshold(pdf_with_repeated_header_footer):
    result = ingest_pdf(pdf_with_repeated_header_footer)
    assert len(result.pages) == 6
    for p in result.pages:
        assert "CS229: Machine Learning Notes" not in p.text
        assert "Page continues below" not in p.text
        assert p.text.strip() != ""


def test_dehyphenates_line_wrapped_words(pdf_with_repeated_header_footer):
    result = ingest_pdf(pdf_with_repeated_header_footer)
    assert "kernel" in result.full_text
    assert "ker-\nnel" not in result.full_text
    assert "ker-nel" not in result.full_text


def test_short_document_below_threshold_does_not_strip_unique_seeming_lines(pdf_short_three_pages):
    # Below 4 pages, the repeated-line stripper should not activate at all —
    # this locks in the documented threshold behavior so it can't silently
    # change again without a test failing.
    result = ingest_pdf(pdf_short_three_pages)
    header_survives = any("CS229: Machine Learning Notes" in p.text for p in result.pages)
    assert header_survives, (
        "Expected header to survive on short documents (< 4 pages) since "
        "the boilerplate stripper requires >= 4 pages to activate."
    )


def test_raises_on_encrypted_pdf(pdf_encrypted):
    with pytest.raises(IngestError, match="password-protected"):
        ingest_pdf(pdf_encrypted)


def test_raises_on_corrupt_pdf(pdf_corrupt):
    with pytest.raises(IngestError):
        ingest_pdf(pdf_corrupt)


def test_raises_on_image_only_pdf(pdf_image_only):
    with pytest.raises(IngestError, match="scanned images"):
        ingest_pdf(pdf_image_only)


def test_raises_on_missing_file():
    with pytest.raises(IngestError, match="not found"):
        ingest_pdf("/tmp/this_file_does_not_exist_12345.pdf")


def test_pdf_result_has_correct_source_type(pdf_with_repeated_header_footer):
    result = ingest_pdf(pdf_with_repeated_header_footer)
    assert result.source_type == "pdf"


def test_pdf_full_text_joins_all_pages(pdf_with_repeated_header_footer):
    result = ingest_pdf(pdf_with_repeated_header_footer)
    for p in result.pages:
        assert p.text in result.full_text


# ── Plain text ingestion tests ────────────────────────────────────────────

def test_ingest_text_basic():
    result = ingest_text("Backpropagation uses the chain rule.")
    assert result.source_type == "text"
    assert len(result.pages) == 1
    assert "chain rule" in result.full_text


def test_ingest_text_collapses_excess_blank_lines():
    result = ingest_text("Line one.\n\n\n\n\nLine two.")
    assert "\n\n\n" not in result.full_text


def test_ingest_text_raises_on_empty_string():
    with pytest.raises(IngestError):
        ingest_text("")


def test_ingest_text_raises_on_whitespace_only():
    with pytest.raises(IngestError):
        ingest_text("    \n\n   ")


# ── Topic ingestion tests ─────────────────────────────────────────────────

def test_ingest_topic_returns_empty_pages_with_warning():
    result = ingest_topic("Convolutional Neural Networks")
    assert result.source_type == "topic"
    assert result.pages == []
    assert result.full_text == ""
    assert len(result.warnings) == 1


def test_ingest_topic_raises_on_empty_string():
    with pytest.raises(IngestError):
        ingest_topic("")


# ── YouTube stub tests ─────────────────────────────────────────────────────

def test_ingest_youtube_raises_not_implemented():
    with pytest.raises(IngestError, match="isn't implemented"):
        ingest_youtube("https://youtube.com/watch?v=abc123")


# ── Dispatcher tests ───────────────────────────────────────────────────────

def test_dispatcher_routes_text_correctly():
    result = ingest("text", raw_text="hello world")
    assert result.source_type == "text"


def test_dispatcher_routes_topic_correctly():
    result = ingest("topic", topic="CNNs")
    assert result.source_type == "topic"


def test_dispatcher_raises_on_unknown_source_type():
    with pytest.raises(IngestError, match="Unknown source_type"):
        ingest("fax", raw_text="hi")


# ── End-to-end: ingest feeds directly into chunk_text ────────────────────

def test_ingested_pdf_text_chunks_cleanly(pdf_with_repeated_header_footer):
    from ml_core.rag.chunker import chunk_text

    result = ingest_pdf(pdf_with_repeated_header_footer)
    chunks = chunk_text(result.full_text, chunk_tokens=30, overlap_tokens=15)

    assert len(chunks) > 0
    full_chunked_text = " ".join(c.text for c in chunks)
    # boilerplate should not have leaked through into chunks
    assert "CS229" not in full_chunked_text
    assert "Page continues below" not in full_chunked_text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))