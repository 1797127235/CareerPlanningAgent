# -*- coding: utf-8 -*-
"""Interview skill loader: load direction config, allocate questions, build prompts."""
from __future__ import annotations

import logging
import re
import yaml
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

_SKILLS_DIR = Path(__file__).resolve().parent.parent / "interview_skills"
_SHARED_REF_DIR = _SKILLS_DIR / "_shared" / "references"

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def load_skill_config(skill_id: str) -> dict:
    """Load SKILL.md + categories.yml for a direction."""
    skill_dir = _SKILLS_DIR / skill_id
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")

    skill_md_path = skill_dir / "SKILL.md"
    categories_path = skill_dir / "categories.yml"

    if not skill_md_path.is_file():
        raise FileNotFoundError(f"SKILL.md not found: {skill_md_path}")
    if not categories_path.is_file():
        raise FileNotFoundError(f"categories.yml not found: {categories_path}")

    # Parse SKILL.md frontmatter + body
    raw_md = skill_md_path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(raw_md)
    if not m:
        raise ValueError(f"{skill_md_path}: missing YAML frontmatter")

    skill_meta = yaml.safe_load(m.group(1)) or {}
    skill_body = m.group(2).strip()

    # Parse categories.yml
    raw_cat = categories_path.read_text(encoding="utf-8")
    cat_data = yaml.safe_load(raw_cat) or {}

    return {
        "skill_id": skill_id,
        "meta": skill_meta,
        "body": skill_body,
        "categories": cat_data.get("categories", []),
        "follow_up_config": cat_data.get("follow_up_config", {}),
        "difficulty_distribution": cat_data.get("difficulty_distribution", {}),
    }


def calculate_allocation(
    categories: list[dict],
    total: int,
    has_resume: bool = True,
) -> dict[str, int]:
    """Distribute total questions across categories by weight.

    Rules:
    - ALWAYS_ONE: exactly 1 question if resume exists
    - CORE: get proportionally more questions (priority in deficit filling)
    - NORMAL: fill remaining
    """
    result: dict[str, int] = {}

    project_cats = [c for c in categories if c.get("priority") == "ALWAYS_ONE"]
    non_project = [c for c in categories if c.get("priority") != "ALWAYS_ONE"]

    remaining = total
    if project_cats and has_resume:
        result[project_cats[0]["key"]] = 1
        remaining -= 1

    if remaining <= 0:
        return result

    total_weight = sum(c["weight"] for c in non_project)
    if total_weight == 0:
        # Fallback: distribute evenly
        for i, c in enumerate(non_project):
            if i < remaining:
                result[c["key"]] = result.get(c["key"], 0) + 1
        return result

    # Compute proportional shares
    shares: dict[str, float] = {}
    for c in non_project:
        shares[c["key"]] = remaining * c["weight"] / total_weight

    # Floor allocation
    allocated = 0
    for c in non_project:
        key = c["key"]
        n = int(shares[key])
        result[key] = result.get(key, 0) + n
        allocated += n

    # Fill deficit: CORE first, then by fractional part descending
    deficit = remaining - allocated
    if deficit > 0:
        items = []
        for c in non_project:
            key = c["key"]
            frac = shares[key] - int(shares[key])
            priority_order = 0 if c.get("priority") == "CORE" else 1
            items.append((priority_order, -frac, key))
        items.sort()

        for i in range(deficit):
            result[items[i % len(items)][2]] += 1

    return result


def build_reference_section(categories: list[dict], max_chars: int = 2000) -> str:
    """Read ref files and build reference content for prompt."""
    # Collect unique ref files referenced by categories
    refs: set[str] = set()
    for c in categories:
        ref = c.get("ref")
        if ref:
            refs.add(ref)

    parts = []
    for ref_name in sorted(refs):
        ref_path = _SHARED_REF_DIR / ref_name
        if ref_path.is_file():
            content = ref_path.read_text(encoding="utf-8").strip()
            parts.append(f"<!-- {ref_name} -->\n{content}")
        else:
            logger.warning("Reference file not found: %s", ref_path)

    combined = "\n\n".join(parts)
    if len(combined) > max_chars:
        combined = combined[:max_chars]
        # Try to cut at a newline to avoid breaking mid-line
        last_nl = combined.rfind("\n")
        if last_nl > max_chars * 0.8:
            combined = combined[:last_nl]
        combined += "\n\n... (truncated)"

    return combined


