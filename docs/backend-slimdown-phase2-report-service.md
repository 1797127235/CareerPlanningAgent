# Backend 瘦身 Phase 2 · report_service.py 拆分

交付人：Kimi
审查 / 文档：Claude
日期：2026-04-15
前序：Phase 1 profile_service 拆分已完成（owner 验收通过），本次套用同套路

---

## 一、背景

### 现状
- `backend/services/report_service.py` = **2598 行**，单文件
- 比 Phase 1 的 profile_service (1872) 还大 38%
- 外部调用者**只有 2 处**（都在 `backend/routers/report.py`）—— 拆分面极小

### 和 Phase 1 的关键差异（Kimi 注意）
| 维度 | Phase 1 profile_service | **Phase 2 report_service** |
|---|---|---|
| 结构 | class + private helpers | **模块级纯函数（无 class）** |
| 文件头 docstring | 明说"5 modules consolidated" | 只描述 pipeline，不声明合并历史 |
| public API | 7 个 class 方法 | **2 个模块函数**（`generate_report` + `polish_narrative`）|
| 全局 state | 全部在 class instance | **5 个模块级 global 变量**（⚠️ 拆分时必须封装） |
| 超大函数 | 最长 ~120 行 | **`generate_report` 552 行 + `_build_action_plan` 453 行**（⚠️ 原样搬不重构） |
| 现役单元测试 | 17 个，全绿 | **无** —— 验证策略不同 |

### 目标
按**领域职责**拆成 7 个子模块 + facade（`pipeline.py`），对外保持 2 个 public 函数签名不变。

### 非目标（不做）
- ❌ 不改任何业务逻辑
- ❌ 不重构 `generate_report` / `_build_action_plan` 超大函数（留给未来 Phase 2.5）
- ❌ 不新增功能
- ❌ 不改 public 函数签名

---

## 二、当前文件地图（Kimi 必读）

### 2.1 函数分区（按行号）

| 行号 | 归属领域 | 函数 |
|---|---|---|
| 36-44 | 全局 state | `_GRAPH_NODES` / `_LEVEL_SKILLS` / `_MARKET` / `_NODE_TO_FAMILY` / `_SKILL_FILL_PATH_CACHE` |
| 47-115 | 数据加载 | `_load_skill_fill_path_cache` / `_classify_fill_path` / `_load_graph_nodes` |
| 133-195 | 数据加载 / 解析 | `reload_static` / `_load_static` / `_parse_data` / `_parse_profile` |
| 195-280 | 技能工具 | `_user_skill_set` / `_norm_skill` / `_skill_matches` / `_skill_in_set` / `_skill_proficiency` |
| 281-473 | **四维评分** | `_score_foundation` / `_score_skills` / `_score_qualities` / `_score_potential` / `_weighted_match_score` |
| 474-893 | **技能缺口** | `_build_skill_gap` / `_skill_action` / `_has_hardcoded_guidance` / `_generate_skill_actions_llm` / `_cosine_sim` / `_batch_embed` / `_build_skill_fill_path_map` / `_embed_classify_skills` / `_infer_implicit_skills_llm` |
| 894-1347 | **Action plan** | `_build_action_plan` ⚠️ 453 行超大函数 |
| 1348-1690 | **方向对齐** | `_canon_skill` / `_preselect_alignment_candidates` / `_normalize_project_sources` / `_build_alignment_prompt` / `_build_career_alignment` |
| 1691-2018 | **叙事生成** | `_generate_narrative` / `_diagnose_profile` |
| 2019-2571 | **主入口** | `generate_report` ⚠️ 552 行超大函数 |
| 2572-2598 | 叙事润色 | `polish_narrative` |

### 2.2 Public API（2 个，非 class 方法）

| 行号 | function | 归属 |
|---|---|---|
| 2019 | `generate_report(user_id, db) -> dict` | pipeline.py |
| 2572 | `polish_narrative(narrative, target_label) -> str` | pipeline.py |
| 133 | `reload_static() -> None` | loaders.py（也算 public，pre-warm 用）|

### 2.3 全局 state 变量（⚠️ 拆分时必须封装）

```python
_GRAPH_NODES: dict[str, dict] = {}
_LEVEL_SKILLS: dict[str, dict] = {}
_MARKET: dict[str, dict] = {}
_NODE_TO_FAMILY: dict[str, str] = {}
_SKILL_FILL_PATH_CACHE: dict[str, str] | None = None
```

