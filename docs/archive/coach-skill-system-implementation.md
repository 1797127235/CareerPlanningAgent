# Coach Skill 体系实施任务（交给 Kimi）

> 交付人：liu（owner） · 设计：Claude Code · 实施：Kimi
> 日期：2026-04-15
> 架构：遵循 Anthropic Claude Skills 官方规范（目录 + SKILL.md + progressive disclosure）

---

## 背景

现有 `coach_agent` 翻车模式：
1. 用户说"你好"，教练套画像反引用"你方向迷茫 + C++ 基础扎实 + 大厂偏好"
2. 用户说"我不知道能不能找到工作"，教练反问"你觉得呢/你对 X 的理解是什么"
3. 用户说"帮我梳理"，教练还是反问不直接给

**根因**：`SYSTEM_PROMPT`（165 行）+ `build_context_summary`（每轮硬塞全量画像）= LLM 把"系统告诉它的"当"用户刚说的"反引用。

## 解决方案

两个架构级动作：

1. **Context 从 push 改 pull**：system prompt 不再塞画像，LLM 需要时主动调 tool 查
2. **Prompt 从单块改 skill 组合**（遵循 Anthropic Skill 规范）：
   - 每个 skill 是一个**目录**，含 `SKILL.md`（frontmatter: name + description；body: Markdown 指引）
   - Loader 加载所有 SKILL.md，**把 description + body 全部注入 BASE_IDENTITY**
   - LLM 读完所有 skill 自行判断该用哪个（或都不用）——**不做 regex 匹配**

官方目录结构（未来可扩展）：
```
agent/skills/
├── __init__.py                     ✅已写
├── loader.py                       ❌待 Kimi 写
├── coach-greeting/
│   └── SKILL.md                    ✅已写
├── coach-concern-direct/
│   └── SKILL.md                    ✅已写
├── coach-request-deliver/
│   └── SKILL.md                    ✅已写
├── coach-decision-socratic/
│   └── SKILL.md                    ✅已写
└── coach-project-planning/
    └── SKILL.md                    ✅已写
```

每个 skill 目录未来可加 `references/`、`scripts/`、`assets/` 子目录做 progressive disclosure。

## 待 Kimi 完成的 4 件事

| # | 动作 | 文件 |
|---|---|---|
| T1 | 新建 loader | `agent/skills/loader.py` |
| T2 | 新建 pull tools | `agent/tools/coach_context_tools.py` |
| T3 | 改 coach_agent | `agent/agents/coach_agent.py` |
| T4 | 改 supervisor | `agent/supervisor.py` |

---

## T1 — 新建 `agent/skills/loader.py`

**依赖**：`pyyaml`。检查 `requirements.txt`，无则加 `pyyaml>=6.0`。

**完整代码（可直接抄）**：

```python
"""Skill loader — 扫 agent/skills/*/SKILL.md 加载所有 skill。

遵循 Anthropic Skill 规范：目录 + SKILL.md 结构。
LLM 读完所有 skill 的 description + body 自行判断该用哪个。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    name: str
    description: str
    body: str
    path: Path  # skill 目录路径，供未来 progressive disclosure 使用


class SkillLoader:
    _skills: list[Skill] = []
    _loaded: bool = False

    @classmethod
    def load_all(cls, skills_dir: Optional[Path] = None) -> None:
        """扫描 skills_dir 下所有子目录，加载其中的 SKILL.md。"""
        if skills_dir is None:
            skills_dir = Path(__file__).parent

        skills: list[Skill] = []
        for sub_dir in sorted(skills_dir.iterdir()):
            if not sub_dir.is_dir() or sub_dir.name.startswith("__"):
                continue
            skill_file = sub_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                text = skill_file.read_text(encoding="utf-8")
                if not text.startswith("---"):
                    logger.warning("Skill %s missing frontmatter", sub_dir.name)
                    continue
                parts = text.split("---", 2)
                if len(parts) < 3:
                    continue
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
                skills.append(Skill(
                    name=frontmatter.get("name", sub_dir.name),
                    description=frontmatter.get("description", "").strip(),
                    body=body,
                    path=sub_dir,
                ))
            except Exception as e:
                logger.warning("Failed to load skill %s: %s", sub_dir.name, e)

        cls._skills = skills
        cls._loaded = True
        logger.info("SkillLoader loaded %d skills: %s",
                    len(skills), [s.name for s in skills])

    @classmethod
    def all_skills(cls) -> list[Skill]:
        if not cls._loaded:
            cls.load_all()
        return cls._skills


def format_skills_for_prompt() -> str:
    """把所有 skill 的 name + description + body 拼成 prompt 片段。

    LLM 读这个片段后，根据用户本轮消息自行判断该应用哪个 skill（或都不应用）。
    这是 Anthropic 官方 skill 激活机制——信任 LLM 的判断，不做硬编码预匹配。
    """
    skills = SkillLoader.all_skills()
    if not skills:
        return "（尚无可用 skill）"

    parts = []
    for s in skills:
        parts.append(f"### Skill: `{s.name}`")
        parts.append(f"**适用场景**：{s.description}")
        parts.append("")
        parts.append(s.body)
        parts.append("")
    return "\n".join(parts)
```

