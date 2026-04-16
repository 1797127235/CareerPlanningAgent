# Report Generation Parallelization Spec

> 将 `backend/services/report/pipeline.py` 中后段的 6 个 LLM 调用从串行改为并发，以显著缩短报告生成总时长。

---

## 目标与收益

| 指标 | 当前（串行） | 目标（并发） |
|------|-------------|-------------|
| 后段 6 个 LLM 调用耗时 | ~266 s | ~76 s（瓶颈 = 最慢的 `market-narrative`） |
| 整份报告总耗时 | ~417 s | ~225 s（从近 7 分钟压到约 3.75 分钟） |

---

## 核心原则

1. **只改一个文件**：`backend/services/report/pipeline.py`。
2. **只用 `concurrent.futures.ThreadPoolExecutor`**：不引入 `asyncio`/`async`/`await`，避免对现有同步调用链产生连锁改动。
3. **先准备好公共输入，再一次性并发**：
   - 所有 6 个任务共同依赖的 `summary` 已在原流程中提前算出。
   - 将 `enriched_missing` 的计算（`_build_skill_fill_path_map`）**从 career_alignment 之后提前到并发批次之前**。
   - 然后一次性 `submit` 6 个任务进线程池。
4. **delta block 保留在并发之后**：它依赖 `action_plan_data` 的结果，天然只能等并发结束后再算。

---

## 当前串行结构（问题）

```python
# ── 前置：summary 已提前算好 ──

# 1) action-plan (LLM)
action_plan_data = _invoke_action_plan_with_retry(...)

# 2) delta（依赖 action_plan_data，不能提前）
delta = ...

# 3) narrative (LLM)
narrative_text = narrative._generate_narrative(...)

# 4) diagnosis (LLM)
diagnosis = narrative._diagnose_profile(...)

# 5) career-alignment (LLM)
career_alignment_data = career_alignment._build_career_alignment(...)

# 6) enriched_missing（本地计算，非 LLM）
enriched_projects, enriched_missing, project_mismatch = skill_gap._build_skill_fill_path_map(...)

# 7) differentiation (LLM，依赖 enriched_missing)
differentiation_advice = _build_differentiation_advice(..., top_missing=enriched_missing)

# 8) market-narrative (LLM)
market_narrative = _build_market_narrative(...)
```

6 个 LLM 调用首尾相接，时间累加。

---

## 目标并发结构

### Step 1 · 前置数据（保持原有逻辑）

- profile / goal / snapshots / projects / skill gap / market_info / summary 等全部按原顺序算完。
- **新增**：把下面这段代码从 career_alignment 之后**上移到并发批次之前**：
  ```python
  project_recs_raw = node.get("project_recommendations", [])[:3]
  top_missing_raw = _skill_gap.get("top_missing", []) if _skill_gap else []
  enriched_projects, enriched_missing, project_mismatch = skill_gap._build_skill_fill_path_map(
      project_recs_raw, top_missing_raw
  )
  report_skill_gap = copy.deepcopy(_skill_gap) if _skill_gap else None
  if report_skill_gap is not None:
      report_skill_gap["top_missing"] = enriched_missing
  ```

### Step 2 · 定义 6 个 worker 函数

在 `generate_report` 内部（或文件级）定义 6 个闭包/worker，每个负责一个 LLM 调用，内部自带 `try/except`：**失败时返回安全默认值，绝不抛异常到线程池外层**。

| Worker | 调用 | 特殊注意 |
|--------|------|---------|
| `_worker_action_plan` | `_invoke_action_plan_with_retry(...)` | 入参和原调用一致 |
| `_worker_narrative` | `narrative._generate_narrative(...)` | 入参和原调用一致 |
| `_worker_diagnosis` | 内部新建 `SessionLocal()`，再调用 `narrative._diagnose_profile(...)` | **不能复用主线程 `db` session**；执行完后关闭 session |
| `_worker_career_alignment` | `career_alignment._build_career_alignment(...)` | 入参和原调用一致；失败返回现有的硬兜底 dict |
| `_worker_differentiation` | `_build_differentiation_advice(...)` | 依赖已提前算好的 `enriched_missing` |
| `_worker_market_narrative` | `_build_market_narrative(...)` | 入参和原调用一致 |

