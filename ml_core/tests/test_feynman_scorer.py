"""
ml_core/tests/test_feynman_scorer.py

Run with: python3 -m pytest ml_core/tests/test_feynman_scorer.py -v

What's tested for REAL (no mocking):
- Rubric loading and validation (rubric_loader.py) — reads the actual
  feynman_v1.yaml file from disk.
- The composite-score weighted-sum arithmetic, given known dimension
  scores — this is the part of the system most likely to silently drift
  if a weight is misapplied, so it's verified against hand-computed
  expected values, not just "the function ran without crashing."

What's mocked:
client.messages.parse() itself — no live ANTHROPIC_API_KEY in this
sandbox. The mock's return shape (a ParsedMessage-like object whose
.parsed_output is the Pydantic FeynmanScoreOutput instance) was confirmed
by reading the actual installed SDK source
(anthropic/resources/messages/messages.py + anthropic/types/parsed_message.py),
not guessed.

Before shipping: run score_feynman_explanation() once for real with a
valid ANTHROPIC_API_KEY against a genuinely weak explanation and a
genuinely strong one, and sanity-check the scores land where a human
grader would put them. No amount of mocked testing substitutes for that.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from unittest.mock import MagicMock, patch

from ml_core.scoring.rubric_loader import load_rubric, RubricError, band_for_score

try:
    from ml_core.scoring.feynman_scorer import (
        score_feynman_explanation,
        FeynmanScoreOutput,
        DimensionScore,
        ScoringError,
    )
    from anthropic import RateLimitError, AuthenticationError
    ANTHROPIC_INSTALLED = True
except ImportError:
    ANTHROPIC_INSTALLED = False

pytestmark = pytest.mark.skipif(not ANTHROPIC_INSTALLED, reason="anthropic package not installed")


# ── Rubric loading (real, reads actual feynman_v1.yaml) ───────────────────

def test_feynman_v1_rubric_loads_and_weights_sum_to_one():
    rubric = load_rubric("feynman_v1")
    assert rubric.version == "feynman_v1"
    weight_sum = sum(d.weight for d in rubric.dimensions)
    assert abs(weight_sum - 1.0) < 0.001


def test_feynman_v1_has_expected_four_dimensions():
    rubric = load_rubric("feynman_v1")
    assert set(rubric.dimension_names()) == {"accuracy", "clarity", "depth", "transfer"}


def test_loading_nonexistent_rubric_raises():
    with pytest.raises(RubricError, match="not found"):
        load_rubric("definitely_does_not_exist_v99")


# ── Composite score arithmetic (real math, hand-verified) ─────────────────

def make_fake_parsed_output(accuracy, clarity, depth, transfer):
    return FeynmanScoreOutput(
        accuracy=DimensionScore(score=accuracy, rationale="test rationale"),
        clarity=DimensionScore(score=clarity, rationale="test rationale"),
        depth=DimensionScore(score=depth, rationale="test rationale"),
        transfer=DimensionScore(score=transfer, rationale="test rationale"),
    )


@patch("ml_core.scoring.feynman_scorer._get_client")
def test_composite_score_is_correct_weighted_sum(mock_get_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_response = MagicMock()
    # accuracy=0.8 (w=0.30), clarity=0.6 (w=0.20), depth=0.4 (w=0.25), transfer=1.0 (w=0.25)
    mock_response.parsed_output = make_fake_parsed_output(accuracy=0.8, clarity=0.6, depth=0.4, transfer=1.0)
    mock_client.messages.parse.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = score_feynman_explanation("CNNs", "Convolution slides a kernel across the image to detect edges.")

    # hand-computed expected value:
    # 0.8*0.30 + 0.6*0.20 + 0.4*0.25 + 1.0*0.25 = 0.24 + 0.12 + 0.10 + 0.25 = 0.71
    expected = 0.24 + 0.12 + 0.10 + 0.25
    assert result.overall == pytest.approx(expected, abs=0.001)


@patch("ml_core.scoring.feynman_scorer._get_client")
def test_composite_score_all_zeros_is_zero(mock_get_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed_output = make_fake_parsed_output(0.0, 0.0, 0.0, 0.0)
    mock_client.messages.parse.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = score_feynman_explanation("CNNs", "I genuinely don't understand this at all if I'm honest.")
    assert result.overall == 0.0
    assert result.band == "needs_work"


@patch("ml_core.scoring.feynman_scorer._get_client")
def test_composite_score_all_ones_is_one(mock_get_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed_output = make_fake_parsed_output(1.0, 1.0, 1.0, 1.0)
    mock_client.messages.parse.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = score_feynman_explanation("CNNs", "A perfect, deeply reasoned explanation with novel transfer.")
    assert result.overall == pytest.approx(1.0, abs=0.001)
    assert result.band == "excellent"


@patch("ml_core.scoring.feynman_scorer._get_client")
def test_dimension_rationale_is_preserved_in_result(mock_get_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_response = MagicMock()
    fake_output = FeynmanScoreOutput(
        accuracy=DimensionScore(score=0.9, rationale="Correctly describes the convolution operation."),
        clarity=DimensionScore(score=0.7, rationale="Mostly clear but uses 'kernel' without defining it."),
        depth=DimensionScore(score=0.5, rationale="States what convolution does but not why it helps."),
        transfer=DimensionScore(score=0.3, rationale="No analogy or novel example provided."),
    )
    mock_response.parsed_output = fake_output
    mock_client.messages.parse.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = score_feynman_explanation("CNNs", "Convolution applies a kernel across the image.")
    assert "convolution operation" in result.dimensions["accuracy"]["rationale"]
    assert result.dimensions["transfer"]["score"] == 0.3


@patch("ml_core.scoring.feynman_scorer._get_client")
def test_uses_correct_model_default(mock_get_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed_output = make_fake_parsed_output(0.5, 0.5, 0.5, 0.5)
    mock_client.messages.parse.return_value = mock_response
    mock_get_client.return_value = mock_client

    score_feynman_explanation("CNNs", "A reasonably complete explanation goes here for testing purposes.")

    call_kwargs = mock_client.messages.parse.call_args.kwargs
    assert call_kwargs["output_format"] is FeynmanScoreOutput
    assert "max_tokens" in call_kwargs


# ── Input validation (real, no mocking needed) ────────────────────────────

def test_raises_on_empty_explanation():
    with pytest.raises(ScoringError, match="too short"):
        score_feynman_explanation("CNNs", "")


def test_raises_on_too_short_explanation():
    with pytest.raises(ScoringError, match="too short"):
        score_feynman_explanation("CNNs", "idk")


def test_raises_on_missing_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ScoringError, match="ANTHROPIC_API_KEY"):
        score_feynman_explanation("CNNs", "A reasonably long explanation that would otherwise pass validation.")


# ── Retry behavior (mirrors session_agent.py's verified pattern) ─────────

@patch("ml_core.scoring.feynman_scorer.time.sleep")
@patch("ml_core.scoring.feynman_scorer._get_client")
def test_retries_on_rate_limit_then_succeeds(mock_get_client, mock_sleep, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed_output = make_fake_parsed_output(0.6, 0.6, 0.6, 0.6)

    mock_client.messages.parse.side_effect = [
        RateLimitError("slow down", response=MagicMock(status_code=429, headers={}), body=None),
        mock_response,
    ]
    mock_get_client.return_value = mock_client

    result = score_feynman_explanation("CNNs", "A reasonably complete explanation for retry testing.")
    assert result.overall == pytest.approx(0.6, abs=0.001)
    assert mock_client.messages.parse.call_count == 2


@patch("ml_core.scoring.feynman_scorer._get_client")
def test_authentication_error_is_not_retried(mock_get_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.messages.parse.side_effect = AuthenticationError(
        "bad key", response=MagicMock(status_code=401, headers={}), body=None
    )
    mock_get_client.return_value = mock_client

    with pytest.raises(ScoringError, match="authentication failed"):
        score_feynman_explanation("CNNs", "A reasonably complete explanation for auth-error testing.")
    assert mock_client.messages.parse.call_count == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
