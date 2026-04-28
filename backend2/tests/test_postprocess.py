"""Postprocess tests."""
from __future__ import annotations

from backend2.schemas.profile import (
    Education,
    Internship,
    ProfileData,
    Project,
    ResumeDocument,
    Skill,
)
from backend2.services.profile.parser.postprocess import postprocess


class TestPostprocessBasic:
    def test_strip_strings(self, sample_resume_document):
        profile = ProfileData(name="  Zhang  ", job_target_text="  Dev  ")
        result = postprocess(profile, sample_resume_document)
        assert result.name == "Zhang"
        assert result.job_target_text == "Dev"

    def test_backfill_raw_text(self, sample_resume_document):
        profile = ProfileData()
        result = postprocess(profile, sample_resume_document)
        assert result.raw_text == sample_resume_document.raw_text

    def test_no_document_no_crash(self):
        profile = ProfileData(name="Test")
        result = postprocess(profile, None)
        assert result.name == "Test"


class TestPostprocessSkills:
    def test_dedupe_skills(self, sample_resume_document):
        profile = ProfileData(skills=[
            Skill(name="Python"),
            Skill(name="python"),
            Skill(name="Java"),
        ])
        result = postprocess(profile, sample_resume_document)
        assert len(result.skills) == 2
        names = [s.name for s in result.skills]
        assert "Python" in names
        assert "Java" in names

    def test_remove_empty_skills(self, sample_resume_document):
        profile = ProfileData(skills=[
            {"name": "Python"},
            {"name": "  "},
            {"name": ""},
        ])
        result = postprocess(profile, sample_resume_document)
        assert len(result.skills) == 1
        assert result.skills[0].name == "Python"


class TestPostprocessProjects:
    def test_remove_empty_projects(self, sample_resume_document):
        profile = ProfileData(projects=[
            Project(name="", description=""),
            Project(name="Proj A", description="Desc A"),
        ])
        result = postprocess(profile, sample_resume_document)
        assert len(result.projects) == 1
        assert result.projects[0].name == "Proj A"

    def test_dedupe_tech_stack(self, sample_resume_document):
        profile = ProfileData(projects=[
            Project(name="Proj", tech_stack=["Python", "python", "Java"]),
        ])
        result = postprocess(profile, sample_resume_document)
        assert result.projects[0].tech_stack == ["Python", "Java"]


class TestPostprocessInternships:
    def test_remove_empty_internships(self, sample_resume_document):
        profile = ProfileData(internships=[
            Internship(company="", role=""),
            Internship(company="ByteDance", role="Dev"),
        ])
        result = postprocess(profile, sample_resume_document)
        assert len(result.internships) == 1
        assert result.internships[0].company == "ByteDance"

    def test_keep_internship_with_only_company(self, sample_resume_document):
        profile = ProfileData(internships=[
            Internship(company="ByteDance", role=""),
        ])
        result = postprocess(profile, sample_resume_document)
        assert len(result.internships) == 1

    def test_keep_internship_with_only_role(self, sample_resume_document):
        profile = ProfileData(internships=[
            Internship(company="", role="Dev"),
        ])
        result = postprocess(profile, sample_resume_document)
        assert len(result.internships) == 1


class TestPostprocessEducation:
    def test_remove_empty_education(self, sample_resume_document):
        profile = ProfileData(education=[
            Education(),
            Education(school="THU", degree="Bachelor"),
        ])
        result = postprocess(profile, sample_resume_document)
        assert len(result.education) == 1
        assert result.education[0].school == "THU"

    def test_strip_education_fields(self, sample_resume_document):
        profile = ProfileData(education=[
            Education(school="  THU  ", degree="  BS  ", major="  CS  "),
        ])
        result = postprocess(profile, sample_resume_document)
        assert result.education[0].school == "THU"
        assert result.education[0].degree == "BS"
        assert result.education[0].major == "CS"


class TestPostprocessAwards:
    def test_remove_noise_awards(self, sample_resume_document):
        profile = ProfileData(awards=["无", "暂无", "Real Award", "—"])
        result = postprocess(profile, sample_resume_document)
        assert result.awards == ["Real Award"]

    def test_dedupe_awards(self, sample_resume_document):
        profile = ProfileData(awards=["Award A", "award a", "Award B"])
        result = postprocess(profile, sample_resume_document)
        assert result.awards == ["Award A", "Award B"]


class TestPostprocessCertificates:
    def test_dedupe_certificates(self, sample_resume_document):
        profile = ProfileData(certificates=["CET-4", "cet-4", "CET-6"])
        result = postprocess(profile, sample_resume_document)
        assert result.certificates == ["CET-4", "CET-6"]


class TestDateRecovery:
    def test_recover_simplified_dates(self, sample_markdown_document):
        profile = ProfileData(
            education=[Education(school="THU", duration="2020 - 2024")],
            internships=[Internship(company="BD", role="Dev", duration="2024 - 2024")],
            projects=[Project(name="Proj", description="Desc", duration="2024 - 2024")],
        )
        result = postprocess(profile, sample_markdown_document)
        assert result.education[0].duration == "2020.09 - 2024.06"
        assert result.internships[0].duration == "2024.03 - 2024.08"

    def test_no_change_for_complete_dates(self, sample_markdown_document):
        profile = ProfileData(
            education=[Education(school="THU", duration="2020.09 - 2024.06")],
        )
        result = postprocess(profile, sample_markdown_document)
        assert result.education[0].duration == "2020.09 - 2024.06"