def _build_historical_section(summaries: list[dict]) -> str:
    """Build deduplication section from past questions."""
    if not summaries:
        return ""

    lines = ["## 历史题目（请避免重复）"]
    for s in summaries:
        q = s.get("question", "")
        area = s.get("focus_area", "")
        if q:
            lines.append(f"- [{area}] {q[:120]}")
    return "\n".join(lines)


# ── Profile-aware question generation ────────────────────────────

# 常见技术关键词池，用于从项目描述/JD 中匹配技能
_TECH_KEYWORDS = [
    # C++ / 系统
    "C++", "C", "Rust", "Go", "Qt", "MFC", "OpenCV", "图像处理", "计算机视觉",
    "嵌入式", "单片机", "ARM", "RTOS", "Linux", "Unix", "epoll", "io_uring",
    "多线程", "并发", "线程池", "锁", "原子操作", "内存管理", "RAII",
    "智能指针", "内存泄漏", "Valgrind", "GDB", "调试", "Profiling",
    # Java / 后端
    "Java", "Spring", "Spring Boot", "Spring Cloud", "MyBatis", "JVM",
    "GC", "垃圾回收", "类加载", "Tomcat", "Netty", "Nginx",
    # 数据库 / 缓存
    "MySQL", "Redis", "MongoDB", "PostgreSQL", "SQL", "NoSQL",
    "索引", "事务", "锁", "分库分表", "主从复制", "缓存", "消息队列",
    "Kafka", "RabbitMQ", "RocketMQ",
    # 前端
    "JavaScript", "TypeScript", "React", "Vue", "Angular", "HTML", "CSS",
    "Webpack", "Vite", "Node.js", "npm", "yarn", "pnpm",
    "浏览器", "DOM", "虚拟DOM", "SSR", "Hydration", "微前端",
    # 算法 / AI
    "机器学习", "深度学习", "神经网络", "NLP", "CV", "推荐系统",
    "PyTorch", "TensorFlow", "Pandas", "NumPy", "Scikit-learn",
    # 工程化 / 运维
    "Docker", "Kubernetes", "K8s", "CI/CD", "Jenkins", "GitLab",
    "Git", "GitHub", "GitLab", "Linux", "Shell", "Python", "Bash",
    "微服务", "分布式", "RPC", "gRPC", "REST", "API 网关",
    "负载均衡", "注册中心", "配置中心", "监控", "Prometheus", "Grafana",
    # 测试
    "单元测试", "集成测试", "自动化测试", "Selenium", "Pytest", "JMeter",
    "性能测试", "压力测试", "接口测试", "Mock", "白盒", "黑盒",
    # 产品
    "需求分析", "用户研究", "数据分析", "AB测试", "竞品分析", "PRD",
    "Axure", "Figma", "Sketch", "SQL", "Excel", "Python",
]


def _analyze_skill_level(profile_data: dict) -> dict[str, list[str]]:
    """Analyze user's skill proficiency based on resume data.

    Returns: {"proficient": [...], "familiar": [...], "gaps": [...]}
    """
    # Extract skill names from profile
    skills_raw = profile_data.get("skills", [])
    skill_names: set[str] = set()
    for s in skills_raw:
        if isinstance(s, dict):
            name = s.get("name", "")
            if name:
                skill_names.add(name.strip().lower())
        elif isinstance(s, str):
            skill_names.add(s.strip().lower())

    # Build project text corpus for skill occurrence check
    project_texts: list[str] = []
    for p in profile_data.get("projects", []):
        if isinstance(p, dict):
            text = f"{p.get('name', '')} {p.get('description', '')} {p.get('tech_stack', '')}"
            project_texts.append(text.lower())
        elif isinstance(p, str):
            project_texts.append(p.lower())

    for it in profile_data.get("internships", []):
        if isinstance(it, dict):
            text = f"{it.get('company', '')} {it.get('role', '')} {it.get('highlights', '')}"
            project_texts.append(text.lower())

    corpus = " ".join(project_texts)

    # Classify each skill
    proficient: list[str] = []
    familiar: list[str] = []

    for skill in skill_names:
        # Check if skill appears in project descriptions
        if skill in corpus:
            proficient.append(skill)
        else:
            familiar.append(skill)

    return {
        "proficient": proficient,
        "familiar": familiar,
    }


