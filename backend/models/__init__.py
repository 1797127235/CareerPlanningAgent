"""SQLAlchemy ORM models — re-exported from domain modules."""
from __future__ import annotations

from backend.models.user import User, UserNotification
from backend.models.profile import Profile, CareerGoal, SjtSession
from backend.models.report import Report
from backend.models.graph import (
    Skill,
    AiToolMapping,
    JobNode,
    JobNodeIntro,
    JobEdge,
    JobScore,
    OnetJob,
    OnetTask,
    TaskAutomation,
    TaskMatching,
    ScoreChangelog,
    RescoreRun,
)
from backend.models.market import MarketSignal, CityMarketSignal
from backend.models.jd import JDDiagnosis, JobApplication, InterviewDebrief
from backend.models.growth import (
    ProjectRecord,
    ProjectLog,
    InterviewRecord,
    GrowthSnapshot,
    SkillUpdate,
    ActionProgress,
    ActionPlanV2,
    PlanWeekProgress,
    GrowthEntry,
)
from backend.models.interview import MockInterview, InterviewQuestionBank
from backend.models.chat import ChatSession, ChatMessage, CoachResult

__all__ = [
    "User",
    "UserNotification",
    "Profile",
    "CareerGoal",
    "SjtSession",
    "Report",
    "Skill",
    "AiToolMapping",
    "JobNode",
    "JobNodeIntro",
    "JobEdge",
    "JobScore",
    "OnetJob",
    "OnetTask",
    "TaskAutomation",
    "TaskMatching",
    "ScoreChangelog",
    "RescoreRun",
    "MarketSignal",
    "CityMarketSignal",
    "JDDiagnosis",
    "JobApplication",
    "InterviewDebrief",
    "ProjectRecord",
    "ProjectLog",
    "InterviewRecord",
    "GrowthSnapshot",
    "SkillUpdate",
    "ActionProgress",
    "ActionPlanV2",
    "PlanWeekProgress",
    "GrowthEntry",
    "MockInterview",
    "InterviewQuestionBank",
    "ChatSession",
    "ChatMessage",
    "CoachResult",
]
