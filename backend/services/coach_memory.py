"""Backward compatibility shim for coach_memory.

The actual implementation has moved to backend.services.coach.memory.
This module re-exports for existing importers.
"""
from backend.services.coach.memory import *  # noqa: F401, F403
