# 职业方向对齐分析（Career Alignment Analysis）· 实施规范

> **交付对象**：Kimi / 执行 Agent
> **版本**：v1.0  · 2026-04-14
> **作者**：Claude (Opus 4.6) via PUA 对齐模式

---

## 0. 背景与原则（必读 · 不可跳过）

本模块替代原报告里已被拆除的 `positioning_level` + `promotion_path 你在这里` 虚假定位逻辑。
我们已经拍板**不再做以下三类事**：

| ❌ 禁止 | 原因 |
|--------|------|
| 生成"N 年到 senior"这类时间预测 | LLM 无 2026 市场数据、无公司晋升梯子信息 → 纯幻觉 |
| 自由文本 `"你适合 X 方向"` 这类标签 | 绕开 graph.json → 数据资产失效 + 学生无法点击下钻 |
| LLM 生成 graph.json 以外的岗位名 | 会编造"AI 内容策略师"这种 LLM 缝合岗位名 → 学生去投，市场没有 |

**本模块唯一的设计原则**：
1. **LLM 作为"数据分析师"，不是"预言家"** —— 只陈述事实、不做预测
2. **输出绑定 `graph.json` 已有 45 个节点** —— 从 curated node_id 集合里选，不自创
3. **诚实输出"不知道"** —— 数据不足或无法判断时显式声明，不用模板硬填
4. **可验证 + 可闭环** —— 每条对齐必须引用学生具体项目/数据，每个 node_id 可跳转到 `RoleDetailPage` 下钻

---

## 1. 数据流顶层设计

```
┌─────────────────────────────────────────────────────────────┐
│ ReportService.generate_report()                             │
│                                                              │
│  1. 读 profile.profile_json  (skills, projects, education)  │
│  2. 读 growth_log.projects   (ProjectRecord + data)         │
│  3. 读 profile.soft_skills    (SJT 评估结果)                 │
│  4. 读 data/graph.json        (45 个节点)                    │
│                   ↓                                          │
│  5. 调用 _build_career_alignment(profile, projects, graph)  │
│                   ↓                                          │
│       [前端预选] skill overlap 取候选 top 15                 │
│                   ↓                                          │
│       [LLM 分析] 返回 {observations, alignments, cannot_judge}│
│                   ↓                                          │
│       [护栏 Validate] node_id 必须在 graph 里，score 0-1 clip│
│                   ↓                                          │
│  6. 写入 report_data["career_alignment"]                    │
└─────────────────────────────────────────────────────────────┘
         ↓
 前端 ReportPage 新 section "方向对齐分析"
         ↓
 学生点击 alignment → 跳转 /roles/{node_id} → RoleDetailPage
         ↓
 形成闭环（alignment → RoleDetailPage → JD 诊断 → 更新报告）
```

---

## 2. 后端实现

### 2.1 新增函数：`_build_career_alignment()` @ `backend/services/report_service.py`

**签名**：
```python
def _build_career_alignment(
    profile_data: dict,          # profile.profile_json 解析后的 dict
    projects: list,              # ProjectRecord list
    graph_nodes: list[dict],     # data/graph.json 的 nodes 数组
    target_node_id: str | None = None,  # 学生当前的目标岗位（如有）
) -> dict | None:
    """
    基于学生数据做方向对齐分析。输出绑定 graph.json node_id。

    返回 schema：
    {
        "observations": str,        # 对学生数据的事实观察，2-3 句
        "alignments": [              # 最多 3 条，按 score 降序
            {
                "node_id": str,      # 必须在 graph_nodes 里存在
                "label": str,        # 从 graph_nodes 回填，不来自 LLM
                "score": float,      # 0-1 clip
                "evidence": str,     # 引用学生具体项目或数字
                "gap": str,          # 还差什么（可为空字符串）
            }
        ],
        "cannot_judge": list[str],  # 显式声明无法判断的维度
    }

    返回 None 表示数据不足（项目 < 2 或技能 < 5 或无软技能数据）。
    """
```

**内部逻辑**：

