"""Profiles router — single-profile system.

Each user has exactly one Profile. Multiple resume uploads are incremental
additions that merge into the same profile (union skills, take higher level).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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

    # Education: update if incoming has richer data
    if incoming.get("education") and any(v for v in incoming["education"].values() if v):
        merged["education"] = incoming["education"]

    # experience_years: keep max
    if incoming.get("experience_years", 0) > existing.get("experience_years", 0):
        merged["experience_years"] = incoming["experience_years"]

    # name: update if incoming provides one
    if incoming.get("name"):
        merged["name"] = incoming["name"]

    # raw_text: always use latest
    if incoming.get("raw_text"):
        merged["raw_text"] = incoming["raw_text"]

    # soft_skills: preserve existing assessment; only set if currently absent
    if not merged.get("soft_skills") and incoming.get("soft_skills"):
        merged["soft_skills"] = incoming["soft_skills"]

    return merged


# ── LLM-based role matching ───────────────────────────────────────────────────

_ROLE_LIST_CACHE: str | None = None
_GRAPH_NODES_CACHE: dict | None = None


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
    """Build a role list string for the LLM prompt. If node_ids given, only include those."""
    global _ROLE_LIST_CACHE
    graph_nodes = _get_graph_nodes()

    if node_ids is not None:
        # Filtered list — don't use cache
        lines = []
        for nid in node_ids:
            n = graph_nodes.get(nid, {})
            label = n.get("label", nid)
            ms = ", ".join(str(s) for s in (n.get("must_skills") or [])[:6])
            lines.append(f"- {nid}: {label}（{ms}）")
        return "\n".join(lines)

    if _ROLE_LIST_CACHE:
        return _ROLE_LIST_CACHE
    lines = []
    for nid, n in graph_nodes.items():
        label = n.get("label", nid)
        ms = ", ".join(str(s) for s in (n.get("must_skills") or [])[:6])
        lines.append(f"- {nid}: {label}（{ms}）")
    _ROLE_LIST_CACHE = "\n".join(lines)
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


_ROLE_MATCH_PROMPT = """你是一个职业匹配 AI。根据用户的技能和背景，完成两件事：

1. 从以下 {role_count} 个岗位中选出最匹配的 1 个作为用户**当前定位**（current_position）
2. 推荐 5-6 个最适合的方向，按匹配度从高到低排序
   - 最匹配的排第一（包括当前定位岗位本身）
   - 只推荐和用户技能有真实关联的岗位，宁少勿滥，不要凑数
   - 每个推荐附一句话理由，说明用户的哪些技能/经验和这个方向相关
   - affinity_pct 反映技能匹配程度（0-100）

【岗位列表】
{role_list}

【用户技能】
{user_skills}

【用户背景】
专业：{major}，学历：{degree}，工作年限：{exp_years}

返回严格 JSON，不要任何其他文字：
{{
  "current_position": {{"role_id": "最匹配岗位ID", "reason": "一句话理由"}},
  "recommendations": [
    {{"role_id": "岗位ID", "label": "中文名", "reason": "一句话推荐理由", "affinity_pct": 匹配度0到100}}
  ]
}}"""


def _llm_match_role(profile_data: dict) -> dict | None:
    """Embedding pre-filter → LLM fine-rank. One call for position + recommendations."""
    try:
        from backend.llm import llm_chat, parse_json_response

        skills = [s.get("name", "") for s in profile_data.get("skills", []) if s.get("name")]
        if not skills:
            return None

        # Step 1: Embedding coarse filter — relative threshold
        candidate_ids = _embedding_prefilter(profile_data)
        role_list = _get_role_list_text(candidate_ids)

        edu = profile_data.get("education", {})
        prompt = _ROLE_MATCH_PROMPT.format(
            role_count=len(candidate_ids),
            role_list=role_list,
            user_skills=", ".join(skills),
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


# ── Resume parsing ────────────────────────────────────────────────────────────

_RESUME_PARSE_PROMPT = """你是一个简历解析 AI。请从以下简历文本中提取结构化信息，以 JSON 格式返回。

