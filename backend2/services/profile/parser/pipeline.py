"""ParserPipeline — 单 LLM 路径编排。

ResumeFile
  -> extract ResumeDocument
  -> collect evidence (optional)
  -> LLM parse ProfileData
  -> postprocess
  -> quality score
  -> ParseResumePreviewResponse parts

不写职业规则，也不持久化数据库。
"""
from __future__ import annotations

import logging

from backend2.schemas.profile import (
    ParseMeta,
    ParseResumePreviewResponse,
    ProfileData,
    ResumeDocument,
    ResumeFile,
)
from backend2.services.profile.parser.base import TextExtractor
from backend2.services.profile.parser.extractors import (
    DocxTextExtractor,
    MarkItDownExtractor,
    OcrVlmExtractor,
    PdfTextExtractor,
    TxtTextExtractor,
)
from backend2.services.profile.parser.llm_parser import LLMParseResult, parse as llm_parse
from backend2.services.profile.parser.postprocess import postprocess
from backend2.services.profile.parser.quality import score_profile

logger = logging.getLogger(__name__)


class ExtractorRegistry:
    """发现并选择正确的 TextExtractor。

    按注册顺序依次尝试；第一个 supports() 返回 True 且 extract() 成功的胜出。
    """

    def __init__(self, extractors: list[TextExtractor] | None = None):
        self._extractors: list[TextExtractor] = list(extractors or [])

    def register(self, extractor: TextExtractor) -> None:
        self._extractors.append(extractor)

    def extract(self, file: ResumeFile) -> ResumeDocument:
        """运行第一个匹配的提取器，返回 ResumeDocument。

        没有任何提取器匹配时，降级为 UTF-8 原始解码。
        """
        for ex in self._extractors:
            if ex.supports(file.filename, file.content_type):
                logger.info("提取器选中: %s -> %s", ex.name, file.filename)
                doc = ex.extract(file.file_bytes, file.filename)
                if doc is not None:
                    if not doc.content_type:
                        doc.content_type = file.content_type
                    return doc
                logger.warning("提取器 %s 对 %s 返回了 None", ex.name, file.filename)

        logger.warning("无匹配的提取器，%s 降级为原始 UTF-8 解码", file.filename)
        raw_text = file.file_bytes.decode("utf-8", errors="ignore")
        return ResumeDocument(
            filename=file.filename,
            content_type=file.content_type,
            raw_text=raw_text,
            text_format="plain",
            extraction_method="raw_fallback",
        )


def default_registry() -> ExtractorRegistry:
    """返回预配置的提取器注册表。

    顺序：txt/md -> markitdown(PDF/DOCX) -> docx -> pdf -> ocr
    """
    return ExtractorRegistry([
        TxtTextExtractor(),
        MarkItDownExtractor(),
        DocxTextExtractor(),
        PdfTextExtractor(),
        OcrVlmExtractor(),
    ])


class ParserPipeline:
    """编排完整的解析流程：提取 -> 解析 -> 后处理 -> 质量评分。"""

    def __init__(
        self,
        registry: ExtractorRegistry | None = None,
        evidence_collector=None,
    ):
        self.registry = registry or default_registry()
        self.evidence_collector = evidence_collector

    def parse(self, file: ResumeFile) -> ParseResumePreviewResponse:
        """运行完整管线，返回预览响应。"""
        warnings: list[str] = []
        meta = ParseMeta()

        # 填充 file_hash
        if not file.file_hash:
            import hashlib
            file.file_hash = hashlib.sha256(file.file_bytes).hexdigest()

        # 1. 提取原始文本
        document = self.registry.extract(file)
        document.file_hash = file.file_hash
        if document.warnings:
            warnings.extend(document.warnings)

        # 2. 收集证据（可选，失败不中断）
        evidence: dict | None = None
        if self.evidence_collector:
            try:
                evidence = self.evidence_collector(file)
                if evidence:
                    meta.evidence_sources.append("resumesdk")
            except Exception as e:
                logger.warning("证据收集失败: %s", e)
                warnings.append(f"证据收集失败: {e}")

        # 3. LLM 语义解析
        parse_result = llm_parse(document, evidence)
        if parse_result is None:
            logger.error("LLM 解析未返回 ProfileData")
            profile = ProfileData()
            warnings.append("LLM 解析失败，返回空画像")
        else:
            profile = parse_result.profile
            meta.llm_model = parse_result.meta.llm_model
            meta.json_repaired = parse_result.meta.json_repaired
            meta.retry_count = parse_result.meta.retry_count

        # 4. 后处理（防御性清理 + 事实保真）
        profile = postprocess(profile, document)

        # 5. 质量评分
        quality_meta = score_profile(profile)
        meta.quality_score = quality_meta.quality_score
        meta.quality_checks = quality_meta.quality_checks

        if warnings:
            meta.warnings = warnings

        return ParseResumePreviewResponse(
            profile=profile,
            document=document,
            meta=meta,
        )
