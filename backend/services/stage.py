"""User journey stage computation — shared between guidance and chat."""
from __future__ import annotations


def compute_stage(
    profile_count: int,
    jd_count: int,
    activity_count: int,
    report_count: int,
) -> str:
    """Compute user journey stage from aggregate counts.

    activity_count = 成长档案活跃记录数（项目 + 实战 + 面试）
    """
    if profile_count == 0:
        return "no_profile"
    if jd_count == 0:
        return "has_profile"
    if activity_count == 0:
        return "first_diagnosis"
    if activity_count < 3:
        return "training"
    if report_count == 0:
        return "growing"
    return "report_ready"


"""Determine the user's current career-planning stage from persisted signals.

Stages (inferred from actions, not user-declared):
  exploring     - Profile absent OR no target_node_id set
  focusing      - Has profile + target + at least 1 report; no interview yet
  job_hunting   - Has at least 1 interview entry in growth_log
  sprinting     - Has >=3 interviews or any offer entry
"""
import json
import logging
from typing import Literal

from sqlalchemy.orm import Session

from backend.db_models import Profile, Report

logger = logging.getLogger(__name__)

Stage = Literal['exploring', 'focusing', 'job_hunting', 'sprinting']


def determine_stage(user_id: int, db: Session) -> Stage:
    """Return the current career stage based on the user's persisted signals."""
    # 1. profile + target
    profile = db.query(Profile).filter_by(user_id=user_id).first()
    has_profile = profile is not None and bool(profile.profile_json)
    target_node_id = None
    if has_profile:
        try:
            target_node_id = json.loads(profile.profile_json).get('target_node_id')
        except Exception:
            target_node_id = None

    if not has_profile or not target_node_id:
        return 'exploring'

    # 2. report count
    report_count = db.query(Report).filter_by(user_id=user_id).count()

    # 3. interview / offer signals
    try:
        from backend.db_models import GrowthEntry, JobApplication

        interview_count = (
            db.query(GrowthEntry)
            .filter_by(user_id=user_id)
            .filter(GrowthEntry.category == 'interview')
            .count()
        )

        offer_count = (
            db.query(JobApplication)
            .filter_by(user_id=user_id)
            .filter(JobApplication.status == 'offer')
            .count()
        )
    except ImportError:
        logger.warning("GrowthEntry/JobApplication model not found - stage determination will skip interview/offer signals")
        interview_count = 0
        offer_count = 0

    # 4. 分档
    if offer_count > 0 or interview_count >= 3:
        return 'sprinting'
    if interview_count >= 1:
        return 'job_hunting'
    if report_count >= 1:
        return 'focusing'
    return 'focusing'
