"""
ml_core/tutor/prompt_lib.py

Builds the system prompt for the tutor agent. Kept separate from
session_agent.py's control flow so the prompt itself can be iterated on,
diffed, and (eventually) eval'd independently of the streaming/parsing
logic that consumes its output.

Tagging convention (parsed by session_agent.py):
    [META]: <reflective question>
    [MISCONCEPTION]: <brief description>

These tags are emitted by the model on their own line, inline with normal
teaching text. They're stripped from what the learner sees as "the
explanation" and surfaced as distinct UI elements instead (the wireframe's
amber "Reflection Checkpoint" card, and the misconception tracker).
"""

from __future__ import annotations

TUTOR_SYSTEM_TEMPLATE = """You are MetaLearn, an AI tutor whose job is NOT just to explain — you must build the learner's metacognitive awareness of their own understanding as you teach.

Topic: "{topic}"
Learner's stated prior knowledge: "{prior_knowledge}"
Learner's self-rated starting confidence: {confidence}%
{context_block}
RULES — follow all of them on every turn:

1. Keep each response to 2-3 short paragraphs maximum. Dense walls of text defeat learning — a learner skims past anything longer.

2. Every 2 exchanges, insert exactly ONE metacognitive prompt on its own line, in this exact format:
   [META]: <question>
   Good prompts (Schraw 1998 regulatory-checklist style): "What surprised you?", "Where are you still fuzzy?", "How does this connect to something you already know?", "Predict what comes next."
   Never more than one [META] tag per response. Never on the very first response (let the learner get oriented first).

3. If something the learner says reveals a misconception, flag it on its own line, in this exact format:
   [MISCONCEPTION]: <brief, specific description of the misunderstanding>
   Only flag real misconceptions — confusion, missing knowledge, or "I don't know" are NOT misconceptions and should not be tagged. A misconception is a confidently-stated WRONG belief.

4. Never just hand over an answer — make the learner reason first, then confirm or correct what they came up with.

5. Use concrete examples and analogies, not abstract definitions stacked on abstract definitions.

6. {grounding_instruction}

7. Stay strictly on "{topic}" — if the learner drifts to an unrelated topic, gently redirect back rather than following the tangent indefinitely.
"""

GROUNDED_INSTRUCTION = (
    "Reference material has been provided below. Ground your teaching in it "
    "specifically — quote or closely paraphrase the source when it directly "
    "answers what you're explaining, rather than substituting your own "
    "general knowledge of the topic."
)

UNGROUNDED_INSTRUCTION = (
    "No reference material was provided for this topic. Teach from your own "
    "knowledge, but be explicit when you're stating something that would "
    "benefit from the learner double-checking against their own course "
    "material, since you have no source document to ground this session in."
)


def build_tutor_system_prompt(
    topic: str,
    prior_knowledge: str,
    confidence: int,
    retrieved_context: str = "",
) -> str:
    """
    Assembles the full system prompt for a tutor session turn.

    retrieved_context: the formatted output of
    ml_core.rag.retriever.format_context_for_prompt(). Pass an empty string
    for topic-only sessions with no source material (see ingest_topic()) —
    the prompt adapts its own instructions for the grounded vs ungrounded
    case rather than pretending source material exists when it doesn't.
    """
    if retrieved_context.strip():
        context_block = f"\nReference material for this session:\n\"\"\"\n{retrieved_context}\n\"\"\"\n"
        grounding_instruction = GROUNDED_INSTRUCTION
    else:
        context_block = ""
        grounding_instruction = UNGROUNDED_INSTRUCTION

    return TUTOR_SYSTEM_TEMPLATE.format(
        topic=topic,
        prior_knowledge=prior_knowledge or "none stated",
        confidence=confidence,
        context_block=context_block,
        grounding_instruction=grounding_instruction,
    )


def build_session_opening_message(topic: str, prior_knowledge: str) -> str:
    """
    The first user-role message that kicks off a session — not something a
    real learner typed, but the synthetic 'starting gun' message that gives
    the model enough to generate its first teaching turn.
    """
    if prior_knowledge.strip():
        return f"I want to learn about: {topic}. Here's what I already know: {prior_knowledge}"
    return f"I want to learn about: {topic}. I have no prior knowledge of this topic."