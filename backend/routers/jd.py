"""JD diagnosis router — submit JD text, get diagnosis + history."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import JDDiagnosis, Profile, User
from backend.services.graph_service import get_graph_service
from backend.services.jd_service import JDService

router = APIRouter()
_jd_svc = JDService()


class DiagnoseRequest(BaseModel):
    jd_text: str
    jd_title: str | None = None


@router.post("/diagnose")
def diagnose(
    req: DiagnoseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit JD text, return diagnosis (profile inferred from current user)."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先上传简历建立画像")
    profile_id = profile.id

    profile_data = json.loads(profile.profile_json or "{}")
    result = _jd_svc.diagnose(req.jd_text, profile_data)

    # Use LLM-extracted title, fall back to user-provided or default
    auto_title = result.pop("jd_title", None)
    title = req.jd_title or auto_title or "JD 诊断"

    # Attach graph context: map JD to graph node + escape routes
    graph_context = None
    extracted = result.get("extracted_skills", [])
    if extracted:
        try:
            graph = get_graph_service(db)
            graph_match = _jd_svc.match_to_graph_node(extracted, graph)
            if graph_match:
                node = graph.get_node(graph_match["node_id"])
                profile_skills = [
                    s.get("name", s) if isinstance(s, dict) else s
                    for s in profile_data.get("skills", [])
                ]
                raw_routes = graph.find_escape_routes(
                    graph_match["node_id"],
                    profile_skills=profile_skills,
                    db_session=db,
                )
                graph_context = {
                    "node_id": graph_match["node_id"],
                    "label": graph_match["label"],
                    "zone": node.get("zone", "transition") if node else "transition",
                    "replacement_pressure": node.get("replacement_pressure", 50) if node else 50,
                    "human_ai_leverage": node.get("human_ai_leverage", 50) if node else 50,
                    "escape_routes": [
                        {
                            "target_label": r.get("target_label", ""),
                            "target_zone": r.get("target_zone", "transition"),
                            "tag": r.get("tag", ""),
                            "gap_skills": [g["name"] if isinstance(g, dict) else str(g) for g in r.get("gap_skills", [])],
                            "estimated_hours": r.get("total_hours", 0),
                        }
                        for r in raw_routes[:3]
                    ],
                }
        except Exception:
            pass  # graph context is best-effort

    # Build inline coach insight
    result["coach_insight"] = _build_coach_insight(db, user.id, title, result)

    # Persist diagnosis (include graph_context in result_json)
    if graph_context:
        result["graph_context"] = graph_context
    row = JDDiagnosis(
        user_id=user.id,
        profile_id=profile_id,
        jd_text=req.jd_text,
        jd_title=title,
        match_score=result.get("match_score", 0),
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # Coach intervention: JD diagnosis complete
    try:
        from backend.routers.guidance import create_coach_intervention
        match_score = result.get("match_score", 0)
        gap_skills = result.get("gap_skills", [])
        gap_count = len(gap_skills)
        if gap_count > 0:
            body = f"匹配度 {match_score}%，发现 {gap_count} 个技能缺口。要我帮你生成补强计划吗？"
        else:
            body = f"匹配度 {match_score}%，核心技能基本覆盖。继续记录投递进展吧。"
        create_coach_intervention(
            db=db,
            user_id=user.id,
            trigger_type="jd_diagnosis_complete",
            title="JD 诊断完成",
            body=body,
            cta_label="生成计划" if gap_count > 0 else "查看结果",
            cta_route="/jd-diagnosis",
        )
    except Exception:
        pass  # Don't fail the diagnosis if intervention creation fails

    return {
        "id": row.id,
        "match_score": result.get("match_score", 0),
        "dimensions": result.get("dimensions", {}),
        "matched_skills": result.get("matched_skills", []),
        "gap_skills": result.get("gap_skills", []),
        "extracted_skills": extracted,
        "resume_tips": result.get("resume_tips", []),
        "graph_context": graph_context,
        "coach_insight": result.get("coach_insight"),
    }


@router.get("/history")
def list_diagnoses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List past JD diagnoses for the current user."""
    rows = (
        db.query(JDDiagnosis)
        .filter(JDDiagnosis.user_id == user.id)
        .order_by(JDDiagnosis.created_at.desc())
        .limit(50)
        .all()
    )
    results = []
    for d in rows:
        item: dict = {
            "id": d.id,
            "profile_id": d.profile_id,
            "jd_title": d.jd_title,
            "match_score": d.match_score,
            "created_at": str(d.created_at),
        }
        if d.result_json:
            detail = json.loads(d.result_json)
            item["dimensions"] = detail.get("dimensions", {})
            item["matched_skills"] = detail.get("matched_skills", [])
            item["gap_skills"] = detail.get("gap_skills", [])
            item["extracted_skills"] = detail.get("extracted_skills", [])
            item["resume_tips"] = detail.get("resume_tips", [])
            item["graph_context"] = detail.get("graph_context")
        results.append(item)
    return results


