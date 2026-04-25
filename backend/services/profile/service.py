# -*- coding: utf-8 -*-
"""ProfileService facade — delegates to sub-modules by domain."""
from __future__ import annotations

from backend.services.profile import scorer, sjt


class ProfileService:
    """Static facade for profile analysis utilities."""

    @staticmethod
    def compute_quality(profile_data: dict) -> dict:
        return scorer.compute_quality(profile_data)

    @staticmethod
    def generate_sjt_questions(profile_data: dict) -> list[dict]:
        return sjt.generate_sjt_questions(profile_data)

    @staticmethod
    def score_sjt_v2(answers: list[dict], questions: list[dict]) -> dict:
        return sjt.score_sjt_v2(answers, questions)

    @staticmethod
    def generate_sjt_advice(
        dimensions: dict,
        answers: list[dict],
        questions: list[dict],
        profile_data: dict,
    ) -> dict[str, str]:
        return sjt.generate_sjt_advice(dimensions, answers, questions, profile_data)