def _extract_project_tech(profile_data: dict) -> list[str]:
    """Extract technology keywords mentioned in project descriptions."""
    tech_found: set[str] = set()

    texts: list[str] = []
    for p in profile_data.get("projects", []):
        if isinstance(p, dict):
            texts.append(f"{p.get('name', '')} {p.get('description', '')} {p.get('tech_stack', '')}")
        elif isinstance(p, str):
            texts.append(p)
    for it in profile_data.get("internships", []):
        if isinstance(it, dict):
            texts.append(f"{it.get('company', '')} {it.get('role', '')} {it.get('highlights', '')}")

    corpus = " ".join(texts)
    for kw in _TECH_KEYWORDS:
        if kw.lower() in corpus.lower():
            tech_found.add(kw)

    return sorted(tech_found)


def _build_gap_analysis(profile_data: dict, jd_text: str) -> dict[str, list[str]]:
    """Compare JD requirements with user skills to find gaps and matches."""
    if not jd_text:
        return {"matched": [], "gaps": [], "jd_skills": []}

    # Extract JD skills
    jd_skills: list[str] = []
    jd_lower = jd_text.lower()
    for kw in _TECH_KEYWORDS:
        if kw.lower() in jd_lower:
            jd_skills.append(kw)

    # Extract user skills
    user_skills: set[str] = set()
    for s in profile_data.get("skills", []):
        if isinstance(s, dict):
            name = s.get("name", "")
            if name:
                user_skills.add(name.strip().lower())
        elif isinstance(s, str):
            user_skills.add(s.strip().lower())

    # Also add project tech
    user_skills.update(t.lower() for t in _extract_project_tech(profile_data))

    matched: list[str] = []
    gaps: list[str] = []

    for jd_skill in jd_skills:
        jd_skill_lower = jd_skill.lower()
        # Fuzzy match: if any user skill contains jd_skill or vice versa
        is_matched = any(
            jd_skill_lower in us or us in jd_skill_lower
            for us in user_skills
        )
        if is_matched:
            matched.append(jd_skill)
        else:
            gaps.append(jd_skill)

    return {
        "matched": matched,
        "gaps": gaps,
        "jd_skills": jd_skills,
    }


