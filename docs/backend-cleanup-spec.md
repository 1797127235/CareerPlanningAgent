# 后端代码整理 — Batch 1

> **状态**：草案 v1（交接给 Kimi 执行）
> **目标**：拆大文件、消重复、集中配置、删死代码
> **预计改动**：~200 行新增 + ~1966 行重新组织（不改行为）
> **硬约束**：纯重构，不改任何功能逻辑、不改 API 接口签名、不改前端

---

## §0 范围

本次只做 4 件事（效果最大、风险最小）：

| # | 事项 | 当前状态 |
|---|---|---|
| 1 | 拆 `profiles.py`（1966 行）| 简历解析 / 画像 CRUD / 图谱定位 / SJT / 技能规范化 全塞一个文件 |
| 2 | 集中环境变量到 `backend/config.py` | 4 处用 `os.getenv` 各读一遍 |
| 3 | `ok()` helper 提取到 `backend/utils.py` | `auth.py` 和 `profiles.py` 各写了一份 |
| 4 | 删除 `backend/models.py`（227 行）| 整个文件没有任何 import 引用 |

**不在本次范围内**：
- `chat.py`（1315 行）拆分 → Batch 2
- `db.py` 的 18 处 `except Exception: pass` → Batch 2
- 类型标注补全 → Batch 2
- 惰性 import 整理 → Batch 2
- 前端任何改动

---

## §1 拆 `profiles.py`（1966 → 5 个文件）

### 目标结构

```
backend/routers/
├── profiles.py              ← 瘦身后仅留 route handler（~250 行）
├── _profiles_helpers.py     ← ok() 移走后的核心 helpers（~120 行）
├── _profiles_graph.py       ← 图谱相关 helpers（~550 行）
├── _profiles_parsing.py     ← 简历解析 + 技能规范化 + VLM/OCR（~520 行）
└── _profiles_sjt.py         ← SJT 软技能评估（~120 行）
```

### 拆分映射（按原文件行号）

**`_profiles_helpers.py`**（核心 helpers，被多个兄弟文件 import）：
- L37-52: `_get_or_create_profile()`
- L54-63: `_resolve_node_label()`
- L65-131: `_profile_to_dict()`
- L138-225: `_merge_profiles()`

**`_profiles_graph.py`**（图谱定位、embedding 预过滤、LLM 匹配、推荐）：
- L326-347: `_graph_changed()`, `_invalidate_graph_cache()`
- L349-384: `_get_graph_nodes()`, `_get_role_list_text()`
- L392-479: `_load_node_embeddings()`, `_embedding_prefilter()`
- L574-635: `_llm_match_role()`
- L694-757: `_filter_recommendations()`
- L762-888: `_auto_locate_on_graph()`
- 包含模块级缓存变量：`_graph_nodes_cache`, `_role_list_text_cache`, `_node_embeddings`, `_graph_mtime`, `_skill_vocab_cache` 等

**`_profiles_parsing.py`**（简历文本提取 + 后处理 + VLM/OCR）：
- L927-939: `_normalize_skill_name()`, `_normalize_skills()`
- L1076-1134: `_is_valid_internship()`, `_internship_to_project_str()`
- L1136-1169: `_postprocess_profile()`
- L1172-1329: `_vlm_supplement_certificates()`, `_extract_profile_multimodal_vl()`
- L1331-1370: `_ocr_pdf_with_vl()`
- L1373-1384: `_build_skill_vocab()`
- L1394-1447: `_extract_profile_with_llm()`
- L1452-1487: `_lazy_fix_misclassified_internships()`

**`_profiles_sjt.py`**（SJT 软技能评估 v2）：
- L1851-1900: `generate_sjt()` route handler
- L1901-1966: `submit_sjt()` route handler
- 这两个是 route handler 而非纯 helper，文件内自带 `@router.post(...)` 装饰器

**`profiles.py`**（瘦身后的主路由文件）：
- L238-313: `refine_profile_project()`, `update_profile_project()` — route handler
- L1492-1503: `get_profile()` — route handler
- L1505-1565: `parse_resume()` — route handler
- L1584-1642: `update_profile()` — route handler
- L1644-1674: `reparse_profile()` — route handler
- L1677-1701: `set_profile_name()` — route handler
- L1703-1717: `set_preferences()` — route handler
- L1724-1845: `reset_profile()` — route handler
- 顶部 import 从兄弟文件引入所需 helper

