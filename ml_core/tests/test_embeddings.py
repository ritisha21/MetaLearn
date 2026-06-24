"""
ml_core/tests/test_embeddings.py

Run with: python3 -m pytest ml_core/tests/test_embeddings.py -v

IMPORTANT — what these tests do and don't prove:
This sandbox has no network access to api.voyageai.com, so none of these
tests make a real API call. Every test below mocks ml_core.rag.embeddings._get_client
to return a fake client with a scripted .embed() method. That means these
tests verify:
  - batching math (chunk lists split into correct-sized groups)
  - retry control flow (RateLimitError/APIConnectionError retried, others not)
  - error message construction and EmbeddingError wrapping
  - the document vs query input_type distinction is actually passed through

These tests do NOT verify:
  - that voyageai.Client.embed() really behaves the way the mock assumes
  - real network/auth/rate-limit behavior against the live Voyage API
  - real embedding vector quality or dimensionality

Before shipping, run a real embed_query() call once against the live API
with a valid VOYAGE_API_KEY to confirm the actual SDK contract matches
what's mocked here.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from unittest.mock import MagicMock, patch

from ml_core.rag.chunker import Chunk
from ml_core.rag import embeddings as emb_module
from ml_core.rag.embeddings import (
    embed_chunks,
    embed_query,
    expected_dimensions,
    EmbeddingError,
)

try:
    from voyageai.error import RateLimitError, APIConnectionError, AuthenticationError, InvalidRequestError
    VOYAGE_INSTALLED = True
except ImportError:
    VOYAGE_INSTALLED = False

pytestmark = pytest.mark.skipif(not VOYAGE_INSTALLED, reason="voyageai package not installed")


def make_chunks(n: int) -> list[Chunk]:
    return [
        Chunk(text=f"chunk number {i}", index=i, token_count=4, char_start=i * 10, char_end=i * 10 + 9)
        for i in range(n)
    ]


def fake_embed_result(n_vectors: int, dim: int = 512):
    """Mimics voyageai's EmbeddingsObject.embeddings shape: list of float lists."""
    result = MagicMock()
    result.embeddings = [[0.1] * dim for _ in range(n_vectors)]
    return result


# ── Missing key / missing package ─────────────────────────────────────────

def test_embed_query_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    with pytest.raises(EmbeddingError, match="VOYAGE_API_KEY"):
        embed_query("what is backpropagation")


def test_embed_chunks_returns_empty_list_for_empty_input():
    # should short-circuit before even checking for an API key
    assert embed_chunks([]) == []


# ── Batching math ──────────────────────────────────────────────────────────

@patch("ml_core.rag.embeddings._get_client")
def test_embed_chunks_batches_correctly(mock_get_client, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.embed.side_effect = lambda texts, **kw: fake_embed_result(len(texts))
    mock_get_client.return_value = mock_client

    chunks = make_chunks(10)
    result = embed_chunks(chunks, batch_size=4)

    # 10 chunks at batch_size=4 -> batches of [4, 4, 2] -> 3 calls total
    assert mock_client.embed.call_count == 3
    call_sizes = [len(call.kwargs["texts"]) for call in mock_client.embed.call_args_list]
    assert call_sizes == [4, 4, 2]
    assert len(result) == 10


@patch("ml_core.rag.embeddings._get_client")
def test_embed_chunks_preserves_chunk_order_and_pairing(mock_get_client, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()

    def fake_embed(texts, **kw):
        # return distinguishable vectors so we can verify pairing, not just counts
        result = MagicMock()
        result.embeddings = [[float(i)] for i in range(len(texts))]
        return result

    mock_client.embed.side_effect = fake_embed
    mock_get_client.return_value = mock_client

    chunks = make_chunks(5)
    result = embed_chunks(chunks, batch_size=5)

    for i, embedded in enumerate(result):
        assert embedded.chunk.index == i
        assert embedded.vector == [float(i)]


@patch("ml_core.rag.embeddings._get_client")
def test_embed_chunks_uses_document_input_type(mock_get_client, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.embed.side_effect = lambda texts, **kw: fake_embed_result(len(texts))
    mock_get_client.return_value = mock_client

    embed_chunks(make_chunks(2))

    call_kwargs = mock_client.embed.call_args.kwargs
    assert call_kwargs["input_type"] == "document"


@patch("ml_core.rag.embeddings._get_client")
def test_embed_query_uses_query_input_type(mock_get_client, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.embed.side_effect = lambda texts, **kw: fake_embed_result(len(texts))
    mock_get_client.return_value = mock_client

    embed_query("what is pooling")

    call_kwargs = mock_client.embed.call_args.kwargs
    assert call_kwargs["input_type"] == "query"


def test_embed_query_raises_on_empty_string(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    with pytest.raises(EmbeddingError, match="empty query"):
        embed_query("   ")


# ── Mismatch detection ─────────────────────────────────────────────────────

@patch("ml_core.rag.embeddings._get_client")
def test_embed_chunks_raises_on_vector_count_mismatch(mock_get_client, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    # deliberately return fewer vectors than chunks sent — simulates a
    # malformed/partial API response
    mock_client.embed.side_effect = lambda texts, **kw: fake_embed_result(len(texts) - 1)
    mock_get_client.return_value = mock_client

    with pytest.raises(EmbeddingError, match="mismatch"):
        embed_chunks(make_chunks(3))


# ── Retry behavior ──────────────────────────────────────────────────────────

@patch("ml_core.rag.embeddings.time.sleep")  # don't actually sleep in tests
@patch("ml_core.rag.embeddings._get_client")
def test_retries_on_rate_limit_then_succeeds(mock_get_client, mock_sleep, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.embed.side_effect = [
        RateLimitError("slow down"),
        fake_embed_result(1),
    ]
    mock_get_client.return_value = mock_client

    vec = embed_query("test query")
    assert mock_client.embed.call_count == 2
    assert mock_sleep.called  # backoff was applied


@patch("ml_core.rag.embeddings.time.sleep")
@patch("ml_core.rag.embeddings._get_client")
def test_exhausts_retries_and_raises_embedding_error(mock_get_client, mock_sleep, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.embed.side_effect = APIConnectionError("network down")
    mock_get_client.return_value = mock_client

    with pytest.raises(EmbeddingError, match="after .* retries"):
        embed_query("test query")
    assert mock_client.embed.call_count == emb_module.MAX_RETRIES


@patch("ml_core.rag.embeddings._get_client")
def test_authentication_error_is_not_retried(mock_get_client, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.embed.side_effect = AuthenticationError("bad key")
    mock_get_client.return_value = mock_client

    with pytest.raises(EmbeddingError, match="authentication failed"):
        embed_query("test query")
    # should fail immediately on first attempt, not retry 3 times
    assert mock_client.embed.call_count == 1


@patch("ml_core.rag.embeddings._get_client")
def test_invalid_request_error_is_not_retried(mock_get_client, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.embed.side_effect = InvalidRequestError("malformed input")
    mock_get_client.return_value = mock_client

    with pytest.raises(EmbeddingError, match="rejected the request"):
        embed_query("test query")
    assert mock_client.embed.call_count == 1


# ── Dimension lookup (pure logic, no client needed) ───────────────────────

def test_expected_dimensions_known_models():
    assert expected_dimensions("voyage-3-lite") == 512
    assert expected_dimensions("voyage-3") == 1024


def test_expected_dimensions_raises_on_unknown_model():
    with pytest.raises(EmbeddingError, match="Unknown model"):
        expected_dimensions("voyage-nonexistent")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))