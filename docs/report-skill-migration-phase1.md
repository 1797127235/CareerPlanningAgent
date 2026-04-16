# Report Prompt · Skill 化迁移 Phase 1

交付人：Kimi
审查 / 文档：Claude
日期：2026-04-16
前序对齐：owner 要求"prompt 膨胀就 skill 化"（见 memory `feedback_skill_architecture.md`）。同时趁迁移顺手做 A（加长）+ B（补未用字段）+ D（气质重写）的内容升级。

---

## 一、背景

### 现状

报告生成的 LLM prompt **全部是 Python 硬编码字符串**，散落在 `backend/services/report/*.py` 的 5 处：

| 文件 | 行号 | 用途 | 当前约束 |
|---|---|---|---|
| `narrative.py` | L13 | `_NARRATIVE_SYSTEM` — 叙事段 system prompt | 固定文案 |
| `narrative.py` | L138-166 | narrative user prompt | `temperature=0.5, max_tokens=400` |
| `narrative.py` | L283-295 | diagnosis 项目诊断 prompt | `temperature=0.3, max_tokens=800` |
| `career_alignment.py` | L250-268 | career_alignment observations + 对齐清单 prompt（_build_alignment_prompt 出） | `temperature=0.2, max_tokens=1200` |
| `pipeline.py` | L597-613 | `polish_narrative` 润色 prompt | `temperature=0.4, max_tokens=600` |
| `pipeline.py` | L209-215 | 项目描述反推技能 prompt（skill inference） | `temperature=0.1, max_tokens=300` |

> `skill_gap.py` 里还有两处 prompt（L100 / L276），本 phase **不迁**（见非目标）。
> `action_plan.py` 里有多个子 prompt，独立一轮再迁，**本 phase 不动**。

### 目标

1. **结构化**：把上述 5 处 prompt 迁到 `backend/skills/<name>/SKILL.md`，遵循 Anthropic 官方 Skill 目录格式。
2. **内容升级**（随迁移一次做到位，避免重复打开同一个 prompt）：
   - A：narrative 字数从 200-300 字 → 400-600 字 3-4 段；career_alignment observations 从一句扩到 2-3 段
   - D：narrative 气质从"教练评估段"换成**"观察手记"**体——像一位老师读完你的履历后给你写的短信，有节奏、有引用、有温度
   - skills 强引证：narrative / career_alignment / diagnosis 的 prompt 里**显式要求** LLM 引用 2-3 个用户的具体 `skill` 或 `ProjectRecord.skills_used` 作为证据，禁止空谈"你的技术底色"
3. **统一入口**：Python 代码里 `from backend.llm import ...` + 手拼 prompt 的地方全部改成 `from backend.skills import load_skill` + `render_skill(name, **ctx)`。

### 为什么做

- Owner 反复反馈"AI 写出来的 narrative 太抽象、不够长、不引用具体内容"，根因是 prompt 藏在代码里难改，也没被严格要求引用。
- 未来会多次调气质（信件体 / 手记体 / 教练体切换），如果每次都要 diff Python 源码，迭代成本高。
- 迁移后，非工程师可以直接改 SKILL.md 试效果；版本管理也更清晰。

### 非目标（不做）

- ❌ 不迁 `action_plan.py` 里的 prompt（内部多个子 prompt 协作，独立一轮处理）。
- ❌ 不迁 `skill_gap.py` 里的两处 prompt（一个是 growth_suggestion，一个是 implicit skill embedding；都是技术性辅助，与报告叙事解耦）。
- ❌ 不改 `backend/llm.py`（DashScope 客户端保持不变）。
- ❌ 不换 LLM 供应商，不引入 Anthropic SDK。Skill 架构**只用其目录 + YAML frontmatter + Markdown body 的组织形式**，不接入 Claude 自动调度。
- ❌ 不动 ReportPage 的 `action_plan`、Chapter IV 渲染。
- ❌ 不展示 `project_recommendations` / `soft_skills`（owner 明确不要）。
- ❌ 不改 `match_score` / `four_dim` 的计算与展示（已删除展示，保持后端生成）。

---

## 二、Skill 官方目录格式（Kimi 必读）

Anthropic Skill 规范：

