"""Quality scoring tests."""
from __future__ import annotations

from backend2.schemas.profile import Education, ProfileData, Skill
from backend2.services.profile.parser.quality import score_profile


class TestScoreProfile:
    def test_empty_profile(self):
        profile = ProfileData()
        meta = score_profile(profile)
        assert meta.quality_score == 0
        assert all(v is False for v in meta.quality_checks.values())

    def test_complete_profile(self):
        profile = ProfileData(
            name="Zhang",
            job_target_text="Backend Dev",
            education=[Education(school="THU")],
            skills=[Skill(name="Python")],
            projects=[{"name": "Proj", "description": "Desc"}],
            internships=[{"company": "BD", "role": "Dev"}],
            awards=["Award"],
            raw_text="some text",
        )
        meta = score_profile(profile)
        assert meta.quality_score == 100
        assert all(v is True for v in meta.quality_checks.values())

    def test_partial_profile(self):
        profile = ProfileData(
            name="Zhang",
            skills=[Skill(name="Python")],
            raw_text="text",
        )
        meta = score_profile(profile)
        assert meta.quality_score == 37
        assert meta.quality_checks["has_name"] is True
        assert meta.quality_checks["has_skills"] is True
        assert meta.quality_checks["has_education"] is False

    def test_certificate_counts_as_awards_or_certificates(self):
        profile = ProfileData(
            name="Zhang",
            certificates=["CET-4"],
        )
        meta = score_profile(profile)
        assert meta.quality_checks["has_awards_or_certificates"] is True

    def test_no_name_no_skills(self):
        profile = ProfileData(
            education=[Education(school="THU")],
            raw_text="text",
        )
        meta = score_profile(profile)
        assert meta.quality_checks["has_name"] is False
        assert meta.quality_checks["has_education"] is True
