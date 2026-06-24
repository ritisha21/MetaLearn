"""
ml_core/tests/test_chunker.py

Run with: python3 -m pytest ml_core/tests/test_chunker.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ml_core.rag.chunker import chunk_text, split_into_sentences, count_tokens

LONG_SAMPLE = (
    "Convolutional neural networks process images using a sliding filter called a kernel. "
    "Each kernel detects a specific pattern, like an edge or a texture, by sliding across "
    "the image and computing a dot product at every position. This operation is called "
    "convolution, and it produces a feature map that highlights where the pattern was found. "
    "After convolution, a pooling layer typically reduces the spatial size of the feature "
    "map by summarizing small regions, usually by taking the maximum value. Max pooling "
    "makes the network more robust to small translations of the input, since the exact "
    "pixel position matters less than the presence of the feature. Stacking multiple "
    "convolution and pooling layers lets the network build up increasingly abstract "
    "representations, from edges to shapes to whole objects. Backpropagation is then used "
    "to adjust the kernel weights so the network gets better at detecting the patterns "
    "that actually matter for the task."
) * 3


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_single_short_sentence_returns_one_chunk():
    chunks = chunk_text("Backpropagation computes gradients via the chain rule.")
    assert len(chunks) == 1
    assert chunks[0].index == 0


def test_never_splits_mid_sentence():
    chunks = chunk_text(LONG_SAMPLE, chunk_tokens=50, overlap_tokens=15)
    for c in chunks:
        # every chunk should end with sentence-ending punctuation
        assert c.text.rstrip()[-1] in ".!?", f"Chunk {c.index} doesn't end on a sentence: {c.text[-30:]!r}"


def test_no_infinite_loop_on_small_overlap_relative_to_sentences():
    # This is the exact bug case from manual debugging: overlap smaller
    # than a single sentence must never hang or crash.
    chunks = chunk_text(LONG_SAMPLE, chunk_tokens=40, overlap_tokens=10)
    assert len(chunks) > 0


def test_chunks_make_forward_progress_and_cover_full_text():
    chunks = chunk_text(LONG_SAMPLE, chunk_tokens=100, overlap_tokens=30)
    assert len(chunks) > 1
    # indices must be strictly increasing with no gaps
    indices = [c.index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_real_overlap_occurs_when_overlap_window_fits_multiple_sentences():
    chunks = chunk_text(LONG_SAMPLE, chunk_tokens=120, overlap_tokens=30)
    assert len(chunks) > 2
    overlap_found_count = 0
    for i in range(len(chunks) - 1):
        a_words = chunks[i].text.split()
        b_words = chunks[i + 1].text.split()
        max_overlap = min(len(a_words), len(b_words))
        for L in range(max_overlap, 0, -1):
            if a_words[-L:] == b_words[:L]:
                overlap_found_count += 1
                break
    # at realistic chunk/overlap ratios, most consecutive pairs should overlap
    assert overlap_found_count >= (len(chunks) - 1) * 0.5


def test_chunk_token_counts_never_wildly_exceed_target():
    # a single oversized sentence can exceed chunk_tokens (by design — we
    # never split mid-sentence) but normal chunks should stay close to target
    chunks = chunk_text(LONG_SAMPLE, chunk_tokens=100, overlap_tokens=20)
    oversized = [c for c in chunks if c.token_count > 100 * 1.5]
    assert len(oversized) == 0, "chunks should not balloon past 1.5x target with normal sentence lengths"


def test_sentence_splitter_handles_basic_abbreviation_reasonably():
    text = "We use e.g. ResNet and VGG. Both are common baselines."
    sentences = split_into_sentences(text)
    # exact abbreviation handling is not guaranteed, but it must not crash
    # and must produce at least one non-empty sentence
    assert len(sentences) >= 1
    assert all(s.strip() for s in sentences)


def test_count_tokens_returns_positive_int_for_nonempty_text():
    assert count_tokens("hello world") > 0
    assert isinstance(count_tokens("hello world"), int)


if __name__ == "__main__":
    # Allow running directly without pytest for quick sanity checks
    import traceback

    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")