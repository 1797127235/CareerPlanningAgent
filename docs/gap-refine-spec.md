# Spec: 运行时 LLM 筛选 skill_gap（gap-refine）

## 背景与目标

当前 `_build_skill_gap`（`backend/services/report/skill_gap.py:324`）的 `top_missing` 完全基于 `node.skill_tiers - user.skills` 集合运算，不看用户的项目内容。结果：

- `systems-cpp` 节点的 `important` 层包含 `GDB / CMake / 高并发 / 性能优化 / 内存管理`
- 用户 156 写过"C++ 高性能网络库"+"高并发内存池"项目
- 但系统判定他"缺高并发 / 缺内存管理 / 缺 GDB"—— **对写过内存池的人说"缺内存管理"是荒谬的**

`top_missing` 再喂给 `action-plan` skill，就产出了你看到的"GDB 相关技术关键词未出现在项目描述中，建议关注..."这种万能模板。

**目标**：在 `_build_skill_gap` 之后插入一道 LLM refine，基于用户具体项目证据筛选 `top_missing`，分三类：

- **keep_missing**：真缺，保留
- **move_to_matched**：项目已体现，移到 matched
- **drop**：工具类/常识类，从列表整体剔除（不算 missing 也不算 matched）

失败时 fallback 到原始 `_skill_gap`，不破坏现有流程。

---

## 改动范围

三个文件：
1. 新建 `backend/skills/gap-refine/SKILL.md`
2. `backend/services/report/skill_gap.py` 新增 `_refine_gap_with_llm`
3. `backend/services/report/pipeline.py` 调用点接入

不改前端、不改 `graph.json`、不改现有 `_build_skill_gap` 的签名和返回结构。

---

## 任务 1：新 skill `gap-refine`

**文件**：`backend/skills/gap-refine/SKILL.md`

```markdown
---
name: gap-refine
description: 基于用户画像和项目证据，从技能缺口列表中识别伪缺口（项目已覆盖 / 工具类默认会）
model: fast
temperature: 0.1
max_tokens: 800
output: json
---

## System

你是技能评估员。你收到：
1. 目标岗位名
2. 一份"技能缺口"列表（每个技能带 tier 和 freq）
3. 学生的画像核心（声明的技能、简历项目描述、知识领域、教育）

你的任务：对每条缺口判断——

- **真缺（keep_missing）**：学生既没声明、项目描述里也没证据。保留。
- **项目已覆盖（move_to_matched）**：项目描述里有**具体证据**（技术名 / 关键词 / 相关实现）能证明学生实际做过。移到已掌握。
- **工具/常识（drop）**：这个"技能"只是工具链或通用常识，不是差异化能力。任何从业者都默认会。剔除。

### 判定标准（严格）

**move_to_matched 的证据要求**：
- 项目描述里必须出现该技能的具体关键词或其**核心实现形式**
- 例："高并发" 缺口 + 项目描述含 "高并发内存池" → 直接匹配
- 例："内存管理" 缺口 + 项目描述含 "tcmalloc / 线程缓存 / 中心内存池" → 间接但强证据
- 例："Redis" 缺口 + 项目描述无任何 Redis / 缓存字样 → **不能** move

**drop 的判定**（**严格保守，宁可放过不可滥杀**）：

只有以下情况才 drop：
- **纯构建/调试工具**：`GDB / LLDB / CMake / Makefile / Git / Docker Desktop` 这类——对应方向的所有工程师都默认会，不是"缺口"
- **基础语法/常识**：`SQL 基础 / HTTP 协议 / JSON` 这类——如果岗位不是专门考这个就 drop
- **和目标方向明显错配**：例如 `frontend` 节点里列了 "Photoshop" 作 bonus 但学生是开发不是设计——drop

**以下不能 drop（这些都是真能力）**：
- 高并发 / 分布式 / 性能优化 / 内存管理 / 系统编程 / 多线程
- 任何带具体框架/协议名的：Redis / Kafka / gRPC / epoll / io_uring
- 任何带具体语言版本特性的：C++20 协程 / Go 泛型 / Rust trait

### 输出格式（严格 JSON）

{
  "keep_missing": ["技能名1", "技能名2"],
  "move_to_matched": [
    {"name": "技能名", "evidence": "从项目描述里摘一句 ≤30 字的关键字"}
  ],
  "drop": [
    {"name": "技能名", "reason": "一句话为什么 drop ≤30 字"}
  ]
}

**硬约束**：
1. 输入 `top_missing` 里的每个技能**必须且仅能**出现在三类之一，不得遗漏、不得重复
2. `move_to_matched` 的 `evidence` 必须是项目描述里的**原文片段**（可缩写，但不得编造）
3. `drop` 宁可保守——拿不准就放 `keep_missing`
4. 不许添加输入列表之外的新技能名
5. 严格 JSON，不要 markdown 代码块

## User

目标岗位：{target_label}

## 技能缺口列表（top_missing）

{missing_block}

## 学生画像

声明的技能：{claimed_skills_line}

知识领域：{knowledge_areas_line}

简历项目描述（原文）：
{projects_block}

教育：{education_line}

---

请输出 JSON。
```

