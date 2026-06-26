"""
ml_core/tests/test_retriever.py

Run with: python3 -m pytest ml_core/tests/test_retriever.py -v

What's tested for REAL (no mocking, no network needed):
ChromaDB's PersistentClient runs entirely on local disk — storage,
deletion, counting, and Chroma's own similarity query all execute against
a real (temporary) Chroma instance, not a mock. This is the strongest
guarantee in this entire test file.

What's tested with an injected vector (partially real):
retrieve() internally calls embed_query(), which needs a live Voyage API
call we don't have network access for in this environment. To still
exercise the Chroma-query + MMR-rerank logic for real, tests call Chroma
and _mmr_select() directly with a hand-supplied query vector, bypassing
embed_query() entirely rather than mocking it. This is deliberately NOT a
mock of retrieve() itself — it's testing the same underlying calls
retrieve() makes, just with the embedding step swapped for a known vector.

What is NOT tested:
embed_query() really hitting Voyage's API. See test_embeddings.py's header
for the same caveat — before shipping, run one real retrieve() call with a
valid VOYAGE_API_KEY to confirm the full path works end to end.
"""

import sys
import os
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
import numpy as np

from ml_core.rag.chunker import Chunk
from ml_core.rag.embeddings import EmbeddedChunk
from ml_core.rag.retriever import (
    store_embedded_chunks,
    delete_source,
    source_chunk_count,
    _get_collection,
    _mmr_select,
    _cosine_similarity,
    format_context_for_prompt,
    RetrievedChunk,
    RetrieverError,
)


@pytest.fixture
def chroma_path(tmp_path, monkeypatch):
    """Each test gets its own throwaway Chroma directory so tests never
    see each other's stored collections."""
    path = str(tmp_path / "chroma_test_data")
    monkeypatch.setenv("CHROMA_PERSIST_PATH", path)
    import ml_core.rag.retriever as retriever_module
    monkeypatch.setattr(retriever_module, "DEFAULT_PERSIST_PATH", path)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def make_embedded_chunks(texts_and_vectors: list[tuple[str, list[float]]]) -> list[EmbeddedChunk]:
    return [
        EmbeddedChunk(
            chunk=Chunk(text=text, index=i, token_count=10, char_start=i * 60, char_end=i * 60 + 59),
            vector=vec,
            model="test-model",
        )
        for i, (text, vec) in enumerate(texts_and_vectors)
    ]


# ── Storage tests (fully real, no mocking) ────────────────────────────────

def test_store_and_count_chunks(chroma_path):
    embedded = make_embedded_chunks([
        ("Convolution detects edges.", [1.0, 0.0, 0.0]),
        ("Pooling shrinks the feature map.", [0.0, 1.0, 0.0]),
    ])
    n = store_embedded_chunks("source_a", embedded)
    assert n == 2
    assert source_chunk_count("source_a") == 2


def test_store_raises_on_empty_chunk_list(chroma_path):
    with pytest.raises(RetrieverError, match="No embedded chunks"):
        store_embedded_chunks("source_empty", [])


def test_store_includes_page_number_metadata(chroma_path):
    embedded = make_embedded_chunks([
        ("Chunk on page 1.", [1.0, 0.0, 0.0]),
        ("Chunk on page 2.", [0.0, 1.0, 0.0]),
    ])
    store_embedded_chunks("source_pages", embedded, page_numbers={0: 1, 1: 2})

    collection = _get_collection("source_pages")
    result = collection.get(ids=["source_pages_0", "source_pages_1"], include=["metadatas"])
    page_numbers = {m["chunk_index"]: m["page_number"] for m in result["metadatas"]}
    assert page_numbers[0] == 1
    assert page_numbers[1] == 2


def test_store_defaults_page_number_to_unknown_marker(chroma_path):
    # ingest_text()/ingest_topic() sources have no real page concept —
    # page_numbers dict simply won't be provided for them.
    embedded = make_embedded_chunks([("No page info.", [1.0, 0.0, 0.0])])
    store_embedded_chunks("source_no_pages", embedded)

    collection = _get_collection("source_no_pages")
    result = collection.get(ids=["source_no_pages_0"], include=["metadatas"])
    assert result["metadatas"][0]["page_number"] == -1


