"""
ml_core/tutor/response_parser.py

Parses raw tutor-agent output into:
  - clean_text: what the learner sees as "the explanation" (tags removed)
  - meta_prompts: list of reflective questions to render as separate UI cards
  - misconceptions: list of flagged misconceptions

Kept as its own module (not inlined in session_agent.py) because parsing
correctness is exactly the kind of thing that's easy to assume works and
actually doesn't — multi-line tag content, tags with no trailing newline at
end-of-stream, multiple tags of the same type in one response. Each of
those is tested explicitly in test_response_parser.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Matches [META]: ... or [MISCONCEPTION]: ... up to the next newline OR end
# of string — the (?:\n|$) alternation is what makes end-of-stream (no
# trailing newline) work correctly, which a naive \n-only pattern misses.
#
# [ \t]* (not \s*) after the colon is deliberate: \s* would also match a
# newline, letting an empty "[META]: \n" tag's capture group bleed onto the
# FOLLOWING line of real teaching text and misidentify it as the prompt's
# content. Restricting to same-line whitespace only means a truly empty
# tag correctly captures nothing, instead of accidentally swallowing the
# next line. See test_empty_tag_content_is_not_included_as_a_blank_prompt.
_META_RE = re.compile(r"\[META\]:[ \t]*(.+?)(?:\n|$)")
_MISCONCEPTION_RE = re.compile(r"\[MISCONCEPTION\]:[ \t]*(.+?)(?:\n|$)")
_ANY_TAG_LINE_RE = re.compile(r"\[(META|MISCONCEPTION)\]:.+?(?:\n|$)")


@dataclass
class ParsedResponse:
    clean_text: str
    meta_prompts: list[str] = field(default_factory=list)
    misconceptions: list[str] = field(default_factory=list)


def parse_tutor_response(raw: str) -> ParsedResponse:
    """
    Extracts all [META] and [MISCONCEPTION] tagged lines from raw model
    output, returning the tag contents separately and the remaining text
    with those tag lines removed and whitespace normalized.
    """
    meta_prompts = [m.strip() for m in _META_RE.findall(raw) if m.strip()]
    misconceptions = [m.strip() for m in _MISCONCEPTION_RE.findall(raw) if m.strip()]

    clean = _ANY_TAG_LINE_RE.sub("", raw)
    # tag removal can leave behind runs of blank lines where the tag used
    # to sit — collapse those so clean_text reads naturally, not full of
    # gaps where a tag line used to be
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    clean = clean.strip()

    return ParsedResponse(clean_text=clean, meta_prompts=meta_prompts, misconceptions=misconceptions)