@router.get("/{diagnosis_id}")
def get_diagnosis(
    diagnosis_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single JD diagnosis record with full details."""
    row = (
        db.query(JDDiagnosis)
        .filter(JDDiagnosis.id == diagnosis_id, JDDiagnosis.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "记录不存在")

    result = {
        "id": row.id,
        "jd_title": row.jd_title,
        "jd_text": row.jd_text,
        "match_score": row.match_score,
        "created_at": str(row.created_at),
    }

    # Parse complete diagnosis result from result_json
    if row.result_json:
        try:
            detail = json.loads(row.result_json)
            result["dimensions"] = detail.get("dimensions", {})
            result["matched_skills"] = detail.get("matched_skills", [])
            result["gap_skills"] = detail.get("gap_skills", [])
            result["extracted_skills"] = detail.get("extracted_skills", [])
            result["resume_tips"] = detail.get("resume_tips", [])
            result["graph_context"] = detail.get("graph_context")
            result["coach_insight"] = detail.get("coach_insight")
        except Exception:
            pass

    return result


class RenameRequest(BaseModel):
    jd_title: str


@router.patch("/{diagnosis_id}/title")
def rename_diagnosis(
    diagnosis_id: int,
    req: RenameRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename a JD diagnosis record."""
    row = (
        db.query(JDDiagnosis)
        .filter(JDDiagnosis.id == diagnosis_id, JDDiagnosis.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "记录不存在")
    row.jd_title = req.jd_title.strip()[:256]
    db.commit()
    return {"success": True, "jd_title": row.jd_title}



@router.post("/{diagnosis_id}/greeting")
def generate_greeting(
    diagnosis_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a personalized greeting script for a JD diagnosis."""
    row = (
        db.query(JDDiagnosis)
        .filter(JDDiagnosis.id == diagnosis_id, JDDiagnosis.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "记录不存在")

    profile = db.query(Profile).filter(Profile.id == row.profile_id).first()
    profile_data = json.loads(profile.profile_json if profile else "{}")
    result_data = json.loads(row.result_json or "{}")

    greeting = _jd_svc.generate_greeting(
        jd_title=row.jd_title or "该岗位",
        extracted_skills=result_data.get("extracted_skills", []),
        matched_skills=result_data.get("matched_skills", []),
        match_score=row.match_score,
        profile=profile_data,
    )
    return {"greeting": greeting}


@router.delete("/{diagnosis_id}")
def delete_diagnosis(
    diagnosis_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a JD diagnosis record."""
    row = (
        db.query(JDDiagnosis)
        .filter(JDDiagnosis.id == diagnosis_id, JDDiagnosis.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "记录不存在")
    db.delete(row)
    db.commit()
    return {"success": True, "message": "已删除"}


# ── Coach insight generator ────────────────────────────────────────────────

def _skill_name(item):
    if isinstance(item, dict):
        return item.get("skill") or item.get("name") or str(item)
    return str(item)


def _build_coach_insight(db: Session, user_id: int, jd_title: str, result: dict) -> dict:
    """基于当前诊断结果和用户历史诊断，生成 Inline 教练洞察卡片数据。"""
    match_score = result.get("match_score", 0)
    gap_skills = result.get("gap_skills", [])
    matched_skills = result.get("matched_skills", [])
    current_gap_names = [_skill_name(g) for g in gap_skills]

    # 获取用户最近 3 次历史诊断
    recent = (
        db.query(JDDiagnosis)
        .filter(JDDiagnosis.user_id == user_id)
        .order_by(JDDiagnosis.created_at.desc())
        .limit(3)
        .all()
    )

    # 收集历史缺口技能
    historical_gaps = []
    for d_row in recent:
        d_detail = json.loads(d_row.result_json or "{}")
        historical_gaps.extend([_skill_name(g) for g in d_detail.get("gap_skills", [])])

    # 统计当前缺口在历史中的出现频率
    freq = {}
    for hg in historical_gaps:
        if hg in current_gap_names:
            freq[hg] = freq.get(hg, 0) + 1

    # 高优先级缺口
    high_priority = [
        _skill_name(g)
        for g in gap_skills
        if isinstance(g, dict) and g.get("priority") == "high"
    ]

    # 选择关键缺口：高优先级 > 共性缺口 > 第一个缺口
    key_gap = None
    if high_priority:
        key_gap = high_priority[0]
    elif freq:
        key_gap = max(freq, key=freq.get)
    elif current_gap_names:
        key_gap = current_gap_names[0]

    # 构建证据链
    evidence = []
    if key_gap and freq.get(key_gap, 0) > 0:
        evidence.append(f"你最近诊断的 {len(recent)} 份 JD 中，{freq[key_gap]} 份也要求了 {key_gap}")
    if key_gap and key_gap in high_priority:
        evidence.append(f"{key_gap} 被标记为高优先级缺口")

    if not current_gap_names:
        return {
            "type": "jd_diagnosis_complete",
            "title": f"JD 诊断完成 · 匹配度 {match_score}%",
            "insight": "核心技能基本覆盖，竞争力不错。建议尽快投递并记录进展，让教练跟踪你的实战成长。",
            "evidence": [f"已匹配 {len(matched_skills)} 项核心技能"],
            "cta": {"text": "记录投递进展", "action": "navigate", "target": "/growth-log"},
            "secondary_cta": {
                "text": "和教练聊聊",
                "action": "open_chat",
                "prompt": f"我诊断了{jd_title}，匹配度{match_score}%，接下来该做什么？",
            },
        }

    # 有缺口时的洞察文案
    insight_parts = [f"这份 JD 有 {len(current_gap_names)} 个技能缺口。"]
    if key_gap:
        if freq.get(key_gap, 0) > 0:
            insight_parts.append(
                f"{key_gap} 是优先级最高的——它在你的历史诊断中也频繁出现，"
                f"说明这是该方向的共性要求，不是个别现象。"
            )
        elif key_gap in high_priority:
            insight_parts.append(f"{key_gap} 被标记为高优先级缺口，建议优先补强。")
        else:
            insight_parts.append(f"其中 {key_gap} 建议优先关注。")

    gap_list = ", ".join(current_gap_names[:5])
    prompt_base = f"基于{jd_title}的诊断结果（匹配度{match_score}%，缺口：{gap_list}）"

    return {
        "type": "jd_diagnosis_complete",
        "title": f"JD 诊断完成 · 匹配度 {match_score}%",
        "insight": "".join(insight_parts),
        "evidence": evidence,
        "cta": {
            "text": "生成补强计划",
            "action": "open_chat",
            "prompt": f"{prompt_base}，帮我生成一份补强计划。",
        },
        "secondary_cta": {
            "text": "和教练聊聊",
            "action": "open_chat",
            "prompt": f"{prompt_base}。这份诊断结果说明了什么？我应该优先补哪个技能？",
        },
    }