返回格式（严格 JSON，不要加注释或 markdown）：
{{
  "name": "姓名（可选）",
  "experience_years": 工作年限数字（在校生/应届生填0）,
  "education": {{"degree": "学位", "major": "专业", "school": "学校"}},
  "skills": [
    {{"name": "技能名称", "level": "advanced|intermediate|familiar|beginner"}}
  ],
  "knowledge_areas": ["知识领域1", "知识领域2"],
  "projects": ["项目描述1", "项目描述2"],
  "awards": ["竞赛/荣誉1", "竞赛/荣誉2"]
}}

【技能命名规则（严格执行）】
技能名称必须使用简短标准名，不要加"语言/编程/系统/框架/开发"等后缀。
优先使用以下标准词表中的名称（如果简历中的技能可以对应上）：
{skill_vocab}
如果简历中的技能不在词表中，使用简短通用名称（如"多线程"而非"多线程编程"，"Linux"而非"Linux系统编程"，"C++"而非"C/C++语言"）。

【字段分类规则（严格执行）】
- projects：仅放实际动手开发/实施的项目，如"高并发内存池"、"SACOS测试项目"
- awards：仅放竞赛获奖、荣誉证书、奖学金，如"软件测试大赛省二"、"程序设计省一"
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


def _ocr_pdf_with_vl(content: bytes) -> str:
    """OCR fallback for scanned PDFs using qwen-vl-plus vision API."""
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
        import openai
        from backend.llm import get_env_str

        api_key = get_env_str("DASHSCOPE_API_KEY")
        base_url = get_env_str("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not api_key:
            logger.warning("No DASHSCOPE_API_KEY for OCR fallback")
            return ""

        doc = fitz.open(stream=_io.BytesIO(content), filetype="pdf")
        texts: list[str] = []
        client = openai.OpenAI(api_key=api_key, base_url=base_url)

        for page_num in range(min(len(doc), 3)):  # OCR at most 3 pages
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()

            resp = client.chat.completions.create(
                model="qwen-vl-plus",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                        {"type": "text", "text": "请识别并提取这张简历图片中的所有文字内容，保持原始格式，不要添加额外说明。"},
                    ],
                }],
                max_tokens=2000,
            )
            page_text = resp.choices[0].message.content or ""
            if page_text.strip():
                texts.append(page_text)

        result = "\n\n".join(texts)
        logger.info("OCR extracted %d chars from scanned PDF", len(result))
        return result
    except Exception as e:
        logger.warning("OCR fallback failed: %s", e)
        return ""


def _build_skill_vocab() -> str:
    """Collect all unique must_skills from graph as standard vocabulary."""
    graph_nodes = _get_graph_nodes()
    all_skills: set[str] = set()
    for n in graph_nodes.values():
        for s in n.get("must_skills", []):
            all_skills.add(s)
    return ", ".join(sorted(all_skills))


def _extract_profile_with_llm(raw_text: str) -> dict:
    try:
        from backend.llm import llm_chat, parse_json_response
        skill_vocab = _build_skill_vocab()
        prompt = _RESUME_PARSE_PROMPT.format(
            resume_text=raw_text[:4000],
            skill_vocab=skill_vocab,
        )
        result = llm_chat([{"role": "user", "content": prompt}], temperature=0)
        parsed = parse_json_response(result)
        parsed.setdefault("skills", [])
        parsed.setdefault("knowledge_areas", [])
        parsed.setdefault("experience_years", 0)
        parsed.setdefault("projects", [])
        parsed.setdefault("awards", [])
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
    except Exception:
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
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Parse resume file and return structured data for preview.

    Does NOT save to DB — call PUT /profiles to merge the result.
    """
    content = await file.read()
    filename = file.filename or "resume.txt"

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

    # OCR fallback for scanned PDFs (pdfplumber returns empty)
    if not raw_text.strip() and filename.lower().endswith(".pdf"):
        raw_text = _ocr_pdf_with_vl(content)

    if not raw_text.strip():
        raise HTTPException(400, "无法提取简历文本")

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

    if req.profile is not None:
        final_data = json.loads(profile.profile_json)
        _auto_locate_on_graph(profile.id, user.id, final_data, db)

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
