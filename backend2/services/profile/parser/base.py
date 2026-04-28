"""解析器插件协议 — TextExtractor 抽象基类。

ParseStrategy 已被移除：新架构中 LLM 是唯一语义解析器，
不再维护多个平级解析策略。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from backend2.schemas.profile import ResumeDocument


class TextExtractor(ABC):
    """将原始文件转为 ResumeDocument（文本 + 元数据）。

    提取器是无状态的，实例化代价低。
    """

    name: str = ""

    @abstractmethod
    def supports(self, filename: str, content_type: str | None) -> bool:
        """返回 True 表示此提取器能处理该文件。"""
        ...

    @abstractmethod
    def extract(self, file_bytes: bytes, filename: str) -> ResumeDocument | None:
        """从文件中提取文本和元数据。

        只在文件格式根本不可处理时返回 None（如加密 PDF）。
        即使文本为空，也应返回有效的 ResumeDocument。
        """
        ...