def _build_profile_aware_section(
    profile_data: dict,
    jd_text: str,
    skill_id: str,
) -> str:
    """Build a structured profile analysis section for the prompt."""
    parts: list[str] = []

    # Skill level analysis
    skill_levels = _analyze_skill_level(profile_data)
    if skill_levels["proficient"] or skill_levels["familiar"]:
        parts.append("### 候选人技能画像")
        if skill_levels["proficient"]:
            parts.append(f"**熟练掌握（有项目实践支撑）：** {', '.join(skill_levels['proficient'][:10])}")
        if skill_levels["familiar"]:
            parts.append(f"**了解/使用过（技能列表提及但无项目细节）：** {', '.join(skill_levels['familiar'][:10])}")

    # Project tech stack
    project_tech = _extract_project_tech(profile_data)
    if project_tech:
        parts.append(f"**项目技术栈关键词：** {', '.join(project_tech[:15])}")

    # ── 成长档案联动：成长项目 ──
    growth_projects = profile_data.get("growth_projects", "")
    if growth_projects:
        parts.append(f"""
### 成长档案中的项目记录（最新）
{growth_projects[:300]}
**要求：技术题优先围绕上述真实项目出题，追问具体技术细节和问题解决过程。**""")

    # ── 成长档案联动：目标方向 gap 技能 ──
    gap_skills = profile_data.get("gap_skills", [])
    if gap_skills:
        if isinstance(gap_skills, list):
            gap_str = ", ".join(str(g) for g in gap_skills[:8])
        else:
            gap_str = str(gap_skills)
        parts.append(f"""
### 目标方向技能缺口
用户设定的职业目标需要补充：{gap_str}
**要求：至少 1 题考察这些 gap 技能的基础概念或学习意愿。**""")

    # ── 成长档案联动：发展报告结论 ──
    report_summary = profile_data.get("report_summary", "")
    if report_summary:
        parts.append(f"""
### 发展报告关键结论
{report_summary[:300]}
**要求：出题深度和方向与报告中的能力评估一致。**""")

    skill_coverage = profile_data.get("skill_coverage", {})
    if skill_coverage and isinstance(skill_coverage, dict):
        coverage_items = []
        for skill, info in list(skill_coverage.items())[:6]:
            if isinstance(info, dict):
                status = info.get("status", info.get("level", ""))
                coverage_items.append(f"{skill}: {status}")
            else:
                coverage_items.append(f"{skill}: {info}")
        if coverage_items:
            parts.append(f"**技能覆盖情况：** {', '.join(coverage_items)}")

    # Career goal label
    career_goal_label = profile_data.get("career_goal_label", "")
    if career_goal_label:
        parts.append(f"**当前职业目标：** {career_goal_label}")

    # JD gap analysis
    gap = _build_gap_analysis(profile_data, jd_text)
    if gap["jd_skills"]:
        parts.append("\n### JD 技能匹配分析")
        if gap["matched"]:
            parts.append(f"**已匹配技能：** {', '.join(gap['matched'][:10])}")
        if gap["gaps"]:
            parts.append(f"**技能缺口（JD要求但画像未体现）：** {', '.join(gap['gaps'][:8])}")

    # Direction-specific guidance
    direction_guidance = {
        "cpp-system-dev": "优先围绕 C++ 核心机制、内存管理、并发编程出题，结合候选人的项目技术栈深挖实现细节。",
        "frontend-dev": "优先围绕浏览器原理、框架深度、工程化实践出题，结合候选人用过的具体技术栈。",
        "java-backend": "优先围绕 JVM、Spring 生态、数据库、分布式出题，结合候选人的项目经验考察工程能力。",
        "algorithm": "优先围绕数据结构、算法设计、机器学习/深度学习基础出题，结合候选人的研究方向深挖。",
        "product-manager": "优先围绕需求分析、数据分析、项目管理出题，结合候选人的项目经历考察产品思维。",
        "test-development": "优先围绕测试理论、自动化测试、性能测试出题，结合候选人的技术栈考察质量意识。",
    }
    guidance = direction_guidance.get(skill_id, "")
    if guidance:
        parts.append(f"\n### 出题方向指引\n{guidance}")

    return "\n".join(parts) if parts else "（画像信息较少，请按通用标准出题）"


