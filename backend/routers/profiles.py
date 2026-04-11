"""Profiles router — single-profile system.

Each user has exactly one Profile. Multiple resume uploads are incremental
additions that merge into the same profile (union skills, take higher level).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import CareerGoal, JobNode, Profile, User
from backend.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

router = APIRouter()


def ok(data=None, message=None):
    result: dict = {"success": True}
    if data is not None:
        result["data"] = data
    if message:
        result["message"] = message
    return result


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_or_create_profile(user_id: int, db: Session) -> Profile:
    """Return the user's single profile, creating an empty one if none exists."""
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(
            user_id=user_id,
            name="",
            profile_json="{}",
            quality_json="{}",
            source="manual",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _resolve_node_label(node_id: str, db: Session) -> str:
    """Resolve node label: try graph service first, then DB, then raw ID."""
    from backend.services.graph_service import get_graph_service
    g = get_graph_service(db)
    gn = g.get_node(node_id)
    if gn:
        return gn.get("label", node_id)
    db_node = db.query(JobNode).filter(JobNode.node_id == node_id).first()
    return db_node.label if db_node else node_id


def _profile_to_dict(profile: Profile, db: Session, user_id: int) -> dict:
    """Serialize a profile with its graph position."""
    # 获取所有 active goals，is_primary 优先
    all_goals = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user_id,
            CareerGoal.profile_id == profile.id,
            CareerGoal.is_active == True,
        )
        .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
        .all()
    )
    primary_goal = next((g for g in all_goals if g.is_primary), all_goals[0] if all_goals else None)

    profile_data = json.loads(profile.profile_json or "{}")
    item: dict = {
        "id": profile.id,
        "name": profile.name,
        "source": profile.source,
        "created_at": str(profile.created_at),
        "updated_at": str(profile.updated_at),
        "profile": profile_data,
        "quality": json.loads(profile.quality_json or "{}"),
    }

    # graph_position: 向后兼容，取主目标快照
    if primary_goal and (primary_goal.from_node_id or primary_goal.target_node_id):
        item["graph_position"] = {
            "from_node_id": primary_goal.from_node_id,
            "from_node_label": _resolve_node_label(primary_goal.from_node_id, db),
            "target_node_id": primary_goal.target_node_id,
            "target_label": primary_goal.target_label,
            "target_zone": primary_goal.target_zone,
            "gap_skills": primary_goal.gap_skills or [],
            "total_hours": primary_goal.total_hours or 0,
            "safety_gain": primary_goal.safety_gain or 0.0,
            "salary_p50": primary_goal.salary_p50 or 0,
        }

    # career_goals: 完整多目标列表 — 只要有 active goal 且有 target 就返回
    goals_with_target = [g for g in all_goals if g.target_node_id]
    if goals_with_target:
        # from_node_id may be empty (e.g. set from role detail page before auto_locate)
        from_node_id = goals_with_target[0].from_node_id or ""
        from_node_label = _resolve_node_label(from_node_id, db) if from_node_id else ""

        item["career_goals"] = [
            {
                "id": g.id,
                "target_node_id": g.target_node_id,
                "target_label": g.target_label,
                "target_zone": g.target_zone,
                "from_node_id": g.from_node_id or from_node_id,
                "from_node_label": from_node_label,
                "gap_skills": g.gap_skills or [],
                "total_hours": g.total_hours or 0,
                "safety_gain": g.safety_gain or 0.0,
                "salary_p50": g.salary_p50 or 0,
                "is_primary": g.is_primary,
                "set_at": g.set_at.isoformat() if g.set_at else None,
            }
            for g in goals_with_target
        ]
    else:
        item["career_goals"] = []

    return item


_LEVEL_ORDER = {"beginner": 0, "familiar": 1, "intermediate": 2, "advanced": 3}


def _merge_profiles(existing: dict, incoming: dict) -> dict:
    """Merge incoming profile data into existing.

    - Skills: union, keep higher level for duplicates.
    - knowledge_areas / projects / awards: set union.
    - education / experience_years: update if incoming has richer data.
    - raw_text: always overwrite with latest upload.
    - soft_skills: preserve existing assessment unless incoming has one.
    """
    merged = dict(existing)

    # Skills: union, higher level wins
    skill_map = {s["name"]: s for s in existing.get("skills", [])}
    for skill in incoming.get("skills", []):
        name = skill["name"]
        if name not in skill_map:
            skill_map[name] = skill
        else:
            existing_lvl = _LEVEL_ORDER.get(skill_map[name].get("level", "beginner"), 0)
            incoming_lvl = _LEVEL_ORDER.get(skill.get("level", "beginner"), 0)
            if incoming_lvl > existing_lvl:
                skill_map[name] = skill
    merged["skills"] = list(skill_map.values())

    # knowledge_areas / projects / awards: union
    merged["knowledge_areas"] = list(
        set(existing.get("knowledge_areas", [])) | set(incoming.get("knowledge_areas", []))
    )
    merged["projects"] = list(
        set(existing.get("projects", [])) | set(incoming.get("projects", []))
    )
    merged["awards"] = list(
        set(existing.get("awards", [])) | set(incoming.get("awards", []))
    )

    # certificates: union by name (case-insensitive dedup)
    existing_certs = {c.lower(): c for c in existing.get("certificates", [])}
    for cert in incoming.get("certificates", []):
        existing_certs.setdefault(cert.lower(), cert)
    merged["certificates"] = list(existing_certs.values())

    # internships: union by (company + role), keep most recent if duplicate
    existing_interns = {
        (i.get("company", "") + "|" + i.get("role", "")): i
        for i in existing.get("internships", [])
        if isinstance(i, dict)
    }
    for intern in incoming.get("internships", []):
        if not isinstance(intern, dict):
            continue
        key = intern.get("company", "") + "|" + intern.get("role", "")
        existing_interns[key] = intern  # incoming overwrites (more recent upload = fresher data)
    merged["internships"] = list(existing_interns.values())

    # Education: update if incoming has richer data
    if incoming.get("education") and any(v for v in incoming["education"].values() if v):
        merged["education"] = incoming["education"]

    # experience_years: keep max (safe against None values stored in existing data)
    inc_exp = incoming.get("experience_years") or 0
    exs_exp = existing.get("experience_years") or 0
    merged["experience_years"] = max(inc_exp, exs_exp)

    # name: update if incoming provides one
    if incoming.get("name"):
        merged["name"] = incoming["name"]

    # raw_text: always use latest
    if incoming.get("raw_text"):
        merged["raw_text"] = incoming["raw_text"]

    # soft_skills: preserve existing assessment; only set if currently absent
    if not merged.get("soft_skills") and incoming.get("soft_skills"):
        merged["soft_skills"] = incoming["soft_skills"]

    # job_target: incoming wins if non-empty, else keep existing
    if incoming.get("job_target"):
        merged["job_target"] = incoming["job_target"]
    elif existing.get("job_target"):
        merged["job_target"] = existing["job_target"]  # preserve, never overwrite with empty

    # primary_domain: incoming wins if non-empty, else keep existing
    if incoming.get("primary_domain"):
        merged["primary_domain"] = incoming["primary_domain"]
    elif existing.get("primary_domain"):
        merged["primary_domain"] = existing["primary_domain"]

    return merged


