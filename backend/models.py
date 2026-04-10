"""
Pydantic 模型定义
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# ==================== 岗位相关模型 ====================

class SkillDistribution(BaseModel):
    must_skills: List[str] = []
    nice_skills: List[str] = []
    skill_frequency: Dict[str, float] = {}


class SalaryStats(BaseModel):
    p25: int = 0
    p50: int = 0
    p75: int = 0


class EducationDistribution(BaseModel):
    本科: float = 0
    大专: float = 0
    硕士: float = 0
    高中: Optional[float] = 0
    中专: Optional[float] = 0
    博士: Optional[float] = 0


class JobType(BaseModel):
    job_type_id: str
    job_type_name: str
    category: str
    job_count: int
    skill_distribution: SkillDistribution
    salary_stats: SalaryStats
    top_cities: List[str] = []
    top_industries: List[str] = []
    education_distribution: Dict[str, float] = {}
    archetype_id: Optional[str] = None


class Archetype(BaseModel):
    archetype_id: str
    archetype_name: str
    total_jobs: int
    member_job_types: List[str]
    common_skills: List[str]
    representative_job_type: str
    base_dimension_scores: Dict[str, int]
    type_distribution: Dict[str, int]


class GraphNode(BaseModel):
    id: str
    label: str
    category: str
    archetype_id: Optional[str] = None
    job_count: Optional[int] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # promotion | transition
    weight: Optional[float] = 1.0


class JobGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ==================== 学生画像相关模型 ====================

class BasicInfo(BaseModel):
    name: str = ""
    school: str = ""
    major: str = ""
    degree: str = ""
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class Internship(BaseModel):
    company: str = ""
    role: str = ""
    months: int = 0
    desc: str = ""


class Project(BaseModel):
    name: str = ""
    tech: List[str] = []
    desc: str = ""


class StudentProfile(BaseModel):
    basic_info: BasicInfo = BasicInfo()
    skills: List[str] = []
    certificates: List[str] = []
    internships: List[Internship] = []
    projects: List[Project] = []
    dimension_scores: Optional[Dict[str, int]] = None
    completeness_score: Optional[int] = None
    competitiveness_score: Optional[int] = None


class ParseResumeResponse(BaseModel):
    success: bool
    data: Optional[StudentProfile] = None
    message: Optional[str] = None


class BuildProfileRequest(BaseModel):
    basic_info: BasicInfo
    skills: List[str] = []
    certificates: List[str] = []
    internships: List[Internship] = []
    projects: List[Project] = []


# ==================== 匹配相关模型 ====================

class MatchResult(BaseModel):
    job_id: str
    job_title: str
    company_name: str
    total_score: int
    basic_score: int
    skill_score: int
    quality_score: int
    potential_score: int
    key_advantages: List[str]
    key_gaps: List[str]
    salary_range: Optional[str] = None
    location: Optional[str] = None


class MatchingProgress(BaseModel):
    step: str
    step_name: str
    status: str  # pending | running | completed | error
    message: str
    timestamp: str


class MatchingSession(BaseModel):
    session_id: str
    status: str  # idle | running | completed | error
    progress: List[MatchingProgress] = []
    results: List[MatchResult] = []
    student_profile: Optional[StudentProfile] = None


class MatchingRequest(BaseModel):
    profile: StudentProfile
    target_job: str = ""
    target_city: Optional[str] = None
    target_industry: Optional[str] = None
    target_direction: Optional[str] = None


# ==================== 报告相关模型 ====================

class ReportChapter(BaseModel):
    chapter: int
    title: str
    content: str


class CareerReport(BaseModel):
    id: str
    title: str
    summary: str = ""
    chapters: List[ReportChapter] = []
    created_at: str
    updated_at: str
    student_name: str
    target_job: str


class UpdateReportRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    chapters: Optional[List[ReportChapter]] = None


class CreateReportRequest(BaseModel):
    student_profile: Optional[StudentProfile] = None
    match_result: Optional[Dict[str, Any]] = None
    target_job: str = ""


class ConfigSaveRequest(BaseModel):
    config: Dict[str, str] = {}


class ExportRequest(BaseModel):
    format: str  # pdf | word


# ==================== 技能相关模型 ====================

class SkillItem(BaseModel):
    canonical_skill: str
    category: str
    aliases: List[str]


# ==================== API 响应模型 ====================

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
