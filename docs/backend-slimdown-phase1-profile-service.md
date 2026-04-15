# Backend 瘦身 Phase 1 · profile_service.py 拆分

交付人：Kimi
审查 / 文档：Claude
日期：2026-04-15
前序对齐：owner 选 Part A → backend 瘦身，最痛一刀先砍 profile_service.py

---

## 一、背景

### 现状
- `backend/services/profile_service.py` = **1872 行**，单文件
- 文件 docstring **自己就说** "Consolidates **five algorithm modules** into one Service class" —— 这是历史上 5 个模块被合成 1 个大文件的产物
- 外部调用者**只有 4 处**，且只依赖一个类 `ProfileService` —— 拆分面小

### 目标
按原本的 5 个领域模块**反向拆开**成一个 package，对外接口保持零变化（`ProfileService` 类的公共方法签名完全不变），内部职责边界清晰化。

### 为什么做
- 1872 行导致任何 profile 相关新需求都落到这一个文件，后续变更高碰撞率
- 读代码/导航效率低（测试失败时很难定位具体哪个算法）
- 未来想单独替换某个算法（比如换 locator 实现）必须动这整个大文件

### 非目标（不做）
- ❌ 不改任何算法实现
- ❌ 不重命名任何公共方法
- ❌ 不改 `ProfileService` 的对外接口签名
- ❌ 不新增功能

---

## 二、当前文件地图（Kimi 必读）

### 2.1 按分隔符划分的现有 section

文件本身已用 `# ═══` 分隔符切好 6 段，基本就是拆分地图：

| 行号 | Section | 归属拆分目标 |
|---|---|---|
| 1-34 | imports + 常量路径 | `shared.py` |
| 36-145 | FAMILY_KEYWORDS 等 family/task 常量 | `shared.py` |
| 147-533 | Graph Locator 私有函数（13 个） | `locator.py` |
| 535-567 | Shared utilities（`_clamp01` / `_user_*`）+ `_SOFT_DIM_ZH` | `shared.py` |
| 583-967 | Four-Dimension Scoring（9 个 `_score_*` 私有函数） | `scorer.py` |
| 969-1085 | Aggregate Scoring（`_score_basic` / `_score_skills_agg` / `_score_qualities` / `_score_potential` / `_infer_career_stage`） | `scorer.py` |
| 1088-1103 | `_cosine_similarity` | `shared.py` |
| 1108-1871 | `class ProfileService` 本体 | 拆到 `service.py` + 各领域模块 |

### 2.2 ProfileService 类的 public method（**6 个，不是 docstring 说的 5 个**）

| 行号 | method | 归属领域 |
|---|---|---|
| 1240 | `compute_quality(profile_data)` | scorer |
| 1324 | `locate_on_graph(profile, nodes=None)` | locator |
| 1432 | `score_four_dimensions(profile, node)` | scorer |
| 1591 | `generate_sjt_questions(profile_data)` | sjt |
| 1703 | `score_sjt_v2(answers, questions)` | sjt |
| 1739 | `generate_sjt_advice(...)` | sjt |
| 1814 | `infer_skills_cooccurrence(skills, ...)` | cooccurrence |

### 2.3 ProfileService 类的 private method

| 行号 | method | 归属 |
|---|---|---|
| 1119 | `__init__(graph_service)` | service.py (持有 graph_service + 子模块实例) |
| 1134 | `_load_profiles()` | service.py（共享缓存） |
| 1145 | `_get_cross_direction_idf()` | service.py（共享缓存） |
| 1152 | `_load_cooccurrence()` | cooccurrence.py |
| 1218 | `_load_skill_embeddings()` | cooccurrence.py |
| 1557 | `_direction_from_node(node)` | sjt.py |
| 1584 | `_load_sjt_templates()` | sjt.py |
| 1695 | `score_to_level(score)` | sjt.py（staticmethod） |

### 2.4 重要：docstring 的死承诺

文件头 docstring 写了：
```
infer_skills_esco()  — ESCO DAG-based skill inference
```

**实际代码里没有这个方法**。要么在 T6 清理 docstring（删掉这一行），要么保留作为 TODO 标记。Kimi 不要凭 docstring 自创实现。

---

## 三、目标拆分结构

### 3.1 新目录布局