# ── LLM-based role matching ───────────────────────────────────────────────────

_ROLE_LIST_CACHE: str | None = None    # cleared on restart — now includes distinguishing_features
_GRAPH_NODES_CACHE: dict | None = None
_skill_vocab_cache: str | None = None


def _get_graph_nodes() -> dict:
    """Load graph.json nodes as dict keyed by node_id (cached)."""
    global _GRAPH_NODES_CACHE
    if _GRAPH_NODES_CACHE is not None:
        return _GRAPH_NODES_CACHE
    graph_path = Path(__file__).resolve().parent.parent.parent / "data" / "graph.json"
    with open(graph_path, "r", encoding="utf-8") as f:
        _GRAPH_NODES_CACHE = {n["node_id"]: n for n in json.load(f).get("nodes", [])}
    return _GRAPH_NODES_CACHE


def _get_role_list_text(node_ids: list[str] | None = None) -> str:
    """Build a role list string for the LLM prompt, including distinguishing_features."""
    global _ROLE_LIST_CACHE
    graph_nodes = _get_graph_nodes()

    def _format_node(nid: str, n: dict) -> str:
        label = n.get("label", nid)
        ms = ", ".join(str(s) for s in (n.get("must_skills") or [])[:6])
        line = f"- {nid}: {label}（核心技能: {ms}）"
        df = n.get("distinguishing_features") or []
        if df:
            line += f"\n  适合信号: {'; '.join(df[:3])}"
        ntrf = n.get("not_this_role_if") or []
        if ntrf:
            line += f"\n  不适合: {'; '.join(ntrf[:2])}"
        return line

    if node_ids is not None:
        return "\n".join(_format_node(nid, graph_nodes.get(nid, {})) for nid in node_ids)

    if _ROLE_LIST_CACHE:
        return _ROLE_LIST_CACHE
    _ROLE_LIST_CACHE = "\n".join(_format_node(nid, n) for nid, n in graph_nodes.items())
    return _ROLE_LIST_CACHE


# ── Embedding pre-filter ─────────────────────────────────────────────────────

_NODE_EMBEDDINGS: dict | None = None


def _load_node_embeddings() -> dict:
    global _NODE_EMBEDDINGS
    if _NODE_EMBEDDINGS is not None:
        return _NODE_EMBEDDINGS
    path = Path(__file__).resolve().parent.parent.parent / "data" / "node_embeddings.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            _NODE_EMBEDDINGS = json.load(f)
    except Exception:
        _NODE_EMBEDDINGS = {"nodes": {}}
    return _NODE_EMBEDDINGS


def _embedding_prefilter(profile_data: dict, ratio: float = 0.70) -> list[str]:
    """Use cosine similarity + relative threshold to find matching node IDs.

    Returns node_ids where sim >= top_sim * ratio (relative threshold).
    Also includes project descriptions for better matching.
    """
    import numpy as np

    emb_data = _load_node_embeddings()
    node_embs = emb_data.get("nodes", {})
    if not node_embs:
        return list(_get_graph_nodes().keys())

    # Build rich user text: skills + project names + descriptions
    skills = [s.get("name", "") for s in profile_data.get("skills", []) if isinstance(s, dict) and s.get("name")]
    if not skills:
        return list(node_embs.keys())

    parts = [" ".join(skills)]
    for p in profile_data.get("projects", [])[:3]:
        if not isinstance(p, dict):
            continue
        pname = p.get("name", "")
        tech = p.get("tech_stack", "") or p.get("technologies", "")
        desc = p.get("description", "") or p.get("highlights", "")
        if pname:
            line = pname
            if tech:
                line += f"({str(tech)[:60]})"
            if desc:
                line += f": {str(desc)[:80]}"
            parts.append(line)

    user_text = " | ".join(parts)

    # Get user embedding
    try:
        import os
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
            base_url=os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            timeout=15,
        )
        resp = client.embeddings.create(
            model=emb_data.get("embedding_model", "text-embedding-v4"),
            input=[user_text],
        )
        user_vec = np.array(resp.data[0].embedding)
    except Exception as e:
        logger.warning("Embedding pre-filter failed: %s", e)
        return list(node_embs.keys())

    # Cosine similarity
    node_ids = list(node_embs.keys())
    node_vecs = np.array([node_embs[nid] for nid in node_ids])
    norms = np.linalg.norm(node_vecs, axis=1, keepdims=True)
    node_vecs_normed = node_vecs / norms
    user_normed = user_vec / np.linalg.norm(user_vec)

    sims = node_vecs_normed @ user_normed
    ranking = np.argsort(sims)[::-1]

    # Relative threshold: keep nodes with sim >= top_sim * ratio
    top_sim = sims[ranking[0]]
    threshold = top_sim * ratio
    candidates = [node_ids[i] for i in ranking if sims[i] >= threshold]

    # Ensure at least 5, at most 8
    if len(candidates) < 5:
        candidates = [node_ids[i] for i in ranking[:5]]
    elif len(candidates) > 8:
        candidates = candidates[:8]

    return candidates