**拆分红线**：这些变量全部进 `loaders.py`，其他子模块**绝对不能** `from loaders import _GRAPH_NODES`，必须通过 **getter 函数** 访问，例如：
```python
# loaders.py
def get_graph_nodes() -> dict[str, dict]:
    _load_static()  # lazy init
    return _GRAPH_NODES
```

### 2.4 现役测试：无

`tests/services/test_report_service.py` 不存在（只有一个孤儿 .pyc）。验证策略见第 7 节。

---

## 三、目标拆分结构

### 3.1 新目录布局

```
backend/services/report/
├── __init__.py              # from .pipeline import generate_report, polish_narrative, reload_static
├── pipeline.py              # 主编排层
│                            #   - generate_report (552 行 ⚠️ 原样搬)
│                            #   - polish_narrative
│                            #   - _parse_data / _parse_profile (pipeline 内部用)
├── loaders.py               # 静态数据 + 全局 state 封装
│                            #   - _GRAPH_NODES / _LEVEL_SKILLS / _MARKET / _NODE_TO_FAMILY / _SKILL_FILL_PATH_CACHE
│                            #   - _load_static / reload_static (public)
│                            #   - _load_skill_fill_path_cache / _classify_fill_path
│                            #   - _load_graph_nodes
│                            #   - getter 函数：get_graph_nodes() / get_level_skills() / get_market() / get_node_to_family() / get_skill_fill_path_cache()
├── shared.py                # 跨子模块共用的纯工具函数
│                            #   - _norm_skill / _user_skill_set / _skill_matches / _skill_in_set / _skill_proficiency
│                            #   - _cosine_sim / _batch_embed
├── scoring.py               # 四维评分
│                            #   - _score_foundation / _score_skills / _score_qualities / _score_potential / _weighted_match_score
├── skill_gap.py             # 技能缺口分析
│                            #   - _build_skill_gap / _skill_action / _has_hardcoded_guidance
│                            #   - _generate_skill_actions_llm / _build_skill_fill_path_map / _embed_classify_skills / _infer_implicit_skills_llm
├── action_plan.py           # Action plan 生成
│                            #   - _build_action_plan (453 行 ⚠️ 原样搬)
├── career_alignment.py      # 方向对齐
│                            #   - _canon_skill / _preselect_alignment_candidates / _normalize_project_sources
│                            #   - _build_alignment_prompt / _build_career_alignment
└── narrative.py             # 叙事生成
                             #   - _generate_narrative / _diagnose_profile
```

### 3.2 数据流编排（pipeline.py 的职责）

```
generate_report(user_id, db)
    ↓
1. loaders.get_graph_nodes() / get_market() / ...  (pre-warm)
2. parse profile / career_goal / growth_snapshots (_parse_* helpers)
3. scoring.score_foundation / score_skills / score_qualities / score_potential
4. scoring.weighted_match_score → total
5. skill_gap.build_skill_gap + skill_gap.embed_classify_skills
6. action_plan.build_action_plan(...)
7. career_alignment.build_career_alignment(...)
8. narrative.diagnose_profile + narrative.generate_narrative
9. 汇总 result dict
10. return result
```

**关键**：子模块之间**不互相调用**。所有跨子模块数据传递由 pipeline.py 编排；子模块接受参数返回结果，是纯函数。

---

## 四、依赖扫描

### 4.1 外部 import 只 2 处

| 文件 | 行 | 当前 import | 改后 |
|---|---|---|---|
| `backend/routers/report.py` | 94 | `from backend.services.report_service import generate_report as _generate` | `from backend.services.report import generate_report as _generate` |
| `backend/routers/report.py` | 218 | `from backend.services.report_service import polish_narrative` | `from backend.services.report import polish_narrative` |

### 4.2 不保留兼容 shim

沿用 Phase 1 规则：直接删 `report_service.py`，改 2 处 import。

---

## 五、Kimi 任务拆解（T1 → T7）

### T1 · 建目录 + `shared.py` + `loaders.py`

