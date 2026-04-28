"""LLMParser robust JSON parsing tests."""
from __future__ import annotations

import pytest

from backend2.schemas.profile import ProfileData, ResumeDocument
from backend2.services.profile.parser.llm_parser import (
    _looks_truncated,
    _robust_json_parse,
    _smart_truncate,
    _try_fix_truncated_json,
)


class TestRobustJsonParse:
    def test_plain_json(self):
        text = '{"name": "Zhang", "skills": []}'
        result, repaired = _robust_json_parse(text)
        assert result == {"name": "Zhang", "skills": []}
        assert repaired is False

    def test_json_in_markdown_fence(self):
        text = '```json\n{"name": "Zhang"}\n```'
        result, repaired = _robust_json_parse(text)
        assert result == {"name": "Zhang"}
        assert repaired is False

    def test_json_with_thinking_tags(self):
        text = '<think>Let me analyze this</think>\n{"name": "Zhang"}'
        result, repaired = _robust_json_parse(text)
        assert result == {"name": "Zhang"}
        assert repaired is False

    def test_json_with_thinking_tags_variant(self):
        text = '<thinking>some reasoning</thinking>\n{"name": "Zhang"}'
        result, repaired = _robust_json_parse(text)
        assert result == {"name": "Zhang"}
        assert repaired is False

    def test_json_with_reasoning_tags(self):
        text = '<reasoning>analysis</reasoning>\n{"name": "Zhang"}'
        result, repaired = _robust_json_parse(text)
        assert result == {"name": "Zhang"}
        assert repaired is False

    def test_text_before_and_after_json(self):
        text = 'Here is the result:\n{"name": "Zhang"}\nHope this helps!'
        result, repaired = _robust_json_parse(text)
        assert result == {"name": "Zhang"}
        assert repaired is False

    def test_empty_string(self):
        result, repaired = _robust_json_parse("")
        assert result is None
        assert repaired is False

    def test_no_json(self):
        result, repaired = _robust_json_parse("Just some text without json")
        assert result is None
        assert repaired is False

    def test_truncated_json_detected_and_fixed(self):
        text = '{"name": "Zhang", "skills": ["Python"'
        assert _looks_truncated(text) is True
        fixed = _try_fix_truncated_json(text)
        assert fixed is not None
        result, repaired = _robust_json_parse(text)
        assert result is not None
        assert result.get("name") == "Zhang"
        assert repaired is True

    def test_truncated_object(self):
        text = '{"name": "Zhang", "education": [{"school": "THU"'
        assert _looks_truncated(text) is True

    def test_complete_json_not_truncated(self):
        text = '{"name": "Zhang", "skills": ["Python"]}'
        assert _looks_truncated(text) is False

    def test_unclosed_string_truncated(self):
        text = '{"name": "Zhang'
        assert _looks_truncated(text) is True


class TestSmartTruncate:
    def test_short_text_unchanged(self):
        text = "short"
        assert _smart_truncate(text, 100) == "short"

    def test_long_text_truncated(self):
        text = "a" * 10000
        result = _smart_truncate(text, 100)
        assert len(result) == 100
        assert result == "a" * 100


class TestLooksTruncated:
    def test_trailing_quote(self):
        assert _looks_truncated('{"name": "') is True

    def test_trailing_colon(self):
        assert _looks_truncated('{"name":') is True

    def test_trailing_comma(self):
        assert _looks_truncated('{"name": "Zhang",') is True

    def test_unbalanced_braces(self):
        assert _looks_truncated('{"name": "Zhang"') is True

    def test_unbalanced_brackets(self):
        assert _looks_truncated('[1, 2, 3') is True

    def test_balanced_complete(self):
        assert _looks_truncated('{"name": "Zhang"}') is False

    def test_empty(self):
        assert _looks_truncated("") is False


class TestTryFixTruncatedJson:
    def test_fix_unclosed_braces(self):
        fixed = _try_fix_truncated_json('{"name": "Zhang"')
        assert fixed == '{"name": "Zhang"}'

    def test_fix_unclosed_brackets(self):
        fixed = _try_fix_truncated_json('[1, 2, 3')
        assert fixed == '[1, 2, 3]'

    def test_fix_both(self):
        fixed = _try_fix_truncated_json('{"skills": ["Python"')
        assert '"skills": ["Python"]' in fixed
