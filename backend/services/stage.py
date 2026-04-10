"""User journey stage computation — shared between guidance and chat."""
from __future__ import annotations


def compute_stage(
    profile_count: int,
    jd_count: int,
    review_count: int,
    report_count: int,
) -> str:
    """Compute user journey stage from aggregate counts."""
    if profile_count == 0:
        return "no_profile"
    if jd_count == 0:
        return "has_profile"
    if review_count == 0:
        return "first_diagnosis"
    if review_count < 3:
        return "training"
    if report_count == 0:
        return "growing"
    return "report_ready"