```python
def _build_career_alignment(profile_data, projects, graph_nodes, target_node_id=None):
    # ── [Gate 1] 数据充足度检查 ──
    skills = profile_data.get("skills", []) or []
    projects_count = len(projects or [])
    soft_skills = profile_data.get("soft_skills", {}) or {}

    if projects_count < 2 or len(skills) < 5:
        logger.info("Career alignment: insufficient data (projects=%d, skills=%d)",
                    projects_count, len(skills))
        return None

    # ── [Step 1] 候选节点预选 ──
    # 基于学生技能集合与各节点 must_skills + skill_tiers 的 overlap 取 top 15
    candidates = _preselect_alignment_candidates(skills, graph_nodes, top_k=15)
    if not candidates:
        return None

    # ── [Step 2] 构造 Prompt ──
    prompt = _build_alignment_prompt(
        skills=skills,
        projects=projects,
        soft_skills=soft_skills,
        candidates=candidates,
        target_node_id=target_node_id,
    )

    # ── [Step 3] 调用 LLM ──
    try:
        from backend.llm import get_llm_client, get_model
        resp = get_llm_client(timeout=30).chat.completions.create(
            model=get_model("slow"),   # 用慢模型追质量，不抢速度
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,           # 低温度降低幻觉
            max_tokens=1200,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
    except Exception as e:
        logger.warning("Career alignment LLM call failed: %s", e)
        return None

    # ── [Step 4] 护栏 Validate ──
    node_map = {n.get("node_id"): n for n in graph_nodes if n.get("node_id")}
    validated = []
    for a in parsed.get("alignments", []):
        nid = a.get("node_id", "")
        if nid not in node_map:
            logger.warning("Career alignment: LLM invented node_id '%s', dropped", nid)
            continue
        # 回填 label（从 graph.json，不信任 LLM）
        a["label"] = node_map[nid].get("label", nid)
        # clip score
        try:
            s = float(a.get("score", 0))
            a["score"] = max(0.0, min(1.0, s))
        except (ValueError, TypeError):
            a["score"] = 0.0
        validated.append(a)

    validated.sort(key=lambda x: x["score"], reverse=True)

    return {
        "observations": parsed.get("observations", ""),
        "alignments": validated[:3],
        "cannot_judge": parsed.get("cannot_judge", []),
    }
```

### 2.2 候选预选：`_preselect_alignment_candidates()`

**目的**：把 LLM 的输出空间从 45 个节点缩到 15 个，同时给 LLM 留一些"不对齐"的节点做对比。

```python
def _preselect_alignment_candidates(
    user_skills: list[str],
    graph_nodes: list[dict],
    top_k: int = 15,
) -> list[dict]:
    """基于技能 overlap 预选候选节点。"""
    user_skill_set = {_canon_skill(s) for s in user_skills if s}
    if not user_skill_set:
        return []

    scored = []
    for node in graph_nodes:
        # 从 skill_tiers 或 must_skills 提取节点要求的技能名集合
        node_skills = set()
        tiers = node.get("skill_tiers", {}) or {}
        for tier in ("core", "important", "bonus"):
            for s in tiers.get(tier, []) or []:
                name = s.get("name") if isinstance(s, dict) else s
                if name:
                    node_skills.add(_canon_skill(name))
        for s in node.get("must_skills", []) or []:
            node_skills.add(_canon_skill(s))

        if not node_skills:
            continue

        overlap = len(user_skill_set & node_skills)
        scored.append({
            "node_id": node.get("node_id"),
            "label": node.get("label"),
            "role_family": node.get("role_family"),
            "career_level": node.get("career_level"),
            "must_skills": list(node_skills)[:8],
            "_overlap": overlap,
        })

    scored.sort(key=lambda x: x["_overlap"], reverse=True)
    # 取 top_k；为 LLM 留对比视角，保留 2-3 个 overlap=0 的节点
    top = scored[:top_k - 3]
    filler = [s for s in scored[top_k:] if s["_overlap"] == 0][:3]
    return top + filler


def _canon_skill(s: str) -> str:
    """技能名规范化：lower + strip。"""
    return (s or "").strip().lower()
```