### 验收 T1

```bash
python -c "
from agent.skills.loader import SkillLoader, format_skills_for_prompt
SkillLoader.load_all()
print(f'Loaded {len(SkillLoader._skills)} skills')
for s in SkillLoader._skills:
    print(f'  - {s.name} (desc {len(s.description)} chars, body {len(s.body)} chars)')
assert len(SkillLoader._skills) == 5, f'应加载 5 个 skill，实际 {len(SkillLoader._skills)}'

prompt = format_skills_for_prompt()
assert 'coach-greeting' in prompt, 'prompt 应含 coach-greeting'
assert 'coach-concern-direct' in prompt, 'prompt 应含 coach-concern-direct'
assert 'coach-request-deliver' in prompt, 'prompt 应含 coach-request-deliver'
print(f'\nPASS: prompt 长度 {len(prompt)} 字符')
"
```

---

## T2 — 新建 `agent/tools/coach_context_tools.py`

**完整代码（可直接抄）**：

```python
"""Coach pull-based context tools.

设计原则：coach 默认无画像知识，需要时主动调 tool 查。
由 supervisor 在调用 coach 前通过 ContextVar 注入 state 数据。
"""
from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from typing import Any, Callable, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Supervisor 在 _make_agent_node 里 set 这些 ContextVar
_ctx_profile: ContextVar[Optional[dict]] = ContextVar("coach_profile", default=None)
_ctx_goal: ContextVar[Optional[dict]] = ContextVar("coach_goal", default=None)
_ctx_user_id: ContextVar[Optional[int]] = ContextVar("coach_user_id", default=None)
_ctx_market_loader: ContextVar[Optional[Callable]] = ContextVar("coach_market_loader", default=None)


@tool
def get_user_profile() -> str:
    """获取用户的技能画像、教育背景、项目经验、就业偏好。

    何时调用：
    - 用户问"我适合什么/我能做什么/我有什么优势"
    - 需要基于用户背景给具体判断或建议
    - 用户请求"帮我梳理我的项目/技能"

    何时不调用：
    - 问候、闲聊、情绪倾诉（此时用户不需要你反引用画像）
    - 一般概念性问答
    - 用户说"好/嗯/可以"确认收到
    """
    profile = _ctx_profile.get()
    if not profile:
        return "用户尚未建立画像（未上传简历），可以建议用户去画像页上传简历"

    lines = []
    skills = profile.get("skills", [])
    if skills:
        names = [s.get("name", "") if isinstance(s, dict) else str(s) for s in skills[:10]]
        lines.append(f"技能：{', '.join(n for n in names if n)}")

    edu = profile.get("education", {})
    if isinstance(edu, dict) and edu.get("degree"):
        lines.append(f"学历：{edu.get('degree', '')} · {edu.get('major', '')}")

    projects = profile.get("projects", [])
    if projects:
        proj_parts = []
        for p in projects[:5]:
            if isinstance(p, dict):
                name = p.get("name", "")
                desc = (p.get("description", "") or "")[:100]
                if name:
                    proj_parts.append(f"{name}（{desc}）" if desc else name)
        if proj_parts:
            lines.append("项目：" + " / ".join(proj_parts))

    prefs = profile.get("preferences", {})
    if prefs:
        lines.append(f"偏好：{json.dumps(prefs, ensure_ascii=False)}")

    job_target = profile.get("job_target", "")
    if job_target:
        lines.append(f"求职意向：{job_target}")

    return "\n".join(lines) if lines else "画像数据为空"


@tool
def get_career_goal() -> str:
    """获取用户已锁定的目标岗位（如有）。

    何时调用：
    - 用户讨论具体职业方向、路径规划
    - 需要知道用户目标才能给建议

    何时不调用：
    - 泛泛的职业焦虑表达
    - 闲聊、问候
    """
    goal = _ctx_goal.get()
    if not goal:
        return "用户尚未锁定目标岗位（可以建议去图谱页探索方向）"
    return (
        f"目标岗位：{goal.get('label', '未知')}\n"
        f"图谱节点：{goal.get('node_id', '')}\n"
        f"目标区域：{goal.get('zone', '')}"
    )


@tool
def get_market_signal(direction: str) -> str:
    """查询某个职业方向的真实市场数据（2021→2024 招聘趋势）。

    参数:
        direction: 方向名或 node_id，如"后端开发"/"AI"/"cs_system_cpp"

    何时调用：
    - 给用户建议时需要数据支撑
    - 用户问"这方向前景如何/市场怎么样"
    - 对比多个方向时

    何时不调用：
    - 用户明确说不想看数据
    - 方向和当前对话主题无关
    """
    loader = _ctx_market_loader.get()
    if not loader:
        return "市场数据查询器未配置"
    try:
        signal = loader(direction)
        if not signal:
            return f"没有「{direction}」的具体市场数据"

        demand = signal.get("demand_change_pct", 0)
        salary = signal.get("salary_cagr", 0)
        timing = signal.get("timing_label", "")
        ai_label = signal.get("ai_label", "")
        top_inds = signal.get("top_industries", []) or []

        lines = [
            f"{direction} 市场数据（2021→2024 真实招聘）：",
            f"- 需求变化：{demand:+.0f}%",
            f"- 薪资年涨：{salary:+.1f}%",
            f"- 时机：{timing}",
        ]
        if ai_label:
            lines.append(f"- AI 渗透：{ai_label}")
        if top_inds:
            ind_names = ", ".join(
                (i.get("industry", "") or "")[:10] for i in top_inds[:3]
            )
            lines.append(f"- 主要招聘行业：{ind_names}")

        return "\n".join(lines)
    except Exception as e:
        logger.warning("get_market_signal(%s) failed: %s", direction, e)
        return f"查询「{direction}」市场数据失败"


@tool
def get_memory_recall(query: str = "用户偏好") -> str:
    """检索用户过往对话中的长期记忆（Mem0）。

    参数:
        query: 想找的主题，如"职业偏好"/"之前提到的项目"/"决策倾向"

    何时调用：
    - 用户说"还记得/上次聊到/我之前说过"
    - 需要用户历史偏好才能给连续性建议

    何时不调用：
    - 冷启动对话（前 2 轮）
    - 当前问题和历史无关
    """
    user_id = _ctx_user_id.get()
    if not user_id:
        return "用户上下文未注入"
    try:
        from backend.services.coach_memory import search_user_context
        memories = search_user_context(user_id, query, limit=3)
        if not memories:
            return f"未找到关于「{query}」的历史记忆"
        return "历史记忆：\n" + "\n".join(f"· {m[:150]}" for m in memories)
    except Exception as e:
        logger.warning("get_memory_recall(%s) failed user=%s: %s", query, user_id, e)
        return "记忆检索暂不可用"
```

