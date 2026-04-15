"""Coach pull-based context tools.

设计原则：coach 默认无画像知识，需要时主动调 tool 查。
由 supervisor 在调用 coach 前通过 ContextVar 注入 state 数据。
"""
from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from typing import Any, Optional

from langchain_core.tools import tool

from agent.market import available_directions, get_signal as _get_market_signal

logger = logging.getLogger(__name__)

# Supervisor 在 _make_agent_node 里 set 这些 ContextVar
_ctx_profile: ContextVar[Optional[dict]] = ContextVar("coach_profile", default=None)
_ctx_goal: ContextVar[Optional[dict]] = ContextVar("coach_goal", default=None)
_ctx_user_id: ContextVar[Optional[int]] = ContextVar("coach_user_id", default=None)


@tool
def get_user_profile() -> str:
    """获取用户的技能画像、教育背景、项目经验、就业偏好。

    何时调用：
    - 用户问"我适合什么/我能做什么/我有什么优势"
    - 需要基于用户背景给具体判断或建议
    - 用户请求"帮我梳理我的项目/技能"

    何时不调用：
    - 问候、闲聊、情绪倾诉（此时用户不需要你反引用画像）
    - 一般概念性问答
    - 用户说"好/嗯/可以"确认收到
    """
    profile = _ctx_profile.get()
    if not profile:
        return "用户尚未建立画像（未上传简历），可以建议用户去画像页上传简历"

    lines = []
    skills = profile.get("skills", [])
    if skills:
        names = [s.get("name", "") if isinstance(s, dict) else str(s) for s in skills[:10]]
        lines.append(f"技能：{', '.join(n for n in names if n)}")

    edu = profile.get("education", {})
    if isinstance(edu, dict) and edu.get("degree"):
        lines.append(f"学历：{edu.get('degree', '')} · {edu.get('major', '')}")

    projects = profile.get("projects", [])
    if projects:
        proj_parts = []
        for p in projects[:5]:
            if isinstance(p, dict):
                name = p.get("name", "")
                desc = (p.get("description", "") or "")[:100]
                if name:
                    proj_parts.append(f"{name}（{desc}）" if desc else name)
        if proj_parts:
            lines.append("项目：" + " / ".join(proj_parts))

    prefs = profile.get("preferences", {})
    if prefs:
        lines.append(f"偏好：{json.dumps(prefs, ensure_ascii=False)}")

    job_target = profile.get("job_target", "")
    if job_target:
        lines.append(f"求职意向：{job_target}")

    return "\n".join(lines) if lines else "画像数据为空"


@tool
def get_career_goal() -> str:
    """获取用户已锁定的目标岗位（如有）。

    何时调用：
    - 用户讨论具体职业方向、路径规划
    - 需要知道用户目标才能给建议

    何时不调用：
    - 泛泛的职业焦虑表达
    - 闲聊、问候
    """
    goal = _ctx_goal.get()
    if not goal:
        return "用户尚未锁定目标岗位（可以建议去图谱页探索方向）"
    return (
        f"目标岗位：{goal.get('label', '未知')}\n"
        f"图谱节点：{goal.get('node_id', '')}\n"
        f"目标区域：{goal.get('zone', '')}"
    )


@tool
def get_market_signal(direction: str) -> str:
    """查询某个职业方向的真实市场数据（2021→2024 招聘趋势）。

    参数:
        direction: 方向名或 node_id，如"后端开发"/"AI"/"cs_system_cpp"
                   （"后端"/"算法"/"devops" 等常见口语化说法会被自动规范化）

    何时调用：
    - 给用户建议时需要数据支撑
    - 用户问"这方向前景如何/市场怎么样"
    - 对比多个方向时

    何时不调用：
    - 用户明确说不想看数据
    - 方向和当前对话主题无关
    """
    try:
        signal = _get_market_signal(direction)
        if not signal:
            dirs = available_directions()
            hint = "、".join(dirs) if dirs else "（系统无数据）"
            return (
                f"「{direction}」未匹配到已有方向。"
                f"系统可查询：{hint}。"
                "请从列表中重调（别名如'后端/算法/devops'会自动规范化）；"
                "若用户问的方向真的不在列表里，直接告诉用户系统无数据，不要编造统计。"
            )

        resolved = signal.get("_resolved_family", direction)
        demand = signal.get("demand_change_pct", 0)
        salary = signal.get("salary_cagr", 0)
        timing = signal.get("timing_label", "")
        ai_label = signal.get("ai_label", "")
        top_inds = signal.get("top_industries", []) or []
        base = signal.get("baseline_year", 2021)
        cmp_yr = signal.get("compare_year", 2024)

        from datetime import date as _date
        today = _date.today()

        # 数据里的 timing_label 常含"现在"（如"现在进入正是时候"），今日已距窗口 2+ 年，替换成窗口期表述避免误导
        for stale_word in ("现在", "目前", "当下"):
            timing = timing.replace(stale_word, f"{cmp_yr} 年时")

        header = f"{resolved} 招聘趋势（观察窗口 {base}→{cmp_yr}；今日 {today.isoformat()}）"
        if resolved != direction.strip():
            header += f"  [用户说的「{direction}」解析为「{resolved}」]"

        lines = [
            header + "：",
            f"- 需求变化：{demand:+.0f}%（{cmp_yr} 相对 {base} 基线）",
            f"- 薪资年涨：{salary:+.1f}%",
            f"- 时机标签：{timing}",
        ]
        if ai_label:
            lines.append(f"- AI 渗透：{ai_label}")
        if top_inds:
            ind_names = ", ".join(
                (i.get("industry", "") or "")[:10] for i in top_inds[:3]
            )
            lines.append(f"- 主要招聘行业：{ind_names}")

        lines.append(
            f"注：以上是 {base}→{cmp_yr} 观察到的趋势，不是当前快照（今日 {today.year}-{today.month:02d}）。"
            f"回复时用「过去三年/截至 {cmp_yr}/近年」等表达，**不要用「现在/目前/当下」**——数据窗口已结束 {today.year - cmp_yr} 年。"
        )

        return "\n".join(lines)
    except Exception as e:
        logger.warning("get_market_signal(%s) failed: %s", direction, e)
        return f"查询「{direction}」市场数据失败"


@tool
def get_memory_recall(query: str = "用户偏好") -> str:
    """检索用户过往对话中的长期记忆（Mem0）。

    参数:
        query: 想找的主题，如"职业偏好"/"之前提到的项目"/"决策倾向"

    何时调用：
    - 用户说"还记得/上次聊到/我之前说过"
    - 需要用户历史偏好才能给连续性建议

    何时不调用：
    - 冷启动对话（前 2 轮）
    - 当前问题和历史无关
    """
    user_id = _ctx_user_id.get()
    if not user_id:
        return "用户上下文未注入"
    try:
        from backend.services.coach_memory import search_user_context
        memories = search_user_context(user_id, query, limit=3)
        if not memories:
            return f"未找到关于「{query}」的历史记忆"
        return "历史记忆：\n" + "\n".join(f"· {m[:150]}" for m in memories)
    except Exception as e:
        logger.warning("get_memory_recall(%s) failed user=%s: %s", query, user_id, e)
        return "记忆检索暂不可用"