---

## 任务 2：`_refine_gap_with_llm` 函数

**文件**：`backend/services/report/skill_gap.py`（追加在文件末尾）

```python
def _refine_gap_with_llm(
    skill_gap_result: dict,
    profile_data: dict,
    target_label: str,
) -> dict:
    """Post-process skill_gap via LLM to drop pseudo-gaps / move to matched.

    Args:
        skill_gap_result: 原始 _build_skill_gap 返回的 dict
        profile_data: parsed profile.profile_json
        target_label: 目标岗位 label（用于 prompt）

    Returns:
        修正后的 dict（同 schema）。失败时原样返回 skill_gap_result。

    副作用：在返回的 dict 里加一个字段 `_refine_meta`，内容如下
    用于日志/调试观察：
    {
        "enabled": True,
        "moved_to_matched": [{"name": "高并发", "evidence": "..."}],
        "dropped": [{"name": "GDB", "reason": "..."}],
        "kept_missing_count": 3,
    }
    如果 refine 失败或跳过，`_refine_meta = {"enabled": False, "reason": "..."}`
    """
    import copy
    import logging
    logger = logging.getLogger(__name__)

    top_missing = skill_gap_result.get("top_missing", []) or []
    if len(top_missing) < 2:
        # 少于 2 条不值得调用 LLM
        out = dict(skill_gap_result)
        out["_refine_meta"] = {"enabled": False, "reason": "top_missing too small"}
        return out

    # 构造 prompt 上下文
    missing_lines = []
    for m in top_missing:
        name = m.get("name", "") if isinstance(m, dict) else str(m)
        tier = m.get("tier", "") if isinstance(m, dict) else ""
        freq = m.get("freq", 0) if isinstance(m, dict) else 0
        missing_lines.append(f"- {name}（{tier}，JD频率 {freq:.2f}）")
    missing_block = "\n".join(missing_lines)

    claimed = []
    for s in (profile_data.get("skills") or []):
        if isinstance(s, dict):
            claimed.append(str(s.get("name", "")))
        elif isinstance(s, str):
            claimed.append(s)
    claimed_skills_line = ", ".join([c for c in claimed if c]) or "（空）"

    knowledge = profile_data.get("knowledge_areas") or []
    knowledge_areas_line = ", ".join([str(k) for k in knowledge if k]) or "（空）"

    projs = profile_data.get("projects") or []
    proj_lines = []
    for p in projs[:4]:
        if isinstance(p, str) and p.strip():
            proj_lines.append(f"- {p[:200]}")
        elif isinstance(p, dict):
            text = p.get("summary") or p.get("description") or p.get("name") or ""
            if text:
                proj_lines.append(f"- {str(text)[:200]}")
    projects_block = "\n".join(proj_lines) or "（无项目描述）"

    edu = profile_data.get("education") or {}
    if isinstance(edu, dict):
        education_line = " · ".join(
            filter(None, [edu.get(k, "") for k in ("degree", "major", "school")])
        ) or "（空）"
    else:
        education_line = "（空）"

    # 调 LLM
    try:
        from backend.skills import invoke_skill
        parsed = invoke_skill(
            "gap-refine",
            target_label=target_label,
            missing_block=missing_block,
            claimed_skills_line=claimed_skills_line,
            knowledge_areas_line=knowledge_areas_line,
            projects_block=projects_block,
            education_line=education_line,
        )
    except Exception as e:
        logger.warning("[gap-refine] LLM failed: %s: %s; fallback to original gap",
                       type(e).__name__, e)
        out = dict(skill_gap_result)
        out["_refine_meta"] = {"enabled": False, "reason": f"llm_fail:{type(e).__name__}"}
        return out

    if not isinstance(parsed, dict):
        out = dict(skill_gap_result)
        out["_refine_meta"] = {"enabled": False, "reason": "bad_output_shape"}
        return out

    keep_set = {str(s).strip() for s in (parsed.get("keep_missing") or []) if s}
    moves = [x for x in (parsed.get("move_to_matched") or []) if isinstance(x, dict)]
    drops = [x for x in (parsed.get("drop") or []) if isinstance(x, dict)]

    # 输入完整性校验：每个 top_missing 必须出现在三类之一
    original_names = [m.get("name", "") if isinstance(m, dict) else str(m) for m in top_missing]
    all_classified = keep_set | {m.get("name", "") for m in moves} | {d.get("name", "") for d in drops}
    unclassified = [n for n in original_names if n and n not in all_classified]
    if unclassified:
        logger.warning("[gap-refine] LLM missed skills %s; treating as keep_missing", unclassified)
        keep_set.update(unclassified)

    # 构造新 top_missing：只保留 keep_set 中的项
    new_top_missing = [
        m for m in top_missing
        if (m.get("name", "") if isinstance(m, dict) else str(m)) in keep_set
    ]

    # 构造新 matched_skills：在原基础上追加 moves
    new_matched = list(skill_gap_result.get("matched_skills", []) or [])
    original_matched_names_lower = {
        (m.get("name", "") if isinstance(m, dict) else str(m)).lower().strip()
        for m in new_matched
    }
    for mv in moves:
        name = str(mv.get("name", "")).strip()
        if not name or name.lower() in original_matched_names_lower:
            continue
        # 找到原 top_missing 里同名项的 tier/freq 信息
        src = next(
            (m for m in top_missing
             if (m.get("name", "") if isinstance(m, dict) else str(m)) == name),
            None,
        )
        tier = src.get("tier", "important") if isinstance(src, dict) else "important"
        freq = src.get("freq", 0) if isinstance(src, dict) else 0
        new_matched.append({
            "name": name,
            "tier": tier,
            "status": "practiced_from_resume",
            "freq": freq,
            "_evidence": str(mv.get("evidence", ""))[:60],
        })

    # 更新 tier stats：移动导致 matched ↑、missing ↓
    out = dict(skill_gap_result)
    out["top_missing"] = new_top_missing
    out["matched_skills"] = new_matched

    # 重算 core / important / bonus 的 matched / pct
    for tier in ("core", "important", "bonus"):
        tier_stats = out.get(tier, {}) or {}
        total = tier_stats.get("total", 0)
        if total <= 0:
            continue
        matched_in_tier = sum(1 for m in new_matched if m.get("tier") == tier)
        tier_stats["matched"] = matched_in_tier
        tier_stats["pct"] = int(matched_in_tier / total * 100) if total else 0
        # practiced_count ≈ status 以 practiced/completed/practiced_from_resume 开头
        tier_stats["practiced_count"] = sum(
            1 for m in new_matched
            if m.get("tier") == tier
            and str(m.get("status", "")).startswith(("practiced", "completed"))
        )
        tier_stats["claimed_count"] = sum(
            1 for m in new_matched
            if m.get("tier") == tier and m.get("status") == "claimed"
        )
        out[tier] = tier_stats

    out["_refine_meta"] = {
        "enabled": True,
        "moved_to_matched": [{"name": m.get("name"), "evidence": m.get("evidence")} for m in moves],
        "dropped": [{"name": d.get("name"), "reason": d.get("reason")} for d in drops],
        "kept_missing_count": len(new_top_missing),
    }

    logger.info(
        "[gap-refine] moved %d to matched, dropped %d, kept %d missing",
        len(moves), len(drops), len(new_top_missing),
    )
    return out
```