def test_collection_name_sanitizes_special_characters(chroma_path):
    # source_ids are often UUIDs with hyphens — must not crash Chroma's
    # collection-name validation
    embedded = make_embedded_chunks([("Test content.", [1.0, 0.0, 0.0])])
    n = store_embedded_chunks("550e8400-e29b-41d4-a716-446655440000", embedded)
    assert n == 1
    assert source_chunk_count("550e8400-e29b-41d4-a716-446655440000") == 1


def test_delete_source_removes_collection(chroma_path):
    embedded = make_embedded_chunks([("Will be deleted.", [1.0, 0.0, 0.0])])
    store_embedded_chunks("source_to_delete", embedded)
    assert source_chunk_count("source_to_delete") == 1

    delete_source("source_to_delete")
    assert source_chunk_count("source_to_delete") == 0


def test_delete_nonexistent_source_is_a_safe_noop(chroma_path):
    # should not raise just because the source was never created
    delete_source("source_that_never_existed")


def test_sources_are_isolated_from_each_other(chroma_path):
    embedded_a = make_embedded_chunks([("Source A content.", [1.0, 0.0, 0.0])])
    embedded_b = make_embedded_chunks([
        ("Source B content one.", [0.0, 1.0, 0.0]),
        ("Source B content two.", [0.0, 0.0, 1.0]),
    ])
    store_embedded_chunks("source_isolated_a", embedded_a)
    store_embedded_chunks("source_isolated_b", embedded_b)

    assert source_chunk_count("source_isolated_a") == 1
    assert source_chunk_count("source_isolated_b") == 2


# ── MMR logic tests (real math, no mocking) ───────────────────────────────

def test_cosine_similarity_identical_vectors_is_one():
    v = np.array([1.0, 2.0, 3.0])
    assert _cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert _cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_handles_zero_vector_without_crashing():
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 1.0])
    assert _cosine_similarity(a, b) == 0.0


def test_mmr_first_pick_is_always_most_relevant():
    query = np.array([1.0, 0.0])
    candidates = [
        np.array([0.0, 1.0]),   # irrelevant
        np.array([0.99, 0.01]), # most relevant
        np.array([0.5, 0.5]),   # somewhat relevant
    ]
    order = _mmr_select(query, candidates, top_k=1, lambda_mult=0.5)
    assert order == [1]


def test_mmr_demotes_near_duplicates_at_balanced_lambda():
    """
    This is the regression test for the actual bug found during manual
    testing: at lambda=0.7 (the original default), three near-duplicate
    chunks ALL made it into the top-4 alongside only one genuinely
    distinct chunk, defeating the purpose of re-ranking entirely. At
    lambda=0.5, two of the three duplicates get swapped out for distinct
    content. This test locks in that lambda=0.5 actually produces
    diversity on a realistic-shaped candidate set, which is the whole
    reason DEFAULT_MMR_LAMBDA was changed from 0.7 to 0.5.
    """
    query = np.array([1.0, 0.0, 0.0, 0.0])
    candidates = [
        np.array([0.98, 0.05, 0.0, 0.0]),  # 0: near-dup A
        np.array([0.97, 0.04, 0.0, 0.0]),  # 1: near-dup B
        np.array([0.96, 0.06, 0.0, 0.0]),  # 2: near-dup C
        np.array([0.6, 0.6, 0.0, 0.0]),    # 3: moderately related
        np.array([0.5, 0.5, 0.3, 0.0]),    # 4: moderately related, different angle
        np.array([0.0, 0.0, 1.0, 0.0]),    # 5: unrelated topic A
        np.array([0.0, 0.0, 0.0, 1.0]),    # 6: unrelated topic B
    ]

    order_balanced = _mmr_select(query, candidates, top_k=4, lambda_mult=0.5)
    near_dup_indices = {0, 1, 2}
    near_dups_selected = len(set(order_balanced) & near_dup_indices)

    assert near_dups_selected <= 2, (
        f"Expected MMR at lambda=0.5 to demote at least one near-duplicate, "
        f"but {near_dups_selected}/3 duplicates were selected: {order_balanced}"
    )


