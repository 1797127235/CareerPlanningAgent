"""Shared utilities used across routers."""
from typing import Any


def ok(data: Any = None, message: str | None = None) -> dict:
    """Wrap a successful response in the standard envelope."""
    result: dict = {"success": True}
    if data is not None:
        result["data"] = data
    if message:
        result["message"] = message
    return result