**动作**：
1. 建目录 `backend/services/report/` + 空 `__init__.py`
2. 建 `shared.py`，移入：`_norm_skill` / `_user_skill_set` / `_skill_matches` / `_skill_in_set` / `_skill_proficiency` / `_cosine_sim` / `_batch_embed`
3. 建 `loaders.py`，移入：
   - 5 个 global state 变量
   - `_load_skill_fill_path_cache` / `_classify_fill_path` / `_load_graph_nodes` / `_load_static` / `reload_static`
   - 新增 **getter 函数**：`get_graph_nodes()` / `get_level_skills()` / `get_market()` / `get_node_to_family()` / `get_skill_fill_path_cache()`
4. `__init__.py` 暂时留空（后续 T7 补）

**T1 验证**：
```bash
python -c "
from backend.services.report.shared import _norm_skill, _user_skill_set, _cosine_sim
from backend.services.report.loaders import reload_static, get_graph_nodes, get_market
reload_static()
print('T1 PASS — shared and loaders importable, static loaded')
print(' graph_nodes:', len(get_graph_nodes()))
print(' market keys:', len(get_market()))
"
```

### T2 · `scoring.py`（四维评分）

**动作**：搬入 `_score_foundation` / `_score_skills` / `_score_qualities` / `_score_potential` / `_weighted_match_score`（line 281-473）。引用 shared / loaders 的用函数调用。

**T2 验证**：
```bash
python -c "
from backend.services.report.scoring import _score_foundation, _score_skills, _score_potential, _weighted_match_score
print('T2 PASS — scoring imports ok')
"
```

### T3 · `skill_gap.py`

**动作**：搬入 line 474-893 的函数：`_build_skill_gap` / `_skill_action` / `_has_hardcoded_guidance` / `_generate_skill_actions_llm` / `_build_skill_fill_path_map` / `_embed_classify_skills` / `_infer_implicit_skills_llm`。

**T3 验证**：
```bash
python -c "
from backend.services.report.skill_gap import _build_skill_gap, _embed_classify_skills
print('T3 PASS')
"
```

### T4 · `action_plan.py`

**动作**：搬入 `_build_action_plan`（line 894-1347，453 行）。**原样搬**，不重构。

**T4 验证**：
```bash
python -c "
from backend.services.report.action_plan import _build_action_plan
import inspect
print('T4 PASS — _build_action_plan lines:', len(inspect.getsource(_build_action_plan).splitlines()))
"
```

### T5 · `career_alignment.py`

**动作**：搬入 line 1348-1690 的函数：`_canon_skill` / `_preselect_alignment_candidates` / `_normalize_project_sources` / `_build_alignment_prompt` / `_build_career_alignment`。

**T5 验证**：
```bash
python -c "
from backend.services.report.career_alignment import _build_career_alignment
print('T5 PASS')
"
```

### T6 · `narrative.py`

**动作**：搬入 `_generate_narrative` / `_diagnose_profile`（line 1691-2018）。

**T6 验证**：
```bash
python -c "
from backend.services.report.narrative import _generate_narrative, _diagnose_profile
print('T6 PASS')
"
```

### T7 · `pipeline.py` + `__init__.py` + 删原文件 + 改外部 import + 全绿回归

**pipeline.py 移入**：
- `generate_report`（line 2019-2571，552 行 ⚠️ 原样搬）
- `polish_narrative`（line 2572-2598）
- `_parse_data` / `_parse_profile`（如果只被 pipeline 用）

**`__init__.py` 最终形态**：
```python
"""Report service package."""
from backend.services.report.pipeline import (  # noqa: F401
    generate_report,
    polish_narrative,
)
from backend.services.report.loaders import reload_static  # noqa: F401
```

**T7 动作**：
1. 删除 `backend/services/report_service.py`（直接 `rm`）
2. 改 2 处外部 import：
   - `backend/routers/report.py:94` → `from backend.services.report import generate_report as _generate`
   - `backend/routers/report.py:218` → `from backend.services.report import polish_narrative`

**T7 全局回归验证**：
```bash
# 1. import 健康
python -c "
from backend.services.report import generate_report, polish_narrative, reload_static
print('ALL IMPORTS OK')
"

# 2. 语法回归
python -c "import backend.services.report.pipeline, backend.services.report.action_plan"

# 3. 全局 pytest 不 regress（基线：23 failed / 103 passed）
pytest tests/ --ignore=tests/services/test_plan_service.py --tb=no -q | tail -5
# 期望：passed 数量 ≥ 103，failed 数量 ≤ 23（Phase 2 改动不引入新 fail）

# 4. 行数对比
wc -l backend/services/report/*.py
# 期望：pipeline.py ~600 行（含 generate_report 552）
#       action_plan.py ~500 行（含 _build_action_plan 453）
#       其他 sub-module < 500 行
#       shared.py + loaders.py 合计 < 400 行
```

