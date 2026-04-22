"""图谱导航工具 — NavigatorAgent 使用的 @tool 函数。"""
from __future__ import annotations

from langchain_core.tools import tool


@tool
def search_jobs(keyword: str) -> str:
    """搜索岗位：按关键词搜索岗位图谱中的岗位节点。返回匹配的岗位列表。"""
    try:
        from backend.services.graph import GraphService

        svc = GraphService()
        svc.load()
        results = svc.search_nodes(keyword)
    except Exception as e:
        return f"搜索岗位时出错：{e}"

    if not results:
        return f"未找到与'{keyword}'相关的岗位。"

    lines: list[str] = []
    for r in results[:8]:
        lines.append(f"- {r.get('label', '?')}（{r.get('role_family', '')}）")
    total = len(results)
    shown = min(total, 8)
    header = f"找到 {total} 个相关岗位" + (f"（显示前 {shown} 个）：" if total > 8 else "：")
    return header + "\n" + "\n".join(lines)


@tool
def recommend_jobs(user_skills: str, preferences_json: str = "") -> str:
    """技能匹配推荐：根据用户技能列表和就业意愿，推荐最匹配的岗位。user_skills为逗号分隔的技能列表，preferences_json为可选的意愿JSON。"""
    skills = [s.strip() for s in user_skills.split(",") if s.strip()]
    if not skills:
        return "请提供技能列表（逗号分隔）。"

    preferences = None
    if preferences_json:
        try:
            import json
            preferences = json.loads(preferences_json)
        except (json.JSONDecodeError, TypeError):
            pass

    try:
        from backend.services.graph import GraphService

        svc = GraphService()
        svc.load()
        results = svc.recommend_by_skills(skills, top_n=5, preferences=preferences)
    except Exception as e:
        return f"推荐岗位时出错：{e}"

    if not results:
        return "未找到与你技能匹配的岗位。"

    lines = [f"根据你的技能和意愿，匹配度最高的 {len(results)} 个方向：\n"]
    for r in results:
        overlap = r.get("overlap_skills", [])
        missing = r.get("missing_skills", [])
        total = len(overlap) + len(missing)
        readiness = round(len(overlap) / total * 100) if total else 0

        lines.append(f"【{r.get('label', '?')}】（{r.get('role_family', '')}）")
        lines.append(f"  准备度: {readiness}%（已具备 {len(overlap)}/{total} 项核心技能）")

        # AI safety context
        rp = r.get("replacement_pressure")
        hal = r.get("human_ai_leverage")
        if rp is not None:
            lines.append(f"  AI替代压力: {rp}/100  人类杠杆: {hal}/100  安全区: {r.get('zone', '?')}")

        # Strategic fields (from enriched graph data)
        market = r.get("market_insight", "")
        if market:
            lines.append(f"  市场洞察: {market}")

        ai_narrative = r.get("ai_impact_narrative", "")
        if ai_narrative:
            lines.append(f"  AI影响分析: {ai_narrative}")

        diff_advice = r.get("differentiation_advice", "")
        if diff_advice:
            lines.append(f"  差异化建议: {diff_advice}")

        employers = r.get("typical_employers", [])
        if employers:
            lines.append(f"  典型雇主: {', '.join(employers[:6])}")

        barrier = r.get("entry_barrier", "")
        if barrier:
            lines.append(f"  应届进入门槛: {barrier}")

        ceiling = r.get("career_ceiling", "")
        if ceiling:
            lines.append(f"  发展天花板: {ceiling}")

        projects = r.get("project_recommendations", [])
        if projects:
            proj_strs = [f"{p['name']}({p.get('why', '')})" for p in projects[:3] if isinstance(p, dict)]
            if proj_strs:
                lines.append(f"  推荐项目: {'; '.join(proj_strs)}")

        # Promotion path
        promo = r.get("promotion_path", [])
        if promo:
            path_str = " -> ".join(p.get("title", "?") for p in promo)
            lines.append(f"  晋升路线: {path_str}")

        # Brief gap info (de-emphasized)
        if missing:
            lines.append(f"  待补技能({len(missing)}): {', '.join(missing[:5])}")
        lines.append("")

    return "\n".join(lines)


