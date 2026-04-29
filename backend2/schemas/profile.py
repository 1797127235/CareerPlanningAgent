"""简历解析的数据契约 — 跨 backend2 模块共享。

本模块只定义 parser 层的输入输出契约，不包含职业判断字段。
职业判断（岗位方向、公司 tier、研究/工程倾向等）属于后续图谱/评估层。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── 子模型 ──────────────────────────────────────────────────────────────

class Skill(BaseModel):
    """单条技能，含熟练度等级。"""

    name: str = Field(..., min_length=1)
    level: Literal["beginner", "familiar", "intermediate", "advanced"] = "familiar"


class DimensionScore(BaseModel):
    """单一维度得分。"""
    name: str = ""
    score: int = Field(default=0, ge=0, le=100)
    source: Literal["resume", "user_input", "manual"] = "manual"


class Constraint(BaseModel):
    """用户硬约束。"""
    type: str = ""
    value: str = ""
    label: str = ""


class Preference(BaseModel):
    """用户偏好。"""
    type: str = ""
    value: str = ""
    label: str = ""


class Education(BaseModel):
    """教育经历。"""

    degree: str = ""
    major: str = ""
    school: str = ""
    graduation_year: int | None = None
    duration: str = ""          # 原始时间范围，如 "2020.09 - 2024.06"


class Internship(BaseModel):
    """实习或工作经历。"""

    company: str = ""
    role: str = ""
    duration: str = ""          # 原始时间范围
    tech_stack: list[str] = Field(default_factory=list)
    highlights: str = ""


class Project(BaseModel):
    """项目经历。"""

    name: str = ""
    description: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    duration: str = ""          # 原始时间范围
    highlights: str = ""


# ── 输入层 ──────────────────────────────────────────────────────────────

class ResumeFile(BaseModel):
    """内部输入对象，不入库，不返回前端。

    给 extractor 提取文本，给 ResumeSDK evidence provider 调用第三方接口。
    """

    filename: str
    content_type: str | None = None
    file_bytes: bytes = Field(exclude=True)
    file_hash: str = ""  # SHA-256，由调用方计算


# ── 提取层 ──────────────────────────────────────────────────────────────

class ResumeDocument(BaseModel):
    """原始文档提取结果 — 只表达文本提取结果，不含原始二进制文件。"""

    filename: str
    content_type: str | None = None
    raw_text: str
    text_format: Literal["plain", "markdown"] = "plain"
    extraction_method: str = ""   # 如 "pdfplumber", "markitdown", "ocr_vlm"
    ocr_used: bool = False
    file_hash: str = ""          # SHA-256，用于重解析去重
    warnings: list[str] = Field(default_factory=list)


# ── 画像层 ──────────────────────────────────────────────────────────────

class ProfileData(BaseModel):
    """简历事实画像 — 只包含简历中明确出现的信息，不产职业判断。

    下游模块（岗位图谱、职位评估、报告生成）只读取此结构，不反向污染 parser。
    """

    name: str = ""
    job_target_text: str = ""     # 简历中写明的求职意向原文
    domain_hint: str = ""         # LLM 弱提示，不是系统推断岗位
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    internships: list[Internship] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    raw_text: str = ""            # 为兼容和追溯保留
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    preferences: list[Preference] = Field(default_factory=list)

    # ── 校验器 ──────────────────────────────────────────────────────────

    @field_validator("skills", mode="before")
    @classmethod
    def _normalize_skills(cls, v: list) -> list:
        """同时接受 Skill、dict 和字符串格式的技能，过滤空值。"""
        if not isinstance(v, list):
            return []
        out: list[dict] = []
        for item in v:
            if isinstance(item, Skill):
                out.append({"name": item.name, "level": item.level})
            elif isinstance(item, dict) and item.get("name"):
                out.append(item)
            elif isinstance(item, str) and item.strip():
                out.append({"name": item.strip(), "level": "familiar"})
        return out

    @field_validator("projects", mode="before")
    @classmethod
    def _normalize_projects(cls, v: list) -> list:
        """接受 Project、dict 格式，过滤空值。"""
        if not isinstance(v, list):
            return []
        out: list[dict] = []
        for item in v:
            if isinstance(item, Project):
                out.append(item.model_dump())
            elif isinstance(item, dict):
                out.append(item)
        return out

    @field_validator("awards", "certificates", mode="before")
    @classmethod
    def _dedupe_strings(cls, v: list) -> list:
        """字符串列表去重（不区分大小写），保持原始顺序。"""
        if not isinstance(v, list):
            return []
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned and cleaned.lower() not in seen:
                    seen.add(cleaned.lower())
                    out.append(cleaned)
        return out

    def to_dict(self) -> dict:
        """序列化为纯字典，用于 JSON 存储和 API 响应。"""
        return self.model_dump(mode="json")


# ── 元信息层 ────────────────────────────────────────────────────────────

class ParseMeta(BaseModel):
    """描述本次解析过程，用于调试和质量展示。"""

    llm_model: str = ""
    evidence_sources: list[str] = Field(default_factory=list)
    json_repaired: bool = False
    retry_count: int = 0
    quality_score: int = 0
    quality_checks: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


# ── 响应层 ──────────────────────────────────────────────────────────────

class ParseResumePreviewResponse(BaseModel):
    """解析预览接口返回值。"""

    profile: ProfileData
    document: ResumeDocument
    meta: ParseMeta


# ── 保存层 ──────────────────────────────────────────────────────────────

class SaveProfileRequest(BaseModel):
    """用户确认保存画像的请求体。

    前端展示解析预览后，用户可编辑或直接确认保存。
    必须显式区分原始解析结果和确认后的结果，以支持审计与重解析。
    """

    raw_profile: ProfileData
    """LLM parser 原始输出（未用户编辑），用于审计和版本对比。"""

    confirmed_profile: ProfileData
    """用户确认/编辑后的最终画像，写入 profiles 主表。"""

    document: ResumeDocument
    """原始文档提取结果，含 file_hash 用于重解析去重。"""

    parse_meta: ParseMeta
    """本次解析的完整元信息快照（quality_score、model、retry_count 等）。"""


class SaveProfileResponse(BaseModel):
    """保存成功后的响应。"""

    profile_id: int
    parse_id: int
    message: str = "保存成功"
