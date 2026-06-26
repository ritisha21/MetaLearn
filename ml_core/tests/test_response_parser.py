"""
ml_core/tests/test_response_parser.py

Run with: python3 -m pytest ml_core/tests/test_response_parser.py -v

Pure-logic tests, no network/mocking needed at all — every case here was
verified by hand first before being written down as an assertion.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ml_core.tutor.response_parser import parse_tutor_response


def test_no_tags_returns_text_unchanged():
    raw = "Convolutional neural networks use filters to detect patterns in images."
    result = parse_tutor_response(raw)
    assert result.clean_text == raw
    assert result.meta_prompts == []
    assert result.misconceptions == []


def test_single_meta_tag_extracted_and_removed():
    raw = (
        "Convolution slides a kernel across the image.\n"
        "[META]: What surprised you about this?\n"
        "This produces a feature map highlighting detected patterns."
    )
    result = parse_tutor_response(raw)
    assert result.meta_prompts == ["What surprised you about this?"]
    assert "[META]" not in result.clean_text
    assert "What surprised you" not in result.clean_text
    assert "Convolution slides a kernel" in result.clean_text
    assert "feature map" in result.clean_text


def test_misconception_tag_with_no_trailing_newline_at_end_of_stream():
    # This is the exact edge case a naive \n-only regex misses: the tag is
    # the very last thing in the string, with no newline after it.
    raw = (
        "You said pooling increases resolution, but it actually decreases it.\n"
        "[MISCONCEPTION]: Learner believes pooling increases spatial resolution"
    )
    result = parse_tutor_response(raw)
    assert result.misconceptions == ["Learner believes pooling increases spatial resolution"]
    assert "[MISCONCEPTION]" not in result.clean_text


def test_both_tag_types_in_one_response():
    raw = (
        "Great question.\n"
        "[MISCONCEPTION]: Thinks backprop only updates the last layer\n"
        "Let me clarify how gradients flow backward through all layers.\n"
        "[META]: Can you predict what happens to early layers in a very deep network?"
    )
    result = parse_tutor_response(raw)
    assert result.meta_prompts == ["Can you predict what happens to early layers in a very deep network?"]
    assert result.misconceptions == ["Thinks backprop only updates the last layer"]
    assert "Great question." in result.clean_text
    assert "gradients flow backward" in result.clean_text


def test_response_that_is_only_a_tag_with_nothing_else():
    raw = "[META]: What do you think happens next?"
    result = parse_tutor_response(raw)
    assert result.meta_prompts == ["What do you think happens next?"]
    assert result.clean_text == ""


def test_empty_string_returns_empty_everything():
    result = parse_tutor_response("")
    assert result.clean_text == ""
    assert result.meta_prompts == []
    assert result.misconceptions == []


def test_multiple_misconceptions_in_one_response():
    raw = (
        "[MISCONCEPTION]: Thinks gradients flow forward\n"
        "[MISCONCEPTION]: Thinks pooling has learnable weights\n"
        "Let's clarify both of these."
    )
    result = parse_tutor_response(raw)
    assert len(result.misconceptions) == 2
    assert "Thinks gradients flow forward" in result.misconceptions
    assert "Thinks pooling has learnable weights" in result.misconceptions


def test_tag_removal_does_not_leave_excessive_blank_lines():
    raw = (
        "First paragraph here.\n"
        "[META]: A reflective question?\n"
        "Second paragraph here."
    )
    result = parse_tutor_response(raw)
    assert "\n\n\n" not in result.clean_text


def test_empty_tag_content_is_not_included_as_a_blank_prompt():
    # malformed/edge model output: a tag with nothing after the colon
    raw = "[META]: \nSome real text follows."
    result = parse_tutor_response(raw)
    assert result.meta_prompts == []  # empty content should be filtered, not kept as ''


def test_whitespace_around_tag_content_is_stripped():
    raw = "[META]:    What surprised you?   "
    result = parse_tutor_response(raw)
    assert result.meta_prompts == ["What surprised you?"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))