def build_prompt(
    skill_id: str,
    resume_text: str,
    difficulty: Literal["junior", "mid", "senior"],
    question_count: int = 5,
    follow_up_count: int = 2,
    historical_summaries: list[dict] | None = None,
    raw_resume_text: str = "",
    jd_text: str = "",
    profile_data: dict | None = None,
    weak_skills: list[str] | None = None,
    type_distribution: dict[str, int] | None = None,
) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) for question generation.

    Returns prompts ready for LLM call.
    """
    cfg = load_skill_config(skill_id)
    categories = cfg["categories"]
    has_resume = bool(resume_text and resume_text.strip() and resume_text != "（画像信息较少）")

    allocation = calculate_allocation(categories, question_count, has_resume=has_resume)

    # Build profile-aware analysis section
    profile_aware_section = ""
    if profile_data:
        profile_aware_section = _build_profile_aware_section(profile_data, jd_text, skill_id)

    # Build allocation description
    alloc_lines = []
    for c in categories:
        key = c["key"]
        if key in allocation and allocation[key] > 0:
            alloc_lines.append(f"- {c.get('label', key)}（{key}）: {allocation[key]} 题 — {c.get('description', '')}")

    allocation_text = "\n".join(alloc_lines)

    ref_section = build_reference_section(categories)
    historical_section = _build_historical_section(historical_summaries or [])

    # Difficulty distribution hint
    diff_dist = cfg.get("difficulty_distribution", {}).get(difficulty, {})
    diff_hint = ""
    if diff_dist:
        parts = []
        for k, v in diff_dist.items():
            parts.append(f"{k}: {int(v * 100)}%")
        diff_hint = f"难度分布建议：{', '.join(parts)}"

    system_prompt = f"""{cfg['body']}

## 出题规则

1. **分类分配**（基础框架，总数 {question_count} 题）：
{allocation_text}

2. **JD 优先覆盖规则（如提供了 JD，此规则优先于分类分配）**：
   - 首先提取 JD 中明确要求的技能关键词和技术方向
   - **至少 60% 的题目必须直接围绕 JD 核心技能展开**
   - 若 JD 要求的技能方向与上述分类不完全匹配，允许灵活调整：最多可将 2 题的 category 替换为 JD 相关方向（如 JD 要求"Qt/图像处理/OpenCV"而分类以系统编程为主，则至少应有 2 题围绕 Qt 开发、图像处理或 OpenCV 展开）
   - 被替换的题目仍需保持技术深度，遵循"使用经验 → 核心原理 → 边界条件 → 优化与故障"的追问链
   - 若 JD 要求与候选人简历技能不匹配，题目应考察其学习能力和迁移能力
   - 每道题的 focus_area 必须体现与 JD 的关联性

3. **画像联动出题（强制执行）**：
   - **熟练掌握的技能** → 出深度题：考察底层原理、性能优化、故障排查、设计取舍
   - **了解/使用过的技能** → 出广度题：考察核心概念、基本用法、典型场景
   - **JD要求的缺口技能** → 出基础概念题：考察学习意愿、迁移能力、基础理解
   - **项目技术栈中的技术** → 必须围绕这些技术出题，追问真实项目中的使用细节
   - 严禁对候选人不熟悉的技能出深度实现题
   - 严禁对候选人未提及的技能假设其有经验

4. **历史弱项复习（如提供）**：
   - 候选人过往面试暴露的薄弱技能，本次必须至少覆盖 1-2 个
   - 对弱项技能出"诊断+引导"题：先考察基础理解，再追问如何补强、学习计划
   - 不要因是弱项就降难度，难度仍按整体级别控制

5. **个性化要求与反幻觉约束（强制执行）**：
   - 若候选人简历中有明确的项目名称，技术题可以引用该项目名
   - **如果简历中没有明确的项目名称，严禁编造任何项目名、公司名、系统名或模块名**
   - 此时使用通用表述，如"请描述你在项目中..."、"在你做过的开发中..."
   - 禁止出现"你在'XXX项目'中提到…"指代简历中不存在的项目
   - 禁止出现 XX/YY/ZZ/AA/BB/某项目/某个公司等占位符或模糊指代
   - 所有题目必须是完整的、可回答的真实面试题

6. **难度控制**：
   - 难度级别：{difficulty}
   - {diff_hint}
   - 每题附带 `difficulty`（easy / medium / hard）

7. **追问机制**：
   - 每道主问题附带 {follow_up_count} 个 follow_ups
   - follow_up 应针对回答中的漏洞或深层原理追问，落到真实场景和可观测指标
   - 不要替候选人补全答案

8. **输出格式**（严格 JSON 数组，不要 markdown 代码块，不要解释文字）：

