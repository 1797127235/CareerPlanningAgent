# tests/test_quick_gaps.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_quick_gaps_basic():
    from backend.plan_adapter import quick_gaps_logic
    user_skills = {"python", "javascript", "html", "css"}
    # weights: Python=5, JavaScript=4, React=3, TypeScript=2, Webpack=1 → total=15
    required = ["Python", "JavaScript", "React", "TypeScript", "Webpack"]
    result = quick_gaps_logic(user_skills, required)
    # matched: Python(5) + JavaScript(4) = 9/15 = 60%
    assert result["match_score"] == 60
    assert "Python" in result["matched_skills"]
    assert "JavaScript" in result["matched_skills"]
    assert len(result["skill_gaps"]) == 3
    # React has highest weight (3) among missing → sorted first with highest delta
    assert result["skill_gaps"][0]["skill"] == "React"
    assert result["skill_gaps"][0]["match_delta"] == 20  # (9+3)/15=80% - 60% = 20%
    assert result["skill_gaps"][0]["match_if_learned"] == 80
    # Each gap should have match_delta > 0
    for g in result["skill_gaps"]:
        assert g["match_delta"] > 0
        assert "match_if_learned" in g


def test_quick_gaps_all_matched():
    from backend.plan_adapter import quick_gaps_logic
    user_skills = {"react", "typescript"}
    required = ["React", "TypeScript"]
    result = quick_gaps_logic(user_skills, required)
    assert result["match_score"] == 100
    assert len(result["skill_gaps"]) == 0


def test_quick_gaps_empty_profile():
    from backend.plan_adapter import quick_gaps_logic
    result = quick_gaps_logic(set(), ["React"])
    assert result["match_score"] == 0
    assert len(result["skill_gaps"]) == 1


def test_quick_gaps_empty_node():
    from backend.plan_adapter import quick_gaps_logic
    result = quick_gaps_logic({"python"}, [])
    assert result["match_score"] == 0
