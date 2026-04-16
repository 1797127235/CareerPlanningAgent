# Spec: 修报告质量两个根因（A + B）

## 背景

用户（系统 C++ 工程师方向）看到第四章行动计划**全是官话**："完善简历"/"建议突出关键词"/"当前项目描述中未见 GDB 相关的具体技术关键词"。

诊断定位了两个独立根因：

### A. action-plan skill 还在 fallback
第四章那些套话句式全部来自 `backend/services/report/action_plan.py` 里的硬编码模板（`text = f"当前项目描述中未见 {name}..."`）。日志显示：
```
action-plan skill failed, fallback to rule-based: Request timed out.
```
此前已把 `_loader.py` 的 LLM timeout 从 120 提到 240 秒，还是 fail。

### B. skill_gap 不读简历项目文本
`_build_skill_gap`（`skill_gap.py:324`）判定用户"有没有某技能"时，只看两个来源：
- 画像 `skills` 字段（用户自己列的 9 个）
- GrowthEntry/ProjectRecord 里 `skills_used`（测试账号为空）

**不看** `profile.projects`（简历解析出的项目文本描述）。导致：

| 技能 | 实际情况 | 系统判定 |
|---|---|---|
| 高并发 | 用户写了"**高并发**内存池"项目 | ❌ gap（未匹配） |
| 内存管理 | 内存池整个项目的核心 | ❌ gap |
| 性能优化 | tcmalloc 对比优化 | ❌ gap |

节点 `systems-cpp` 的 `skill_tiers.important` 包含：`STL / 高并发 / 性能优化 / 内存管理 / GDB / CMake`。用户简历项目里已经体现"高并发""内存池""tcmalloc""Reactor"——**但系统不读这些文本**，所以把一个写过内存池的人判定"缺内存管理"。

---

## 任务 A：让 action-plan skill 真正跑起来

### A1. 诊断日志加固

**文件**：`backend/skills/_loader.py`

当前 `invoke_skill` 只记录一个通用 `Exception`，看不到具体是 timeout 还是 JSON 错还是 prompt 错。改成：

```python
def invoke_skill(name: str, **ctx) -> str | dict:
    import time
    from backend.llm import get_llm_client, get_model
    system, user, skill = render_skill(name, **ctx)

    t0 = time.time()
    try:
        resp = get_llm_client(timeout=240).chat.completions.create(
            model=get_model(skill.model),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=skill.temperature,
            max_tokens=skill.max_tokens,
        )
    except Exception as e:
        elapsed = time.time() - t0
        # 打印具体异常类型 + 耗时 + prompt 长度
        import logging
        logging.getLogger(__name__).warning(
            "[skill:%s] LLM call failed after %.1fs (model=%s, max_tokens=%d, "
            "system_len=%d, user_len=%d): %s: %s",
            name, elapsed, get_model(skill.model), skill.max_tokens,
            len(system), len(user), type(e).__name__, e,
        )
        raise

    elapsed = time.time() - t0
    raw = resp.choices[0].message.content.strip()

    if skill.output == "json":
        import json, logging
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            result = json.loads(raw.strip())
            logging.getLogger(__name__).info(
                "[skill:%s] OK in %.1fs, tokens_est=%d", name, elapsed, len(raw)
            )
            return result
        except json.JSONDecodeError as e:
            logging.getLogger(__name__).warning(
                "[skill:%s] JSON parse failed after %.1fs; first 300 chars of raw:\n%s",
                name, elapsed, raw[:300],
            )
            raise SkillOutputParseError(f"{name}: {e}") from e

    logging.getLogger(__name__).info(
        "[skill:%s] OK in %.1fs", name, elapsed
    )
    return raw
```

这样每次 action-plan 跑完后 terminal 会打印：
- `[skill:action-plan] OK in 48.3s` → 成功
- `[skill:action-plan] LLM call failed after 240.0s ... ReadTimeout` → 超时
- `[skill:action-plan] JSON parse failed after 32.1s; first 300 chars: {"stages":[{"stage":1,"label":"...` → LLM 返回格式错

### A2. 压缩 action-plan prompt

**文件**：`backend/skills/action-plan/SKILL.md`

`max_tokens` 从 2000 降到 **1500**（新 SKILL 允许稀疏输出，1500 足够 6-8 条 items）：

```yaml
max_tokens: 1500
```