```
skill-name/
├── SKILL.md              ← 必须
│   ├── YAML frontmatter（name、description 必填）
│   └── Markdown 正文指令
└── 可选资源
    ├── scripts/          ← 可执行脚本（确定性任务）
    ├── references/       ← 按需加载的参考文档
    └── assets/           ← 输出中使用的资源
```

本 phase 所有 skill 只用 `SKILL.md` 一个文件。`scripts/` `references/` `assets/` 都**不建**。

---

## 三、项目中的落地结构

```
backend/
├── skills/                           ← 新建
│   ├── __init__.py                   ← 暴露 load_skill / render_skill
│   ├── _loader.py                    ← 加载 + 渲染的实现
│   ├── narrative/
│   │   └── SKILL.md
│   ├── diagnosis/
│   │   └── SKILL.md
│   ├── career-alignment/
│   │   └── SKILL.md
│   ├── polish/
│   │   └── SKILL.md
│   └── skill-inference/
│       └── SKILL.md
```

目录名用 **kebab-case**（`career-alignment`）以对齐 Anthropic 官方示例。Python import 用 `load_skill("career-alignment")`。

---

## 四、SKILL.md 文件规范

### 4.1 YAML frontmatter 字段

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `name` | ✅ | str | 和目录名一致 |
| `description` | ✅ | str | 一句话描述这个 skill 做啥（供未来 agent 调度参考，本 phase 仅作记号） |
| `model` | ✅ | `"fast"` \| `"slow"` | 映射到 `backend.llm.get_model(preset)` |
| `temperature` | ✅ | float | 0.0-1.0 |
| `max_tokens` | ✅ | int | 生成上限 |
| `output` | ✅ | `"text"` \| `"json"` | text 直接返回 string；json 会尝试 parse，失败抛 `SkillOutputParseError` |

### 4.2 Body 规范

Body 是纯 Markdown。**规定两个二级 section**：

```markdown
## System

<system prompt 文本——LLM 的角色和约束>

## User

<user prompt 模板，可含 {变量} 占位符>
```

**变量语法**：Python `.format()` 的 `{变量名}`。**不用 Jinja2**，不支持条件/循环（复杂场景在 Python 侧预处理好再传进来）。

**变量值必须都提前在 Python 侧字符串化**（比如技能列表拼成 `"C++, Python, PyTorch"`）。SKILL.md 不做模板逻辑。

### 4.3 完整例子（narrative skill）

`backend/skills/narrative/SKILL.md`：

```markdown
---
name: narrative
description: 生成报告 Chapter I 的叙事段落，400-600 字，观察手记体，强引证用户具体 skill 和项目
model: fast
temperature: 0.5
max_tokens: 800
output: text
---

## System

你是一位读了很多学生履历的老师，正在为一名 IT 方向的学生写一封短观察手记。语气像给学生发的一封信：温和，具体，不给分，不评等级。你看的是对方已经有的材料——教育、技能、项目——然后指出你从这些材料里读到的东西。

硬约束：
- 写 400-600 字，拆成 3-4 段，段之间空行。
- **必须引用对方具体的 2-3 个技能名或项目名**（从下面给你的清单里挑，不要造）。如果清单里没东西可引，诚实地说"目前你的履历材料还不够，先把最近做的事记一下"。
- 不要出现分数、百分比、"综合""匹配度""readiness""核心/重要/加分"这类量化词。
- 不要出现"作为一名学生你……"这种套话模板。
- 直接输出正文，不要标题，不要"尊敬的同学"。

## User

目标方向：{target_label}

学生已声明的技能（来自简历）：
{claimed_skills}

学生的项目清单（名字 + 描述）：
{projects_list}

学生教育背景：
{education_line}

上一份报告到现在的变化（若有）：
{delta_line}

市场侧看这个方向的处境：
{market_line}

请写这封观察手记。
```

---

## 五、Loader 规格

### 5.1 `backend/skills/_loader.py`

