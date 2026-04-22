"""画像分析工具 — ProfileAgent 使用的 @tool 函数。"""
from __future__ import annotations

import json

from langchain_core.tools import tool


@tool
def locate_on_graph(profile_json: str) -> str:
    """图谱定位：根据用户画像数据，在268个岗位节点中找到最匹配的位置。需要传入profile的JSON字符串。"""
    try:
        profile = json.loads(profile_json)
    except (json.JSONDecodeError, TypeError):
        return "画像数据格式错误，请提供有效的JSON字符串。"

    try:
        from backend.services.graph_service import GraphService
        from backend.services.profile_service import ProfileService

        graph_svc = GraphService()
        graph_svc.load()
        profile_svc = ProfileService(graph_svc)
        result = profile_svc.locate_on_graph(profile)
    except Exception as e:
        return f"图谱定位时出错：{e}"

    if not result or not result.get("node_id"):
        return "未能在图谱中定位到匹配岗位。请检查画像数据是否完整（需要技能、项目经验等信息）。"

    lines = [
        f"最佳匹配岗位: {result.get('label', '')}",
        f"匹配分数: {result.get('score', 0):.2f}",
        f"职业族群置信度: {result.get('family_confidence', 0):.2f}",
        "",
        "Top-5 候选岗位：",
    ]

    candidates = result.get("candidates", [])
    for i, c in enumerate(candidates, 1):
        lines.append(f"  {i}. {c.get('label', '?')}（得分: {c.get('score', 0):.4f}）")

    return "\n".join(lines)


@tool
def get_user_profile(profile_id: int) -> str:
    """查看画像：读取用户保存的能力画像摘要信息。"""
    try:
        from backend.db import SessionLocal
        from backend.models import Profile

        db = SessionLocal()
        try:
            profile = db.query(Profile).filter_by(id=profile_id).first()
        finally:
            db.close()
    except Exception as e:
        return f"读取画像时出错：{e}"

    if profile is None:
        return f"未找到 ID 为 {profile_id} 的画像记录。"

    try:
        data = json.loads(profile.profile_json) if isinstance(profile.profile_json, str) else profile.profile_json
    except (json.JSONDecodeError, TypeError):
        data = {}

    basic = data.get("basic_info", {})
    name = basic.get("name", profile.name or "未知")
    edu = basic.get("education", "N/A")
    major = basic.get("major", "N/A")

    skills = data.get("skills", [])
    skill_names = []
    for s in skills[:10]:
        if isinstance(s, dict):
            skill_names.append(f"{s.get('name', '?')}({s.get('level', '')})")
        else:
            skill_names.append(str(s))

    lines = [
        f"画像 #{profile_id} — {name}",
        f"  学历: {edu} · 专业: {major}",
        f"  来源: {profile.source}",
        f"  技能: {', '.join(skill_names) if skill_names else '无'}",
    ]

    projects = data.get("projects", [])
    if projects:
        lines.append(f"  项目: {len(projects)} 个")

    return "\n".join(lines)


@tool
def score_profile(profile_json: str, node_id: str) -> str:
    """四维度评分：评估用户画像与目标岗位的匹配程度，从基础要求、职业技能、职业素养、发展潜力四个维度打分。"""
    try:
        profile = json.loads(profile_json)
    except (json.JSONDecodeError, TypeError):
        return "画像数据格式错误，请提供有效的JSON字符串。"

    if not node_id or not node_id.strip():
        return "需要指定目标岗位的 node_id 才能进行评分。"

    try:
        from backend.services.graph_service import GraphService
        from backend.services.profile_service import ProfileService

        graph_svc = GraphService()
        graph_svc.load()
        target_node = graph_svc.get_node(node_id.strip())
        if target_node is None:
            return f"未找到 node_id='{node_id}' 对应的岗位节点。"

        profile_svc = ProfileService(graph_svc)
        result = profile_svc.score_four_dimensions(profile, target_node)
    except Exception as e:
        return f"四维度评分时出错：{e}"

    lines = [
        f"目标岗位: {target_node.get('label', node_id)}",
        "",
        "四维度匹配评分：",
    ]

    dim_names = {"basic": "基础要求", "skills": "职业技能", "qualities": "职业素养", "potential": "发展潜力"}
    for key, name in dim_names.items():
        dim = result.get(key, {})
        score = dim.get("score", 0)
        lines.append(f"  {name}: {score:.0f}/100")
        detail = dim.get("detail", "")
        if detail:
            lines.append(f"    {detail}")

    overall = result.get("overall_score", result.get("weighted_score", 0))
    lines.append(f"\n综合得分: {overall:.0f}/100")

    return "\n".join(lines)