### A3. 重试一次再 fallback

**文件**：`backend/services/report/pipeline.py` 第 359-385 行

当前逻辑：
```python
try:
    from backend.skills import invoke_skill
    action_plan_data = invoke_skill("action-plan", ...)
    action_plan_data = _coerce_action_plan(action_plan_data)
except Exception as e:
    logger.warning("action-plan skill failed, fallback to rule-based: %s", e)
    action_plan_data = action_plan._build_action_plan(...)
```

改成：第一次 timeout/JSON 错时**重试一次**（只针对这两类）；重试还失败才 fallback。

```python
import time
from backend.skills import invoke_skill
from backend.skills._loader import SkillOutputParseError

def _invoke_action_plan_with_retry(max_retries=1, **kwargs):
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return invoke_skill("action-plan", **kwargs)
        except (TimeoutError, SkillOutputParseError) as e:
            last_exc = e
            logger.warning("action-plan attempt %d/%d failed: %s: %s",
                          attempt + 1, max_retries + 1, type(e).__name__, e)
            if attempt < max_retries:
                time.sleep(2)
                continue
        except Exception as e:
            # 非可重试异常（key 错、网络断等）直接抛
            raise
    raise last_exc

try:
    action_plan_data = _invoke_action_plan_with_retry(
        target_label=goal.target_label,
        node_requirements_line=_format_node_requirements(node),
        market_line=narrative._format_market(market_info),
        summary_json=json.dumps(summary, ensure_ascii=False),
        prev_recommendations_block=_format_prev_recs(summary["prev_report_recommendations"]),
        completed_block=_format_completed(summary["completed_since_last_report"]),
    )
    action_plan_data = _coerce_action_plan(action_plan_data)
except Exception as e:
    logger.warning("action-plan skill failed after retry, fallback to rule-based: %s", e)
    action_plan_data = action_plan._build_action_plan(...)  # 保持现有 fallback 代码不变
```

注意：DashScope 的 timeout 错误是 `openai.APITimeoutError`，不是标准 `TimeoutError`。实际实现时捕获的异常类需要看 backend.llm 封装。**实现前先看一眼 `backend/llm.py` 确认实际抛的异常类型**，把 `TimeoutError` 换成正确的类。

---

## 任务 B：`skill_gap` 从简历项目文本抽技能

### B1. 新函数：从 profile 文本抽技能

**文件**：`backend/services/report/skill_gap.py`

在 `_build_skill_gap` 之前新增：

```python
def _extract_practiced_from_profile_text(
    profile_data: dict, node_skills: list[str]
) -> set[str]:
    """扫描简历项目文本（profile.projects + profile.raw_text + profile.internships），
    看 node.skill_tiers 的技能名是否出现在文本中，若出现视为有实战证据。

    规则：
    - 大小写不敏感
    - 中文直接 substring；英文用 word boundary（避免 "Go" 匹配到 "Google"）
    - 匹配到的 skill 加入返回集合

    Args:
        profile_data: profile.profile_json 反序列化结果
        node_skills: 节点 skill_tiers 里所有技能名（core + important + bonus）

    Returns:
        set of skill names (原大小写) that appear in profile text
    """
    import re
    # 拼接所有简历文本
    texts: list[str] = []
    projs = profile_data.get("projects") or []
    for p in projs:
        if isinstance(p, str):
            texts.append(p)
        elif isinstance(p, dict):
            for k in ("summary", "description", "detail", "name"):
                v = p.get(k)
                if isinstance(v, str):
                    texts.append(v)
    interns = profile_data.get("internships") or []
    for it in interns:
        if isinstance(it, dict):
            for k in ("summary", "description"):
                v = it.get(k)
                if isinstance(v, str):
                    texts.append(v)
        elif isinstance(it, str):
            texts.append(it)
    raw = profile_data.get("raw_text") or ""
    if isinstance(raw, str):
        texts.append(raw)

    blob = "\n".join(texts)
    blob_lower = blob.lower()

    found: set[str] = set()
    for skill in node_skills:
        if not skill:
            continue
        # 判断 skill 是 CJK 还是 英文字母数字
        has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in skill)
        if has_cjk:
            # 中文直接 substring
            if skill in blob:
                found.add(skill)
        else:
            # 英文用 word boundary（防止 "Go" 匹配 "Google"）
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, blob_lower):
                found.add(skill)
    return found
```