_ROLE_MATCH_PROMPT = """你是一个职业匹配 AI。根据用户的完整背景，完成两件事：

1. 从以下 {role_count} 个岗位中选出最匹配的 1 个作为用户**当前定位**（current_position）
2. 推荐 5-6 个最适合的方向，按匹配度从高到低排序
   - 只推荐和用户背景有真实关联的岗位，宁少勿滥
   - 每个推荐附一句话理由，说明用户的哪些经历/信号匹配该方向
   - affinity_pct 反映综合契合度（0-100）

【匹配优先级规则 — 严格执行，违反视为严重错误】
0. **job_target 是最高优先级**：如果用户简历中有明确的求职意向（job_target 不为空），必须将最符合该意向的岗位排在推荐第一位，这是用户的主观选择，任何技能分析都不能覆盖它。例如：job_target="产品经理实习" → 产品经理必须出现在推荐里且排名靠前。
1. **primary_domain > 单项技能**：用户主方向是第二权重。
2. **career_signals 是区分相似岗位的关键信号**：
   - has_publication=true + research_vs_engineering=research → 算法工程师/研究岗优先于工程岗
   - competition_awards（Kaggle金牌/数学建模）→ 算法/数据科学岗加权
   - internship_company_tier=顶级大厂 → 整体上调
   - research_vs_engineering=engineering → 工程岗优先于研究岗
3. **工具技能不驱动主方向**：Docker/Linux/Git/CI/CD 是辅助技能，不能是 DevOps 匹配的主要依据（除非 primary_domain=系统/基础设施）。
4. **distinguishing_features 是决定因素**：当两个岗位技能相似时，对照每个岗位的"适合信号"和"不适合"来判断，而非单纯技能重叠度。

【熟练度折算（严格执行）】
每个技能括号里是熟练度，affinity_pct 计算时必须按折算系数考虑：
  - expert / proficient / advanced → 1.0 完整技能点
  - intermediate                    → 0.5 技能点
  - familiar                        → 0.3 技能点
  - beginner                        → 0.2 技能点
举例："机器学习(familiar)" = 只是了解过，不能作为推荐 ML 岗位的强信号。

【高门槛方向 affinity_pct 上限（违反视为严重错误）】
■ AI 数据科学家 / 机器学习工程师 / 算法工程师 / AI 工程师 / AI Agent 工程师：
  硬核信号定义（满足才能给高分）：
    (a) 论文发表（SCI / EI / CCF-A/B）
    (b) 学科竞赛奖（Kaggle 铜牌以上 / ACM / 数学建模国奖）
    (c) 独立实现过模型（不仅调 sklearn.cluster / fit_predict）
    (d) 深度学习框架（PyTorch/TensorFlow）完整项目经历
  - 零硬核信号：affinity_pct ≤ 50
  - 1 条硬核信号：affinity_pct ≤ 60
  - 2+ 条硬核信号：可以 70+
  ⚠ "在项目里用过聚类算法分类用户" 是数据分析的日常，不算硬核信号。

■ 数据分析师 / BI 分析师 / 数据工程师：
  门槛低得多，Python+Excel+SQL 其一 intermediate 以上 + 一段数据分析实习 → affinity_pct ≥ 80；
  全满足 + 真实业务产出（用户画像/销售分析/报表）→ affinity_pct ≥ 85

■ 产品经理：
  偏业务思维岗位，看业务理解而非硬技能。默认 50-65 区间，有产品实习或完整产品经历可到 75+

【岗位列表（含区分信号）】
{role_list}

【用户求职意向（最高优先级）】
{job_target}

【用户主方向】
{primary_domain}

【用户职业信号】
{career_signals}

【用户技能（含熟练度）】
{user_skills}

【用户背景】
专业：{major}，学历：{degree}，工作年限：{exp_years}

返回严格 JSON，不要任何其他文字：
{{
  "current_position": {{"role_id": "最匹配岗位ID", "reason": "一句话理由"}},
  "recommendations": [
    {{"role_id": "岗位ID", "label": "中文名", "reason": "一句话推荐理由（必须提到熟练度）", "affinity_pct": 匹配度0到100}}
  ]
}}"""


def _llm_match_role(profile_data: dict) -> dict | None:
    """LLM role matching using full node list (embedding prefilter removed — only 40 nodes)."""
    try:
        from backend.llm import llm_chat, parse_json_response

        # Preserve level for LLM affinity_pct calibration
        skill_objs = [s for s in profile_data.get("skills", []) if isinstance(s, dict) and s.get("name")]
        if skill_objs:
            skills_with_level = ", ".join(
                f"{s.get('name')}({s.get('level') or 'unspecified'})" for s in skill_objs
            )
        else:
            # Fallback: use knowledge_areas when skills are empty (no level info available)
            ka = (profile_data.get("knowledge_areas") or [])[:10]
            if not ka:
                return None
            skills_with_level = ", ".join(ka)

        # Use all nodes directly — 40 nodes fits comfortably in one LLM call
        all_node_ids = list(_get_graph_nodes().keys())
        role_list = _get_role_list_text(all_node_ids)
        candidate_ids = all_node_ids

        edu = profile_data.get("education", {})
        job_target = profile_data.get("job_target", "") or "未指定"
        primary_domain = profile_data.get("primary_domain", "未知")
        cs = profile_data.get("career_signals", {})
        career_signals_text = (
            f"论文发表: {'有（' + cs.get('publication_level','') + '）' if cs.get('has_publication') else '无'}，"
            f"竞赛获奖: {'/'.join(cs.get('competition_awards') or []) or '无'}，"
            f"领域专精: {cs.get('domain_specialization') or '无'}，"
            f"研究/工程倾向: {cs.get('research_vs_engineering','未知')}，"
            f"开源贡献: {'有' if cs.get('open_source') else '无'}，"
            f"实习公司: {cs.get('internship_company_tier','未知')}"
        ) if cs else "未提取到职业信号"
        prompt = _ROLE_MATCH_PROMPT.format(
            role_count=len(candidate_ids),
            role_list=role_list,
            job_target=job_target,
            primary_domain=primary_domain,
            career_signals=career_signals_text,
            user_skills=skills_with_level,
            major=edu.get("major", "未知"),
            degree=edu.get("degree", "未知"),
            exp_years=profile_data.get("experience_years", 0),
        )

        # Step 2: LLM fine-rank on reduced candidate set
        result = llm_chat([{"role": "user", "content": prompt}], temperature=0, timeout=60)
        parsed = parse_json_response(result)
        if parsed and parsed.get("current_position", {}).get("role_id"):
            return parsed
        if parsed and parsed.get("role_id"):
            return {"current_position": parsed, "recommendations": []}
        return None
    except Exception as e:
        logger.warning("LLM role matching failed: %s", e)
        return None


# ── Graph positioning ─────────────────────────────────────────────────────────