---

## 任务 3：pipeline 接入

**文件**：`backend/services/report/pipeline.py`

找到这行（约 324 行左右）：
```python
_skill_gap = skill_gap._build_skill_gap(
    profile_data, node, practiced, completed_practiced,
    extra_practiced=text_practiced,
)
```

在其**后面**立刻加：

```python
# Runtime gap refine: LLM-based pseudo-gap filtering
_skill_gap = skill_gap._refine_gap_with_llm(
    _skill_gap,
    profile_data=profile_data,
    target_label=goal.target_label,
)
```

不需要任何其他改动。失败会自动 fallback。

---

## 任务 4：下游 action-plan 受益验证

`_skill_gap` 传给 action-plan skill 的上下文，其中的 `top_missing` 现在已是 refine 后结果。不需要改 action-plan 的 SKILL.md，因为它本来就只会看到我们喂进去的 `top_missing`。

---

## 验收标准

### 后端日志

用户 156（systems-cpp 方向）点"再生成"应能看到：

```
[skill-inference] OK in X.Xs, inferred=[...]
[gap-refine] moved 2 to matched, dropped 2, kept 1 missing
```

### 报告第一章（技能匹配度）
- `important` 层的 matched 从 "STL 1/6" 变成 "STL + 高并发 + 内存管理 3/6"（或更多）
- `top_missing` 不再包含：高并发、内存管理、性能优化、GDB、CMake
- 可能剩下的：性能优化（如 LLM 判定证据不够）、其他真的没见过的

### 报告第四章（行动计划）
- 不再出现"未见 GDB 相关技术关键词"这类模板
- 剩余的建议基于真正的 gap 或项目加深方向

### 失败时
- `[gap-refine] LLM failed: APITimeoutError: ...; fallback to original gap`
- 报告仍然能正常生成，用原 `_build_skill_gap` 结果
- 不破坏任何现有流程

### 不破坏
- 老报告（data_json 里没 `_refine_meta`）读不崩
- 前端不需要改（`matched_skills` 里多了 `practiced_from_resume` status 和 `_evidence` 字段，前端如果不认识这些新字段会直接忽略）
- 其他 skill（narrative / career-alignment / action-plan）的输入结构不变

---

## 不要做的事

- 不要改 `graph.json`（offline 整理是下一步的独立任务）
- 不要改 `_build_skill_gap` 的签名或核心逻辑（只是在外面套一层）
- 不要让 LLM 生成新技能名（硬约束 4）
- 不要把 `drop` 过于激进——宁可留着也不删错（硬约束 3）
- 不要改前端 `ChapterI.tsx` 之类——后端兼容为主

---

## 估算

- 新 SKILL.md：1 个文件
- skill_gap.py：+120 行（一个新函数）
- pipeline.py：+5 行
- 工作量：1 小时编码 + 0.5 小时自测（点一次生成看日志 + 看报告）