### 2.3 Prompt 模板：`_build_alignment_prompt()`

```python
def _build_alignment_prompt(skills, projects, soft_skills, candidates, target_node_id):
    # 提取项目数据：描述 + 是否含数字
    proj_lines = []
    for p in projects[:6]:  # 最多 6 个项目，防 prompt 过长
        desc = getattr(p, "description", "") or ""
        name = getattr(p, "name", "") or "未命名"
        if not desc:
            continue
        proj_lines.append(f"- [{name}] {desc[:200]}")
    projects_block = "\n".join(proj_lines) or "（无项目数据）"

    # 软技能
    ss_lines = []
    for k, v in (soft_skills or {}).items():
        if k.startswith("_"):
            continue
        if isinstance(v, (int, float)):
            ss_lines.append(f"- {k}: {int(v)}/100")
    soft_block = "\n".join(ss_lines) or "（无软技能评估）"

    # 候选节点
    cand_lines = []
    for c in candidates:
        cand_lines.append(
            f'- {{"node_id": "{c["node_id"]}", '
            f'"label": "{c["label"]}", '
            f'"role_family": "{c.get("role_family","")}", '
            f'"career_level": "{c.get("career_level","")}", '
            f'"key_skills": {c["must_skills"][:5]}}}'
        )
    candidates_block = "\n".join(cand_lines)

    target_hint = ""
    if target_node_id:
        target_hint = f"\n\n学生目前标定的目标岗位 node_id: {target_node_id}（若此岗位在候选列表中，请给出对齐评估；若不在，请观察其他对齐方向）"

    return f"""你是职业数据分析师。你的任务是根据学生数据**观察 + 对齐**，不做预测、不贴级别、不给时间表。

# 严格规则

1. **只陈述事实**：所有结论必须能从给定的学生数据里找到依据
2. **不做时间预测**：禁止输出"N 年到 senior"这类时间表
3. **不贴等级标签**：禁止输出"你是中级/初级/资深"这类分类判断
4. **node_id 只能从候选列表里选**：不许自创岗位名、不许拼接新词
5. **每个 alignment 必须引用具体 evidence**：要么是学生某个项目里的数字、要么是某个技能名、要么是某个软技能分数——不许空泛描述
6. **不确定就说不知道**：把无法从数据里得出的结论放进 `cannot_judge` 字段
7. **最多输出 3 条 alignments**，按对齐度排序

# 学生数据

## 技能（来自简历 + 成长档案）
{", ".join(skills[:30])}

## 项目（含数据）
{projects_block}

## 软技能评估
{soft_block}
{target_hint}

# 候选岗位（你只能从这 {len(candidates)} 个里选）

{candidates_block}

# 输出 JSON schema（严格遵守，不要额外文字）

{{
  "observations": "2-3 句对学生数据的事实观察，必须引用具体数据",
  "alignments": [
    {{
      "node_id": "从候选列表里选的 node_id",
      "score": 0.85,
      "evidence": "引用学生具体项目/数字/技能作为对齐证据",
      "gap": "对齐到该岗位还差什么（可以为空字符串）"
    }}
  ],
  "cannot_judge": [
    "你无法从数据里判断的维度，例如：'实际工作节奏与晋升速度'"
  ]
}}

只输出 JSON，不要 markdown 代码块包裹，不要解释性文字。
"""
```

### 2.4 在 `generate_report()` 中集成

**位置**：在 `report_service.py` 的 `generate_report()` 函数里，找到 `report_data = { ... }` 的构造位置（约 1690 行附近），**删除**旧的 `promotion_path`（保留但降级）+ 添加 `career_alignment`：