def _auto_locate_on_graph(
    profile_id: int, user_id: int, profile_data: dict, db: Session
) -> dict | None:
    """Locate profile on career graph + generate recommendations in one LLM call.

    Returns current position dict and caches recommendations for instant loading.
    """
    try:
        from backend.services.graph_service import get_graph_service

        graph = get_graph_service(db)

        llm_result = _llm_match_role(profile_data)
        if not llm_result:
            return None

        current_pos = llm_result.get("current_position", llm_result)
        node_id = current_pos["role_id"]

        node = graph.get_node(node_id)
        if not node:
            return None
        node_label = node.get("label", node_id)

        existing_goal = (
            db.query(CareerGoal)
            .filter_by(user_id=user_id, profile_id=profile_id, is_active=True)
            .first()
        )
        if existing_goal:
            db.query(CareerGoal).filter_by(
                user_id=user_id, profile_id=profile_id, is_active=True
            ).update({"from_node_id": node_id})
        else:
            goal = CareerGoal(
                user_id=user_id,
                profile_id=profile_id,
                from_node_id=node_id,
                target_node_id="",
                target_label="",
                target_zone="",
                is_primary=True,
            )
            db.add(goal)

        # Cache recommendations from the same LLM call
        recs_raw = llm_result.get("recommendations", [])
        if recs_raw:
            from backend.routers.recommendations import _save_rec_cache
            from backend.services.gap_analyzer import profile_hash

            # Enrich with graph data
            graph_path = Path(__file__).resolve().parent.parent.parent / "data" / "graph.json"
            graph_nodes: dict = {}
            try:
                nodes_list = json.loads(graph_path.read_text(encoding="utf-8")).get("nodes", [])
                graph_nodes = {n["node_id"]: n for n in nodes_list}
            except Exception:
                pass

            skills = [s.get("name", "") for s in profile_data.get("skills", []) if s.get("name")]
            enriched = []
            for r in recs_raw[:6]:
                rid = r.get("role_id", "")
                gn = graph_nodes.get(rid, {})
                enriched.append({
                    "role_id": rid,
                    "label": r.get("label", gn.get("label", rid)),
                    "affinity_pct": r.get("affinity_pct", 50),
                    "matched_skills": [],
                    "gap_skills": gn.get("must_skills", [])[:4],
                    "gap_hours": 0,
                    "zone": gn.get("zone", "safe"),
                    "salary_p50": gn.get("salary_p50", 0),
                    "reason": r.get("reason", ""),
                    "channel": r.get("channel", "entry"),
                    "career_level": gn.get("career_level", 0),
                    "replacement_pressure": gn.get("replacement_pressure", 50),
                    "human_ai_leverage": gn.get("human_ai_leverage", 50),
                })

            # Add promotion targets from vertical edges
            graph_edges = json.loads(graph_path.read_text(encoding="utf-8")).get("edges", [])
            rec_ids = {r["role_id"] for r in enriched}
            # Find vertical targets reachable from any recommended role
            promotion_targets = set()
            for e in graph_edges:
                if e.get("edge_type") == "vertical" and e["source"] in rec_ids:
                    promotion_targets.add(e["target"])
            # Also find targets from current_position
            for e in graph_edges:
                if e.get("edge_type") == "vertical" and e["source"] == node_id:
                    promotion_targets.add(e["target"])
            # Add promotion nodes (not already in recs)
            for pid in promotion_targets:
                if pid not in rec_ids:
                    pn = graph_nodes.get(pid, {})
                    if pn:
                        enriched.append({
                            "role_id": pid,
                            "label": pn.get("label", pid),
                            "affinity_pct": 0,
                            "matched_skills": [],
                            "gap_skills": pn.get("must_skills", [])[:4],
                            "gap_hours": 0,
                            "zone": pn.get("zone", "safe"),
                            "salary_p50": pn.get("salary_p50", 0),
                            "reason": "晋升方向",
                            "channel": "promotion",
                            "career_level": pn.get("career_level", 0),
                            "replacement_pressure": pn.get("replacement_pressure", 50),
                            "human_ai_leverage": pn.get("human_ai_leverage", 50),
                        })

            profile = db.query(Profile).filter(Profile.id == profile_id).first()
            if profile:
                p_hash = profile_hash(profile_data)
                rec_resp = {"recommendations": enriched, "user_skill_count": len(skills)}
                _save_rec_cache(profile, p_hash, rec_resp, db)

        db.commit()
        return {"node_id": node_id, "label": node_label}
    except Exception as e:
        import traceback
        print(f"[auto_locate] FAILED for user={user_id}: {e}")
        traceback.print_exc()
        return None


# ── Skill alias normalization ─────────────────────────────────────────────────
# Maps common resume variants → canonical graph vocab names (lowercase key)
_SKILL_ALIASES: dict[str, str] = {
    # Game engine
    "unreal engine 5": "Unreal", "unreal engine 4": "Unreal",
    "ue5": "Unreal", "ue4": "Unreal", "unreal engine": "Unreal",
    "unity3d": "Unity",
    # Spring / Java
    "springboot": "Spring Boot", "spring-boot": "Spring Boot",
    "spring boot framework": "Spring Boot",
    "mybatisplus": "MyBatis", "mybatis-plus": "MyBatis",
    # LangChain ecosystem
    "langgraph": "LangChain", "langchain4j": "LangChain",
    "langserve": "LangChain", "langchain/langgraph": "LangChain",
    # Vector DBs
    "pgvector": "Vector DB", "pinecone": "Vector DB",
    "weaviate": "Vector DB", "chroma": "Vector DB",
    "milvus": "Vector DB", "qdrant": "Vector DB",
    # LLM APIs
    "openai api": "OpenAI API", "chatgpt api": "OpenAI API",
    "gpt-4": "OpenAI API", "gpt4": "OpenAI API",
    "dashscope": "OpenAI API",
    # Frontend
    "react.js": "React", "reactjs": "React",
    "vue.js": "Vue.js", "vuejs": "Vue.js",
    "nextjs": "Next.js",
    "nodejs": "Node.js",
    # DB
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    # K8s
    "k8s": "Kubernetes",
    # PyTorch / TF
    "pytorch": "PyTorch", "tensorflow": "TensorFlow",
}


def _normalize_skill_name(name: str) -> str:
    return _SKILL_ALIASES.get(name.lower().strip(), name)


def _normalize_skills(skills: list) -> list:
    """Normalize each skill's name using the alias map."""
    result = []
    for s in skills:
        if isinstance(s, dict):
            result.append({**s, "name": _normalize_skill_name(s.get("name", ""))})
        else:
            result.append(s)
    return result


# ── Resume parsing ────────────────────────────────────────────────────────────