@tool
def get_job_detail(job_name: str) -> str:
    """查看岗位详情：查询岗位图谱中指定岗位的详细信息，包括技能要求、AI影响评分等。"""
    try:
        from backend.services.graph import GraphService

        svc = GraphService()
        svc.load()
        node = svc.get_node_by_label(job_name)
    except Exception as e:
        return f"查询岗位详情时出错：{e}"

    if node is None:
        return f"未找到名为'{job_name}'的岗位。可以用搜索工具先查找。"

    lines = [f"【{node.get('label', job_name)}】"]

    # Description
    desc = node.get("description", "")
    if desc:
        lines.append(f"  简介: {desc}")

    lines.append(f"  职业族群: {node.get('role_family', 'N/A')}")

    # Core tasks
    tasks = node.get("core_tasks", [])
    if tasks:
        lines.append(f"  日常工作: {', '.join(tasks)}")

    # AI scores
    rp = node.get("replacement_pressure", node.get("ai_exposure"))
    hal = node.get("human_ai_leverage", node.get("human_premium"))
    zone = node.get("zone", "N/A")
    lines.append(f"  AI替代压力: {rp}/100（越低越安全）")
    lines.append(f"  人类杠杆: {hal}/100（越高说明AI越能增强你的能力）")
    lines.append(f"  安全区: {zone}")

    # Strategic fields
    market = node.get("market_insight", "")
    if market:
        lines.append(f"  市场洞察: {market}")

    ai_narrative = node.get("ai_impact_narrative", "")
    if ai_narrative:
        lines.append(f"  AI影响分析: {ai_narrative}")

    diff_advice = node.get("differentiation_advice", "")
    if diff_advice:
        lines.append(f"  差异化建议: {diff_advice}")

    employers = node.get("typical_employers", [])
    if employers:
        lines.append(f"  典型雇主: {', '.join(employers[:6])}")

    barrier = node.get("entry_barrier", "")
    if barrier:
        lines.append(f"  应届进入门槛: {barrier}")

    ceiling = node.get("career_ceiling", "")
    if ceiling:
        lines.append(f"  发展天花板: {ceiling}")

    projects = node.get("project_recommendations", [])
    if projects:
        for p in projects[:3]:
            if isinstance(p, dict):
                lines.append(f"  推荐项目: {p.get('name', '?')} — {p.get('why', '')}（难度: {p.get('difficulty', '?')}）")

    # Skills
    must_skills = node.get("must_skills", [])
    if must_skills:
        lines.append(f"  核心技能: {', '.join(must_skills[:10])}")

    # Promotion path
    promo = node.get("promotion_path", [])
    if promo:
        path_str = " -> ".join(p.get("title", "?") for p in promo)
        lines.append(f"  晋升路线: {path_str}")

    # Related majors
    majors = node.get("related_majors", [])
    if majors:
        lines.append(f"  相关专业: {', '.join(majors)}")

    return "\n".join(lines)


@tool
def get_escape_routes(node_id: str) -> str:
    """逃生路线：从指定图谱节点出发，计算最佳转型路径。需要提供当前所在岗位的node_id。"""
    if not node_id or not node_id.strip():
        return "需要先定位你在图谱中的位置，才能计算逃生路线。请先完成画像分析。"

    try:
        from backend.services.graph import GraphService

        svc = GraphService()
        svc.load()
        routes = svc.find_escape_routes(node_id.strip())
    except Exception as e:
        return f"计算逃生路线时出错：{e}"

    if not routes:
        return f"从'{node_id}'出发未找到可行的逃生路线。可能当前位置已经比较安全。"

    lines = [f"从当前位置出发，找到 {len(routes)} 条转型路线：\n"]
    for i, route in enumerate(routes, 1):
        tag = route.get("tag", "")
        tag_str = f"[{tag}] " if tag else ""
        lines.append(
            f"{i}. {tag_str}{route.get('target_label', route.get('target', '?'))}"
        )
        lines.append(f"   安全区: {route.get('target_zone', 'N/A')}")
        lines.append(f"   安全增益: {route.get('safety_gain', 0):+.1f}")
        lines.append(f"   总转型成本: {route.get('total_cost', 'N/A')}")

        gap_skills = route.get("gap_skills", [])
        if gap_skills:
            skill_names = [g["name"] if isinstance(g, dict) else str(g) for g in gap_skills[:5]]
            lines.append(f"   需补技能: {', '.join(skill_names)}")
        lines.append(f"   预估学习时长: {route.get('total_hours', 'N/A')}小时")
        lines.append("")

    return "\n".join(lines)
