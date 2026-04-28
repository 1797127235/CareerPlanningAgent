"""解析器插件协议 — TextExtractor 和 ParseStrategy 抽象基类。

定义了管线如何发现和调用提取器、策略，而不依赖它们的具体实现。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from backend2.schemas.profile import ParseCandidate, ResumeDocument


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


class ParseStrategy(ABC):
    """将 ResumeDocument 转为 ParseCandidate（结构化画像）。

    策略是无状态的，实例化代价低。
    策略内部可以使用 LLM、第三方 API 或规则逻辑。
    不允许修改传入的 ResumeDocument。
    """

    name: str = ""

    @abstractmethod
    def parse(self, document: ResumeDocument) -> ParseCandidate | None:
        """解析文档并返回候选画像。

        当策略无法产出结果时返回 None（如 LLM 超时、格式错误）。
        管线会尝试下一个策略。
        """
        ...