```python
"""Skill loader: parse YAML frontmatter + Markdown body from SKILL.md files.

Usage:
    from backend.skills import load_skill, render_skill

    skill = load_skill("narrative")
    system_prompt, user_prompt, cfg = render_skill("narrative",
        target_label="系统C++工程师",
        claimed_skills="C++, Python, PyTorch",
        projects_list="- Muduo 网络库复现\n- ...",
        education_line="某 211 学校 · 计算机 · 硕士",
        delta_line="距上次报告 8 天，期间完成了 Redis 基础。",
        market_line="目前招聘窗口一般，薪资 p50 ¥28k。",
    )
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

_SKILLS_DIR = Path(__file__).parent


class SkillNotFoundError(Exception): ...
class SkillFormatError(Exception): ...
class SkillOutputParseError(Exception): ...


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    model: Literal["fast", "slow"]
    temperature: float
    max_tokens: int
    output: Literal["text", "json"]
    system: str
    user_template: str


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@lru_cache(maxsize=32)
def load_skill(name: str) -> Skill:
    """Load and cache a skill by directory name."""
    skill_path = _SKILLS_DIR / name / "SKILL.md"
    if not skill_path.is_file():
        raise SkillNotFoundError(f"{skill_path} not found")

    raw = skill_path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        raise SkillFormatError(f"{skill_path}: missing YAML frontmatter")

    meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)

    # 拆 ## System / ## User
    system_match = re.search(r"##\s*System\s*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
    user_match = re.search(r"##\s*User\s*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
    if not system_match or not user_match:
        raise SkillFormatError(f"{skill_path}: missing ## System or ## User section")

    required = {"name", "description", "model", "temperature", "max_tokens", "output"}
    missing = required - set(meta.keys())
    if missing:
        raise SkillFormatError(f"{skill_path}: frontmatter missing {missing}")

    return Skill(
        name=meta["name"],
        description=meta["description"],
        model=meta["model"],
        temperature=float(meta["temperature"]),
        max_tokens=int(meta["max_tokens"]),
        output=meta["output"],
        system=system_match.group(1).strip(),
        user_template=user_match.group(1).strip(),
    )


def render_skill(name: str, **ctx) -> tuple[str, str, Skill]:
    """Load a skill and render its user template with ctx variables.

    Returns (system_prompt, user_prompt, skill) — skill carries model config.
    """
    skill = load_skill(name)
    try:
        user_prompt = skill.user_template.format(**ctx)
    except KeyError as e:
        raise SkillFormatError(f"{name}: missing template variable {e}") from e
    return skill.system, user_prompt, skill


def invoke_skill(name: str, **ctx) -> str | dict:
    """End-to-end: render + call LLM + optional JSON parse.

    For skills with output=json, returns parsed dict (raises SkillOutputParseError
    on malformed output).  For text, returns raw string.
    """
    from backend.llm import get_llm_client, get_model
    system, user, skill = render_skill(name, **ctx)

    resp = get_llm_client(timeout=120).chat.completions.create(
        model=get_model(skill.model),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=skill.temperature,
        max_tokens=skill.max_tokens,
    )
    raw = resp.choices[0].message.content.strip()

    if skill.output == "json":
        import json
        # 容错剥壳 ```json ... ```
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError as e:
            raise SkillOutputParseError(f"{name}: {e}") from e

    return raw
```

### 5.2 `backend/skills/__init__.py`

```python
from backend.skills._loader import (
    Skill,
    SkillNotFoundError,
    SkillFormatError,
    SkillOutputParseError,
    load_skill,
    render_skill,
    invoke_skill,
)

__all__ = [
    "Skill",
    "SkillNotFoundError",
    "SkillFormatError",
    "SkillOutputParseError",
    "load_skill",
    "render_skill",
    "invoke_skill",
]
```

### 5.3 依赖

`pyyaml` — 已存在于 `backend/requirements.txt`？请先 `grep -E "^pyyaml|^PyYAML" backend/requirements.txt`。不在的话加 `pyyaml>=6.0`。

---

## 六、5 个 Skill 的详细规格

### 6.1 `backend/skills/narrative/SKILL.md`

**替换**：`narrative.py` 的 `_NARRATIVE_SYSTEM`（L13）+ `_generate_narrative` 的 prompt body（L138-166）。

**Frontmatter**：
```yaml
name: narrative
description: 报告 Chapter I 的叙事段落，观察手记体，强引证用户 skill
model: fast
temperature: 0.5
max_tokens: 800
output: text
```

**System**（用 §4.3 例子的 System 段原文）。

**User 模板变量**：

