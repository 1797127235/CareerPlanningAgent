"""JD 搜索工具 — 用 Tavily API 搜索互联网真实招聘 JD。

参考 JobMatch-AI (github.com/FelixNg1022/JobMatch-AI) 的三层过滤：
1. 聚合站域名黑名单
2. 文章/博客/列表页检测
3. JD 内容验证（包含岗位职责/任职要求关键词）
"""
from __future__ import annotations

import json
import logging
import re

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ── Layer 1: Aggregator domain blocklist ─────────────────────────────────────
# Inspired by JobMatch-AI's 37-item list, extended with Chinese job sites

# Block search/listing pages and non-job content, but ALLOW individual JD detail pages
_BLOCKED_DOMAINS = [
    # JD template / sample sites (not real postings)
    "youzhuo.io", "pvuik.com", "meijob.com", "zhiyeapp.com",
    # Social / forum / Q&A (not job postings)
    "reddit.com", "zhihu.com", "v2ex.com",
    "jianshu.com", "juejin.cn", "csdn.net/blog",
    # International aggregators (not relevant for Chinese market)
    "linkedin.com", "indeed.com", "glassdoor.com", "monster.com",
    "ziprecruiter.com", "simplyhired.com",
    # Low-quality / off-topic sources
    "gaoxiaojob.com",   # 高校人才网 — content quality poor, includes non-tech roles
    "yingjiesheng.com", # 应届生求职网 — often outdated
    "jobui.com",        # content thin
]

# Search/listing page URL patterns to block (individual JD pages are allowed)
_LISTING_PAGE_PATTERNS = [
    r"zhipin\.com/web/geek/job\?",  # BOSS搜索页
    r"zhipin\.com/\?",
    r"search\.51job\.com",          # 51job搜索
    r"sou\.zhaopin\.com",           # 智联搜索
    r"liepin\.com/zhaopin/",        # 猎聘列表
    r"lagou\.com/zhaopin/",         # 拉钩列表
    r"/jobs\?", r"/jobs/search", r"/joblist",
]

# ── Layer 2: Article / blog / guide detection ────────────────────────────────

_ARTICLE_PATTERNS = [
    r"/blog/", r"/article/", r"/news/", r"/guide",
    r"complete.guide", r"how.to", r"tutorial",
    r"薪资报告", r"行业分析", r"面经",
]

# ── Layer 3: JD content verification ─────────────────────────────────────────

_JD_INDICATORS_ZH = ["岗位职责", "任职要求", "职位描述", "技能要求", "工作职责", "职位要求", "招聘"]
_JD_INDICATORS_EN = ["responsibilities", "requirements", "qualifications", "apply now", "hiring"]


def _is_blocked(url: str) -> bool:
    """Check if URL is a blocked site, listing page, or article."""
    url_lower = url.lower()
    # Domain blocklist (non-job sites)
    if any(d in url_lower for d in _BLOCKED_DOMAINS):
        return True
    # Search/listing page patterns (individual JD pages pass through)
    if any(re.search(p, url_lower) for p in _LISTING_PAGE_PATTERNS):
        return True
    # Article/guide detection
    if any(re.search(p, url_lower) for p in _ARTICLE_PATTERNS):
        return True
    return False


def _looks_like_jd(text: str) -> bool:
    """Verify content actually contains job posting indicators."""
    text_lower = text.lower()
    return (
        any(ind in text_lower for ind in _JD_INDICATORS_ZH)
        or any(ind in text_lower for ind in _JD_INDICATORS_EN)
    )


