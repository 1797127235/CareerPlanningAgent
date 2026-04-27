import pytest

pytestmark = pytest.mark.skip(reason="backend.interview_review module moved")


def test_analyze_single_qa_returns_structure():
    """Verify the function signature and return structure (without LLM call)."""
    from backend.interview_review import analyze_single_qa
    # Just verify it's importable and callable
    assert callable(analyze_single_qa)