```python
# ── 方向对齐分析（LLM 分析 + graph 绑定）──
try:
    career_alignment = _build_career_alignment(
        profile_data=profile_data,
        projects=projects,
        graph_nodes=_load_graph_nodes(),  # 新辅助函数，见下
        target_node_id=target_node_id,
    )
except Exception as e:
    logger.warning("Career alignment build failed: %s", e)
    career_alignment = None

# ...

report_data = {
    # ...（其他字段保持不变）
    "promotion_path": node.get("promotion_path", []),  # 保留，作为参考材料
    "soft_skills": node.get("soft_skills", {}),         # 保留（岗位要求语境，前端已标注）
    "career_alignment": career_alignment,               # 新增
    "generated_at": datetime.now(timezone.utc).isoformat(),
}
```

### 2.5 辅助函数：`_load_graph_nodes()`

**位置**：`report_service.py` 顶部，加缓存避免每次报告都 disk I/O：

```python
from pathlib import Path
_GRAPH_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "graph.json"
_graph_cache: list[dict] | None = None
_graph_mtime: float = 0.0

def _load_graph_nodes() -> list[dict]:
    """Load & cache graph.json nodes, auto-invalidate on mtime change."""
    global _graph_cache, _graph_mtime
    try:
        mtime = _GRAPH_PATH.stat().st_mtime
        if _graph_cache is None or mtime != _graph_mtime:
            with open(_GRAPH_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            _graph_cache = data.get("nodes", [])
            _graph_mtime = mtime
        return _graph_cache or []
    except Exception as e:
        logger.warning("Failed to load graph.json: %s", e)
        return []
```

---

## 3. 前端实现

### 3.1 TypeScript interface（`ReportPage.tsx` 顶部）

```typescript
interface AlignmentItem {
  node_id: string
  label: string
  score: number        // 0-1
  evidence: string
  gap: string
}

interface CareerAlignment {
  observations: string
  alignments: AlignmentItem[]
  cannot_judge: string[]
}

// 在 ReportData interface 里加：
interface ReportData {
  // ... 已有字段
  career_alignment?: CareerAlignment | null
}
```

### 3.2 新增组件：`CareerAlignmentSection`

**位置**：`frontend/src/pages/ReportPage.tsx` 内部新增，或单独抽出 `frontend/src/components/report/CareerAlignmentSection.tsx`

```tsx
import { Target, ArrowRight, CircleAlert } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

function CareerAlignmentSection({ alignment }: { alignment: CareerAlignment | null | undefined }) {
  const navigate = useNavigate()

  // 数据不足态
  if (!alignment) {
    return (
      <motion.div variants={fadeUp} className="glass p-5">
        <div className="g-inner">
          <div className="flex items-center gap-2 mb-2">
            <Target size={15} className="text-slate-400" />
            <p className="text-[13px] font-semibold text-slate-700">方向对齐分析</p>
          </div>
          <p className="text-[12px] text-slate-500 leading-relaxed">
            还需要更多数据才能做出可信分析。建议先补：
          </p>
          <ul className="text-[12px] text-slate-500 mt-2 space-y-1 pl-4">
            <li>· 至少 2 个有具体数字的项目（QPS、用户量、准确率等）</li>
            <li>· 5 个以上技能（简历或成长档案填写）</li>
            <li>· 完成软技能评估（SJT）</li>
          </ul>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => navigate('/growth-log?tab=projects')}
              className="btn-glass text-[11px] px-3 py-1"
            >
              去补项目
            </button>
            <button
              onClick={() => navigate('/profile?tab=soft-skills')}
              className="btn-glass text-[11px] px-3 py-1"
            >
              去做评估
            </button>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div variants={fadeUp} className="glass p-5">
      <div className="g-inner space-y-4">
        {/* Header with honesty label */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Target size={15} className="text-indigo-500" />
            <p className="text-[13px] font-semibold text-slate-700">方向对齐分析</p>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
              AI 观察 · 非预测
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            基于你的项目数据和技能画像做的事实对齐，不包含时间表或级别预测
          </p>
        </div>

        {/* Observations */}
        {alignment.observations && (
          <div className="text-[12.5px] text-slate-700 leading-relaxed px-3 py-2.5 bg-slate-50/60 rounded-lg">
            {alignment.observations}
          </div>
        )}

        {/* Alignments */}
        {alignment.alignments.length > 0 && (
          <div className="space-y-2.5">
            <p className="text-[11px] text-slate-500 font-medium">可能对齐的方向：</p>
            {alignment.alignments.map((a) => (
              <button
                key={a.node_id}
                onClick={() => navigate(`/roles/${a.node_id}`)}
                className="w-full text-left rounded-xl p-3.5 transition-all duration-200 hover:shadow-md cursor-pointer"
                style={{
                  background: 'rgba(99,102,241,0.06)',
                  border: '1px solid rgba(99,102,241,0.18)',
                }}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[13px] font-semibold text-slate-800">{a.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-indigo-600 tabular-nums">
                      对齐度 {Math.round(a.score * 100)}%
                    </span>
                    <ArrowRight size={12} className="text-indigo-400" />
                  </div>
                </div>
                {a.evidence && (
                  <p className="text-[11.5px] text-slate-600 leading-relaxed">
                    <span className="text-emerald-600">证据：</span>{a.evidence}
                  </p>
                )}
                {a.gap && (
                  <p className="text-[11.5px] text-slate-600 leading-relaxed mt-1">
                    <span className="text-amber-600">缺口：</span>{a.gap}
                  </p>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Cannot judge */}
        {alignment.cannot_judge.length > 0 && (
          <div className="pt-3 border-t border-slate-100">
            <div className="flex items-start gap-1.5">
              <CircleAlert size={12} className="text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[11px] text-slate-500 mb-1">系统无法判断的（需要你自己决策）：</p>
                <ul className="text-[11.5px] text-slate-600 space-y-0.5">
                  {alignment.cannot_judge.map((s, i) => (
                    <li key={i}>· {s}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
```