def test_mmr_at_high_lambda_can_still_select_all_duplicates():
    # Documents the OTHER side of the same finding: high lambda really
    # does favor pure relevance over diversity, by design. This isn't a
    # bug at lambda=0.9 — it's the documented behavior of that parameter,
    # and the test exists so nobody "fixes" this case without realizing
    # it's intentional MMR behavior, not broken MMR behavior.
    query = np.array([1.0, 0.0, 0.0, 0.0])
    candidates = [
        np.array([0.98, 0.05, 0.0, 0.0]),
        np.array([0.97, 0.04, 0.0, 0.0]),
        np.array([0.96, 0.06, 0.0, 0.0]),
        np.array([0.0, 0.0, 1.0, 0.0]),
    ]
    order_high_relevance = _mmr_select(query, candidates, top_k=3, lambda_mult=0.95)
    near_dup_indices = {0, 1, 2}
    assert set(order_high_relevance) == near_dup_indices


def test_mmr_top_k_larger_than_candidates_returns_all():
    query = np.array([1.0, 0.0])
    candidates = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
    order = _mmr_select(query, candidates, top_k=10, lambda_mult=0.5)
    assert len(order) == 2


def test_mmr_empty_candidates_returns_empty():
    query = np.array([1.0, 0.0])
    assert _mmr_select(query, [], top_k=4, lambda_mult=0.5) == []


# ── Real Chroma query + MMR integration (no embed_query needed) ──────────

def test_chroma_query_plus_mmr_end_to_end_with_injected_vector(chroma_path):
    """
    Exercises the real Chroma similarity query AND the real MMR reranker
    together, using a hand-supplied query vector to stand in for what
    embed_query() would normally return. This is the strongest test we can
    run on the retrieval path without live Voyage API access — everything
    except the query embedding itself is real.
    """
    embedded = make_embedded_chunks([
        ("Convolution kernels detect edges.", [0.98, 0.05, 0.0, 0.0]),
        ("Convolution kernels detect local patterns.", [0.97, 0.04, 0.0, 0.0]),
        ("Pooling reduces feature map size.", [0.0, 1.0, 0.0, 0.0]),
        ("Backpropagation computes gradients.", [0.0, 0.0, 1.0, 0.0]),
    ])
    store_embedded_chunks("mmr_integration_source", embedded)

    query_vector = [0.9, 0.1, 0.0, 0.0]  # stands in for embed_query()'s output
    collection = _get_collection("mmr_integration_source")
    raw = collection.query(
        query_embeddings=[query_vector],
        n_results=4,
        include=["documents", "metadatas", "embeddings"],
    )

    candidate_vectors = [np.array(e) for e in raw["embeddings"][0]]
    mmr_order = _mmr_select(np.array(query_vector), candidate_vectors, top_k=3, lambda_mult=0.5)

    selected_docs = [raw["documents"][0][i] for i in mmr_order]
    # the two near-duplicate convolution chunks should NOT both survive
    # alongside each other at the top of a 3-result selection
    conv_count = sum(1 for d in selected_docs if "Convolution" in d)
    assert conv_count <= 1, f"Expected at most 1 convolution chunk in diverse top-3, got {conv_count}: {selected_docs}"


# ── format_context_for_prompt tests (pure logic) ──────────────────────────

def test_format_context_empty_list_returns_empty_string():
    assert format_context_for_prompt([]) == ""


def test_format_context_includes_page_number_when_present():
    chunks = [RetrievedChunk(text="Some text.", score=1.0, chunk_index=0, page_number=4, source_id="s1")]
    formatted = format_context_for_prompt(chunks)
    assert "page 4" in formatted
    assert "Some text." in formatted


def test_format_context_omits_page_tag_when_none():
    chunks = [RetrievedChunk(text="Some excerpt with no page metadata.", score=1.0, chunk_index=0, page_number=None, source_id="s1")]
    formatted = format_context_for_prompt(chunks)
    # the (page N) tag specifically should be absent — check for the tag
    # pattern, not the word "page" in isolation, since source text itself
    # may legitimately contain that word
    assert "(page" not in formatted
    assert "Some excerpt with no page metadata." in formatted


def test_format_context_joins_multiple_chunks():
    chunks = [
        RetrievedChunk(text="First chunk.", score=1.0, chunk_index=0, page_number=1, source_id="s1"),
        RetrievedChunk(text="Second chunk.", score=0.8, chunk_index=1, page_number=2, source_id="s1"),
    ]
    formatted = format_context_for_prompt(chunks)
    assert "First chunk." in formatted
    assert "Second chunk." in formatted


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))