"""Shared state blackboard for multi-agent conversation."""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CareerState(TypedDict):
    """All sub-agents read/write this shared state."""

    messages: Annotated[list[BaseMessage], add_messages]
    user_id: int | None  # authenticated user
    profile_id: int | None  # active profile
    user_profile: dict | None  # cached profile data
    career_goal: dict | None  # target job node
    current_node_id: str | None  # graph position from locate
    user_stage: str  # no_profile | no_goal | beginner | ...
    last_diagnosis: dict | None  # latest JD diagnosis result
    # Growth coach state
    coach_memo: str  # natural-language memo about user from prior sessions
    page_context: dict | None  # {route, label, data} — what page the user is on
    tool_hint: str  # hint for sub-agent on which tool to use (e.g. "search_real_jd")
    last_active_agent: str  # track which agent responded last (for follow-up routing)
    growth_context: dict | None  # projects + pursuits from growth log