### Import 规则

```python
# profiles.py 顶部
from backend.routers._profiles_helpers import (
    _get_or_create_profile, _resolve_node_label,
    _profile_to_dict, _merge_profiles,
)
from backend.routers._profiles_graph import _auto_locate_on_graph
from backend.routers._profiles_parsing import (
    _extract_profile_with_llm, _extract_profile_multimodal_vl,
    _postprocess_profile, _normalize_skills,
    _lazy_fix_misclassified_internships, _ocr_pdf_with_vl,
    _vlm_supplement_certificates,
)
```

```python
# _profiles_graph.py 需要从 _profiles_helpers import
from backend.routers._profiles_helpers import _get_or_create_profile

# _profiles_parsing.py 需要从 _profiles_graph import
from backend.routers._profiles_graph import _build_skill_vocab
```

**`_profiles_sjt.py` 特殊处理**：它包含 route handler（`@router.post`），所以需要在文件内创建自己的 `router` 或者从 `profiles.py` 传入。推荐方案：

```python
# _profiles_sjt.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.auth import get_current_user
from backend.db import get_db
from backend.routers._profiles_helpers import _get_or_create_profile

router = APIRouter()

@router.post("/profiles/sjt/generate")
def generate_sjt(...): ...
```

然后在 `profiles.py` 里 include：
```python
from backend.routers._profiles_sjt import router as sjt_router
# 在 app.py 里或 profiles.py 里 include sjt_router
```

**或者更简单**：SJT 的两个 handler 直接留在 `profiles.py` 里（它们只有 ~120 行），不单独拆文件。由 Kimi 判断——如果拆出来 import 链变复杂，就留在 `profiles.py`。

### 验证标准

拆完后：
1. `python -c "from backend.routers.profiles import router"` 无 import 错误
2. 所有 API 接口（`GET /profiles`, `PUT /profiles`, `POST /profiles/parse-resume`, `DELETE /profiles`, `POST /profiles/sjt/generate`, `POST /profiles/sjt/submit`, `PATCH /profiles/name`, `PATCH /profiles/preferences`, `POST /profiles/reparse`）行为不变
3. `profiles.py` 行数 < 400
4. 每个拆出去的文件 < 600 行

---

## §2 集中环境变量到 `backend/config.py`（新增）

### 当前散落位置

| 文件 | 行号 | 读的变量 |
|---|---|---|
| `backend/routers/profiles.py` | L445-446 | `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL` |
| `backend/services/coach_memory.py` | L27-32 | `DASHSCOPE_API_KEY`, `OPENAI_API_KEY`, `LLM_BASE_URL`, `MEM0_LLM_MODEL`, `MEM0_EMBEDDING_MODEL`, `MEM0_LLM_TEMPERATURE` |
| `backend/services/graph_service.py` | L61, L64 | `DASHSCOPE_API_KEY`, `OPENAI_API_KEY`, `LLM_BASE_URL` |
| `backend/app.py` | L67 | `CORS_ORIGINS` |
| `backend/auth.py` | L23 | `JWT_SECRET_KEY` |

### 目标

新增 `backend/config.py`：

```python
"""Centralized configuration — single source of truth for env vars."""
import os

# ── LLM / DashScope ──────────────────────────────────────────────────────
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ── Mem0 (Coach Memory) ──────────────────────────────────────────────────
MEM0_LLM_MODEL: str = os.getenv("MEM0_LLM_MODEL", "qwen-plus")
MEM0_EMBEDDING_MODEL: str = os.getenv("MEM0_EMBEDDING_MODEL", "text-embedding-v3")
MEM0_LLM_TEMPERATURE: float = float(os.getenv("MEM0_LLM_TEMPERATURE", "0.1"))

# ── Auth ─────────────────────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "career-planner-secret-key-2024")

# ── CORS ─────────────────────────────────────────────────────────────────
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
```

然后在 4 个引用处改为：
```python
from backend.config import DASHSCOPE_API_KEY, LLM_BASE_URL
```

**注意**：`backend/llm.py` 已有自己的 `get_env_str()` / `get_env_int()` 和 `_MODEL_MAP`。不要和 `config.py` 冲突。`llm.py` 的 helper 保留（它有 fallback 逻辑），但 `config.py` 用于**其他文件**不想通过 `llm.py` 间接访问的场景。