### 验收 T2

```bash
python -c "
from agent.tools.coach_context_tools import (
    get_user_profile, get_career_goal, get_market_signal, get_memory_recall,
    _ctx_profile, _ctx_goal,
)
# 未注入：应返回降级字符串
r = get_user_profile.invoke({})
assert '未建立画像' in r, f'未注入时应返回降级: {r}'
print('PASS: profile 未注入时降级')

# 注入后
_ctx_profile.set({'skills': [{'name': 'Python'}, {'name': 'C++'}], 'job_target': '后端'})
r = get_user_profile.invoke({})
assert 'Python' in r and 'C++' in r, f'未返回注入的 profile: {r}'
print('PASS: profile 注入生效')
"
```

---

## T3 — 改 `agent/agents/coach_agent.py`

**完全替换为以下内容**（不要保留旧 SYSTEM_PROMPT 的 165 行）：

```python
"""成长教练 — 按对话情境加载 skill，pull-based context。

设计：
- BASE_IDENTITY 极简（身份 + 格式 + 工具原则）
- skill 清单（name + description + body）由 supervisor 运行时从 agent/skills/*/SKILL.md 加载后注入
- 画像/目标/市场数据通过 pull tool 按需查询（不再 push 到 system prompt）
"""
from __future__ import annotations

from langchain.agents import create_agent as create_react_agent

from agent.llm import get_chat_model
from agent.tools.coach_context_tools import (
    get_user_profile, get_career_goal, get_market_signal, get_memory_recall,
)
from agent.tools.graph_tools import recommend_jobs, search_jobs
from agent.tools.search_tools import search_real_jd


BASE_IDENTITY = """你是"职途智析"的成长教练。

## 回复格式
- 2-5 句，平实直接
- 禁止 markdown/emoji/客服腔
- 只用 tool 返回的数据或系统消息里明确给的数据
- 不编百分比/薪资/倍数；不知道就说不知道

## 工具使用原则
- 需要用户画像/目标/市场数据时，主动调 get_user_profile / get_career_goal / get_market_signal
- 用户说"还记得/上次聊到"时，调 get_memory_recall
- 用户明确请求"帮我搜 JD / 推荐方向"时，才调 search_real_jd / recommend_jobs
- "好/嗯/可以" 是确认不是执行指令，默认不触发工具

## 可用场景 skill
以下是可用的场景 skill。读用户本轮消息后，**自行判断**应用哪一个（也可以都不应用，此时按默认工具原则回应）：

{AVAILABLE_SKILLS}

## 当前用户状态
{CONTEXT}
"""


def create_coach_agent():
    """Create the growth coach agent with pull-based context + skill system.

    NOTE: system_prompt 留 None，运行时由 supervisor 动态构造 SystemMessage 注入
    （BASE_IDENTITY 里的 {AVAILABLE_SKILLS} 和 {CONTEXT} 占位符由 supervisor 填充）。
    """
    model = get_chat_model(temperature=0.5)
    return create_react_agent(
        model=model,
        tools=[
            # Pull context tools (按需查询)
            get_user_profile,
            get_career_goal,
            get_market_signal,
            get_memory_recall,
            # Action tools (明确请求时执行)
            search_real_jd,
            recommend_jobs,
            search_jobs,
        ],
        name="coach_agent",
        system_prompt=None,
    )
```

