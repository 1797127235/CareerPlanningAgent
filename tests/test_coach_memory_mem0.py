"""Tests for coach_memory Mem0 wrapper.

All external API calls are mocked to avoid network/LLM dependencies.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.services import coach_memory


@pytest.fixture(autouse=True)
def reset_memory_singleton():
    """Reset the module-level _memory singleton before each test."""
    coach_memory._memory = None
    yield
    coach_memory._memory = None


class TestGetMemory:
    @patch("backend.services.coach_memory.Memory.from_config")
    def test_lazy_initialization(self, mock_from_config):
        mock_mem = MagicMock()
        mock_from_config.return_value = mock_mem
        mem = coach_memory.get_memory()
        assert mem is mock_mem
        mock_from_config.assert_called_once()

    @patch("backend.services.coach_memory.Memory.from_config")
    def test_singleton(self, mock_from_config):
        mock_mem = MagicMock()
        mock_from_config.return_value = mock_mem
        m1 = coach_memory.get_memory()
        m2 = coach_memory.get_memory()
        assert m1 is m2
        mock_from_config.assert_called_once()


class TestAddConversation:
    @patch("backend.services.coach_memory.Memory.from_config")
    def test_add_conversation_success(self, mock_from_config):
        mock_mem = MagicMock()
        mock_from_config.return_value = mock_mem
        coach_memory.add_conversation(42, "user: hello\nassistant: hi")
        mock_mem.add.assert_called_once_with("user: hello\nassistant: hi", user_id="42")

    @patch("backend.services.coach_memory.Memory.from_config")
    def test_add_conversation_failure_is_silent(self, mock_from_config):
        mock_mem = MagicMock()
        mock_mem.add.side_effect = RuntimeError("API down")
        mock_from_config.return_value = mock_mem
        coach_memory.add_conversation(42, "user: hello")
        mock_mem.add.assert_called_once()


class TestSearchUserContext:
    @patch("backend.services.coach_memory.Memory.from_config")
    def test_search_returns_memories(self, mock_from_config):
        mock_mem = MagicMock()
        mock_mem.search.return_value = [
            {"memory": "用户喜欢数据驱动", "score": 0.9},
            {"memory": "用户对AI替代焦虑", "score": 0.8},
        ]
        mock_from_config.return_value = mock_mem
        results = coach_memory.search_user_context(42, "用户焦虑")
        assert "用户喜欢数据驱动" in results
        assert "用户对AI替代焦虑" in results
        mock_mem.search.assert_called_once_with(query="用户焦虑", user_id="42", limit=5)

    @patch("backend.services.coach_memory.Memory.from_config")
    def test_search_failure_returns_empty(self, mock_from_config):
        mock_mem = MagicMock()
        mock_mem.search.side_effect = RuntimeError("API down")
        mock_from_config.return_value = mock_mem
        results = coach_memory.search_user_context(42, "test")
        assert results == []


class TestMigrateLegacyMemo:
    @patch("backend.services.coach_memory.Memory.from_config")
    def test_migrate_success(self, mock_from_config):
        mock_mem = MagicMock()
        mock_from_config.return_value = mock_mem
        coach_memory.migrate_legacy_memo(42, "老用户备注")
        mock_mem.add.assert_called_once_with("[历史备忘录] 老用户备注", user_id="42")

    @patch("backend.services.coach_memory.Memory.from_config")
    def test_migrate_empty_text_no_op(self, mock_from_config):
        mock_mem = MagicMock()
        mock_from_config.return_value = mock_mem
        coach_memory.migrate_legacy_memo(42, "   ")
        mock_mem.add.assert_not_called()

    @patch("backend.services.coach_memory.Memory.from_config")
    def test_migrate_failure_is_silent(self, mock_from_config):
        mock_mem = MagicMock()
        mock_mem.add.side_effect = RuntimeError("API down")
        mock_from_config.return_value = mock_mem
        coach_memory.migrate_legacy_memo(42, "老用户备注")
        mock_mem.add.assert_called_once()