| 变量 | 类型 | 来源（调用方准备） |
|---|---|---|
| `target_label` | str | `goal.target_label` |
| `claimed_skills` | str | `profile_data.skills` 的 name 拼成逗号分隔 |
| `projects_list` | str | `ProjectRecord` + `profile_data.projects` 的 name / desc 拼成多行，每行一条 |
| `education_line` | str | `education.school + major + degree` 拼成一行 |
| `delta_line` | str | 有 delta 时："距上次报告 N 天，期间多掌握了 X"；无则留空字符串 |
| `market_line` | str | `node.salary_p50 / timing_label / demand_change_pct` 拼一行；无数据留空 |

**调用点改动**：`narrative.py::_generate_narrative` 内部去掉 L13 / L138-185 的硬编码，改成：

```python
from backend.skills import invoke_skill
text = invoke_skill(
    "narrative",
    target_label=target_label,
    claimed_skills=", ".join(s.get("name", "") for s in claimed_skills or []),
    projects_list="\n".join(f"- {p}" for p in _format_projects_for_prompt(projects)),
    education_line=_format_education(education),
    delta_line=_format_delta_line(delta),  # 调用方传入已组装好的 delta
    market_line=_format_market(market_info),
)
return text.strip()
```

> `_format_*` 辅助函数放在 `narrative.py` 文件底部，都是纯字符串拼接，不动 Skill 文件。
> `delta` 参数是新增：`pipeline.py::generate_report` 在算完 `delta` 后（L456-537）把它往下传给 `_generate_narrative`。

### 6.2 `backend/skills/diagnosis/SKILL.md`

**替换**：`narrative.py` L283-298 里的诊断 prompt。

**Frontmatter**：
```yaml
name: diagnosis
description: 扫描用户每个项目描述，标出"做了什么但没说明白什么"的具体改进点
model: fast
temperature: 0.3
max_tokens: 800
output: json
```

**System**（保持现有"简历优化专家"角色，但加强输出 schema 约束）。

**User 模板变量**：`target_label`、`projects_json`（项目列表的 JSON 字符串）。

**Output**：期望 JSON array，每条 `{source, source_type, source_id, current_text, status, highlight, issues, suggestion}`——保持现有 ReportV2Data.diagnosis shape 不变。

### 6.3 `backend/skills/career-alignment/SKILL.md`

**替换**：`career_alignment.py::_build_alignment_prompt` 整块，以及 L250-274 的调用。

**Frontmatter**：
```yaml
name: career-alignment
description: 给出学生和目标方向的定性 fit 分析 + 3 条对齐维度 + 无法判断的保留项
model: slow
temperature: 0.2
max_tokens: 1600     # 从 1200 提到 1600，给 observations 扩到 2-3 段的空间
output: json
```

**System** 新要求（D 气质 + A 加长）：
- observations 字段从一句扩到 **2-3 段**，每段至少引用 1 个用户具体技能或项目名
- alignments 保持 3 条（不动 schema）
- cannot_judge 至少 1 条（诚实）

**User 模板变量**：`candidates_json`、`target_node_id`、`skills_list`、`projects_list`、`soft_skills_summary`。

**Output schema** 保持现状。

### 6.4 `backend/skills/polish/SKILL.md`

**替换**：`pipeline.py::polish_narrative`（L597-613）。

**Frontmatter**：
```yaml
name: polish
description: 润色已有的 narrative，保留事实与数字，只改语感
model: fast
temperature: 0.4
max_tokens: 800
output: text
```

**User 模板变量**：`target_label`、`narrative`。

**调用点**：`pipeline.py::polish_narrative` 内部直接 `return invoke_skill("polish", target_label=target_label, narrative=narrative)`。

### 6.5 `backend/skills/skill-inference/SKILL.md`

**替换**：`pipeline.py` L209-230 里反推项目技能的 prompt。

**Frontmatter**：
```yaml
name: skill-inference
description: 从项目描述文本反推技术栈技能
model: fast
temperature: 0.1
max_tokens: 300
output: json
```

**System**：技术栈分析助手角色（保持现有）。

**User 模板变量**：`projects_text`（多行项目描述拼接）。

**Output**：JSON array of skill name strings，或 object `{"skills": [...]}`。

---

## 七、调用方改动清单

### 7.1 `backend/services/report/narrative.py`

1. 删除 L13-21 `_NARRATIVE_SYSTEM`。
2. `_generate_narrative`（L52 起）：
   - 删除 L138-185 的 prompt + client.chat 调用
   - 改为 `invoke_skill("narrative", **ctx)`
   - **新增一个参数** `delta: dict | None = None`（可选，用于叙事化 delta）
