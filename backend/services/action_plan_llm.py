# -*- coding: utf-8 -*-
"""
Action plan LLM generator — replaces the hardcoded template engine in
`_build_action_plan` with a structured LLM-driven approach.

Design constraints (from product & UX):
  - Descriptive tone only; no imperative commands
  - No concrete project prescriptions
  - No hardcoded learning-resource URLs
  - 3 stages with 2-4 items each
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.llm import get_llm_client, get_model, parse_json_response

logger = logging.getLogger(__name__)

# ─── Pydantic models ──────────────────────────────────────────────────────────

class PlanItem(BaseModel):
    id: str
    type: Literal["skill", "project", "job_prep"]
    text: str = Field(..., max_length=350, description="描述式建议，禁止祈使句，要求内容充实、有细节")
    tag: str = Field(default="")
    priority: Literal["high", "medium", "low"] = "medium"
    phase: Literal[1, 2, 3] = 1
    done: bool = False


class GrowthStage(BaseModel):
    stage: int = Field(..., ge=1, le=3)
    label: str
    duration: str
    milestone: str
    items: list[PlanItem]


class ActionPlan(BaseModel):
    stages: list[GrowthStage]
    # Backward-compat aliases
    skills: list[PlanItem] = Field(default_factory=list)
    project: list[PlanItem] = Field(default_factory=list)
    job_prep: list[PlanItem] = Field(default_factory=list)


# ─── Simple in-memory cache (suitable for single-process dev; replace with Redis later) ───

_CACHE: dict[str, dict] = {}
_CACHE_TTL_SECONDS = 24 * 3600


def _cache_key(context: dict) -> str:
    """Deterministic cache key based on minimal context."""
    payload = json.dumps(context, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _get_cached_plan(key: str) -> dict | None:
    return _CACHE.get(key)


def _set_cached_plan(key: str, plan: dict) -> None:
    _CACHE[key] = plan


# ─── Prompt engineering ───────────────────────────────────────────────────────

_SYSTEM_PROMPT = """你是一位职业规划观察员。你的任务是基于用户项目经历和岗位要求的深度对比，生成一份描述式的三阶段成长计划。

【核心原则】
1. 你是“诊断者”，不是“监工”。只描述现状、具体盲区和可选方向，不命令用户必须做什么。
2. 必须仔细阅读用户的项目描述，对比岗位要求，指出**具体的技术盲区或可量化缺失点**（而不是复述“你缺高并发”“你缺性能优化”这种粗粒度标签）。
3. 严禁引用用户已有的具体项目名称来生成新任务（例如禁止说“在『某某项目』基础上引入 XX”）。
4. 不维护任何外部学习资源链接，但可以建议用户通过搜索引擎或技术社区检索关键词。

【输入使用优先级】
- 第一优先级：用户的项目描述（做了什么、用了什么技术、有没有量化数据）
- 第二优先级：岗位的具体要求（skill_tiers + ai_impact_narrative）
- 第三优先级：top_missing 列表（仅作参考，不要直接复述）

【教练视角 — 不只诊断技能，还要观察发展阶段】
- 把目标岗位的学生视为一个特定职业阶段的个体：如果是初级/校招岗位，关注「基础扎实度 + 项目完整度」；如果是中高级岗位，关注「系统深度 + 可量化影响」。
- 阶段 1（求职准备）的任务要体现「Impact-first」思维：如果学生项目描述里缺少动词+动作+数字的结构，要指出这会在简历筛选中削弱竞争力。

【输出要求 — 具体、充实、有细节】
❌ 禁止输出这种粗粒度判断：
  - "高并发存在缺口"
  - "性能优化需要通过实战掌握"
  - "系统编程存在缺口"

✅ 应该输出这种具体盲区（要有上下文、有解释、有后果）：
  - "当前项目覆盖了内存分配和网络 I/O，但缺少可量化的性能基准数据（如 QPS/latency benchmark）。在面试中，面试官往往会围绕性能数字展开追问，没有 benchmark 会让技术深度难以被验证。"
  - "项目中对系统调用的使用以 epoll 为主，但缺少对 io_uring 或内核调度机制的比较性理解。这意味着在讨论高并发架构选型时，可能难以回答『为什么不用 io_uring』这类进阶问题。"
  - "已有项目证明了工程落地能力，但缺少公开可验证的文档（GitHub README）和测试覆盖说明。对于校招或社招初筛而言，可在线查看的工程化痕迹是简历脱颖而出的重要加分项。"

【内容丰富度要求 — 必须遵守】
- 每个 item 的 text 长度建议在 60–150 个汉字之间，太短会被认为信息不足。
- 不要只写一句话下结论，要补充「为什么重要」或「在面试/求职中会带来什么影响」。
- 阶段 2 的技能任务：如果项目已涉及该方向，要说明「已有哪些」+「还缺哪些」+「缺了会怎样」。
- 阶段 3 的项目/求职任务：要给出 2 条具体观察，而不是泛泛的鼓励。