_RESUME_PARSE_PROMPT = """你是一个简历解析 AI。请从以下简历文本中提取结构化信息，以 JSON 格式返回。

返回格式（严格 JSON，不要加注释或 markdown）：
{{
  "name": "姓名（可选）",
  "job_target": "简历中明确写出的求职意向/目标岗位原文，如'产品经理实习'、'前端开发工程师'，无则填空字符串",
  "primary_domain": "此人最主要的技术/职能方向，从以下选一个：AI/LLM开发|后端开发|前端开发|游戏开发|数据工程|系统/基础设施|安全|算法研究|产品设计/PM|其他",
  "career_signals": {{
    "has_publication": true或false（是否有论文发表，包括在投/预印本）,
    "publication_level": "顶会（NeurIPS/ICML/CVPR/ACL/KDD/ICLR等）|CCF-A|CCF-B|CCF-C|无",
    "competition_awards": ["获奖竞赛名称，如Kaggle金牌、数学建模省一等奖"],
    "domain_specialization": "深耕的细分领域，如异常检测、推荐系统、计算机视觉等，无则填空字符串",
    "research_vs_engineering": "research（偏学术/算法创新）|engineering（偏工程落地）|balanced（均衡）",
    "open_source": true或false（是否有开源项目/贡献）,
    "internship_company_tier": "顶级大厂（字节/阿里/腾讯/华为/百度等）|中大厂|初创/中小公司|无"
  }},
  "experience_years": 工作年限数字（在校生/应届生填0）,
  "education": {{"degree": "学位", "major": "专业", "school": "学校"}},
  "skills": [
    {{"name": "技能名称", "level": "advanced|intermediate|familiar|beginner"}}
  ],
  "knowledge_areas": ["知识领域1", "知识领域2"],
  "internships": [
    {{
      "company": "公司名称",
      "role": "实习岗位名称",
      "duration": "时间范围，如2024.10-2024.12",
      "tech_stack": ["技术1", "技术2"],
      "highlights": "核心成果一句话描述，如：优化索引性能提升38%"
    }}
  ],
  "projects": ["项目描述1", "项目描述2"],
  "awards": ["竞赛/荣誉1", "竞赛/荣誉2"],
  "certificates": ["证书名称，必须 100% 完整抽取，见下方规则"]
}}

【技能命名规则（严格执行）】
技能名称必须使用简短标准名，不要加"语言/编程/系统/框架/开发"等后缀。
优先使用以下标准词表中的名称（如果简历中的技能可以对应上）：
{skill_vocab}
如果简历中的技能不在词表中，使用简短通用名称（如"多线程"而非"多线程编程"，"Linux"而非"Linux系统编程"，"C++"而非"C/C++语言"）。
【别名归一化（强制）】Unreal Engine 5/UE5 → Unreal，LangGraph/LangChain4j → LangChain，PGVector → Vector DB，SpringBoot → Spring Boot。

【字段分类规则（严格执行）】
- internships：在企业/机构的实习经历（有明确公司名+岗位），每段实习单独一条
- projects：仅放实际动手开发/实施的个人或课程项目，如"高并发内存池"、"SACOS测试项目"；实习期间做的项目不重复放这里
- awards：仅放竞赛获奖、荣誉证书、奖学金，如"软件测试大赛省二"、"程序设计省一"
- certificates：**一切资质证书**，必须 100% 完整抽取，不得按"是否与求职相关"过滤。包括但不限于：
  • 外语类：CET-4/6、BEC、TOEFL、IELTS、日语 N1/N2、韩语 TOPIK 等
  • 技术/职业类：软考（初级/中级/高级）、PMP、CFA、ACCA、CPA、一级/二级建造师、NCRE 计算机等级、华为/思科/阿里云/AWS 认证等
  • **普通话水平测试等级证书**：一甲、一乙、二甲、二乙、三甲、三乙（**必须收录**）
  • **机动车驾驶证**：C1、C2、C3、B1、B2、A1、A2（**必须收录**）
  • 教师资格证、心理咨询师、会计从业、证券从业等各类从业资格
  • 任何简历中"证书""资质""技能证书""其他""个人证书"等板块出现的内容，一律收录
  **禁止**：禁止把驾驶证/普通话证书因为"和求职无关"而丢弃——这是学生自我介绍的一部分，必须保留原样录入
- 竞赛名称禁止出现在 projects 中；项目名称禁止出现在 awards 中

技能等级判定规则（严格执行，宁低勿高，默认从低档开始）：
- advanced（高级）：须有以下任一硬性证据：主导开源项目/重要贡献、竞赛获奖（省级+）、≥1年该技术工作经验、发表相关论文/专利
- intermediate（中级）：在≥2个有实质规模的项目中担任主要负责人，OR有≥3个月该技术实习/工作经验，OR有省级及以上竞赛获奖
- familiar（了解）：课程项目或个人项目中实际使用过，有代码产出
- beginner（入门）：学过课程/看过教程，实践经验有限

【中文用词 → 等级上限映射（强制执行）】
简历中出现以下词汇时，对应技能的等级上限如下，不得超越：
- "了解" / "接触过" / "有所了解" → 上限 beginner
- "熟悉" / "能够使用" / "会使用" / "具备" / "理解" → 上限 familiar
- "熟练" / "掌握" / "能独立" → 上限 intermediate
- "精通" / "深度掌握" / "专精" → 上限 advanced（仍需核实硬性证据）
注意：简历对某技能使用"熟悉"，则该技能最高只能判 familiar，即使有相关项目也不得上调。

【强制约束 — 应届生/在校生（experience_years=0）】
1. 绝大多数技能应判为 familiar 或 beginner
2. intermediate 须同时满足：(a) 有实质项目证据 且 (b) 简历用词达到"熟练/掌握"级别
3. advanced 极少出现，仅限"精通"原词 + 开源/竞赛等可验证硬性成就同时存在
4. 竞赛获奖可将相关技能从 familiar 提升至 intermediate，但不能到 advanced
5. 证据不足时强制向下取一档

简历文本：
{resume_text}

只返回 JSON，不要有任何其他文字。"""


_AWARD_KEYWORDS = (
    "大赛", "竞赛", "比赛", "获奖", "奖学金", "省一", "省二", "省三",
    "国一", "国二", "国三", "一等奖", "二等奖", "三等奖", "特等奖",
    "金奖", "银奖", "铜奖", "优秀奖", "荣誉", "证书", "认证",
)


def _postprocess_profile(parsed: dict) -> dict:
    projects: list = parsed.get("projects", [])
    awards: list = parsed.get("awards", [])
    clean_projects = []
    for item in projects:
        text = str(item)
        if any(kw in text for kw in _AWARD_KEYWORDS):
            if text not in awards:
                awards.append(text)
        else:
            clean_projects.append(item)
    parsed["projects"] = clean_projects
    parsed["awards"] = awards
    return parsed