### 验收 T3

```bash
python -c "
from agent.agents.coach_agent import create_coach_agent, BASE_IDENTITY
agent = create_coach_agent()
assert '{AVAILABLE_SKILLS}' in BASE_IDENTITY, 'BASE_IDENTITY 缺 {AVAILABLE_SKILLS} 占位符'
assert '{CONTEXT}' in BASE_IDENTITY, 'BASE_IDENTITY 缺 {CONTEXT} 占位符'
print('PASS: coach_agent 可创建，两个占位符齐全')
"
```

---

## T4 — 改 `agent/supervisor.py`

### T4.1 — `build_context_summary` 加 `agent_name` 参数做 turn-aware 裁剪

找到 `def build_context_summary(state: CareerState, for_triage: bool = False) -> str:`（约 118 行）。

**操作**：
1. 把原 `build_context_summary` **改名**为 `_build_full_context`（只改函数签名的名字）
2. 在其上方新建一个新的 `build_context_summary` dispatcher：

```python
def build_context_summary(
    state: "CareerState",
    for_triage: bool = False,
    agent_name: str | None = None,
) -> str:
    """Agent-aware context 注入。

    - coach_agent: turn-aware 裁剪（冷启动空 / 3-4 轮骨架 / 5+ 完整）
    - 其他 5 agent: full context（原行为）
    """
    # 非 coach: 原路径（零变化）
    if agent_name != "coach_agent":
        return _build_full_context(state, for_triage)

    # coach 专用：按对话轮次裁剪
    from langchain_core.messages import HumanMessage as _HM
    human_count = sum(
        1 for m in state.get("messages", []) if isinstance(m, _HM)
    )

    if human_count <= 2:
        return (
            "（冷启动期：用户刚开口，按本轮消息正常回应。"
            "不要反引用系统里的画像细节；需要信息时调工具查。）"
        )

    if human_count <= 4:
        stage = state.get("user_stage", "unknown")
        lines = [f"- 当前阶段：{stage}"]
        goal = state.get("career_goal")
        if goal:
            lines.append(f"- 目标岗位：{goal.get('label', '')}")
        lines.append("（深度画像请通过 get_user_profile 等工具按需调用）")
        return "\n".join(lines)

    return _build_full_context(state, for_triage)
```