【句式禁令 — 绝对不可违反】
- 禁止以以下动词开头：完成、搭建、实现、编写、学习、掌握、阅读、深入、用、通过、进行、梳理、配置、部署。
- 禁止出现指令性短语：你应该、你需要、你必须、建议你先、最好去做。
- 每个建议必须是观察句或开放式表达，例如：
  ❌ 完成 TypeScript 官方 Handbook 基础篇
  ✅ TypeScript 的类型系统是该方向的重要基础，值得在项目实践中逐步建立体感
  ❌ 用 Redis 实现缓存穿透防护
  ✅ Redis 的缓存策略在高并发场景中经常出现，结合现有项目探索其实践形态会更有帮助

【输出格式 — 严格 JSON】
必须输出如下 JSON 结构，不要任何 markdown 代码块标记，不要解释：
{
  "stages": [
    {
      "stage": 1,
      "label": "立即整理",
      "duration": "0-2周",
      "milestone": "string",
      "items": [
        {
          "id": "string",
          "type": "skill|project|job_prep",
          "text": "描述式文本，要求充实有细节",
          "tag": "短标签",
          "priority": "high|medium|low",
          "phase": 1
        }
      ]
    },
    {
      "stage": 2,
      "label": "技能补强",
      "duration": "2-6周",
      "milestone": "string",
      "items": []
    },
    {
      "stage": 3,
      "label": "项目冲刺与求职",
      "duration": "6-12周",
      "milestone": "string",
      "items": []
    }
  ]
}

【阶段与内容要求】
- 阶段 1（立即整理）：求职准备类任务，如简历整理、投递策略。生成 2 个 items，不要出现技能学习任务。
- 阶段 2（技能补强）：根据**具体技术盲区**生成 2–4 个描述式任务。如果项目已经覆盖了某方向但缺少某个具体维度，要指出来，而不是重复整个方向。
- 阶段 3（项目冲刺与求职）：项目方向参考或求职推进任务，生成 2–3 个 items，不要绑定具体项目名，但可以指出“简历/作品集缺少哪些具体元素”。

【标签规范】
- skill 类型：tag 用 "具体盲区" 或 "面试追问点" 或 "可量化缺失"
- project 类型：tag 用 "展示资料完整性" 或 "实战方向参考"
- job_prep 类型：tag 用 "求职必备" 或 "投递策略"
"""

_IMPERATIVE_PREFIXES = (
    "完成", "搭建", "实现", "编写", "学习", "掌握", "阅读",
    "深入", "用", "通过", "进行", "梳理", "配置", "部署",
    "建议你", "你应该", "你需要", "你必须", "最好", "先",
)


def _is_descriptive(text: str) -> bool:
    """Rule-based filter: reject imperative openings."""
    t = text.strip()
    return not any(t.startswith(p) for p in _IMPERATIVE_PREFIXES)


def _build_user_prompt(context: dict) -> str:
    """Assemble rich context for the LLM — project descriptions first."""
    proj_summary = "\n".join(
        f"- {p.get('name', '未命名')}: {p.get('desc', '无描述')}" for p in context.get("projects", [])
    ) or "无"

    missing_lines = []
    for m in context.get("top_missing", []):
        line = f"- {m['name']}（{m.get('tier', 'important')}）"
        if m.get("fill_path"):
            line += f" · 补法类型: {m['fill_path']}"
        missing_lines.append(line)
    missing_block = "\n".join(missing_lines) or "无"

    market = context.get("market", {})
    market_block = (
        f"- 需求变化: {market.get('demand_change_pct', '—')}%; "
        f"薪资年增长率: {market.get('salary_cagr', '—')}%; "
        f"市场中位月薪: {market.get('salary_p50', '—')} 元"
    )

    return f"""请根据以下数据生成描述式成长计划（严格 JSON，不要 markdown 标记）。
重点：仔细阅读【项目经历】和【岗位要求】，找出**具体的技术盲区**，不要泛泛而谈。

# 项目经历（这是最重要的输入）
{proj_summary}

# 岗位要求
- 岗位: {context.get('node_label', '')}
- AI 影响叙事: {context.get('ai_impact_narrative', '') or '无'}
- 差异化方向: {context.get('differentiation_advice', '') or '无'}

# 已有技能标签
{', '.join(context.get('skills', [])) or '无'}

# 求职状态
已投递 {context.get('app_count', 0)} 家公司

# 技能缺口列表（仅供参考，不要直接复述）
{missing_block}

# 市场信号
{market_block}