> **关于 diagnosis 的 db session**：`narrative._diagnose_profile` 会用到 `db.query(...)`。SQLAlchemy session 不是线程安全的，因此必须在 worker 内部通过 `from backend.db import SessionLocal; db = SessionLocal()` 新建独立 session，并在返回前 `db.close()`。

### Step 3 · 一次性提交并发

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=6) as executor:
    f_action = executor.submit(_worker_action_plan)
    f_narrative = executor.submit(_worker_narrative)
    f_diagnosis = executor.submit(_worker_diagnosis)
    f_alignment = executor.submit(_worker_career_alignment)
    f_diff = executor.submit(_worker_differentiation)
    f_market = executor.submit(_worker_market_narrative)

    # 收集结果（顺序无所谓，用 .result() 阻塞等待全部完成）
    action_plan_data = f_action.result()
    narrative_text = f_narrative.result()
    diagnosis = f_diagnosis.result()
    career_alignment_data = f_alignment.result()
    differentiation_advice = f_diff.result()
    market_narrative = f_market.result()
```

### Step 4 · delta block（串行保留）

```python
# 只在有 prev_report 时才计算
delta = None
if prev_report:
    ... # 原 delta 逻辑，依赖 action_plan_data
```

### Step 5 · 组装 payload

`report_data` 的组装逻辑完全不变，只是此时 6 个字段都已经拿到。

---

## 代码修改清单（精准定位）

1. **文件顶部 import**：增加 `from concurrent.futures import ThreadPoolExecutor, as_completed`。
2. **summary 之后**：把 `enriched_missing` / `report_skill_gap` 的构建从 career_alignment 之后**剪贴移动到 summary 之后**。
3. **新增 6 个 worker 闭包**：放在 `generate_report` 中合适位置（建议在 `summary` 和 `enriched_missing` 准备好之后、线程池之前）。
4. **替换原有 6 处串行调用**：用 `ThreadPoolExecutor` 一次性提交并 `.result()` 收集。
5. **delta block 位置不变**：仍放在并发结果收集之后。

---

## 不要做（Scope 红线）

以下事项**明确不做**，严防 scope creep：

1. **不改任何 skill prompt**：`action-plan`、`narrative`、`diagnosis`、`career-alignment`、`differentiation`、`market-narrative` 的 prompt 文件一律不动。
2. **不引入新依赖**：只使用 Python 标准库的 `concurrent.futures`。
3. **不做 Phase 2 优化**：
   - 不合并 LLM 调用；
   - 不替换底层模型；
   - 不做流式输出；
   - 不改 HTTP client 并发配置（如 `aiohttp`、`httpx` 异步池）。
4. **不碰数据库模型或 schema**：不改 `backend/db_models.py`、不加新字段。
5. **不改前端**：`frontend/` 目录下的任何文件均不修改。
6. **不改动 `invoke_skill` 内部实现**：只把它当作黑盒在 `pipeline.py` 里并发调用。

---

## 风险与兜底

| 风险 | 应对 |
|------|------|
| 某个 LLM 调用超时/失败 | 每个 worker 内部 `try/except`，返回和原串行逻辑一致的 fallback 值 |
| 线程内 db session 泄漏 | diagnosis worker 内 `try/finally: db.close()` |
| ThreadPoolExecutor 异常吞掉日志 | worker 内捕获后 `logger.warning(..., exc_info=True)`，确保可排查 |
| 并发导致 API rate limit | 当前 6 并发在 OpenAI tier 内通常可接受；若触发 limit，再考虑 Phase 2 的 `max_workers` 调小或请求合并 |

---

## 验收标准

- [ ] `backend/services/report/pipeline.py` 是本次唯一被修改的 Python 文件。
- [ ] `generate_report` 中 6 个 LLM 调用全部进入 `ThreadPoolExecutor`。
- [ ] `delta` 计算仍在并发批次之后。
- [ ] 单元测试或本地 mock 跑通：报告生成流程不报错，返回的 JSON 结构与原来一致。
- [ ] （可选）在真实环境打 log，确认整段并发耗时从 ~266 s 降至 ~80 s 以内。