def _vlm_supplement_certificates(content: bytes) -> list[str]:
    """Secondary VLM call dedicated to extracting certificates.

    Why a separate call: qwen-vl-plus often subjectively filters out items like
    "普通话二级乙等" or "机动车驾驶证C2" during JSON extraction even when the main
    prompt says "100% include" — too many instructions dilute attention.

    This isolated single-task call gets much higher compliance.
    Returns raw list of certificate strings (may be empty on failure).
    """
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
        import openai
        from backend.llm import get_env_str, parse_json_response

        api_key = get_env_str("DASHSCOPE_API_KEY")
        base_url = get_env_str("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not api_key:
            return []

        doc = fitz.open(stream=_io.BytesIO(content), filetype="pdf")
        content_parts: list[dict] = []
        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            })

        # Single-task prompt: much higher instruction compliance than multi-field JSON
        prompt_text = (
            "请识别图像中的简历，找出所有「证书 / 资质 / 技能证书 / 其他」板块里的**全部内容**，"
            "一字不落地原样列出。\n"
            "必须收录（不得按相关性过滤）：\n"
            "- 外语证书：CET-4/6、BEC、TOEFL、IELTS、日语 N1/N2、韩语 TOPIK 等\n"
            "- 普通话水平测试：一甲、一乙、二甲、二乙、三甲、三乙\n"
            "- 机动车驾驶证：C1、C2、C3、B1、B2、A1、A2\n"
            "- 计算机等级 / 软考 / PMP / 云厂商认证\n"
            "- 教师资格证、会计/证券/心理从业证\n"
            "- 任何出现在证书板块的内容\n\n"
            '返回严格 JSON 数组，如：["英语（CET-4）", "普通话二级乙等", "机动车驾驶证C2"]\n'
            "只返回 JSON 数组，不要任何解释。找不到则返回 []。"
        )
        content_parts.append({"type": "text", "text": prompt_text})

        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[{"role": "user", "content": content_parts}],
            max_tokens=500,
        )
        raw = resp.choices[0].message.content or ""
        parsed = parse_json_response(raw)
        if isinstance(parsed, list):
            return [str(c).strip() for c in parsed if c and str(c).strip()]
        return []
    except Exception as e:
        logger.warning("VLM certificate supplement failed: %s", e)
        return []


def _extract_profile_multimodal_vl(content: bytes) -> dict:
    """Directly extract structured profile from scanned PDF pages using qwen-vl-plus.

    Skips the OCR→text intermediate step. Sends each page image + resume parse prompt
    to the vision model and returns a structured profile dict.
    """
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
        import openai
        from backend.llm import get_env_str, parse_json_response

        api_key = get_env_str("DASHSCOPE_API_KEY")
        base_url = get_env_str("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not api_key:
            logger.warning("No DASHSCOPE_API_KEY for multimodal profile extraction")
            return {}

        doc = fitz.open(stream=_io.BytesIO(content), filetype="pdf")
        skill_vocab = _build_skill_vocab()

        # Build message content: all page images + extraction prompt
        content_parts: list[dict] = []
        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            })

        # CRITICAL: use .format() (NOT .replace()) so {{...}} double-braces
        # are correctly converted to {..} in the JSON template shown to the LLM.
        # Using .replace() leaves double-braces intact, confusing the model.
        prompt_text = _RESUME_PARSE_PROMPT.format(
            resume_text="[见上方简历图片，请仔细识别图片中的所有文字并按要求提取结构化信息]",
            skill_vocab=skill_vocab,
        )
        content_parts.append({"type": "text", "text": prompt_text})

        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[{"role": "user", "content": content_parts}],
            max_tokens=3000,
        )
        raw_result = resp.choices[0].message.content or ""
        parsed = parse_json_response(raw_result)
        if not parsed or not isinstance(parsed, dict):
            logger.warning("Multimodal VL profile extraction: invalid JSON response")
            return {}

        parsed.setdefault("skills", [])
        parsed.setdefault("knowledge_areas", [])
        parsed.setdefault("experience_years", 0)
        parsed.setdefault("projects", [])
        parsed.setdefault("awards", [])
        parsed.setdefault("internships", [])
        parsed.setdefault("certificates", [])

        # Double-insurance: VLM tends to subjectively drop items like 普通话/驾驶证 from
        # the main JSON call. Run a dedicated single-task cert extraction and merge.
        supplemental_certs = _vlm_supplement_certificates(content)
        if supplemental_certs:
            existing_norm = {str(c).strip().lower() for c in parsed.get("certificates", [])}
            for c in supplemental_certs:
                if c.strip().lower() not in existing_norm:
                    parsed["certificates"].append(c)
                    existing_norm.add(c.strip().lower())
            logger.info("Certificate supplement merged: %d total after merge", len(parsed["certificates"]))

        parsed = _postprocess_profile(parsed)
        parsed["soft_skills"] = {
            "_version": 2,
            "communication": None, "learning": None, "collaboration": None,
            "innovation": None, "resilience": None,
        }
        # Store a raw_text placeholder so hasProfile check and reparse work.
        # We use the LLM's raw response as a text record.
        if not parsed.get("raw_text"):
            parsed["raw_text"] = f"[multimodal_extracted] {raw_result[:3000]}"
        logger.info(
            "Multimodal VL extraction: %d skills, %d projects, job_target=%s",
            len(parsed.get("skills", [])), len(parsed.get("projects", [])),
            parsed.get("job_target", ""),
        )
        return parsed
    except Exception as e:
        logger.warning("Multimodal VL profile extraction failed: %s", e)
        return {}


def _ocr_pdf_with_vl(content: bytes) -> str:
    """OCR fallback for scanned PDFs using qwen-vl-plus vision API.
    Used as last resort when _extract_profile_multimodal_vl also fails.
    """
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
        import openai
        from backend.llm import get_env_str

        api_key = get_env_str("DASHSCOPE_API_KEY")
        base_url = get_env_str("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not api_key:
            return ""

        doc = fitz.open(stream=_io.BytesIO(content), filetype="pdf")
        texts: list[str] = []
        client = openai.OpenAI(api_key=api_key, base_url=base_url)

        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            resp = client.chat.completions.create(
                model="qwen-vl-plus",
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": "请识别并提取这张简历图片中的所有文字内容，保持原始格式，不要添加额外说明。"},
                ]}],
                max_tokens=2000,
            )
            page_text = resp.choices[0].message.content or ""
            if page_text.strip():
                texts.append(page_text)

        return "\n\n".join(texts)
    except Exception as e:
        logger.warning("OCR fallback failed: %s", e)
        return ""


def _build_skill_vocab() -> str:
    """Collect all unique must_skills from graph as standard vocabulary (module-level cached)."""
    global _skill_vocab_cache
    if _skill_vocab_cache is not None:
        return _skill_vocab_cache
    graph_nodes = _get_graph_nodes()
    all_skills: set[str] = set()
    for n in graph_nodes.values():
        for s in n.get("must_skills", []):
            all_skills.add(s)
    _skill_vocab_cache = ", ".join(sorted(all_skills))
    return _skill_vocab_cache


_SKILLS_RETRY_PROMPT = """从以下简历文本中只提取技能列表，返回严格 JSON，不要其他文字：
{{"skills": [{{"name": "技能名（英文或通用短名）", "level": "familiar"}}]}}

优先使用词表中的名称：{skill_vocab}
简历：{resume_text}"""


