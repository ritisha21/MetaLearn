"""
ml_core/tests/test_session_agent.py

Run with: python3 -m pytest ml_core/tests/test_session_agent.py -v

IMPORTANT — what these tests do and don't prove:
This sandbox has no ANTHROPIC_API_KEY configured, so no test here makes a
real call to the Claude API. Every test mocks
ml_core.tutor.session_agent._get_client to return a fake client whose
.messages.stream(...) context manager yields a scripted text_stream.

The mock's shape was NOT guessed — it was built by reading the actual
installed anthropic SDK source (anthropic/lib/streaming/_messages.py) to
confirm that MessageStream.text_stream really is a plain Python generator
assigned as an instance attribute in __init__, yielding bare text-delta
strings. That source-reading step is what these tests rest on; it is not
a substitute for a real end-to-end call.

Before shipping: run session_agent.py's stream_message() once for real
against a live ANTHROPIC_API_KEY to confirm the actual API still matches
this SDK version's documented streaming contract.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

from ml_core.tutor.session_agent import SessionAgent, TutorAgentError, MAX_RETRIES

try:
    from anthropic import RateLimitError, APIConnectionError, AuthenticationError, BadRequestError
    ANTHROPIC_INSTALLED = True
except ImportError:
    ANTHROPIC_INSTALLED = False

pytestmark = pytest.mark.skipif(not ANTHROPIC_INSTALLED, reason="anthropic package not installed")


def make_fake_stream_manager(tokens: list[str]):
    """
    Builds a fake object that mimics MessageStreamManager's real contract:
    used as `with client.messages.stream(...) as stream:`, where `stream`
    has a .text_stream attribute that's an iterator of plain text tokens.
    This mirrors the verified-by-reading-source shape, not a guess.
    """
    @contextmanager
    def fake_stream(**kwargs):
        fake_stream_obj = MagicMock()
        fake_stream_obj.text_stream = iter(tokens)
        yield fake_stream_obj

    return fake_stream


def make_error_raising_stream(error_to_raise):
    @contextmanager
    def fake_stream(**kwargs):
        raise error_to_raise
        yield  # unreachable, but needed for generator shape

    return fake_stream


# ── Basic streaming behavior ────────────────────────────────────────────

@patch("ml_core.tutor.session_agent._get_client")
def test_stream_message_yields_tokens_in_order(mock_get_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.messages.stream = make_fake_stream_manager(["Convolution ", "slides ", "a kernel."])
    mock_get_client.return_value = mock_client

    agent = SessionAgent(topic="CNNs", confidence=50)
    history = agent.build_opening_history()
    tokens = list(agent.stream_message(history))

    assert tokens == ["Convolution ", "slides ", "a kernel."]


@patch("ml_core.tutor.session_agent._get_client")
def test_send_message_concatenates_and_parses(mock_get_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.messages.stream = make_fake_stream_manager([
        "Convolution detects patterns.\n",
        "[META]: What surprised you?",
    ])
    mock_get_client.return_value = mock_client

    agent = SessionAgent(topic="CNNs", confidence=50)
    history = agent.build_opening_history()
    turn = agent.send_message(history)

    assert "Convolution detects patterns." in turn.parsed.clean_text
    assert turn.parsed.meta_prompts == ["What surprised you?"]
    assert turn.raw_text == "Convolution detects patterns.\n[META]: What surprised you?"


# ── System prompt construction ────────────────────────────────────────────

def test_system_prompt_includes_topic_and_confidence():
    agent = SessionAgent(topic="Backpropagation", prior_knowledge="some calculus", confidence=65)
    assert "Backpropagation" in agent.system_prompt
    assert "65%" in agent.system_prompt
    assert "some calculus" in agent.system_prompt


def test_system_prompt_grounded_mode_when_context_provided():
    agent = SessionAgent(topic="CNNs", retrieved_context="Convolution slides a kernel across pixels.")
    assert "Reference material" in agent.system_prompt
    assert "Convolution slides a kernel" in agent.system_prompt


def test_system_prompt_ungrounded_mode_when_no_context():
    agent = SessionAgent(topic="CNNs", retrieved_context="")
    assert "No reference material was provided" in agent.system_prompt


def test_opening_history_includes_prior_knowledge_when_given():
    agent = SessionAgent(topic="CNNs")
    history = agent.build_opening_history(prior_knowledge="I know about edge detection")
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert "edge detection" in history[0]["content"]


def test_opening_history_states_no_prior_knowledge_when_empty():
    agent = SessionAgent(topic="CNNs")
    history = agent.build_opening_history(prior_knowledge="")
    assert "no prior knowledge" in history[0]["content"].lower()


# ── Missing key / missing package ─────────────────────────────────────────

def test_stream_message_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = SessionAgent(topic="CNNs")
    history = agent.build_opening_history()
    with pytest.raises(TutorAgentError, match="ANTHROPIC_API_KEY"):
        list(agent.stream_message(history))


# ── Retry behavior ──────────────────────────────────────────────────────────

@patch("ml_core.tutor.session_agent.time.sleep")
@patch("ml_core.tutor.session_agent._get_client")
def test_retries_on_rate_limit_then_succeeds(mock_get_client, mock_sleep, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()

    call_count = {"n": 0}

    @contextmanager
    def flaky_stream(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RateLimitError("slow down", response=MagicMock(status_code=429, headers={}), body=None)
        fake_stream_obj = MagicMock()
        fake_stream_obj.text_stream = iter(["Recovered after retry."])
        yield fake_stream_obj

    mock_client.messages.stream = flaky_stream
    mock_get_client.return_value = mock_client

    agent = SessionAgent(topic="CNNs")
    history = agent.build_opening_history()
    tokens = list(agent.stream_message(history))

    assert tokens == ["Recovered after retry."]
    assert call_count["n"] == 2
    assert mock_sleep.called


@patch("ml_core.tutor.session_agent.time.sleep")
@patch("ml_core.tutor.session_agent._get_client")
def test_exhausts_retries_and_raises(mock_get_client, mock_sleep, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.messages.stream = make_error_raising_stream(
        APIConnectionError(request=MagicMock())
    )
    mock_get_client.return_value = mock_client

    agent = SessionAgent(topic="CNNs")
    history = agent.build_opening_history()
    with pytest.raises(TutorAgentError, match="after .* retries"):
        list(agent.stream_message(history))


@patch("ml_core.tutor.session_agent._get_client")
def test_authentication_error_is_not_retried(mock_get_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.messages.stream = make_error_raising_stream(
        AuthenticationError("bad key", response=MagicMock(status_code=401, headers={}), body=None)
    )
    mock_get_client.return_value = mock_client

    agent = SessionAgent(topic="CNNs")
    history = agent.build_opening_history()
    with pytest.raises(TutorAgentError, match="authentication failed"):
        list(agent.stream_message(history))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))