### 3.3 在 `ReportPage` 渲染流程中嵌入

**位置**：当前 promotion_path timeline 那个 section（约 1044 行）**之前**或**之后**插入：

```tsx
{/* ── 方向对齐分析（LLM 分析 + graph 绑定） ── */}
<CareerAlignmentSection alignment={data.career_alignment} />

{/* ── 晋升路径（参考材料，已降级）── */}
{data.promotion_path && data.promotion_path.length > 0 && (
  // ... 已有代码，保留
)}
```

---

## 4. 风险护栏总览

| 风险 | 护栏 |
|------|------|
| LLM 输出不存在的 node_id | `_build_career_alignment` 里 validate，不在 `graph_nodes` 里的直接 drop |
| LLM 输出 score 超出 0-1 | `clip(0, 1)` |
| LLM 用 Markdown 代码块包裹 JSON | prompt 明确要求 + 代码里 strip ```json``` 前缀 |
| LLM 返回非 JSON 格式 | try/except `json.loads`，失败返回 None |
| LLM 幻觉项目数据 | evidence 字段不做硬 validate，但 UI 标注"AI 观察 · 非预测"，把责任透明化 |
| 学生数据不足 | Gate 1 直接返回 None → 前端显示"数据不足 + 引导补 CTA" |
| 候选为 0 | `_preselect_alignment_candidates` 返回空 → `_build_career_alignment` 返回 None |
| graph.json mtime 变化 | `_load_graph_nodes` 自动 invalidate 缓存 |

---

## 5. 边界条件测试用例

| 场景 | 期望行为 |
|------|---------|
| 新用户 · 0 项目 | `career_alignment: null` → 前端显示数据不足态 |
| 用户有 1 个项目 | 同上（阈值是 2） |
| 用户有 5 个项目但都无描述 | 项目过滤后少于 2 → null |
| 用户技能 < 5 | null |
| 用户 SJT 未做 | **仍可生成** alignment（soft_skills 字段为空串"（无软技能评估）"，LLM 可以照样分析技能+项目） |
| LLM 超时 | try/except 捕获 → 返回 None → 前端显示"分析生成失败，可刷新重试" |
| LLM 返回 `alignments: []` | 前端 observations 正常显示，alignments 列表空 → 不显示对齐卡片 |
| LLM 返回 node_id 是已删除的节点 | validate 时 drop → 可能只剩 1-2 条，照常显示 |