---

## §3 `ok()` helper 提取到 `backend/utils.py`（新增）

### 当前

- `backend/routers/auth.py:20-27` — 定义 `ok()`
- `backend/routers/profiles.py:26-32` — 定义一模一样的 `ok()`

### 目标

新增 `backend/utils.py`：

```python
"""Shared utilities used across routers."""
from typing import Any


def ok(data: Any = None, message: str | None = None) -> dict:
    """Wrap a successful response in the standard envelope."""
    result: dict = {"success": True}
    if data is not None:
        result["data"] = data
    if message:
        result["message"] = message
    return result
```

然后在 `auth.py` 和 `profiles.py` 顶部改为：
```python
from backend.utils import ok
```

删掉两个文件里各自的 `ok()` 定义。

---

## §4 删除 `backend/models.py`

`grep -r "from backend.models" backend/` 和 `grep -r "from backend import models" backend/` 均返回空。227 行 Pydantic models 完全没有被 import 过。整个文件可以安全删除。

---

## §5 回归 checklist

1. `python -c "from backend.app import app; print('app OK')"` 无 import 错误
2. `python -c "from backend.routers.profiles import router"` 无 import 错误
3. `python -c "from backend.routers.auth import router"` 无 import 错误
4. `python -c "from backend.config import DASHSCOPE_API_KEY, LLM_BASE_URL, JWT_SECRET_KEY, CORS_ORIGINS"` 无 import 错误
5. `python -c "from backend.utils import ok"` 无 import 错误
6. `profiles.py` 行数 < 400
7. `_profiles_graph.py` + `_profiles_parsing.py` + `_profiles_helpers.py` 合计行数 ≈ 原 `profiles.py` 去掉 route handler 的部分
8. `backend/models.py` 不存在
9. 全局 `grep -rn "os.getenv\|os.environ" backend/routers/ backend/services/` 只在 `backend/config.py`（或 `backend/llm.py`）里出现，其他文件不再直接调 `os.getenv`
10. `POST /api/profiles/parse-resume` 上传一份简历正常返回（端到端不回归）
11. `GET /api/profiles` 正常返回

---

## §6 执行边界 & 求助规则

遇到以下情况**不要自己猜，写下问题先停**：

1. 拆文件时遇到**循环 import**（A 依赖 B 且 B 依赖 A）→ 先沟通哪边该惰性 import
2. `_profiles_graph.py` 的模块级缓存变量如果被其他文件直接读写（不通过函数）→ 先沟通是否改成函数式访问
3. `_profiles_sjt.py` 的 route 注册方式如果嫌复杂 → 可以选择留在 `profiles.py` 不拆，但要沟通
4. `config.py` 里的默认值如果和原散落处的默认值不一致 → 以原散落处为准，但先沟通

---

## §7 交付物

1. 新增文件：
   - `backend/config.py`
   - `backend/utils.py`
   - `backend/routers/_profiles_helpers.py`
   - `backend/routers/_profiles_graph.py`
   - `backend/routers/_profiles_parsing.py`
   - `backend/routers/_profiles_sjt.py`（可选，如果拆出来 import 不复杂）

2. 修改文件：
   - `backend/routers/profiles.py`（瘦身到 < 400 行）
   - `backend/routers/auth.py`（删 `ok()` 定义，改用 `from backend.utils import ok`）
   - `backend/services/coach_memory.py`（改用 `from backend.config import ...`）
   - `backend/services/graph_service.py`（改用 `from backend.config import ...`）
   - `backend/app.py`（改用 `from backend.config import CORS_ORIGINS`）

3. 删除文件：
   - `backend/models.py`

4. Commit message 建议：
   ```
   refactor(backend): split profiles.py + centralize config + delete dead code

   - Split profiles.py (1966 lines) into 5 files by domain:
     _profiles_helpers / _profiles_graph / _profiles_parsing / _profiles_sjt
   - New backend/config.py centralizes env var reads (was scattered in 4 files)
   - New backend/utils.py extracts shared ok() helper (was duplicated in 2 files)
   - Delete unused backend/models.py (227 lines, zero imports)
   ```

---

## §8 开工前先回一句

收到 spec 后，先回："文档读完，准备开工"——如果有任何在 §6 里列出的不确定，同步提出。