def _extract_profile_with_llm(raw_text: str) -> dict:
    try:
        from backend.llm import llm_chat, parse_json_response
        skill_vocab = _build_skill_vocab()
        prompt = _RESUME_PARSE_PROMPT.format(
            resume_text=raw_text[:2500],
            skill_vocab=skill_vocab,
        )
        result = llm_chat([{"role": "user", "content": prompt}], temperature=0)
        parsed = parse_json_response(result)

        # Retry: if primary parse failed or returned no skills, do a focused skills-only call
        if not parsed or not parsed.get("skills"):
            logger.warning("_extract_profile_with_llm: primary parse returned no skills, retrying")
            retry_prompt = _SKILLS_RETRY_PROMPT.format(
                skill_vocab=skill_vocab,
                resume_text=raw_text[:1500],
            )
            retry_result = llm_chat([{"role": "user", "content": retry_prompt}], temperature=0)
            retry_parsed = parse_json_response(retry_result)
            if retry_parsed and retry_parsed.get("skills"):
                if not parsed:
                    parsed = {}
                parsed["skills"] = retry_parsed["skills"]

        if not parsed:
            parsed = {}
        # Normalize skill names using alias map
        parsed["skills"] = _normalize_skills(parsed.get("skills", []))
        parsed.setdefault("knowledge_areas", [])
        parsed.setdefault("experience_years", 0)
        parsed.setdefault("projects", [])
        parsed.setdefault("awards", [])
        parsed.setdefault("internships", [])
        parsed.setdefault("certificates", [])
        parsed = _postprocess_profile(parsed)
        parsed["raw_text"] = raw_text[:6000]
        parsed["soft_skills"] = {
            "_version": 2,
            "communication": None,
            "learning": None,
            "collaboration": None,
            "innovation": None,
            "resilience": None,
        }
        return parsed
    except Exception as e:
        logger.exception("_extract_profile_with_llm failed: %s", e)
        return {
            "skills": [],
            "knowledge_areas": [],
            "experience_years": 0,
            "raw_text": raw_text[:6000],
        }


# ── GET /profiles — return single profile ───────────────────────────────────

@router.get("")
@router.get("/")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the current user's profile. Auto-creates an empty one if none exists."""
    profile = _get_or_create_profile(user.id, db)

    # Lazy backfill: auto-locate on graph if position missing
    # No lazy backfill here — auto_locate runs during profile save, not during GET.
    # This keeps GET /profiles fast (no LLM calls).
    return ok(_profile_to_dict(profile, db, user.id))


# ── POST /profiles/parse-resume — parse only, don't save ────────────────────