def _extract_requirements(text: str) -> str:
    """Extract technical requirements section, filter salary/benefits noise."""
    patterns = [
        r"(?:任职要求|岗位要求|职位要求|技能要求|Requirements)[\s:：]*([\s\S]{30,800}?)(?:薪资|福利|待遇|工作地|联系|投递|公司介绍|$)",
        r"(?:岗位职责|工作职责|Job Description)[\s:：]*([\s\S]{30,800}?)(?:薪资|福利|待遇|$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return text[:500].strip()


def _extract_skills(text: str) -> list[str]:
    """Extract skill keywords from JD text."""
    known_skills = [
        "C++", "C", "Java", "Python", "Go", "Rust", "JavaScript", "TypeScript",
        "React", "Vue", "Node.js", "Spring", "Django", "Flask",
        "Linux", "Docker", "K8s", "Kubernetes", "AWS", "MySQL", "Redis", "MongoDB",
        "Git", "CI/CD", "微服务", "分布式", "多线程", "高并发",
        "机器学习", "深度学习", "NLP", "计算机视觉", "TensorFlow", "PyTorch",
        "数据结构", "算法", "设计模式", "网络编程", "操作系统",
        "Unity", "Unreal", "OpenGL", "Vulkan", "Qt", "MFC",
        "嵌入式", "RTOS", "STM32", "ARM", "FPGA",
    ]
    found = []
    text_upper = text.upper()
    for skill in known_skills:
        if skill.upper() in text_upper or skill in text:
            found.append(skill)
    return found[:8]


# ── Official career sites loader ─────────────────────────────────────────────

def _load_career_sites() -> dict:
    """Load official career sites config from YAML.

    Returns:
        alias_map:        {alias -> campus_domain}
        all_campus:       all campus_domain values (default search scope)
        all_social:       all social domain values (fallback)
    """
    import os
    import yaml
    config_path = os.path.join(os.path.dirname(__file__), "career_sites.yaml")
    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        alias_map: dict[str, str] = {}
        all_campus: list[str] = []
        all_social: list[str] = []
        for site in data.get("sites", {}).values():
            campus = site.get("campus_domain", site.get("domain", ""))
            social = site.get("domain", "")
            if campus:
                all_campus.append(campus)
            if social and social not in all_social:
                all_social.append(social)
            for alias in site.get("aliases", []):
                if campus:
                    alias_map[str(alias).lower()] = campus
        return {"alias_map": alias_map, "all_campus": all_campus, "all_social": all_social}
    except Exception as e:
        logger.warning("Failed to load career_sites.yaml: %s", e)
        return {"alias_map": {}, "all_campus": [], "all_social": []}


@tool
def search_real_jd(query: str) -> str:
    """搜索真实JD：只从官方招聘网站搜索真实招聘岗位，返回结构化JSON。
    输入搜索关键词（如"字节跳动 后端工程师 校招"或"腾讯 C++ 校园招聘"）。
    重要：应届生用户请在关键词中加"校招"或"校园招聘"，否则会返回社招职位（要求工作经验）。
    返回格式为 [JD_SEARCH_RESULTS:json] 标记，前端会渲染为可点击的卡片。
    """
    if not query or not query.strip():
        return "请提供搜索关键词，如'C++ 后端开发'。"

    try:
        import os
        from tavily import TavilyClient

        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            return "未配置 TAVILY_API_KEY，无法搜索。请在 .env 中添加。"

        client = TavilyClient(api_key=api_key)

        # Load official sites config
        sites_config = _load_career_sites()
        alias_map: dict = sites_config["alias_map"]
        all_campus: list = sites_config["all_campus"]

        # Detect company-specific query → restrict to that company's campus domain
        query_lower = query.lower()
        matched_domain = next(
            (domain for alias, domain in alias_map.items() if alias in query_lower),
            None
        )
        # Default: campus domains only (no social hire results)
        include_domains = [matched_domain] if matched_domain else all_campus

        search_query = f"{query.strip()} 招聘 岗位职责 任职要求"
        response = client.search(
            query=search_query,
            search_depth="advanced",
            max_results=10,
            include_answer=False,
            include_domains=include_domains,  # Campus recruitment domains only
        )

        raw_results = response.get("results", [])
        if not raw_results:
            company_hint = f"「{matched_domain}」校招页" if matched_domain else "各大厂校招官网"
            return f"在{company_hint}未搜到与'{query}'相关的校招岗位，可能该职位本季度未开放校招，建议关注秋招/春招窗口期。"

        # Filter: must look like actual JD content
        filtered = [r for r in raw_results if _looks_like_jd(r.get("content", ""))]
        if not filtered:
            filtered = raw_results[:3]

        # Build structured results
        jd_cards = []
        for r in filtered[:5]:
            content = r.get("content", "")
            requirements = _extract_requirements(content)
            skills = _extract_skills(content)

            jd_cards.append({
                "title": r.get("title", "未知职位"),
                "url": r.get("url", ""),
                "source": _get_domain(r.get("url", "")),
                "skills": skills,
                "requirements": requirements,
                "full_text": content[:1000],
            })

        # Return structured marker for frontend rendering
        marker = f"[JD_SEARCH_RESULTS:{json.dumps(jd_cards, ensure_ascii=False)}]"
        summary = f"搜到 {len(jd_cards)} 份相关招聘，你可以选择感兴趣的做匹配度诊断。"
        return f"{summary}\n{marker}"

    except ImportError:
        return "未安装 tavily-python，请运行: pip install tavily-python"
    except Exception as e:
        logger.exception("Tavily search failed")
        return f"搜索时出错：{e}"


def _get_domain(url: str) -> str:
    """Extract readable domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # Remove www prefix
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return url[:30]