```
backend/services/profile/
├── __init__.py        # 只做 re-export: from .service import ProfileService
├── service.py         # class ProfileService (facade)
│                      # 持有 graph_service 引用 + 持有 locator/scorer/sjt/cooccurrence 子模块
│                      # public method 全部保留，内部 delegate 给子模块
├── shared.py          # 共享常量 + utilities：
│                      #   - FAMILY_KEYWORDS / _SOFT_DIM_ZH / 路径常量
│                      #   - _clamp01 / _cosine_similarity
│                      #   - _user_skill_map / _user_cert_set / _user_competency_names
│                      #   - _soft_skills_as_list
├── locator.py         # 图谱定位（含 13 个 `_collect_*` / `_build_*` / `_task_match` / ...）
│                      # 对外暴露 locate_on_graph(profile, graph_service, nodes=None) 函数
├── scorer.py          # 四维评分（含 `_score_skill_coverage` / `_score_skill_depth` / ...）
│                      # 对外暴露 compute_quality / score_four_dimensions 函数
├── sjt.py             # SJT 情境判断（含 _load_sjt_templates / score_to_level / _direction_from_node）
│                      # 对外暴露 generate_sjt_questions / score_sjt_v2 / generate_sjt_advice 函数
└── cooccurrence.py    # 共现技能推断（含 _load_cooccurrence / _load_skill_embeddings）
                       # 对外暴露 infer_skills_cooccurrence 函数
```

### 3.2 facade 模式（service.py 骨架）

```python
# backend/services/profile/service.py

from typing import Any
from backend.services.profile import locator, scorer, sjt, cooccurrence


class ProfileService:
    """Profile service facade — delegates to sub-modules by domain."""

    def __init__(self, graph_service: Any):
        self.graph_service = graph_service
        # 子模块状态（cache）
        self._profiles_cache: dict | None = None
        self._cross_direction_idf: dict | None = None
        self._cooccurrence_state = cooccurrence.CoocState()  # 封装 cache

    # ── Public API：薄包装 delegate ──────────────────────────

    def compute_quality(self, profile_data: dict) -> dict:
        return scorer.compute_quality(profile_data)

    def locate_on_graph(self, profile: dict, nodes: list | None = None) -> dict:
        return locator.locate_on_graph(profile, self.graph_service, nodes)

    def score_four_dimensions(self, profile: dict, node: dict) -> dict:
        return scorer.score_four_dimensions(profile, node, self._get_cross_direction_idf())

    def generate_sjt_questions(self, profile_data: dict) -> list[dict]:
        return sjt.generate_sjt_questions(profile_data)

    def score_sjt_v2(self, answers: list[dict], questions: list[dict]) -> dict:
        return sjt.score_sjt_v2(answers, questions)

    def generate_sjt_advice(self, *args, **kwargs) -> Any:
        return sjt.generate_sjt_advice(*args, **kwargs)

    def infer_skills_cooccurrence(self, skills: list[str], **kwargs) -> list[str]:
        return cooccurrence.infer_skills_cooccurrence(
            skills, self._cooccurrence_state, **kwargs
        )

    # ── 共享 cache（跨子模块使用） ────────────────────────────

    def _load_profiles(self) -> dict:
        if self._profiles_cache is None:
            # 实现保持原样，从 _PROFILES_PATH 加载
            ...
        return self._profiles_cache

    def _get_cross_direction_idf(self) -> dict:
        if self._cross_direction_idf is None:
            self._cross_direction_idf = scorer.compute_idf_cross_direction(self._load_profiles())
        return self._cross_direction_idf
```

**关键**：sub-module 里的函数**是纯函数**（传入必要参数，不访问全局 state）；state（profile cache / cooccurrence cache）由 `service.py` 的 facade 持有并按需传入。

---

## 四、依赖扫描（Kimi 不要漏改）

### 4.1 外部 import 4 处（修改后目标：全部零改动，继续 work）

| 文件 | 行 | 当前 import | 拆分后是否改动 |
|---|---|---|---|
| `agent/tools/profile_tools.py` | 19 | `from backend.services.profile_service import ProfileService` | **改**：换成 `from backend.services.profile import ProfileService` |
| `agent/tools/profile_tools.py` | 109 | 同上 | **改**：同 |
| `backend/routers/profiles.py` | 19 | 同上 | **改**：同 |
| `tests/conftest.py` | 40 | 同上 | **改**：同 |
| `tests/services/test_profile_service.py` | 14 | 同上 | **改**：同 |