### B2. 接入 `_build_skill_gap`

`_build_skill_gap` 签名加参数 `extra_practiced: set[str] | None = None`，在 `_process_tier` 里把这个并入判定：

```python
def _build_skill_gap(
    profile_data: dict,
    node: dict,
    practiced: set[str] | None = None,
    completed_practiced: set[str] | None = None,
    extra_practiced: set[str] | None = None,  # 新增
) -> dict:
    ...
    # 合并三个来源
    practiced = (practiced or set()) | (extra_practiced or set())
    ...
    has_project_data = bool(practiced or completed_practiced)
```

注意：这里 `extra_practiced` 合并进 `practiced`，意思是"从简历文本抽出的技能也算实战证据"。`has_project_data` 要变 True。

### B3. 在 pipeline 里调用

**文件**：`backend/services/report/pipeline.py` 第 324 行附近（调 `_build_skill_gap` 的地方）

```python
# 原代码：
_skill_gap = skill_gap._build_skill_gap(profile_data, node, practiced, completed_practiced)

# 改为：
all_node_skills = []
for tier in ("core", "important", "bonus"):
    for s in (node.get("skill_tiers", {}).get(tier) or []):
        if s.get("name"):
            all_node_skills.append(s["name"])
text_practiced = skill_gap._extract_practiced_from_profile_text(
    profile_data, all_node_skills
)
if text_practiced:
    logger.info("[skill_gap] extracted %d skills from profile text: %s",
                len(text_practiced), sorted(text_practiced))

_skill_gap = skill_gap._build_skill_gap(
    profile_data, node, practiced, completed_practiced,
    extra_practiced=text_practiced,
)
```

### B4. `matched_skills` 状态加一档

现有状态：`completed | practiced | claimed`
加一档：`practiced_from_resume`（从简历项目文本抽到的）

这样前端第一章可以显示"该技能在你简历项目里出现过"作为证据，比 claimed 可信。

**文件**：`backend/services/report/shared.py` 的 `_skill_proficiency` 函数

当前函数签名：`_skill_proficiency(name, user_skills, practiced, completed_practiced, has_project_data) -> (is_matched: bool, status: str)`

需要区分 practiced 的来源。方案：额外加参数 `text_practiced: set[str] | None = None`，判断顺序：

1. 在 `completed_practiced` → `status = "completed"`
2. 在 `practiced`（ProjectRecord / GrowthEntry 来源）→ `status = "practiced"`
3. 在 `text_practiced`（简历文本来源）→ `status = "practiced_from_resume"`
4. 在 `user_skills`（画像 claim 列表）→ `status = "claimed"`
5. 否则 → missing

**这条是 nice-to-have**，如果实现有难度可以先不做——把 text_practiced 直接并进 practiced（status=practiced），前端一致。

---

## 验收标准

完成 A + B 后，用 user_id=156（系统 C++ 方向）点"再生成一次"，预期：

### 后端日志
```
[skill_gap] extracted N skills from profile text: ['C++', '多线程', '高并发', '内存管理', '网络编程', 'Linux', ...]
[skill:action-plan] OK in 35.xx s
```

### 报告第一章（skill_gap 匹配度）
- `important` 层匹配率不再是"只有 STL 1/6"
- `top_missing` 里**不该**出现"高并发""内存管理""性能优化"（简历文本里有）
- 可能剩的 gap：GDB、CMake、gRPC、协程等真的没在简历里提的

### 报告第四章（action_plan）
- 内容来自新 SKILL.md（LLM 生成），不是 rule-based 模板
- 每条 observation **引用** profile_core.projects 里具体内容（如"你在 C++ 高性能网络库里实现过 Reactor..."）
- 不出现 "未见 GDB 相关技术关键词" 这种万能模板句

### 不破坏
- 老报告（data_json 里没 profile_core 字段）读不崩
- skill-inference / career-alignment / narrative 等其他 skill 不受影响

---

## 不要做的事

- 不要动前端（前端已修好）
- 不要改图谱 `data/graph.json` 里节点定义（改节点需要大改）
- 不要改 action_plan.py 的 rule-based fallback 代码（保留兜底）
- 不要大改 `_skill_proficiency`，如果新增 `practiced_from_resume` 状态太复杂就并进 practiced（方案 B4 的 nice-to-have 部分）
