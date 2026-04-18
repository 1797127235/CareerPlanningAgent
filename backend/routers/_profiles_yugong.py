"""愚公AI (ygys.net) 简历解析 API client — SOAP WebService.

API: http://service.ygys.net/resumeservice.asmx
Method: TransResumeByJsonStringForFileBase64(username, pwd, content, ext)
Returns: JSON string with ResumeInfo structure.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any

import requests

from backend.config import RESUMESDK_APPKEY, RESUMESDK_APPSECRET

logger = logging.getLogger(__name__)

_TIMEOUT = 60
_SOAP_URL = "http://service.ygys.net/resumeservice.asmx"


def _call_yugong(file_content: bytes, filename: str) -> dict | None:
    """Call 愚公AI API and return parsed result dict."""
    username = RESUMESDK_APPKEY
    pwd = RESUMESDK_APPSECRET
    if not username or not pwd:
        logger.warning("愚公AI credentials not configured (need APPKEY + APPSECRET)")
        return None

    ext = filename.rsplit(".", 1)[-1] if "." in filename else "pdf"
    b64_cont = base64.b64encode(file_content).decode("ascii")

    # SOAP request body
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <TransResumeByJsonStringForFileBase64 xmlns="http://tempuri.org/">
      <username>{username}</username>
      <pwd>{pwd}</pwd>
      <content>{b64_cont}</content>
      <ext>{ext}</ext>
    </TransResumeByJsonStringForFileBase64>
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/TransResumeByJsonStringForFileBase64",
    }

    try:
        resp = requests.post(
            _SOAP_URL,
            headers=headers,
            data=soap_body.encode("utf-8"),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning("愚公AI request timed out after %ds", _TIMEOUT)
        return None
    except requests.exceptions.RequestException as e:
        logger.warning("愚公AI request failed: %s", e)
        return None

    # Parse SOAP response to extract JSON string
    try:
        # The response contains: <TransResumeByJsonStringForFileBase64Result>{json}</TransResumeByJsonStringForFileBase64Result>
        text = resp.text
        start_tag = "<TransResumeByJsonStringForFileBase64Result>"
        end_tag = "</TransResumeByJsonStringForFileBase64Result>"
        start = text.find(start_tag)
        end = text.find(end_tag)
        if start == -1 or end == -1:
            logger.warning("愚公AI SOAP response missing expected tags")
            return None
        json_str = text[start + len(start_tag):end]
        # The JSON may be XML-escaped
        json_str = json_str.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        result = json.loads(json_str)
        if not result:
            logger.warning("愚公AI returned empty JSON")
            return None
        return result
    except json.JSONDecodeError as e:
        logger.warning("愚公AI returned invalid JSON: %s", e)
        return None
    except Exception as e:
        logger.warning("愚公AI response parsing failed: %s", e)
        return None


# ── Field mapping: 愚公AI → our profile format ───────────────────────────────

_LEVEL_MAP = {
    "精通": "advanced",
    "熟练": "intermediate",
    "熟悉": "familiar",
    "了解": "beginner",
    "一般": "beginner",
}


def _parse_skills(skill_text: str) -> list[dict]:
    """Parse 愚公AI skill text like 'Python、PyTorch、深度学习' into skill list."""
    if not skill_text:
        return []
    # Split by common separators
    separators = ["、", ",", ";", "；", " ", "|", "/"]
    parts = [skill_text]
    for sep in separators:
        new_parts = []
        for p in parts:
            new_parts.extend([s.strip() for s in p.split(sep) if s.strip()])
        parts = new_parts

    # Deduplicate while preserving order
    seen: set[str] = set()
    result = []
    for name in parts:
        key = name.lower()
        if key not in seen and len(name) >= 1:
            seen.add(key)
            result.append({"name": name, "level": "familiar"})
    return result


def _parse_it_skills(it_skills: list[dict] | None) -> list[dict]:
    """Parse ITSkills array from 愚公AI."""
    if not it_skills:
        return []
    result = []
    for s in it_skills:
        if not isinstance(s, dict):
            continue
        name = s.get("SkillType", "").strip()
        level_raw = s.get("CompetencyLevel", "").strip()
        if not name:
            continue
        level = _LEVEL_MAP.get(level_raw, "familiar")
        result.append({"name": name, "level": level})
    return result


def _map_yugong_to_profile(yg_result: dict) -> dict:
    """Convert 愚公AI result to our internal profile format."""
    if not yg_result:
        return {}

    # Handle nested structure
    data = yg_result.get("ResumeInfo", yg_result)
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        data = yg_result

    # Basic info (use `or ""` to handle None values from API)
    name = str(data.get("Name") or "").strip()
    job_target = str(data.get("Title") or "").strip()
    major = str(data.get("Speciality") or "").strip()
    school = str(data.get("School") or "").strip()
    degree = str(data.get("AdvancedDegree") or "").strip()
    edu_level = str(data.get("Education") or "").strip()

    def _safe_list(key: str) -> list:
        """Get a list field, treating None/scalar as empty/single-item list."""
        v = data.get(key)
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        if isinstance(v, list):
            return v
        return []

    # Skills from multiple sources
    skills: list[dict] = []
    # 1. Skill field (free text like "Python、PyTorch、深度学习")
    skill_text = str(data.get("Skill") or "").strip()
    skills.extend(_parse_skills(skill_text))
    # 2. ITSkills (structured array)
    skills.extend(_parse_it_skills(_safe_list("ITSkills")))

    # Education
    education = {"degree": degree or edu_level, "major": major, "school": school}

    # Work experience → internships
    internships: list[dict] = []
    for exp in _safe_list("ExperienceDetail"):
        if not isinstance(exp, dict):
            continue
        company = str(exp.get("Company") or "").strip()
        if not company:
            continue
        desc = str(exp.get("Summary") or "").strip()
        # Extract tech stack from description
        tech_stack: list[str] = []
        if desc:
            for tech in ["Python", "PyTorch", "C++", "TensorFlow", "OpenCV", "Mamba", "NeRF", "CUDA", "Git"]:
                if tech.lower() in desc.lower():
                    tech_stack.append(tech)
        internships.append({
            "company": company,
            "role": str(exp.get("Title") or "").strip(),
            "duration": f"{exp.get('StartDate') or ''}-{exp.get('EndDate') or ''}".strip("-"),
            "tech_stack": tech_stack[:5],
            "highlights": desc[:200],
        })

    # Projects
    projects: list[str] = []
    for proj in _safe_list("ProjectDetail"):
        if not isinstance(proj, dict):
            continue
        proj_name = str(proj.get("ProjectName") or "").strip()
        proj_desc = str(proj.get("ProjectDescription") or "").strip()
        proj_duty = str(proj.get("Responsibilities") or "").strip()
        if proj_name or proj_desc:
            text = " ".join(p for p in [proj_name, proj_desc, proj_duty] if p)
            if text:
                projects.append(text)

    # Certificates
    certificates: list[str] = []
    # English certs
    for e in _safe_list("GradeOfEnglish"):
        if isinstance(e, dict):
            cert_name = str(e.get("NameOfCertificate") or "").strip()
            score = str(e.get("Score") or "").strip()
            if cert_name:
                if score:
                    certificates.append(f"{cert_name}({score})")
                else:
                    certificates.append(cert_name)
    # Language certs
    for l in _safe_list("LanguagesSkills"):
        if isinstance(l, dict):
            lang = str(l.get("Languages") or "").strip()
            score = str(l.get("Score") or "").strip()
            if lang:
                cert = f"{lang}"
                if score:
                    cert += f"({score})"
                certificates.append(cert)
    # Other certs
    other_certs = str(data.get("Certificate") or "").strip()
    if other_certs:
        for c in other_certs.split("、"):
            c = c.strip()
            if c and c not in certificates:
                certificates.append(c)

    # Awards
    awards: list[str] = []
    encouragement = str(data.get("Encouragement") or "").strip()
    if encouragement:
        awards.append(encouragement)

    # Career signals
    domain_spec = ""
    skill_names = [s["name"] for s in skills]
    skill_text_lower = " ".join(skill_names).lower()
    proj_text = " ".join(projects).lower()
    if any(k in skill_text_lower for k in ["图像", "分割", "检测", "视觉", "mamba", "nerf"]):
        domain_spec = "计算机视觉"
    elif any(k in skill_text_lower for k in ["nlp", "语言", "文本", "bert", "gpt"]):
        domain_spec = "自然语言处理"

    # Primary domain
    combined = skill_text_lower + " " + proj_text
    if any(k in combined for k in ["图像分割", "目标检测", "mamba", "nerf", "深度学习", "pytorch", "计算机视觉"]):
        primary_domain = "算法研究"
    elif any(k in combined for k in ["llm", "大模型", "rag", "agent"]):
        primary_domain = "AI/LLM开发"
    elif any(k in combined for k in ["react", "vue", "前端", "javascript"]):
        primary_domain = "前端开发"
    elif any(k in combined for k in ["java", "spring", "后端"]):
        primary_domain = "后端开发"
    else:
        primary_domain = "其他"

    # Experience years
    exp_years = 0
    try:
        exp_str = str(data.get("Experience", "0")).strip()
        exp_years = int(float(exp_str))
    except (ValueError, TypeError):
        pass

    # Knowledge areas
    knowledge_areas: list[str] = []
    if any(k in skill_names for k in ["Python", "C++", "Java"]):
        knowledge_areas.append("编程开发")
    if any(k in skill_names for k in ["PyTorch", "TensorFlow", "深度学习", "机器学习"]):
        knowledge_areas.append("人工智能")
    if any(k in skill_names for k in ["图像分割", "目标检测", "计算机视觉"]):
        knowledge_areas.append("计算机视觉")

    profile = {
        "name": name,
        "job_target": job_target,
        "primary_domain": primary_domain,
        "career_signals": {
            "has_publication": False,
            "publication_level": "无",
            "competition_awards": [],
            "domain_specialization": domain_spec,
            "research_vs_engineering": "balanced",
            "open_source": False,
            "internship_company_tier": "无",
        },
        "experience_years": exp_years,
        "education": education,
        "skills": skills,
        "knowledge_areas": knowledge_areas,
        "internships": internships,
        "projects": projects,
        "awards": awards,
        "certificates": certificates,
        "raw_text": json.dumps(yg_result, ensure_ascii=False)[:6000],
        "soft_skills": {
            "_version": 2,
            "communication": None,
            "learning": None,
            "collaboration": None,
            "innovation": None,
            "resilience": None,
        },
        "_source": "yugong",
    }

    return profile


def parse_with_yugong(file_content: bytes, filename: str) -> dict | None:
    """Parse resume via 愚公AI API. Returns profile dict or None on failure."""
    logger.info("Trying 愚公AI (ygys.net) for %s", filename)
    yg_result = _call_yugong(file_content, filename)
    if yg_result is None:
        return None

    profile = _map_yugong_to_profile(yg_result)
    skill_count = len(profile.get("skills", []))
    logger.info(
        "愚公AI success: %d skills, %d projects, %d internships",
        skill_count,
        len(profile.get("projects", [])),
        len(profile.get("internships", [])),
    )

    # Quality gate
    if skill_count == 0:
        logger.warning("愚公AI returned 0 skills, treating as failure")
        return None

    return profile