---

## 6. 验证脚本

**执行后 Kimi 必须跑**：

```bash
# 1. 后端 boot + 模块 import 检查
python -c "from backend.services.report_service import _build_career_alignment, _preselect_alignment_candidates, _load_graph_nodes; print('OK imports')"

# 2. graph.json 加载
python -c "from backend.services.report_service import _load_graph_nodes; nodes=_load_graph_nodes(); print('graph nodes:', len(nodes))"

# 3. 全局 app boot
python -c "from backend.app import create_app; app=create_app(); print('BOOT OK routes=', len(app.routes))"

# 4. 前端 typecheck
cd frontend && npx tsc --noEmit && echo FE_OK
```

**四项全 OK 才算交付完成**。

---

## 7. 不要做的事（反向清单）

| ❌ 禁止 | 理由 |
|--------|------|
| 把 `positioning_level` 重新加回来 | 上一轮刚砍掉，换马甲不行 |
| LLM prompt 里要求输出"预计 N 年" | 违反核心原则 |
| 前端显示"AI 推荐你做 X" | 措辞要用"对齐"，不用"推荐" |
| 在 `cannot_judge` 里填套话（比如"市场变化快"） | `cannot_judge` 必须是具体到数据维度的"不知道" |
| 扩大 candidates 到全部 45 个节点 | 输入膨胀 → LLM 性能和 token 双下降 |
| 在 prompt 里给 LLM 展示学生的 profile.name / email | PII 不进 prompt |

---

## 8. 完成标准（Definition of Done）

- [ ] `report_service.py` 新增 3 个函数：`_build_career_alignment` / `_preselect_alignment_candidates` / `_load_graph_nodes` / `_build_alignment_prompt`
- [ ] `generate_report()` 内集成 `career_alignment` 字段
- [ ] `ReportPage.tsx` 新增 `CareerAlignmentSection` 组件并渲染
- [ ] 数据不足态有独立 UI + CTA 按钮
- [ ] 每个 alignment 卡片可点击跳转 `/roles/{node_id}`
- [ ] 6 项验证脚本全部通过
- [ ] 生成一份真实报告，肉眼检查：
  - 无"senior/mid/junior"字样
  - 无"N 年能到 X"字样
  - 每个 alignment 的 `evidence` 都引用了学生真实项目或数据
  - `cannot_judge` 不为空（显式诚实）

---

## 附录 A · 完整 LLM Prompt 示例（供 Kimi 对齐）

> 参见 `_build_alignment_prompt()` 函数实现。确保实际 prompt 里每个 placeholder 都被正确替换。

## 附录 B · 设计决策记录（供未来追溯）

- **为何 top_k=15**：45 个节点里塞满 LLM 上下文会导致 prompt 过长；取 15 个候选（top 12 + 3 个 filler）既给 LLM 选择空间、又防过长。
- **为何 score 用 0-1 而非 0-100**：避免 LLM 混淆为百分数，降低数值解析复杂度，前端 `*100` 转显示即可。
- **旧 `promotion_path` 已从报告 payload 中删除**（原 v1.0 spec 保留它的判断被推翻）。理由：和 `career_alignment` 在叙事上冗余——两个模块都在回答"职业方向如何走"，保留会让学生困惑看哪个。`graph.json` 里该字段仍保留，供 RoleDetailPage / Coverflow 等岗位详情场景使用。
- **为何不删 `soft_skills`**：UX 评审时用户已决定保留作为岗位参考信息。本次变更范围只涉及 alignment 模块。

---

**终端指令**：
```
Kimi，请严格按本规范实施。
所有函数签名、Prompt 模板、字段名、UI 文案必须与本规范对齐。
若实施过程中发现规范内的矛盾或缺漏，请先提问，不要自行决策。
完成后跑第 6 节的 4 项验证脚本，贴输出给用户确认。
```