---

## 六、拆分红线（Kimi 严格遵守）

1. **不改任何业务逻辑** —— 只移动代码
2. **不重构 `generate_report` (552 行) 和 `_build_action_plan` (453 行)** —— 原样搬，超大函数是本次 scope 外
3. **不新增 public 函数** —— 对外只保留 `generate_report` + `polish_narrative` + `reload_static`
4. **全局 state 变量必须封装**：
   - 5 个 global 进 `loaders.py`
   - 其他 sub-module 通过 getter 函数访问（`get_graph_nodes()` 等），**禁止** `from loaders import _GRAPH_NODES`
5. **sub-module 之间不互相 import 私有符号** —— 有共享需要进 `shared.py`
6. **子模块是纯函数** —— 不持有状态；需要的数据通过参数传入
7. **外部 import 路径全改 + 不留 shim** —— 直接 rm 原 `report_service.py`
8. **不引入新依赖**
9. **每个 T 完成后**：必跑对应验证脚本，贴输出证据；任何一项失败停下来修
10. **不动测试文件** —— `tests/services/test_report_service.py` 本来就不存在；`tests/__pycache__/test_report_v2.cpython-*.pyc` 是孤儿 pyc 可以不管（会自动被覆盖）

---

## 七、验证策略（无单元测试 baseline 下的替代）

由于没有 `test_report_service.py`，Phase 2 的验证依赖：

1. **import 健康**：每个 T 后 `python -c "from ..."` 无报错
2. **语法正确**：`python -c "import ..."` 全部 module
3. **全局 pytest 不 regress**：基线 **103 passed / 23 failed**（Phase 1 完成后的数据），Phase 2 完成后必须 ≥ 103 passed
4. **运行时烟测**（owner 侧最终验收，doc 里写给 owner）：
   ```bash
   # 启动 backend
   python -m uvicorn backend.app:app --reload

   # 另一个终端 curl（需要有效 user token）：
   curl -X GET "http://localhost:8000/api/report/generate" \
        -H "Authorization: Bearer <token>"
   # 期望：返回非空 JSON，含 total_score / four_dimensions / skill_gap / action_plan / career_alignment / narrative 等字段
   ```

---

## 八、交付 checklist（Kimi 自查）

- [ ] T1 `shared.py` + `loaders.py`（含 getter 封装），验证 PASS
- [ ] T2 `scoring.py`，验证 PASS
- [ ] T3 `skill_gap.py`，验证 PASS
- [ ] T4 `action_plan.py`（`_build_action_plan` 原样搬，行数 ≈ 453），验证 PASS
- [ ] T5 `career_alignment.py`，验证 PASS
- [ ] T6 `narrative.py`，验证 PASS
- [ ] T7 `pipeline.py` + `__init__.py` 完成；原 `report_service.py` 已删；2 处外部 import 已改；`pytest` 不 regress（≥ 103 passed）
- [ ] 每个 sub-module 行数如预期（见 T7 验证第 4 条）
- [ ] 无新增依赖
- [ ] 全局 state 封装验证：在 pipeline.py 里 `import backend.services.report.loaders as L; assert hasattr(L, 'get_graph_nodes')` 通过

---

## 附录 · 相关参考

- 前序 Phase 1 文档：[`backend-slimdown-phase1-profile-service.md`](./backend-slimdown-phase1-profile-service.md)（已完成，Kimi 交付验收通过）
- 原文件：`backend/services/report_service.py`（拆完后删除）
- 路由调用方：`backend/routers/report.py`（改 2 处 import）

## 与 Phase 1 的实践对比

| 项 | Phase 1 profile | Phase 2 report |
|---|---|---|
| 文件大小 | 1872 行 | 2598 行（+38%） |
| 拆分后子模块数 | 6 + facade | 7 + facade |
| class facade | ProfileService | 无（保持模块级函数风格） |
| 测试保障 | 17 个单元测试 | 无 — 靠 import + 回归 + 运行时烟测 |
| 主要风险 | 测试契约（infer_skills_esco） | 超大函数 + 全局 state 封装 |
