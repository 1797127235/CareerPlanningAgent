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
                raw_routes = graph.find_escape_routes(graph_match["node_id"], db_session=db)
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

    return {
        "id": row.id,
        "match_score": result.get("match_score", 0),
        "dimensions": result.get("dimensions", {}),
        "matched_skills": result.get("matched_skills", []),
        "gap_skills": result.get("gap_skills", []),
        "extracted_skills": extracted,
        "resume_tips": result.get("resume_tips", []),
        "graph_context": graph_context,
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
