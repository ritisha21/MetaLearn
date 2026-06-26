"""
ml_core/tutor/session_agent.py

The live "AI Tutor Chat" from the wireframe. Orchestrates a streaming
Claude conversation grounded (optionally) in retrieved RAG context, and
parses each response into clean teaching text + meta-prompts +
misconceptions for the UI to render separately.

Design notes:

State lives OUTSIDE the agent. SessionAgent does not own a database
connection, does not persist conversation history itself, and does not
know about source_ids or Chroma. It takes a conversation history in
(plain list of {"role", "content"} dicts) and returns new turns out. This
keeps it testable with zero database/network setup beyond mocking the
Claude client itself, and means the FastAPI layer — not this module —
owns the actual persistence decision (Postgres, Supabase, wherever).

Streaming, not single-shot. The wireframe shows a live chat UI, not a
spinner-then-blob. send_message() is a generator that yields raw text
tokens as they arrive, then a final ParsedResponse once the stream
completes — callers can render tokens live and only deal with structured
meta/misconception data after the full response is in.

Retry behavior mirrors embeddings.py's Voyage retry logic by design — same
shape of problem (transient vs permanent API errors), same fix. See that
module's docstring for the reasoning; it isn't repeated here in full.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Iterator

try:
    import anthropic
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        RateLimitError,
        OverloadedError,
        AuthenticationError,
        BadRequestError,
        AnthropicError,
    )
except ImportError:
    anthropic = None

from ml_core.tutor.prompt_lib import build_tutor_system_prompt, build_session_opening_message
from ml_core.tutor.response_parser import parse_tutor_response, ParsedResponse

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TOKENS = 1000
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.5

# Errors worth retrying with backoff — all transient by nature.
_RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, OverloadedError) if anthropic else ()


class TutorAgentError(Exception):
    """Raised for failures that are NOT worth retrying, or for retries
    exhausted. Always carries a specific reason."""


@dataclass
class SessionTurn:
    """One complete tutor response, after streaming finishes and parsing
    has run. role is always 'assistant' here — this represents OUR output,
    not the learner's input."""
    parsed: ParsedResponse
    raw_text: str  # unparsed, for storing the true model output in history


def _get_client() -> "anthropic.Anthropic":
    if anthropic is None:
        raise TutorAgentError(
            "anthropic package is not installed. Run `pip install anthropic` to enable the tutor agent."
        )
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise TutorAgentError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env — the tutor agent cannot run without it."
        )
    return anthropic.Anthropic(api_key=api_key, max_retries=0)  # we handle retries ourselves, deliberately


class SessionAgent:
    """
    One instance per learning session. Holds the system prompt (built once,
    at session start, from topic/prior-knowledge/confidence/RAG-context) and
    exposes send_message() to advance the conversation turn by turn.

    Conversation history is passed in and mutated by the caller between
    calls — this class does not retain it internally between calls, so a
    FastAPI request handler can rehydrate a SessionAgent fresh on every
    request from whatever's stored in the database, rather than needing a
    long-lived in-memory session object.
    """

    def __init__(
        self,
        topic: str,
        prior_knowledge: str = "",
        confidence: int = 50,
        retrieved_context: str = "",
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        self.topic = topic
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = build_tutor_system_prompt(
            topic=topic,
            prior_knowledge=prior_knowledge,
            confidence=confidence,
            retrieved_context=retrieved_context,
        )

    def build_opening_history(self, prior_knowledge: str = "") -> list[dict]:
        """Returns the initial single-message history that kicks off a
        session, before any real learner input exists yet."""
        opening = build_session_opening_message(self.topic, prior_knowledge)
        return [{"role": "user", "content": opening}]

    def stream_message(self, history: list[dict]) -> Iterator[str]:
        """
        Sends `history` to Claude and yields raw text tokens as they
        stream in. Does NOT parse or append to history — that's the
        caller's job, using the accumulated text after this generator
        is exhausted (see send_message() for the non-streaming-friendly
        wrapper that does both steps for you).

        Retries transient errors before the stream starts. Once a stream
        has actually begun emitting tokens, we do NOT retry mid-stream —
        a partial response retried from scratch would silently duplicate
        or corrupt whatever the caller already rendered to the learner.
        """
        client = _get_client()
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                with client.messages.stream(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=self.system_prompt,
                    messages=history,
                ) as stream:
                    for text in stream.text_stream:
                        yield text
                return  # stream completed successfully
            except _RETRYABLE_ERRORS as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BASE_BACKOFF_SECONDS * (2 ** attempt))
                continue
            except AuthenticationError as e:
                raise TutorAgentError(f"Claude API authentication failed — check ANTHROPIC_API_KEY: {e}") from e
            except BadRequestError as e:
                raise TutorAgentError(f"Claude API rejected the request: {e}") from e
            except AnthropicError as e:
                raise TutorAgentError(f"Claude API error: {e}") from e

        raise TutorAgentError(
            f"Tutor agent failed after {MAX_RETRIES} retries (rate limit, timeout, or overload). "
            f"Last error: {last_error}"
        )

    def send_message(self, history: list[dict]) -> SessionTurn:
        """
        Convenience wrapper for non-streaming callers (e.g. tests, batch
        eval scripts): consumes the full stream, parses the result, and
        returns a SessionTurn. Real-time UI callers should use
        stream_message() directly instead and parse only after exhausting it.
        """
        full_text = "".join(self.stream_message(history))
        parsed = parse_tutor_response(full_text)
        return SessionTurn(parsed=parsed, raw_text=full_text)