总共 **5 处 import 改动**（profile_tools.py 两处）。

### 4.2 不保留兼容 shim

**决策：直接删 `profile_service.py`，改 5 处 import。**

沿用 Progressive Disclosure 升级时定的规则：不留 shim，一次改干净。因为：
- 只有 5 处 import，改完就结束
- ProfileService 类名不变，语义完全等价
- 保留 shim 会让未来开发者两个路径都能 import，迷惑

---

## 五、Kimi 任务拆解（T1 → T6）

### T1 · 建目录 + 移动常量和 utilities 到 shared.py

**步骤**：
1. 创建 `backend/services/profile/` 目录 + 空 `__init__.py`
2. 创建 `shared.py`，移入：
   - `FAMILY_KEYWORDS` / `_SOFT_DIM_ZH` 等常量字典
   - 路径常量 `_PROJECT_ROOT` / `_PROFILES_PATH` / `_EVIDENCE_PATH` / `_SKILL_EMBEDDINGS_PATH`
   - `_clamp01` / `_cosine_similarity`
   - `_user_skill_map` / `_user_cert_set` / `_user_competency_names` / `_soft_skills_as_list`
3. `__init__.py` 暂时加一行 `from .shared import *`（后续会改）

**T1 验证**：
```bash
python -c "from backend.services.profile.shared import FAMILY_KEYWORDS, _clamp01, _cosine_similarity; print('T1 PASS', len(FAMILY_KEYWORDS), 'families')"
```

### T2 · locator.py（图谱定位）

移入：
- 私有函数（line 152-533）：`_collect_profile_text` / `_build_family_task_vocab` / `_infer_family_prior` / `_task_match` / `_skill_names_from_profile` / `_node_skill_set` / `_build_skill_idf` / `_weighted_skill_match` / `_extract_terms` / `_title_bonus` / `_soft_match_lite` / `_competency_match`
- ProfileService.locate_on_graph 方法（line 1324-1431）→ 抽成纯函数 `locate_on_graph(profile, graph_service, nodes=None)`

凡是引用常量/utilities 的地方改成 `from backend.services.profile.shared import XXX`。

**T2 验证**：
```bash
python -c "from backend.services.profile.locator import locate_on_graph; print('T2 PASS')"
```

### T3 · scorer.py（四维评分）

移入：
- 私有函数（line 588-1085）：`_compute_idf_cross_direction` / `_score_skill_coverage` / `_score_skill_depth` / `_score_experience` / `_score_education` / `_score_practice` / `_score_certificates` / `_score_competency` / `_compute_weights` / `_infer_career_stage` / `_score_basic` / `_score_skills_agg` / `_score_qualities` / `_score_potential`
- ProfileService.compute_quality（line 1240-1323）→ 纯函数 `compute_quality(profile_data)`
- ProfileService.score_four_dimensions（line 1432-1556）→ 纯函数 `score_four_dimensions(profile, node, cross_direction_idf)`
- Exported helper: `compute_idf_cross_direction(profiles)` 供 service facade 调用

**T3 验证**：测试 `tests/services/test_profile_service.py::test_score_four_dimensions*` 必须全绿。

### T4 · sjt.py（SJT 情境判断）

移入：
- ProfileService._load_sjt_templates（line 1584）
- ProfileService.generate_sjt_questions（line 1591）→ 纯函数
- ProfileService._direction_from_node（line 1557）
- ProfileService.score_to_level（line 1695）
- ProfileService.score_sjt_v2（line 1703）→ 纯函数
- ProfileService.generate_sjt_advice（line 1739）→ 纯函数

**T4 验证**：
```bash
python -c "from backend.services.profile.sjt import generate_sjt_questions, score_sjt_v2; print('T4 PASS')"
```

### T5 · cooccurrence.py + service.py facade

**cooccurrence.py 移入**：
- ProfileService._load_cooccurrence（line 1152-1217）
- ProfileService._load_skill_embeddings（line 1218-1239）
- ProfileService.infer_skills_cooccurrence（line 1814-1871）
- 封装 `CoocState` 类持有 `_cooccurrence_conditional` 和 `_skill_embeddings_cache` 状态
- 纯函数 `infer_skills_cooccurrence(skills, state, **kwargs)`

