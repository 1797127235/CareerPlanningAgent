"""
agent/llm.py — Re-exports from backend.llm for backward compatibility.

The actual implementation lives in backend/llm.py.
Agent code can continue to `from agent.llm import ...` without changes.
"""
from backend.llm import (  # noqa: F401
    get_chat_model,
    get_env_int,
    get_env_str,
    get_llm_client,
    get_model,
    llm_chat,
    load_env,
    parse_json_response,
)