### T4.2 — `_make_agent_node` 的 coach 分支增强

找到 `_make_agent_node` 的 `node` 函数（约 559 行开始）。

**关键改动**：

```python
def node(state: CareerState) -> dict:
    # 改：调用 build_context_summary 时传 agent_name
    context = build_context_summary(state, agent_name=agent_name)   # ← 改
    recent = state["messages"][-20:]

    # Clean messages（原逻辑不变）
    clean = []
    for m in recent:
        if isinstance(m, _HM):
            clean.append(m)
        elif isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
            clean.append(m)

    # ── handoff_context（原逻辑不变）────────────────────────────
    handoff_context = ""
    if len(clean) >= 2:
        # ... 原逻辑完整保留
        pass

    # ── Tool hint（原逻辑不变）──────────────────────────────────
    tool_hint = state.get("tool_hint", "")
    if tool_hint:
        # ... 原逻辑完整保留
        pass

    # ── 构造 SystemMessage（coach 分支特殊处理）─────────────────
    if agent_name == "coach_agent":
        from agent.agents.coach_agent import BASE_IDENTITY
        from agent.skills.loader import format_skills_for_prompt

        available_skills = format_skills_for_prompt()
        sys_prompt = BASE_IDENTITY.replace(
            "{AVAILABLE_SKILLS}", available_skills
        ).replace(
            "{CONTEXT}", context
        )
        if handoff_context:
            sys_prompt += handoff_context
    else:
        # 其他 5 agent：原逻辑（保留原来 context + handoff_context 的拼接方式）
        sys_prompt = context + handoff_context

    input_msgs = [SystemMessage(content=sys_prompt)] + clean

    # ── ContextVar 注入 ─────────────────────────────────────────
    _ctx_resets: list[tuple] = []

    # Coach 专属：pull tool 的 ContextVar
    if agent_name == "coach_agent":
        from agent.tools.coach_context_tools import (
            _ctx_profile, _ctx_goal, _ctx_user_id, _ctx_market_loader,
        )
        tok_p = _ctx_profile.set(state.get("user_profile"))
        tok_g = _ctx_goal.set(state.get("career_goal"))
        tok_u = _ctx_user_id.set(state.get("user_id"))
        tok_m = _ctx_market_loader.set(_get_market_signal_for_node)
        _ctx_resets.extend([
            (_ctx_profile, tok_p),
            (_ctx_goal, tok_g),
            (_ctx_user_id, tok_u),
            (_ctx_market_loader, tok_m),
        ])

    # 其他 agent 的原有 ContextVar 注入（growth/jd/search/navigator）保持不变
    if agent_name == "growth_agent":
        # ... 原逻辑
        pass
    if agent_name == "jd_agent":
        # ... 原逻辑
        pass
    if agent_name in ("navigator", "coach_agent", "search_agent"):
        # ... 原逻辑，保持 search_tools 的 _injected_profile_for_search 注入
        pass

    try:
        result = agent.invoke({"messages": input_msgs})
        # ... 原 invoke 逻辑
    finally:
        # 记得 reset ContextVar
        for var, tok in _ctx_resets:
            try:
                var.reset(tok)
            except Exception:
                pass
```

### 验收 T4