# 输出要求
1. 严格输出 JSON，stages 必须包含 3 个阶段，阶段 1 和阶段 3 各 2 个 items，阶段 2 生成 2–4 个 items。
2. text 必须描述式且禁止祈使句，每条 text 要求 60–150 个汉字，内容充实，有「为什么」和「会怎样」的解释。
3. **必须指出具体盲区**（例如缺少 benchmark 数据、缺少某类系统调用分析、缺少可验证文档等），禁止只说“你缺高并发/性能优化/系统编程”。
"""


def _validate_and_coerce(raw: Any, context: dict) -> dict:
    """Validate LLM JSON, coerce into backward-compat shape, and fallback on violations."""
    if not isinstance(raw, dict):
        raise ValueError("LLM response is not a dict")

    stages_raw = raw.get("stages", [])
    if len(stages_raw) != 3:
        raise ValueError(f"Expected 3 stages, got {len(stages_raw)}")

    stages: list[dict] = []
    skills: list[PlanItem] = []
    project: list[PlanItem] = []
    job_prep: list[PlanItem] = []

    for idx, s in enumerate(stages_raw, start=1):
        label = s.get("label") or ["立即整理", "技能补强", "项目冲刺与求职"][idx - 1]
        duration = s.get("duration") or ["0-2周", "2-6周", "6-12周"][idx - 1]
        milestone = s.get("milestone") or ""
        items_raw = s.get("items", [])
        items_out: list[dict] = []

        for it in items_raw:
            text = it.get("text", "")
            if not _is_descriptive(text):
                # Rewrite once with low temperature if possible, else fallback
                text = _fallback_text(it.get("skill_name") or it.get("type"), context)
            item_dict = {
                "id": it.get("id") or f"item_{idx}_{len(items_out)}",
                "type": it.get("type", "skill"),
                "text": text,
                "tag": it.get("tag", ""),
                "priority": it.get("priority", "medium"),
                "phase": idx,
                "done": False,
            }
            items_out.append(item_dict)
            pi = PlanItem.model_validate(item_dict)
            if pi.type == "skill":
                skills.append(pi)
            elif pi.type == "project":
                project.append(pi)
            elif pi.type == "job_prep":
                job_prep.append(pi)

        stages.append({
            "stage": idx,
            "label": label,
            "duration": duration,
            "milestone": milestone,
            "items": items_out,
        })

    return {
        "stages": stages,
        "skills": [p.model_dump() for p in skills],
        "project": [p.model_dump() for p in project],
        "job_prep": [p.model_dump() for p in job_prep],
    }


def _fallback_text(key: str | None, context: dict) -> str:
    """Ultimate fallback when LLM violates descriptive constraints."""
    if not key:
        return "结合当前方向的特点，探索适合自己的学习或实践路径。"
    return f"{key} 是当前方向的常见技术栈，结合你的项目背景探索其实践路径会更有价值。"


def _rewrite_with_low_temperature(prompt: str, context: dict) -> dict:
    """One-shot low-temperature rewrite for descriptive violations."""
    try:
        client = get_llm_client(timeout=60)
        resp = client.chat.completions.create(
            model=get_model("fast"),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt + "\n\n【注意】上次的输出中有祈使句，请全部改为描述式表达。"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000,
        )
        raw = parse_json_response(resp.choices[0].message.content or "")
        return _validate_and_coerce(raw, context)
    except Exception as exc:
        logger.warning("Low-temperature rewrite failed: %s", exc)
        raise


def build_action_plan_with_llm(context: dict) -> dict:
    """
    Build a descriptive action plan via LLM.

    Args:
        context: {
            "node_label": str,
            "ai_impact_narrative": str,
            "differentiation_advice": str,
            "skills": list[str],
            "projects": list[dict],
            "app_count": int,
            "top_missing": list[dict],
            "market": dict,
        }

    Returns:
        dict matching the legacy ActionPlan shape (stages + skills/project/job_prep).
    """
    cache_key = _cache_key(context)
    cached = _get_cached_plan(cache_key)
    if cached is not None:
        logger.info("Action plan cache hit for key=%s", cache_key)
        return cached

    prompt = _build_user_prompt(context)

    try:
        client = get_llm_client(timeout=60)
        resp = client.chat.completions.create(
            model=get_model("fast"),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=2000,
        )
        raw_text = resp.choices[0].message.content or ""
        raw = parse_json_response(raw_text)

        try:
            plan = _validate_and_coerce(raw, context)
        except ValueError as ve:
            logger.warning("Initial LLM plan validation failed (%s), attempting rewrite", ve)
            plan = _rewrite_with_low_temperature(prompt, context)

        _set_cached_plan(cache_key, plan)
        return plan

    except Exception as exc:
        logger.error("LLM action plan generation failed: %s", exc)
        raise