3. `_generate_diagnosis`（找到对应函数名）：
   - 同样换成 `invoke_skill("diagnosis", ...)`
4. 底部加 `_format_projects_for_prompt / _format_education / _format_delta_line / _format_market` 辅助函数。

### 7.2 `backend/services/report/career_alignment.py`

1. `_build_alignment_prompt` 改写：不再返回拼好的字符串，而是返回 ctx dict（变量值）。
2. L250 附近：`prompt = _build_alignment_prompt(...)` → `ctx = _build_alignment_ctx(...)`；`client.chat.completions.create` 调用整块替换为 `parsed = invoke_skill("career-alignment", **ctx)`。
3. 移除手写的 JSON 剥壳（L269-274）—— loader 统一处理。

### 7.3 `backend/services/report/pipeline.py`

1. `polish_narrative`（L592-618）：整个函数体改成 `return invoke_skill("polish", target_label=target_label, narrative=narrative)`，异常继续吞回 narrative。
2. 项目技能反推（L203-230）：整个 try 块里的 client.chat 改成 `invoke_skill("skill-inference", projects_text="\n".join(f"- {t[:100]}" for t in _texts_to_infer))`。保持现有的 dict/list 合并逻辑。
3. `generate_report` 调 `_generate_narrative` 时传 `delta`（目前 delta 在 L446-537 算，narrative 在更早，顺序要调整：先算 delta，再 call narrative）。

---

## 八、前端配套改动（B 方向）

与 Skill 迁移**解耦可独立上线**。不需要 Kimi 做。Claude 会在 Skill 迁移完成后单独一轮做。本节仅登记需求，Kimi 无需动。

- `frontend/src/components/report/ChapterII.tsx` 加一个小节 `AI 时代的这个方向`，渲染 `data.ai_impact_narrative`（目前未展示）。
- `frontend/src/components/report/Prologue.tsx` 或 `ChapterI` 开头加 delta 叙事：如果 `data.delta.gained_skills.length > 0`，显示一行 italic 小字"距上次报告 {N} 天，期间多掌握了 {A, B}"。不显示分数变化。

---

## 九、回归测试 Checklist

迁移完成后 Kimi 自测：

- [ ] `python -c "from backend.skills import load_skill; s = load_skill('narrative'); print(s.name, s.model)"` 成功输出。
- [ ] 5 个 skill 都能 `load_skill`，YAML frontmatter 字段齐。
- [ ] 手动跑一次 `POST /report/generate`，返回的 `ReportV2Data` 字段齐：
  - `narrative` 存在且 >= 300 字
  - `diagnosis` 是 array，每项有 source/current_text/status/suggestion
  - `career_alignment.observations` 存在且 >= 150 字，含至少 1 个具体技能名
  - `career_alignment.alignments` 有 3 条
  - `skill_gap.top_missing` 保留（没被本迁移动）
- [ ] 之前生成的老报告还能 `GET /report/{id}` 正常读出（不变更 Report.data_json schema）。
- [ ] `editReport / polishReport / deleteReport` 三个接口测试不回归。
- [ ] LLM 调用失败时（timeout 或 429），narrative 回退到现有 fallback 逻辑（不 500）。

---

## 十、不在本次范围内

- ❌ `action_plan` 的 prompt（下一轮）
- ❌ `skill_gap` 的 growth_suggestion / embedding prompt（辅助性质，不影响 UX）
- ❌ ChatSession / 成长教练的 prompt（不是报告范畴）
- ❌ 前端 ChapterII 加 `ai_impact_narrative` + 开头 delta 叙事（Claude 自己做，不占 Kimi 工时）
- ❌ 改 `match_score` 显示（已删除）

---

## 十一、提交约定

1. 一个 commit，message 前缀 `feat(skills)` 或 `refactor(report)`。
2. 文件清单：
   - 新增：`backend/skills/` 整个目录（`_loader.py` + `__init__.py` + 5 个子目录下的 SKILL.md）
   - 修改：`narrative.py` / `career_alignment.py` / `pipeline.py`
   - 修改：`backend/requirements.txt`（若需要加 pyyaml）
3. 不动任何前端文件。
4. 不动 `backend/routers/report.py`。
5. 不改数据库 schema，不改 `ReportV2Data` shape。

完工后把 commit hash 贴给 Claude 审查。
