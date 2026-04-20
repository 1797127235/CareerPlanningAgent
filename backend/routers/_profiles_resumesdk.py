"""ResumeSDK API client — third-party resume parsing with fallback to self-hosted.

Supports:
  - Alibaba Cloud Marketplace (alicloudapi.com): APPCODE auth, form-urlencoded
  - SaaS (resumesdk.com): uid+pwd auth, JSON

Usage:
    result = parse_with_resumesdk(file_content, filename)
    if result is None:
        result = fallback_to_selfhosted(file_content, filename)
"""
from __future__ import annotations

import base64
import json
import logging

import requests

from backend.config import (
    RESUMESDK_APPCODE,
    RESUMESDK_APPKEY,
    RESUMESDK_APPSECRET,
    RESUMESDK_BASE_URL,
    RESUMESDK_ENABLED,
    RESUMESDK_PWD,
    RESUMESDK_UID,
)
from backend.routers._profiles_parsing import _extract_skills_from_text

logger = logging.getLogger(__name__)

_TIMEOUT = 60


def _is_aliyun_market() -> bool:
    return "alicloudapi.com" in RESUMESDK_BASE_URL or "apigw" in RESUMESDK_BASE_URL


def _call_resumesdk(file_content: bytes, filename: str) -> dict | None:
    """Call ResumeSDK API and return raw result dict."""
    logger.info("ResumeSDK call start: enabled=%s has_appcode=%s base_url=%s", RESUMESDK_ENABLED, bool(RESUMESDK_APPCODE), RESUMESDK_BASE_URL)
    if not RESUMESDK_ENABLED:
        logger.info("ResumeSDK disabled via config")
        return None

    if not RESUMESDK_APPCODE and not (RESUMESDK_UID and RESUMESDK_PWD):
        logger.warning("ResumeSDK enabled but no credentials configured")
        return None

    b64_cont = base64.b64encode(file_content).decode("ascii")

    # ── Alibaba Cloud Marketplace: form-urlencoded + APPCODE ──────────────
    if _is_aliyun_market():
        if not RESUMESDK_APPCODE:
            logger.warning("Alibaba Cloud Market requires APPCODE")
            return None
        headers = {
            "Authorization": f"APPCODE {RESUMESDK_APPCODE}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        payload = {
            "file_name": filename,
            "file_cont": b64_cont,
            "need_avatar": 0,
            "ocr_type": 1,
        }
        logger.info("ResumeSDK request: JSON body, file_name=%s file_cont_len=%d", filename, len(b64_cont))
        try:
            resp = requests.post(
                RESUMESDK_BASE_URL,
                headers=headers,
                json=payload,
                timeout=_TIMEOUT,
            )
            logger.info("ResumeSDK (Aliyun) HTTP status=%s", resp.status_code)
            resp.raise_for_status()
            data = resp.json()
            logger.info("ResumeSDK (Aliyun) response keys=%s", list(data.keys()))
        except requests.exceptions.Timeout:
            logger.warning("ResumeSDK (Aliyun) timed out after %ds", _TIMEOUT)
            return None
        except requests.exceptions.RequestException as e:
            resp_text = getattr(e.response, 'text', '')[:500] if hasattr(e, 'response') and e.response else ''
            logger.warning("ResumeSDK (Aliyun) request failed: %s | resp=%s", e, resp_text)
            return None
        except json.JSONDecodeError as e:
            logger.warning("ResumeSDK (Aliyun) invalid JSON: %s | raw=%s", e, resp.text[:200])
            return None
    else:
        # ── SaaS mode: JSON + uid/pwd ─────────────────────────────────────
        headers = {"Content-Type": "application/json"}
        if RESUMESDK_UID and RESUMESDK_PWD:
            headers["uid"] = RESUMESDK_UID
            headers["pwd"] = RESUMESDK_PWD
        elif RESUMESDK_APPCODE:
            headers["Authorization"] = f"APPCODE {RESUMESDK_APPCODE}"

        payload = {
            "file_name": filename,
            "file_cont": b64_cont,
            "need_avatar": 0,
        }
        try:
            resp = requests.post(
                RESUMESDK_BASE_URL,
                headers=headers,
                json=payload,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            logger.warning("ResumeSDK (SaaS) timed out after %ds", _TIMEOUT)
            return None
        except requests.exceptions.RequestException as e:
            logger.warning("ResumeSDK (SaaS) request failed: %s", e)
            return None
        except json.JSONDecodeError as e:
            logger.warning("ResumeSDK (SaaS) invalid JSON: %s", e)
            return None

    status = data.get("status", {})
    code = status.get("code")
    logger.info("ResumeSDK status code=%s message=%s", code, status.get("message"))
    if code != 200:
        logger.warning("ResumeSDK error: code=%s message=%s", code, status.get("message"))
        return None

    result = data.get("result")
    if result and isinstance(result, dict):
        logger.info("ResumeSDK result keys=%s", list(result.keys()))
    logger.info("ResumeSDK result type=%s has_skills=%s", type(result).__name__, bool(result and result.get("skills")))
    return result


# ── Field mapping: ResumeSDK → our profile format ───────────────────────────

_RESUME_LEVEL_MAP = {
    "精通": "advanced",
    "熟练": "intermediate",
    "熟悉": "familiar",
    "了解": "beginner",
    "一般": "beginner",
    "良好": "familiar",
}


def _map_skills(rs_skills: list[dict]) -> list[dict]:
    """Map ResumeSDK skills to our format."""
    result = []
    for s in rs_skills:
        if isinstance(s, dict):
            name = s.get("skill_name", "").strip()
            level_raw = s.get("skill_level", "")
            if not name:
                continue
            level = _RESUME_LEVEL_MAP.get(str(level_raw).strip(), "familiar")
            result.append({"name": name, "level": level})
        elif isinstance(s, str) and s.strip():
            result.append({"name": s.strip(), "level": "familiar"})
    return result


def _map_education(rs_edu: list[dict]) -> dict:
    """Map ResumeSDK education (highest degree) to our format."""
    if not rs_edu or not isinstance(rs_edu, list):
        return {}
    # Take the highest education (usually first or last)
    highest = rs_edu[0] if isinstance(rs_edu[0], dict) else {}
    for edu in rs_edu:
        if isinstance(edu, dict):
            # Prefer higher degree
            degree = edu.get("degree", "")
            if degree in ("博士", "硕士"):
                highest = edu
                break
    return {
        "degree": highest.get("degree", ""),
        "major": highest.get("major", ""),
        "school": highest.get("school", ""),
    }


def _map_internships(rs_work: list[dict]) -> list[dict]:
    """Map ResumeSDK work experience to our internship format."""
    result = []
    for w in rs_work:
        if not isinstance(w, dict):
            continue
        company = w.get("company_name", "").strip()
        if not company:
            continue
        # Extract tech stack from job_description or skill list
        tech_stack: list[str] = []
        desc = w.get("job_description", "")
        # Simple heuristic: look for common tech keywords in description
        if desc:
            common_tech = ["Python", "Java", "C++", "Go", "React", "Vue", "PyTorch",
                          "TensorFlow", "Docker", "Kubernetes", "SQL", "Linux"]
            for tech in common_tech:
                if tech.lower() in desc.lower():
                    tech_stack.append(tech)

        result.append({
            "company": company,
            "role": w.get("job_title", "").strip(),
            "duration": f"{w.get('start_date', '')}-{w.get('end_date', '')}".strip("-"),
            "tech_stack": tech_stack[:5],
            "highlights": desc[:200] if desc else "",
        })
    return result


def _is_management_subsection(name: str, desc: str, tech_stack: list) -> bool:
    """Return True if this 'project' is actually a project-management subsection.

    ResumeSDK often splits a single project description into multiple entries
    where each sub-heading (实验论证, 质量控制, etc.) becomes a fake project.
    """
    # Keywords that indicate a project subsection, not a real project
    subsection_keywords = [
        "实验论证", "实验验证", "规划", "计划", "质量控制", "质量管理",
        "迭代过程", "迭代", "项目进展", "进展", "项目建设", "建设",
        "锻炼", "证明", "能力", "资源管理", "范围管理", "任务分配",
        "运营流程", "流程", "进度控制", "风险管理", "沟通管理",
        "需求分析", "可行性分析", "文献综述", "文献调研",
    ]

    combined = (name + " " + desc).lower()
    is_subsection = any(kw in combined for kw in subsection_keywords)

    # If tech_stack exists and is non-empty, it's likely a real project
    # (management subsections rarely have a technology_stack field)
    if tech_stack and any(t.strip() for t in tech_stack):
        return False

    # If the name itself is a subsection keyword and description is process-oriented
    process_words = ["负责", "主导", "管理", "协调", "规划", "控制", "分配", "汇报"]
    is_process_desc = sum(1 for w in process_words if w in combined) >= 2

    return is_subsection or is_process_desc


def _map_projects(rs_projects: list) -> list[str]:
    """Map ResumeSDK projects to our string list format.

    ResumeSDK sometimes returns project entries as JSON-encoded strings
    rather than dicts. We handle both forms, filter noise, deduplicate,
    and produce readable Chinese text.

    Critical: ResumeSDK often splits a single project into multiple
    management-subsection entries (实验论证/质量控制/迭代过程 etc.).
    These must be filtered out or merged.
    """
    import json as _json

    # ── Step 1: Parse all entries ─────────────────────────────────────────
    entries: list[dict] = []
    for p in rs_projects:
        entry: dict = {}
        if isinstance(p, dict):
            entry = p
        elif isinstance(p, str) and p.strip():
            try:
                parsed = _json.loads(p.strip())
                if isinstance(parsed, dict):
                    entry = parsed
                else:
                    continue
            except _json.JSONDecodeError:
                entries.append({"_text": p.strip()})
                continue
        else:
            continue
        entries.append(entry)

    # ── Step 2: Score each entry (tech signal vs noise) ──────────────────
    scored: list[tuple[int, str, dict]] = []  # (score, text, raw_entry)

    for entry in entries:
        if "_text" in entry:
            scored.append((5, entry["_text"], entry))
            continue

        name = entry.get("project_name", "").strip()
        desc = (
            entry.get("project_description", "").strip()
            or entry.get("description", "").strip()
            or entry.get("details", "").strip()
            or entry.get("project_desc", "").strip()
        )
        duty = entry.get("project_duty", "").strip()
        company = entry.get("company", "").strip()
        role = entry.get("role", "").strip()
        tech_stack = entry.get("technology_stack", []) or []
        if isinstance(tech_stack, str):
            tech_stack = [s.strip() for s in tech_stack.split(",") if s.strip()]

        # Build readable text
        parts: list[str] = []
        if name:
            parts.append(name)
        if company and company != name:
            parts.append(f"（{company}）")
        if role and role not in name:
            parts.append(f"【{role}】")
        if desc and desc not in name:
            parts.append(desc)
        if duty and duty not in desc:
            parts.append(f"职责：{duty}")
        text = " ".join(parts)
        if not text:
            continue

        # Score: higher = more likely to be a real project
        score = 0

        # +2: Has description or duty (real projects usually have details)
        if (desc and len(desc) > 30) or (duty and len(duty) > 20):
            score += 2

        # +1: Has a concrete project name (not just management subsection titles)
        subsection_kws = ["实验论证", "实验验证", "质量控制", "质量管理", "迭代过程",
                          "项目进展", "项目建设", "锻炼", "证明", "资源管理",
                          "运营流程", "进度控制", "风险管理", "沟通管理", "规划", "计划"]
        if name and not any(kw in name for kw in subsection_kws):
            score += 1

        # -2: Strong management-subsection signal
        if _is_management_subsection(name, desc, tech_stack):
            score -= 2

        # -1: Very short entry (likely a fragment)
        if len(text) < 20:
            score -= 1

        scored.append((score, text, entry))

    # ── Step 3: Keep only entries with positive score, sorted by score ────
    scored.sort(key=lambda x: -x[0])
    texts = [text for score, text, entry in scored if score > 0]

    # Hard limit: max 5 projects (ResumeSDK often over-splits)
    texts = texts[:5]

    # ── Step 4: Deduplicate ──────────────────────────────────────────────
    deduped: list[str] = []
    for text in texts:
        is_dup = False
        for i, existing in enumerate(deduped):
            if text in existing or existing in text:
                is_dup = True
                if len(text) > len(existing):
                    deduped[i] = text
                break
            # Word-level overlap (character-based for Chinese)
            chars_t = set(text)
            chars_e = set(existing)
            if chars_t and chars_e:
                overlap = len(chars_t & chars_e) / max(len(chars_t), len(chars_e))
                if overlap > 0.5:
                    is_dup = True
                    if len(text) > len(existing):
                        deduped[i] = text
                    break
        if not is_dup:
            deduped.append(text)

    return deduped


def _extract_cert_name(cert: dict | str) -> str:
    """Extract certificate name from ResumeSDK's various dict formats."""
    if isinstance(cert, str):
        return cert.strip()
    if isinstance(cert, dict):
        # ResumeSDK uses different field names across versions/platforms
        for key in ["certificate_name", "cert_name", "name", "title", "证书名称"]:
            val = cert.get(key, "")
            if val and str(val).strip():
                return str(val).strip()
        # Fallback: any non-empty string value in the dict
        for v in cert.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _map_certificates(rs_certs: list, raw_text: str = "") -> list[str]:
    """Map ResumeSDK certificates to string list.

    Also does regex fallback on raw_text because ResumeSDK often misses
    language certs (CET-4/6, TOEFL, IELTS, etc.).
    """
    import re as _re

    result = []
    for c in rs_certs:
        name = _extract_cert_name(c)
        if name and name not in result:
            result.append(name)

    # Regex fallback for certs ResumeSDK tends to miss
    if raw_text:
        cert_patterns = [
            (r"CET[-\s]?4", "英语（CET-4）"),
            (r"CET[-\s]?6", "英语（CET-6）"),
            (r"英语六级", "英语（CET-6）"),
            (r"英语四级", "英语（CET-4）"),
            (r"大学英语六级", "英语（CET-6）"),
            (r"大学英语四级", "英语（CET-4）"),
            (r"TOEFL", "TOEFL"),
            (r"IELTS", "IELTS"),
            (r"托福", "托福"),
            (r"雅思", "雅思"),
            (r"日语\s*N1", "日语 N1"),
            (r"日语\s*N2", "日语 N2"),
            (r"普通话\s*([一二三甲乙]+)", r"普通话\1"),
            (r"驾驶[证照]\s*[ABC]\d", "机动车驾驶证"),
            (r"软考\s*(初级|中级|高级)", r"软考\1"),
            (r"PMP", "PMP"),
            (r"CFA", "CFA"),
            (r"CPA", "CPA"),
        ]
        for pattern, replacement in cert_patterns:
            for match in _re.finditer(pattern, raw_text, _re.IGNORECASE):
                cert = _re.sub(pattern, replacement, match.group(0), flags=_re.IGNORECASE)
                cert = cert.strip()
                if cert and cert not in result:
                    result.append(cert)

    return result


def _extract_award_name(award: dict | str) -> str:
    """Extract award name from ResumeSDK's various dict formats."""
    if isinstance(award, str):
        return award.strip()
    if isinstance(award, dict):
        for key in ["award_name", "name", "title", "奖项名称", "荣誉名称"]:
            val = award.get(key, "")
            if val and str(val).strip():
                return str(val).strip()
        for v in award.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _map_awards(rs_awards: list) -> list[str]:
    """Map ResumeSDK awards to string list."""
    result = []
    for a in rs_awards:
        name = _extract_award_name(a)
        if name and name not in result:
            result.append(name)
    return result


def _map_career_signals(rs_result: dict) -> dict:
    """Derive career signals from ResumeSDK result."""
    # ResumeSDK doesn't directly provide these, we infer from available data
    has_pub = False
    pub_level = "无"
    domain_spec = ""
    research_vs_eng = "balanced"

    # Check projects/thesis for research signals
    projects = rs_result.get("project_experience", [])
    thesis = rs_result.get("thesis", [])
    if thesis or any("论文" in str(p) or "发表" in str(p) for p in projects):
        has_pub = True
        pub_level = "无"  # Can't determine level from ResumeSDK

    # Determine domain from skills
    skills = _extract_skill_names(rs_result.get("skills", []))
    skill_text = " ".join(skills).lower()
    if any(k in skill_text for k in ["图像", "分割", "检测", "视觉", "cv", "mamba", "nerf"]):
        domain_spec = "计算机视觉"
    elif any(k in skill_text for k in ["nlp", "语言", "文本", "bert", "gpt"]):
        domain_spec = "自然语言处理"
    elif any(k in skill_text for k in ["推荐", "搜索", "排序"]):
        domain_spec = "推荐系统"

    # Research vs engineering based on thesis and projects
    if thesis or has_pub:
        research_vs_eng = "research"
    elif len(projects) >= 3:
        research_vs_eng = "engineering"

    return {
        "has_publication": has_pub,
        "publication_level": pub_level,
        "competition_awards": [],
        "domain_specialization": domain_spec,
        "research_vs_engineering": research_vs_eng,
        "open_source": False,
        "internship_company_tier": "无",
    }


def _extract_skill_names(rs_skills: list) -> list[str]:
    """Extract just skill names from ResumeSDK skills."""
    names = []
    for s in rs_skills:
        if isinstance(s, dict):
            name = s.get("skill_name", "").strip()
            if name:
                names.append(name)
        elif isinstance(s, str) and s.strip():
            names.append(s.strip())
    return names


def _infer_primary_domain(rs_result: dict) -> str:
    """Infer primary_domain from ResumeSDK result, using ALL available text."""
    skills = _extract_skill_names(rs_result.get("skills", []))
    skill_text = " ".join(skills).lower()

    # Also scan project descriptions, internship descriptions, and work duty
    projects = rs_result.get("project_experience", [])
    proj_text = " ".join(str(p) for p in projects).lower()

    work = rs_result.get("work_experience", [])
    work_text = ""
    for w in work:
        if isinstance(w, dict):
            work_text += " " + w.get("job_description", "")
            work_text += " " + w.get("job_title", "")

    # Scan skills field text (ResumeSDK sometimes puts all skills in a text field)
    skills_raw = str(rs_result.get("skills", "")).lower()

    combined = skill_text + " " + proj_text + " " + work_text + " " + skills_raw

    # CV / Deep Learning — highest priority for tech resumes
    cv_signals = ["图像分割", "目标检测", "语义分割", "实例分割", "mamba", "nerf",
                  "三维重建", "计算机视觉", "opencv", "cnn", "transformer",
                  "深度学习", "pytorch", "tensorflow", "神经网络", "医学图像",
                  "影像", "图像处理", "卷积", "resnet", "unet", "yolo",
                  "心脏图像", "x光", "ct", "mri", "超声", "影像分割"]
    if any(k in combined for k in cv_signals):
        return "算法研究"

    # AI / LLM
    llm_signals = ["llm", "大模型", "rag", "agent", "langchain", "llamaindex",
                   "nlp", "自然语言处理", "bert", "gpt", "chatgpt", "openai",
                   "提示工程", "prompt", "向量数据库", "embedding"]
    if any(k in combined for k in llm_signals):
        return "AI/LLM开发"

    # Frontend
    if any(k in combined for k in ["react", "vue", "angular", "前端", "javascript", "typescript", "css", "html"]):
        return "前端开发"

    # Backend
    if any(k in combined for k in ["java", "spring", "后端", "mysql", "redis", "微服务", "go语言", "gin"]):
        return "后端开发"

    # Data
    if any(k in combined for k in ["数据分析", "数据仓库", "spark", "flink", "hadoop", "etl", "报表"]):
        return "数据工程"

    # Game
    if any(k in combined for k in ["unity", "unreal", "游戏", "ue", "cocos"]):
        return "游戏开发"

    # Security
    if any(k in combined for k in ["安全", "渗透", "密码学", "区块链", "web3"]):
        return "安全"

    # Infra
    if any(k in combined for k in ["kubernetes", "docker", "linux", "运维", "devops", "sre"]):
        return "系统/基础设施"

    # PM
    if any(k in combined for k in ["产品", "pm", "产品经理", "需求分析"]):
        return "产品设计/PM"

    return "其他"


def _supplement_skills_from_resumesdk(
    skills: list[dict],
    projects: list[str],
    internships: list[dict],
    raw_text: str,
) -> list[dict]:
    """When ResumeSDK returns too few or too coarse skills, supplement from raw text.

    Always scans raw_text (not just projects) because ResumeSDK often misses
    fine-grained skills (epoll, Reactor, STL, smart pointers, etc.) even when
    they appear prominently in the resume.
    """
    existing = {s["name"].lower() for s in skills}

    # Always supplement if we have fewer than 8 skills or the skills look too coarse
    # (e.g. only generic ones like "C++", "SQL", "Linux" without any framework/lib)
    coarse_only = all(s["name"].lower() in {"c++", "sql", "mysql", "github", "linux", "git"} for s in skills)
    if len(existing) >= 8 and not coarse_only:
        return skills

    sources: list[str] = []
    # raw_text is the most reliable source — it contains everything ResumeSDK parsed
    if raw_text:
        sources.append(raw_text)
    for p in projects:
        sources.append(str(p))
    for i in internships:
        if isinstance(i, dict):
            sources.append(i.get("highlights", ""))
            sources.append(", ".join(i.get("tech_stack", [])))

    combined = " ".join(str(s) for s in sources if s)
    supplemental = _extract_skills_from_text(combined)

    added = 0
    for skill in supplemental:
        name = skill["name"]
        if name.lower() not in existing:
            skills.append(skill)
            existing.add(name.lower())
            added += 1

    if added:
        logger.info("Supplemented %d skills from ResumeSDK raw text", added)
    return skills


def _fix_job_target(job_target: str, projects: list[str], internships: list[dict]) -> str:
    """Fix ResumeSDK job_target misclassification.

    ResumeSDK sometimes misclassifies '项目负责人' (a role inside a project description)
    as job_target. We only clear job_target if it's a pure project-role phrase with
    no hint of being a real job title.

    Do NOT clear just because job_target conflicts with technical skills —
    user's explicit 求职意向 is sacred, even if it's '项目管理'.
    """
    if not job_target:
        return ""

    # Only clear if it's a pure project-internal role (not a real position)
    pure_project_role_keywords = ["项目负责人", "技术负责人", "组长", "队长"]
    jt_stripped = job_target.strip()

    if jt_stripped in pure_project_role_keywords:
        logger.info("Clearing pure project-role misclassified as job_target: %r", job_target)
        return ""

    # '项目管理' is a legitimate job target (PM/项目经理 direction)
    # Do NOT clear it even if resume has tech background — respect user's choice.
    return job_target


def _map_resumesdk_to_profile(rs_result: dict) -> dict:
    """Convert ResumeSDK result to our internal profile format."""
    if not rs_result:
        return {}

    # ── Debug: probe where skills are hiding ──
    for k, v in rs_result.items():
        if isinstance(v, list) and len(v) > 0:
            logger.info("ResumeSDK probe: key=%s type=list len=%d sample=%s", k, len(v), str(v[0])[:100])
        elif isinstance(v, dict) and v:
            logger.info("ResumeSDK probe: key=%s type=dict keys=%s", k, list(v.keys()))

    basic = rs_result.get("basic_info", {}) or {}
    contact = rs_result.get("contact", {}) or {}
    expect = rs_result.get("expect_job", {}) or {}

    # Build job_target from expect_job
    job_target = ""
    if isinstance(expect, dict):
        job_target = expect.get("job_title", "").strip()
    elif isinstance(expect, str):
        job_target = expect.strip()

    # Education
    edu_list = rs_result.get("education", [])
    education = _map_education(edu_list)

    # Skills
    skills = _map_skills(rs_result.get("skills", []))

    # Work experience → internships
    internships = _map_internships(rs_result.get("work_experience", []))

    # Projects
    projects = _map_projects(rs_result.get("project_experience", []))

    # Certificates
    # Certificates — pass raw JSON text for regex fallback (catches CET-6 etc.)
    raw_json_text = json.dumps(rs_result, ensure_ascii=False)
    certificates = _map_certificates(rs_result.get("certificate", []), raw_json_text)

    # Awards
    awards = _map_awards(rs_result.get("award", []))

    # Fix job_target misclassification before using it for domain inference
    job_target = _fix_job_target(job_target, projects, internships)

    # Supplement skills from project/internship descriptions
    raw_text = json.dumps(rs_result, ensure_ascii=False)
    skills = _supplement_skills_from_resumesdk(skills, projects, internships, raw_text)

    # Career signals — use supplemented skills for better inference
    career_signals = _map_career_signals(rs_result)
    # Update domain specialization with supplemented skills
    skill_names = [s["name"] for s in skills]
    skill_text = " ".join(skill_names).lower()
    if any(k in skill_text for k in ["图像", "分割", "检测", "视觉", "cv", "mamba", "nerf"]):
        career_signals["domain_specialization"] = "计算机视觉"
    elif any(k in skill_text for k in ["nlp", "语言", "文本", "bert", "gpt"]):
        career_signals["domain_specialization"] = "自然语言处理"

    # Primary domain — use supplemented skills
    enriched_result = dict(rs_result)
    enriched_result["skills"] = [{"skill_name": s["name"], "skill_level": s["level"]} for s in skills]
    primary_domain = _infer_primary_domain(enriched_result)

    # Experience years
    exp_years = 0
    work_list = rs_result.get("work_experience", [])
    if work_list:
        exp_years = len(work_list)

    # Knowledge areas from supplemented skills — infer from ALL text signals, not just skill names
    knowledge_areas = []
    skill_text_lower = " ".join(skill_names).lower()
    all_text = (skill_text_lower + " " + raw_text.lower())[:3000]

    # Programming fundamentals
    if any(k in skill_names for k in ["Python", "C++", "Java", "Go", "Rust", "C"]):
        knowledge_areas.append("编程开发")

    # AI / ML
    if any(k in skill_names for k in ["PyTorch", "TensorFlow", "深度学习", "机器学习", "神经网络"]):
        knowledge_areas.append("人工智能")

    # Computer Vision
    if any(k in skill_names for k in ["图像分割", "目标检测", "计算机视觉", "OpenCV", "Mamba", "NeRF"]):
        knowledge_areas.append("计算机视觉")

    # Linux / Systems programming
    linux_sys_signals = ["linux", "epoll", "poll", "select", "reactor", "proactor",
                         "io多路复用", "系统调用", "posix", "内核", "驱动",
                         "进程", "线程", "ipc", "mmap", "零拷贝"]
    if any(k in all_text for k in linux_sys_signals):
        knowledge_areas.append("Linux系统编程")

    # Network programming / high-performance networking
    net_signals = ["tcp/ip", "socket", "udp", "http", "网络编程", "网络库",
                   "muduo", "libevent", "libuv", "nio", "非阻塞", "异步io",
                   "高并发", "高可用", "负载均衡", "反向代理", "网关"]
    if any(k in all_text for k in net_signals):
        knowledge_areas.append("网络编程")

    # C++ systems / infrastructure
    cpp_sys_signals = ["内存池", "线程池", "对象池", "tcmalloc", "jemalloc",
                       "allocator", "raii", "智能指针", "右值引用", "移动语义",
                       "stl", "模板", "元编程", "并发编程"]
    if any(k in all_text for k in cpp_sys_signals):
        knowledge_areas.append("C++系统开发")

    # Database
    db_signals = ["mysql", "redis", "mongodb", "elasticsearch", "sql", "数据库",
                  "索引", "事务", "b+树", "存储引擎", "分库分表", "主从同步"]
    if any(k in all_text for k in db_signals):
        knowledge_areas.append("数据库")

    # Data structures & algorithms
    algo_signals = ["数据结构", "算法", "leetcode", "动态规划", "图论", "树",
                    "排序", "哈希", "链表", "栈", "队列", "二叉树"]
    if any(k in all_text for k in algo_signals):
        knowledge_areas.append("数据结构与算法")

    # Distributed systems / backend infrastructure
    dist_signals = ["微服务", "分布式", "grpc", "rpc", "protobuf", "消息队列",
                    "kafka", "rabbitmq", "rocketmq", "docker", "kubernetes",
                    "k8s", "容器", "cicd", "devops"]
    if any(k in all_text for k in dist_signals):
        knowledge_areas.append("分布式系统")

    # Frontend
    if any(k in skill_names for k in ["React", "Vue", "Angular", "前端", "JavaScript", "TypeScript", "CSS", "HTML"]):
        knowledge_areas.append("前端开发")

    # Embedded
    embedded_signals = ["嵌入式", "单片机", "mcu", "arm", "rtos", "freertos",
                        "fpga", "verilog", "pcb", "can总线", "串口", "spi"]
    if any(k in all_text for k in embedded_signals):
        knowledge_areas.append("嵌入式开发")

    # Security
    sec_signals = ["安全", "渗透", "密码学", "区块链", "web3", "逆向", "漏洞"]
    if any(k in all_text for k in sec_signals):
        knowledge_areas.append("安全")

    # De-duplicate and limit
    seen = set()
    deduped = []
    for ka in knowledge_areas:
        if ka not in seen:
            seen.add(ka)
            deduped.append(ka)
    knowledge_areas = deduped[:6]  # cap at 6 to avoid UI clutter

    profile = {
        "name": basic.get("name", "").strip(),
        "job_target": job_target,
        "primary_domain": primary_domain,
        "career_signals": career_signals,
        "experience_years": exp_years,
        "education": education,
        "skills": skills,
        "knowledge_areas": knowledge_areas,
        "internships": internships,
        "projects": projects,
        "awards": awards,
        "certificates": certificates,
        "raw_text": raw_text[:6000],
        "soft_skills": {
            "_version": 2,
            "communication": None,
            "learning": None,
            "collaboration": None,
            "innovation": None,
            "resilience": None,
        },
        "_source": "resumesdk",
    }

    return profile


def parse_with_resumesdk(file_content: bytes, filename: str) -> dict | None:
    """Parse resume via ResumeSDK API. Returns profile dict or None on failure."""
    logger.info("Trying ResumeSDK for %s", filename)
    rs_result = _call_resumesdk(file_content, filename)
    if rs_result is None:
        return None

    profile = _map_resumesdk_to_profile(rs_result)
    skill_count = len(profile.get("skills", []))
    logger.info(
        "ResumeSDK success: %d skills, %d projects, %d internships",
        skill_count,
        len(profile.get("projects", [])),
        len(profile.get("internships", [])),
    )

    # Quality gate: reject if ResumeSDK returned empty/too few skills
    # (scanned PDF may return structure but miss tech details)
    if skill_count == 0:
        logger.warning("ResumeSDK returned 0 skills, treating as failure")
        return None

    return profile