**service.py facade**：按第 3.2 骨架实现，delegate 到 sub-module。

**`__init__.py` 最终形态**：
```python
"""ProfileService package."""
from backend.services.profile.service import ProfileService  # noqa: F401
```

**T5 验证**：
```bash
python -c "from backend.services.profile import ProfileService; s = ProfileService(graph_service=None); print('T5 PASS', type(s).__name__)"
```

### T6 · 删除原文件 + 改 5 处外部 import + 全绿回归

**步骤**：
1. 删除 `backend/services/profile_service.py`（直接 `rm`）
2. 改 5 处外部 import：
   - `agent/tools/profile_tools.py` 两处（line 19, 109）
   - `backend/routers/profiles.py` line 19
   - `tests/conftest.py` line 40
   - `tests/services/test_profile_service.py` line 14
   把 `from backend.services.profile_service import ProfileService` 全部改成 `from backend.services.profile import ProfileService`
3. 清理 docstring 里的死承诺：从 `service.py` 的 ProfileService 类 docstring 里**删掉** `infer_skills_esco()` 那一行（或改成 `# TODO: infer_skills_esco 规划中未实现`）

**T6 全局回归验证**：
```bash
# 1. profile service 测试全绿
pytest tests/services/test_profile_service.py -v

# 2. 全局回归
pytest tests/ -v

# 3. import 健康
python -c "
from backend.services.profile import ProfileService
from agent.tools.profile_tools import *
from backend.routers.profiles import router
print('ALL IMPORTS OK')
"

# 4. 行数对比
wc -l backend/services/profile/*.py
# 期望：每个 sub-module < 500 行；shared.py < 200 行；service.py < 200 行
```

---

## 六、拆分红线（Kimi 严格遵守）

1. **不改算法实现** —— 只搬代码 + 必要的参数化（私有函数变纯函数时传入 state）
2. **不重命名 public method** —— `ProfileService` 的 7 个 public method 签名原样保留
3. **不新增 public method** —— 包括不凭 docstring 实现 `infer_skills_esco`
4. **sub-module 之间不互相 import 私有符号** —— 有共享需要就进 `shared.py`
5. **所有 cache / state 只在 `service.py` 持有** —— sub-module 函数是无副作用纯函数（`_load_cooccurrence` 等里用的是传入的 state 对象，不是全局单例）
6. **外部 import 路径全改 + 不留 shim** —— `backend.services.profile_service` 直接 rm 删除，5 处外部 import 一次改完
7. **不引入新依赖** —— 不 pip install 任何新包
8. **每个 T 完成后**：必跑对应验证命令，贴输出证据；任何一项失败停下来修，不要跳到下一个 T

---

## 七、拆分后预估

| 指标 | 拆分前 | 拆分后 |
|---|---|---|
| 最大单文件行数 | **1872** | 预计 < 500（scorer.py 最大） |
| profile 相关代码可发现性 | 一个大文件搜索 | 按领域目录即时定位 |
| 新增算法（如 infer_skills_esco）时碰撞面 | 必动 1872 行文件 | 只动 inferrer.py（新增一个 sub-module） |

---

## 八、交付 checklist（Kimi 自查）

- [ ] T1 `shared.py` 建立，import 验证 PASS
- [ ] T2 `locator.py` 建立，import 验证 PASS
- [ ] T3 `scorer.py` 建立，`test_score_four_dimensions*` 测试全绿
- [ ] T4 `sjt.py` 建立，import 验证 PASS
- [ ] T5 `cooccurrence.py` + `service.py` facade 建立，ProfileService 可实例化
- [ ] T6 原 `profile_service.py` 已删除；5 处外部 import 已改；`pytest tests/` 全绿
- [ ] docstring 死承诺 `infer_skills_esco` 已清理
- [ ] 每个 sub-module 行数 < 500；总新增行数应 ≈ 原 1872 + facade 薄包装 ≈ 1900-2000
- [ ] 无新增依赖

---

## 附录 · 参考

- 前序文档：`docs/coach-skill-progressive-disclosure.md`（类似的拆分 + 解耦红线模式）
- 原文件：`backend/services/profile_service.py`（拆完后删除）
- 测试文件：`tests/services/test_profile_service.py`（拆完后必须全绿，不改测试代码，只改 import 路径）