```json
[
  {{
    "id": "q1",
    "type": "technical",
    "category": "CPP_CORE",
    "question": "题目内容",
    "focus_area": "考察方向",
    "difficulty": "medium",
    "follow_ups": [
      "追问内容1：基于候选人回答中的漏洞继续深挖",
      "追问内容2：落到真实场景和可观测指标"
    ]
  }}
]
```

注意：`follow_ups` 必须是字符串数组，每个元素是一道追问文字。

## 参考知识库

{ref_section}
"""

    # 优先使用原始简历全文，让 LLM 自己找项目名；无原始文本则用摘要
    resume_for_llm = raw_resume_text if raw_resume_text else resume_text

    # 提取 JD 核心技能关键词，在 user prompt 中显式列出
    jd_skills_hint = ""
    if jd_text:
        # 常见技术关键词列表，用于从 JD 中提取
        tech_keywords = [
            "Qt", "MFC", "WPF", "Swing", "GUI", "界面", "控件", "自定义控件",
            "OpenCV", "图像处理", "计算机视觉", "视觉", "图像",
            "Socket", "TCP", "UDP", "USB", "串口", "CAN", "通信",
            "嵌入式", "单片机", "ARM", "RTOS", "裸机",
            "Redis", "MySQL", "数据库", "SQL",
            "Docker", "K8s", "Kubernetes", "容器",
            "微服务", "分布式", "RPC", "消息队列",
            "大数据", "Spark", "Hadoop", "Flink",
            "前端", "React", "Vue", "Angular", "HTML", "CSS", "JavaScript",
            "Python", "Go", "Java", "Rust",
            "机器学习", "深度学习", "AI", "神经网络", "NLP", "CV",
            "数据结构", "算法", "线性表", "栈", "队列", "树", "图",
            "调试", "GDB", "Valgrind", "性能分析", "Profiling",
            "多线程", "并发", "线程池", "锁", "原子操作",
            "网络编程", "epoll", "select", "poll", "IO多路复用",
            "内存管理", "RAII", "智能指针", "内存泄漏",
            "设计模式", "架构", "重构",
        ]
        found = [kw for kw in tech_keywords if kw in jd_text]
        if found:
            jd_skills_hint = f"\n**JD 核心技能关键词：** {', '.join(found[:15])}\n"

    jd_section = f"""
**岗位 JD 要求（必须优先围绕这些技能出题）：**
{jd_text[:2000] if jd_text else "（未提供 JD，请根据岗位名称和候选人画像出题）"}
{jd_skills_hint}
**重要：上述 JD 中提到的核心技能必须被题目覆盖，不能遗漏。**""" if jd_text else ""

    # Build weak skills section
    weak_section = ""
    if weak_skills:
        weak_section = f"""
### 历史薄弱技能（必须覆盖）
候选人过往面试评估中反复暴露的薄弱点：{', '.join(weak_skills)}
**要求：本次出题至少 1-2 题必须围绕上述弱项，考察其是否有针对性地补强。**"""

    # Build type distribution section
    type_section = ""
    if type_distribution:
        parts = []
        total_assigned = 0
        for t, count in type_distribution.items():
            label = {"technical": "技术题", "scenario": "场景题", "behavioral": "行为题"}.get(t, t)
            parts.append(f"{label}：{count} 题")
            total_assigned += count
        if parts:
            type_section = f"""
### 题型占比要求（用户指定）
{' / '.join(parts)}，共 {total_assigned} 题
**要求：严格按此比例分配 `type` 字段，技术题(type=technical)、场景题(type=scenario)、行为题(type=behavioral)。**"""

    user_prompt = f"""**目标岗位：** {cfg['meta'].get('name', skill_id)}
**难度级别：** {difficulty}

**候选人简历（原文）：**
{resume_for_llm if resume_for_llm else "（未提供简历）"}

{profile_aware_section}
{jd_section}
{weak_section}
{type_section}

{historical_section}

请按上述规则生成 {question_count} 道面试题，严格 JSON 数组格式。"""

    return system_prompt, user_prompt