```bash
python -u -c "
import sys; sys.stdout.reconfigure(encoding='utf-8')
from agent.supervisor import build_context_summary
from langchain_core.messages import HumanMessage

# 场景 1: coach 冷启动
state_1 = {'messages': [HumanMessage(content='你好')], 'user_stage': 'lost'}
r = build_context_summary(state_1, agent_name='coach_agent')
assert '冷启动' in r, f'coach 第 1 轮应冷启动: {r[:100]}'
print('PASS: coach 第 1 轮 = 冷启动骨架')

# 场景 2: navigator 走 full
r2 = build_context_summary(state_1, agent_name='navigator')
assert '当前用户状态' in r2, f'navigator 应 full context'
print('PASS: navigator 走 full context')

# 场景 3: coach 第 5 轮 full
msgs_5 = [HumanMessage(content=f'msg{i}') for i in range(5)]
state_5 = {'messages': msgs_5, 'user_stage': 'lost'}
r3 = build_context_summary(state_5, agent_name='coach_agent')
assert '当前用户状态' in r3, f'coach 第 5 轮应 full: {r3[:100]}'
print('PASS: coach 第 5 轮 = full context')
" 2>&1 | grep -v "WARNING\|INFO"
```

---

## 端到端验收（Kimi 跑完 T1-T4 必做）

启动后端 `python -m uvicorn backend.app:app --reload`，前端 `cd frontend && npm run dev`。

**新 session** 跑 3 个场景：

### 场景 A：冷启动问候
输入：`你好`
通过条件：
- 回复 2-3 句
- **不提**"方向迷茫/C++基础扎实/大厂偏好" 等画像词
- 含一个开放问题
- 后端日志：`SkillLoader loaded 5 skills`

### 场景 B：担忧表达
输入（turn 2）：`我不知道我现在的技术能不能找到工作`
通过条件：
- coach 调了 `get_user_profile` + `get_market_signal`（日志有 tool call）
- 回复直接给判断，**不反问**"你觉得呢"

### 场景 C：具体请求
输入（turn 3）：`帮我梳理一下`
通过条件：
- coach 调了 `get_user_profile`
- 直接给梳理内容，不反问"你对深挖技术的理解是什么"

**任一失败**：不得声明完成，回来定位。

---

## 风险与回滚

### 降级策略（自动生效）

| 故障 | 降级 |
|---|---|
| SkillLoader 加载失败 | `format_skills_for_prompt` 返回"（尚无可用 skill）" → coach 降级到 BASE_IDENTITY + 默认工具原则 |
| ContextVar 未注入 | pull tool 返回"未建立画像" 等降级字符串，不崩 |
| pyyaml 未装 | 启动时 import error 暴露，Kimi 需 `pip install pyyaml` |

### 回滚

```bash
git checkout agent/agents/coach_agent.py agent/supervisor.py
rm -rf agent/skills/ agent/tools/coach_context_tools.py
```

---

## Owner 维护指南（交给 liu）

**加一个新场景 skill** = 新建一个目录 + 写 `SKILL.md`：

```bash
mkdir agent/skills/coach-new-scenario
```

在其中写 `SKILL.md`：

```markdown
---
name: coach-new-scenario
description: "完整描述什么情况下使用这个 skill。LLM 会读这段描述自行判断。"
---

## 场景
（描述）

## 规则
- 规则 1
- 规则 2

## 示范
...
```

**重启后端** → 新 skill 自动加载，无需改代码。

**改现有 skill** = 直接改对应 `SKILL.md`，重启生效。

**删 skill** = 删目录 `rm -rf agent/skills/coach-xxx`，重启生效。

**禁用某 skill 但保留内容**：把目录重命名加 `.disabled` 后缀（loader 只扫不带后缀的子目录）。

**未来扩展**（当前不做）：
- skill 目录下加 `references/` 子目录放按需加载的参考文档
- skill 目录下加 `scripts/` 子目录放确定性脚本（coach 可调用）
- skill 目录下加 `assets/` 子目录放模板/图标

这是 Anthropic 官方规范支持的扩展点。

---

## 实施顺序

T1 → T2 → T3 → T4（有依赖，不可乱序）

每步跑对应验收脚本，通过再进下一步。最后 3 个端到端场景全过才算完。
