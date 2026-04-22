"""Internship validation and demotion logic."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Keywords that indicate a real company/organization entity
_ORG_ENTITY_KEYWORDS = (
    "公司", "集团", "科技", "有限", "股份", "研究院", "研究所", "实验室",
    "银行", "医院", "学院", "大学", "政府", "局", "部", "中心",
    "Ltd", "Co.", "Inc.", "Corp", "Technology", "Tech",
)

# Keywords that suggest the name is a project title, not a company
_PROJECT_TITLE_KEYWORDS = (
    "项目", "系统", "平台", "工程", "模块", "框架", "工具", "脚本",
    "App", "应用", "网站", "小程序", "后台", "前台", "管理后台",
)

# Internship identity words that should appear in the full entry text
_INTERNSHIP_IDENTITY_WORDS = (
    "实习", "兼职", "intern", "internship",
)

# Role suffixes / patterns that indicate a real job title
_VALID_ROLE_SUFFIXES = (
    "工程师", "实习生", "助理", "分析师", "经理", "专员",
    "开发者", "架构师", "设计师", "运营", "产品", "研发",
    "engineer", "intern", "analyst", "manager", "developer",
)

# Role patterns that are task descriptions, NOT job titles
_TASK_DESCRIPTION_ROLE_SUFFIXES = (
    "工作",
    "任务",
)


def _is_valid_internship(entry: dict) -> bool:
    """Return True if this entry is a genuine internship (not a misclassified project).

    Relaxed rules for student resumes — many student internships are at labs,
    research groups, or small companies that don't have formal org suffixes.
    """
    company = str(entry.get("company") or "").strip()
    role = str(entry.get("role") or "").strip()

    if not company:
        return False

    combined = " ".join([
        company, role,
        str(entry.get("duration") or ""),
        str(entry.get("highlights") or ""),
    ])

    company_role_text = f"{company} {role}"
    if any(w in company_role_text for w in _INTERNSHIP_IDENTITY_WORDS):
        return True

    if not role:
        return False

    has_org = any(kw in company for kw in _ORG_ENTITY_KEYWORDS)
    has_project_title = any(kw in company for kw in _PROJECT_TITLE_KEYWORDS)
    if has_project_title and not has_org:
        return False

    role_is_task_desc = any(role.endswith(sfx) for sfx in _TASK_DESCRIPTION_ROLE_SUFFIXES)
    if role_is_task_desc:
        return False

    return True


def _internship_to_project_str(entry: dict) -> str:
    """Convert a misclassified internship entry back to a project description string."""
    parts = []
    company = (entry.get("company") or "").strip()
    role = (entry.get("role") or "").strip()
    if company:
        parts.append(company)
    if role and role != company:
        parts.append(f"（{role}）")
    highlights = (entry.get("highlights") or "").strip()
    if highlights:
        parts.append(f"：{highlights}")
    tech = entry.get("tech_stack") or []
    if isinstance(tech, list) and tech:
        parts.append(f"技术栈：{', '.join(str(t) for t in tech)}")
    return "".join(parts) or str(entry)