@router.post("/parse-resume")
async def parse_resume(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Parse resume file and return structured data for preview.

    Does NOT save to DB — call PUT /profiles to merge the result.
    """
    # ── File validation ───────────────────────────────────────────────
    _MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    _ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}
    _ALLOWED_MIMES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }

    # Peek at first 10 MB, reject the rest
    content = await file.read(_MAX_SIZE + 1)
    if len(content) > _MAX_SIZE:
        raise HTTPException(413, "文件过大，请上传 10MB 以内的简历文件")

    filename = (file.filename or "resume.txt").strip()
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式 {ext!r}，请上传 PDF、Word 或 TXT 格式的简历")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in _ALLOWED_MIMES and content_type != "application/octet-stream":
        raise HTTPException(400, "文件类型不符，请上传简历文档")

    if filename.lower().endswith(".pdf"):
        try:
            import pdfplumber
            import io
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                raw_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            raw_text = content.decode("utf-8", errors="ignore")
    else:
        raw_text = content.decode("utf-8", errors="ignore")

    # Scanned PDF: use multimodal VL to extract profile directly (image → structured data)
    if not raw_text.strip() and filename.lower().endswith(".pdf"):
        profile_data = _extract_profile_multimodal_vl(content)
        if profile_data and profile_data.get("skills"):
            quality_data = ProfileService.compute_quality(profile_data)
            return ok({"profile": profile_data, "quality": quality_data})
        # Fallback: OCR text → LLM
        raw_text = _ocr_pdf_with_vl(content)

    if not raw_text.strip():
        raise HTTPException(400, "无法提取简历文本，请使用文字版 PDF 或直接粘贴简历文本")

    profile_data = _extract_profile_with_llm(raw_text)
    quality_data = ProfileService.compute_quality(profile_data)
    return ok({"profile": profile_data, "quality": quality_data})


# ── PUT /profiles — create-or-merge profile ──────────────────────────────────

class UpdateProfileRequest(BaseModel):
    profile: dict | None = None
    quality: dict | None = None
    merge: bool = True  # True = merge incoming into existing; False = overwrite

    model_config = {"extra": "ignore"}


@router.put("")
@router.put("/")
def update_profile(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create-or-update the user's single profile.

    If merge=True (default), incoming skills/knowledge_areas/projects/awards
    are merged with existing data. If merge=False, existing data is replaced.
    """
    profile = _get_or_create_profile(user.id, db)

    if req.profile is not None:
        if req.merge:
            existing = json.loads(profile.profile_json or "{}")
            merged = _merge_profiles(existing, req.profile)
        else:
            merged = req.profile

        profile.profile_json = json.dumps(merged, ensure_ascii=False, default=str)
        # Sync name to DB column only when source is NOT 'resume' (user confirmed)
        # During resume upload, name goes into profile_json but DB column stays null
        source = (req.profile or {}).get("source", "")
        if source != "resume" and merged.get("name") and not profile.name:
            profile.name = str(merged["name"]).strip()
        quality_data = ProfileService.compute_quality(merged)
        profile.quality_json = json.dumps(quality_data, ensure_ascii=False, default=str)

    if req.quality is not None:
        profile.quality_json = json.dumps(req.quality, ensure_ascii=False, default=str)

    db.commit()
    db.refresh(profile)

    # Graph location + growth event run in background threads — don't block the response
    if req.profile is not None:
        import threading as _threading
        from backend.db import SessionLocal as _SL
        _final = json.loads(profile.profile_json)
        _pid, _uid = profile.id, user.id
        _skill_count = len(_final.get("skills", []))
        _source = (_final or {}).get("source", "")

        def _locate_bg():
            _bg_db = _SL()
            try:
                _auto_locate_on_graph(_pid, _uid, _final, _bg_db)
            except Exception:
                logger.exception("Background graph location failed (profile %s)", _pid)
            finally:
                _bg_db.close()

        def _growth_event_bg():
            """Record profile_created milestone on first resume upload."""
            if _source != "resume" or _skill_count == 0:
                return
            _bg_db = _SL()
            try:
                from backend.db_models import GrowthEvent
                # Only record if this is truly the first upload (no prior profile_created events)
                exists = _bg_db.query(GrowthEvent).filter_by(
                    user_id=_uid, event_type="profile_created"
                ).first()
                if not exists:
                    from backend.services.growth_log_service import record_profile_created
                    record_profile_created(_uid, _pid, _skill_count, _bg_db)
            except Exception:
                pass
            finally:
                _bg_db.close()

        _threading.Thread(target=_locate_bg, daemon=True).start()
        _threading.Thread(target=_growth_event_bg, daemon=True).start()

    return ok(_profile_to_dict(profile, db, user.id), message="画像已更新")


# ── POST /profiles/reparse — re-run LLM on stored raw_text ──────────────────

@router.post("/reparse")
def reparse_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-run LLM extraction on stored raw_text and update the profile."""
    profile = _get_or_create_profile(user.id, db)
    existing = json.loads(profile.profile_json or "{}")
    raw_text = existing.get("raw_text") or existing.get("markdown", "")
    if not raw_text.strip():
        raise HTTPException(400, "没有原始简历文本，请重新上传简历")

    profile_data = _extract_profile_with_llm(raw_text)
    quality_data = ProfileService.compute_quality(profile_data)

    profile.profile_json = json.dumps(profile_data, ensure_ascii=False, default=str)
    profile.quality_json = json.dumps(quality_data, ensure_ascii=False, default=str)
    db.commit()
    db.refresh(profile)

    graph_position = _auto_locate_on_graph(profile.id, user.id, profile_data, db)
    result = _profile_to_dict(profile, db, user.id)
    if graph_position:
        result["graph_position"] = graph_position
    return ok(result, message="重新解析完成")


# ── PATCH /profiles/name — lightweight name update ────────────────────────────

class SetNameRequest(BaseModel):
    name: str


@router.patch("/name")
def set_profile_name(
    req: SetNameRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set the profile display name. Lightweight — no LLM calls."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "画像不存在")
    profile.name = req.name.strip()
    db.commit()
    return ok(message="姓名已更新")


# ── PATCH /profiles/preferences — save career preferences ────────────────────

class PreferencesRequest(BaseModel):
    work_style: str = ""      # tech / product / data / management
    value_priority: str = ""  # growth / stability / balance / innovation
    work_intensity: str = ""  # high / moderate / low
    company_type: str = ""    # big_tech / growing / startup / state_owned
    ai_attitude: str = ""     # do_ai / avoid_ai / no_preference
    current_stage: str = ""   # lost / know_gap / ready / not_started


@router.patch("/preferences")
def set_preferences(
    req: PreferencesRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save career preferences into profile_json.preferences field."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "画像不存在")

    profile_data = json.loads(profile.profile_json or "{}")
    profile_data["preferences"] = req.model_dump(exclude_none=True)
    profile.profile_json = json.dumps(profile_data, ensure_ascii=False)
    db.commit()
    return ok(message="就业意愿已保存")


# ── DELETE /profiles — reset profile data ────────────────────────────────────

@router.delete("")
@router.delete("/")
def reset_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reset the user's profile to empty state (keeps the record, clears data)."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return ok(message="画像已清空")

    profile.profile_json = "{}"
    profile.quality_json = "{}"
    profile.name = ""
    profile.source = "manual"

    # Single-profile system: delete all career goals by user_id
    # (profile_id filter alone misses residual rows from old multi-profile data)
    db.query(CareerGoal).filter(
        CareerGoal.user_id == user.id
    ).delete(synchronize_session=False)

    db.commit()
    return ok(message="画像已重置")


# ── SJT soft-skill assessment (v2) ───────────────────────────────────────────

@router.post("/sjt/generate")
def generate_sjt(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate personalized SJT questions based on the user's profile."""
    import uuid
    from datetime import datetime, timedelta, timezone
    from backend.db_models import SjtSession

    profile = _get_or_create_profile(user.id, db)
    profile_data = json.loads(profile.profile_json or "{}")

    try:
        questions = ProfileService.generate_sjt_questions(profile_data)
    except Exception:
        try:
            questions = ProfileService.generate_sjt_questions(profile_data)
        except Exception as e:
            raise HTTPException(500, f"生成失败，请重试: {e}")

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    session = SjtSession(
        id=session_id,
        profile_id=profile.id,
        questions_json=json.dumps(questions, ensure_ascii=False),
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    db.add(session)
    db.commit()

    safe_questions = [
        {
            "id": q["id"],
            "dimension": q["dimension"],
            "scenario": q["scenario"],
            "options": [{"id": o["id"], "text": o["text"]} for o in q["options"]],
        }
        for q in questions
    ]
    return ok({"session_id": session_id, "questions": safe_questions})


class SjtSubmitRequest(BaseModel):
    session_id: str
    answers: list[dict]


@router.post("/sjt/submit")
def submit_sjt(
    req: SjtSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Score SJT v2 answers, generate advice, write back to profile."""
    from datetime import datetime, timezone
    from backend.db_models import SjtSession

    profile = _get_or_create_profile(user.id, db)

    session = db.query(SjtSession).filter(SjtSession.id == req.session_id).first()
    if not session:
        raise HTTPException(410, "评估会话不存在，请重新开始")
    if session.profile_id != profile.id:
        raise HTTPException(400, "会话与画像不匹配")

    now_utc = datetime.now(timezone.utc)
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now_utc:
        db.delete(session)
        db.commit()
        raise HTTPException(410, "评估已过期，请重新开始")

    questions = json.loads(session.questions_json)
    expected_ids = {q["id"] for q in questions}
    submitted_ids = {a.get("question_id") for a in req.answers}
    missing = expected_ids - submitted_ids
    if missing:
        raise HTTPException(400, f"缺少以下题目的回答: {', '.join(sorted(missing))}")

    result = ProfileService.score_sjt_v2(req.answers, questions)
    dimensions = result["dimensions"]

    profile_data = json.loads(profile.profile_json or "{}")
    advice = ProfileService.generate_sjt_advice(dimensions, req.answers, questions, profile_data)

    soft_skills = {"_version": 2}
    for dim, info in dimensions.items():
        soft_skills[dim] = {
            "score": info["score"],
            "level": info["level"],
            "advice": advice.get(dim, ""),
        }

    profile_data["soft_skills"] = soft_skills
    profile.profile_json = json.dumps(profile_data, ensure_ascii=False, default=str)
    quality_data = ProfileService.compute_quality(profile_data)
    profile.quality_json = json.dumps(quality_data, ensure_ascii=False, default=str)

    db.delete(session)
    db.commit()

    all_scores = [info["score"] for info in dimensions.values()]
    overall_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
    overall_level = ProfileService.score_to_level(overall_score)

    return ok({
        "dimensions": [
            {"key": dim, "level": info["level"], "advice": advice.get(dim, "")}
            for dim, info in dimensions.items()
        ],
        "overall_level": overall_level,
    })
