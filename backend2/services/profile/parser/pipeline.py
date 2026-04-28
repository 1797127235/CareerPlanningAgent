"""ResumeParserPipeline — 编排提取器、策略、合并、标准化。

本模块本身不包含任何解析逻辑，只负责将插件组件串联起来并定义执行顺序。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend2.schemas.profile import ParseCandidate, ProfileData, ResumeDocument
from backend2.services.profile.parser.base import ParseStrategy, TextExtractor
from backend2.services.profile.parser.extractors import (
    DocxTextExtractor,
    OcrVlmExtractor,
    PdfTextExtractor,
    TxtTextExtractor,
)
from backend2.services.profile.parser.strategies import LLMDirectStrategy, ResumeSDKStrategy

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """ResumeParserPipeline.parse() 的最终输出。"""

    profile: ProfileData
    document: ResumeDocument
    candidates: list[ParseCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ExtractorRegistry:
    """发现并选择正确的 TextExtractor。

    按注册顺序依次尝试；第一个 supports() 返回 True 的胜出。
    """

    def __init__(self, extractors: list[TextExtractor] | None = None):
        self._extractors: list[TextExtractor] = list(extractors or [])

    def register(self, extractor: TextExtractor) -> None:
        """将一个提取器追加到优先级列表末尾。"""
        self._extractors.append(extractor)

    def extract(self, file_bytes: bytes, filename: str, content_type: str | None = None) -> ResumeDocument:
        """运行第一个匹配的提取器，返回 ResumeDocument。

        如果没有任何提取器匹配，降级为 UTF-8 原始解码。
        """
        for ex in self._extractors:
            if ex.supports(filename, content_type):
                logger.info("提取器选中: %s → %s", ex.name, filename)
                doc = ex.extract(file_bytes, filename)
                if doc is not None:
                    # 保留原始文件字节，供需要原始文件的策略（如 ResumeSDK）使用
                    doc.file_bytes = file_bytes
                    doc.content_type = content_type
                    return doc
                logger.warning("提取器 %s 对 %s 返回了 None", ex.name, filename)

        # 最终兜底：当作纯文本处理（尽力解码）
        logger.warning("无匹配的提取器，%s 降级为原始 UTF-8 解码", filename)
        raw_text = file_bytes.decode("utf-8", errors="ignore")
        return ResumeDocument(
            filename=filename,
            content_type=content_type,
            raw_text=raw_text,
            extractor="raw_fallback",
            file_bytes=file_bytes,
        )


def default_pipeline() -> "ResumeParserPipeline":
    """返回预配置的管线，包含所有标准提取器和策略。

    用法::
        from backend2.services.profile.parser import default_pipeline
        pipeline = default_pipeline()
        result = pipeline.parse(file_bytes, filename)
    """
    registry = ExtractorRegistry([
        TxtTextExtractor(),
        DocxTextExtractor(),
        PdfTextExtractor(),
        OcrVlmExtractor(),
    ])
    strategies: list[ParseStrategy] = [
        ResumeSDKStrategy(),
        LLMDirectStrategy(),
    ]
    return ResumeParserPipeline(registry, strategies)


class ResumeParserPipeline:
    """编排完整的解析流程。

    用法::

        pipeline = ResumeParserPipeline()
        result = pipeline.parse(file_bytes, "resume.pdf")
        print(result.profile.name)
    """

    def __init__(
        self,
        extractor_registry: ExtractorRegistry | None = None,
        strategies: list[ParseStrategy] | None = None,
    ):
        self.extractors = extractor_registry or ExtractorRegistry()
        self.strategies: list[ParseStrategy] = list(strategies or [])

    def parse(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> ParseResult:
        """运行完整管线：提取 → 解析（多策略） → 合并 → 标准化。"""
        # 1. 提取原始文本
        document = self.extractors.extract(file_bytes, filename, content_type)

        # 2. 运行所有策略
        candidates: list[ParseCandidate] = []
        for strategy in self.strategies:
            try:
                candidate = strategy.parse(document)
                if candidate is not None:
                    candidates.append(candidate)
                    logger.info(
                        "策略 %s 产出候选: skills=%d projects=%d",
                        strategy.name,
                        len(candidate.profile.skills),
                        len(candidate.profile.projects),
                    )
            except Exception:
                logger.exception("策略 %s 执行失败", strategy.name)

        # 3. 合并候选结果
        merged = _merge_candidates(candidates, document)

        # 4. 标准化
        normalized = _normalize_profile(merged, document)

        # 5. 向后兼容：保留原始文本引用
        normalized.raw_text = document.raw_text

        warnings: list[str] = []
        if not candidates:
            warnings.append("所有解析策略均未返回结果")
        warnings.extend(document.warnings)
        for c in candidates:
            warnings.extend(c.warnings)

        return ParseResult(
            profile=normalized,
            document=document,
            candidates=candidates,
            warnings=warnings,
        )


# ── 占位实现 — 后续步骤会替换为独立模块 ─────────────────────────────────
# 当前为最小可用实现，确保管线能跑通。


def _merge_candidates(candidates: list[ParseCandidate], document: ResumeDocument) -> ProfileData:
    """合并多个 ParseCandidate 为一个 ProfileData。

    当前占位实现：取 confidence 最高的候选结果。
    后续 Step 7 将替换为完整的字段级合并逻辑。
    """
    if not candidates:
        logger.warning("无候选可合并，%s 返回空画像", document.filename)
        return ProfileData()

    sorted_candidates = sorted(candidates, key=lambda c: c.confidence, reverse=True)
    best = sorted_candidates[0].profile
    return best.model_copy(deep=True)


def _normalize_profile(profile: ProfileData, document: ResumeDocument) -> ProfileData:
    """标准化和清洗合并后的画像。

    当前占位实现：仅保证列表字段不为 None。
    后续 Step 8 将替换为技能别名归一化、粒度折叠、实习校验等完整逻辑。
    """
    if profile.skills is None:
        profile.skills = []
    if profile.projects is None:
        profile.projects = []
    if profile.internships is None:
        profile.internships = []
    if profile.awards is None:
        profile.awards = []
    if profile.certificates is None:
        profile.certificates = []
    if profile.knowledge_areas is None:
        profile.knowledge_areas = []
    return profile


def is_insufficient_profile(profile: ProfileData) -> bool:
    """Return True if the profile lacks all critical semantic fields.

    A profile with no name, no skills, no projects, no internships,
    no education, and no domain is considered empty / insufficient.
    """
    return (
        not profile.name.strip()
        and len(profile.skills) == 0
        and len(profile.projects) == 0
        and len(profile.internships) == 0
        and not profile.education.school
        and not profile.primary_domain
    )
