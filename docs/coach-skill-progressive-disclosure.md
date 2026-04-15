# Coach Skill 系统 · Progressive Disclosure 升级

交付人：Kimi
审查 / 文档：Claude
日期：2026-04-15

---

## 一、背景与目标

### 背景
当前 coach skill 架构是「全量 push」—— `format_skills_for_prompt()` 把全部 9 个 SKILL.md 的 name + description + body 拼成 ~7700 字符（~1930 tokens）塞进 SystemMessage，每请求每轮都付这个代价。当扩到 10+ skill、总量破 8000 chars / 2000 tokens 后，每次对话会白烧可观 token，且 base cost 随 skill 数线性增长。

### 目标
升级为 **Progressive Disclosure**（Pessini 2026-02 Medium 文章的标准实现）：
1. SystemMessage 里只塞 catalog（name + description，~500 tokens 总量，**与 skill 数量几乎解耦**）
2. LLM 根据本轮消息自行判断需要哪个 skill → 调 `load_skill(skill_name)` tool 动态加载该 skill 的完整 body
3. 简单问候场景不加载任何 skill body，0 额外成本

### 收益（预估）

| 场景 | 当前 tokens | 升级后 tokens | 节省 |
|---|---|---|---|
| "你好"（纯问候） | 1930 | ~500 | **74%** |
| 单场景（如 resume-review） | 1930 | ~500 + 250 = 750 | **61%** |
| 多场景联动 | 1930 | ~500 + 500 = 1000 | **48%** |
| 扩到 20 skill 时的 base cost | ~4300 | ~800 | **81%** |

---

## 二、现状扫描（Kimi 必读）

### 2.1 当前涉及文件（改动范围）

| 文件 | 当前职责 | 改动性质 |
|---|---|---|
| `agent/skills/loader.py` | `SkillLoader` + `format_skills_for_prompt()` | **重写**（拆出 catalog / full 两条路径） |
| `agent/tools/coach_context_tools.py` | 4 个 pull tool（get_user_profile 等） | **新增** `load_skill` tool（第 5 个） |
| `agent/agents/coach_agent.py` | `BASE_IDENTITY` 含 `{AVAILABLE_SKILLS}` 占位符 | **微改**（占位符换名 + tools list 加一项） |
| `agent/supervisor.py` | coach 分支用 `format_skills_for_prompt()` | **微改**（换函数名） |
| `agent/skills/__init__.py` | export `format_skills_for_prompt` | **更新**（改 export 名） |
| `test_e2e_coach_skill.py` | E2E 测试，用 `format_skills_for_prompt` | **更新**（改引用 + 加 load_skill 测试） |

### 2.2 现状依赖点（Kimi 不要漏改）

- `agent/supervisor.py:644,646` — coach 分支的 skill 注入
- `agent/skills/__init__.py:6` — 模块 export
- `test_e2e_coach_skill.py:14,55` — 测试引用

**无其他外部依赖**。清理边界干净。

### 2.3 现有 9 个 skill（Kimi 不需要改这些文件）

```
agent/skills/
├── coach-concern-direct/SKILL.md
├── coach-confirmation/SKILL.md
├── coach-decision-socratic/SKILL.md
├── coach-emotional-support/SKILL.md
├── coach-greeting/SKILL.md
├── coach-market-signal/SKILL.md
├── coach-project-planning/SKILL.md
├── coach-request-deliver/SKILL.md
└── coach-resume-review/SKILL.md
```

每个 SKILL.md 格式保持不变（`---` frontmatter + body），本次升级只改 loader / agent / tool 层。

---

## 三、升级后架构（顶层设计）

```
          ┌─────────────────────────────────────┐
          │ SystemMessage（每请求）              │
          │                                     │
          │  BASE_IDENTITY                      │
          │  + {SKILL_CATALOG}  ← 轻量 catalog  │
          │    = 9 条 "name: description"       │
          │    ≈ 500 tokens                     │
          │  + {CONTEXT}                        │
          └─────────────────────────────────────┘
                       ↓
              LLM 读 catalog + 本轮消息
                       ↓
         判断需要哪个 skill？
           ├─ 不需要 → 直接回复（不 load）
           └─ 需要 → 调 load_skill(skill_name) tool
                        ↓
              SkillLoader.load_full(name)
                        ↓
               返回完整 SKILL.md body
                        ↓
              LLM 按 body 规则回复
```

**关键解耦原则**：
1. `load_skill` tool 只负责调用 `SkillLoader.load_full()`，不直接读文件
2. `SkillLoader` 启动时 eager load catalog（~500 tokens，开销小），body 改成 lazy + memoize
3. `load_skill` 的 docstring **动态注入** 9 个有效 skill 名，防止 LLM 调错名（Pessini 标准做法）
4. 不暴露 `format_skills_for_prompt()` — 删除，不保留兼容层（避免误用）

---

## 四、任务拆解（T1 → T6）

### T1：重写 `agent/skills/loader.py`

**目标**：拆出 `format_catalog_for_prompt()`（轻量）和 `load_full(name)`（按需），删除 `format_skills_for_prompt()`。

**完整新代码**：

```python
"""Skill loader — Progressive Disclosure 版本。

职责拆分：
  - scan / catalog: 启动时加载 name + description，~500 tokens，永久驻留
  - full: 按需加载 body，首次读文件 + memoize

遵循 Anthropic Skill 规范：目录 + SKILL.md 结构。
LLM 读 catalog 后调 load_skill(name) tool 拿 full body，不做硬编码预匹配。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SkillCatalogEntry:
    """Lightweight metadata（只含 name + description + 目录路径）。"""
    name: str
    description: str
    path: Path  # skill 目录路径（load_full 用）


class SkillLoader:
    """Skill 存储层。启动加载 catalog，body 按需 + cache。"""

    _catalog: list[SkillCatalogEntry] = []
    _body_cache: dict[str, str] = {}
    _loaded: bool = False

    @classmethod
    def load_catalog(cls, skills_dir: Optional[Path] = None) -> None:
        """扫描所有子目录，只解析 frontmatter（快速启动）。"""
        if skills_dir is None:
            skills_dir = Path(__file__).parent

        catalog: list[SkillCatalogEntry] = []
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
                catalog.append(SkillCatalogEntry(
                    name=frontmatter.get("name", sub_dir.name),
                    description=frontmatter.get("description", "").strip(),
                    path=sub_dir,
                ))
            except Exception as e:
                logger.warning("Failed to scan skill %s: %s", sub_dir.name, e)

        cls._catalog = catalog
        cls._body_cache = {}
        cls._loaded = True
        logger.info("SkillLoader catalog loaded: %d skills %s",
                    len(catalog), [s.name for s in catalog])

    @classmethod
    def all_catalog(cls) -> list[SkillCatalogEntry]:
        if not cls._loaded:
            cls.load_catalog()
        return cls._catalog

    @classmethod
    def skill_names(cls) -> list[str]:
        """用于 load_skill tool 的 docstring 动态注入。"""
        return [s.name for s in cls.all_catalog()]

    @classmethod
    def load_full(cls, name: str) -> Optional[str]:
        """按需加载 skill 的完整 body，memoize。

        返回 None = skill 不存在。
        """
        if name in cls._body_cache:
            return cls._body_cache[name]

        entry = next((s for s in cls.all_catalog() if s.name == name), None)
        if entry is None:
            logger.warning("load_full: unknown skill %r", name)
            return None

        skill_file = entry.path / "SKILL.md"
        try:
            text = skill_file.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else ""
            cls._body_cache[name] = body
            return body
        except Exception as e:
            logger.warning("load_full(%s) failed: %s", name, e)
            return None


def format_catalog_for_prompt() -> str:
    """把 catalog（name + description）拼成轻量 prompt 片段。

    LLM 读 catalog 后判断需要哪个 skill，调 load_skill(name) 按需加载 body。
    """
    catalog = SkillLoader.all_catalog()
    if not catalog:
        return "（尚无可用 skill）"

    lines = ["## 可用场景 skill（读完本轮消息后判断是否需要其中某个，需要则调 `load_skill` 工具加载详细规则）", ""]
    for s in catalog:
        lines.append(f"- **{s.name}**: {s.description}")
    return "\n".join(lines)
```

**清理清单（T1 必删）**：
- ❌ 删除 `format_skills_for_prompt()`
- ❌ 删除旧 `Skill` dataclass（被 `SkillCatalogEntry` 替代）
- ❌ 删除 `load_all()`（被 `load_catalog()` 替代）
- ❌ 删除 `all_skills()`（被 `all_catalog()` 替代）

**T1 验证脚本**：

```python
python -c "
from agent.skills.loader import SkillLoader, format_catalog_for_prompt
SkillLoader.load_catalog()
catalog = SkillLoader.all_catalog()
print(f'catalog entries: {len(catalog)}')
for c in catalog:
    print(f'  - {c.name}: desc={len(c.description)}ch')

prompt = format_catalog_for_prompt()
print(f'catalog prompt = {len(prompt)} chars (~{len(prompt)//4} tokens)')
assert len(catalog) == 9
assert 'coach-greeting' in SkillLoader.skill_names()

# 验证 lazy load + memoize
body1 = SkillLoader.load_full('coach-greeting')
body2 = SkillLoader.load_full('coach-greeting')  # 应命中 cache
assert body1 == body2
assert len(body1) > 100
assert SkillLoader.load_full('nonexistent-skill') is None
print('[T1] PASS — catalog ~', len(prompt), 'chars; load_full works + cached')
"
```

---

### T2：新增 `load_skill` tool（`agent/tools/coach_context_tools.py`）

**目标**：新增第 5 个 pull tool，LLM 调它来动态加载某个 skill 的完整 body。使用 **dynamic docstring** 注入有效 skill 名，防止 LLM 调错名。

**改动点**：在现有文件**追加**以下内容（保留原 4 个 tool 不动）：

```python
# ── load_skill tool (Progressive Disclosure) ──────────────────────────────
# 放在文件末尾，其他 4 个 tool 之后

@tool
def load_skill(skill_name: str) -> str:
    """（此处 docstring 会在模块加载后被动态替换，包含真实的可用 skill 名清单）"""
    from agent.skills.loader import SkillLoader
    body = SkillLoader.load_full(skill_name)
    if body is None:
        return f"未找到 skill「{skill_name}」。可用 skill: {', '.join(SkillLoader.skill_names())}"
    return body


# Dynamic docstring 注入（模块加载时执行）
def _inject_load_skill_docstring():
    """启动时把真实 skill 名清单 + 使用说明写进 load_skill.description。

    LangChain @tool 装饰后的 description 就是 docstring。
    此处修改 load_skill.description 确保 LLM 看到的工具说明永远和实际 skill 列表同步。
    """
    try:
        from agent.skills.loader import SkillLoader
        names = SkillLoader.skill_names()
        doc = (
            "加载指定 coach skill 的完整规则（场景/规则/示范/反面教材）。\n\n"
            "使用时机：你读完本轮用户消息 + catalog（SystemMessage 里）后，"
            "判断本轮应用某个 skill 时，调本工具拿该 skill 的完整规则再回复。\n\n"
            "参数:\n"
            f"    skill_name: 必须是以下 {len(names)} 个之一 — {', '.join(names)}\n\n"
            "何时调用:\n"
            "- catalog 里某个 skill 描述匹配当前用户消息场景\n"
            "- 当前任务需要该 skill 的具体规则指引\n\n"
            "何时不调用:\n"
            "- 纯问候/闲聊（greeting skill 如果本身也不需要，就直接回）\n"
            "- 用户确认词（好/嗯/可以），直接 1-2 句推进即可\n"
            "- 你已经清楚该怎么回复，且没有 skill 明显匹配"
        )
        load_skill.description = doc
    except Exception as exc:
        logger.warning("load_skill docstring injection skipped: %s", exc)


_inject_load_skill_docstring()
```

**T2 验证脚本**：

```python
python -c "
from agent.tools.coach_context_tools import load_skill, get_user_profile, get_career_goal, get_market_signal, get_memory_recall
from langchain_core.tools import BaseTool

# 5 个 tool 都是 BaseTool
for t in [get_user_profile, get_career_goal, get_market_signal, get_memory_recall, load_skill]:
    assert isinstance(t, BaseTool)

# load_skill 的 description 含全部 9 个 skill 名
desc = load_skill.description
print(f'load_skill.description 长度: {len(desc)}')
print(desc[:500])
assert 'coach-greeting' in desc
assert 'coach-emotional-support' in desc
assert 'coach-comparison-detox' in desc or len([n for n in desc.split() if 'coach-' in n]) >= 9

# invoke test
out = load_skill.invoke({'skill_name': 'coach-greeting'})
assert '问候' in out or '寒暄' in out or len(out) > 100
print('[T2] PASS — dynamic docstring + invoke works')
"
```

---

### T3：微改 `agent/agents/coach_agent.py`

**目标**：
1. `BASE_IDENTITY` 里的占位符 `{AVAILABLE_SKILLS}` 改为 `{SKILL_CATALOG}`
2. 提示语从"以下是可用的场景 skill，自行判断"改为"以下是 catalog，需要时调 load_skill 加载规则"
3. `create_coach_agent()` 的 tools list 里加上 `load_skill`

**改动 diff**：

```python
# BASE_IDENTITY —— 改第 34-38 行那段

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

## 可用 skill catalog
{SKILL_CATALOG}

读完用户本轮消息后：
1. 如果某个 skill 的描述明显匹配 → 调 `load_skill(skill_name)` 工具加载完整规则，按规则回复
2. 如果多个匹配 → 选最具体的一个（比如"你好，AI 前景咋样" 选 market-signal 而非 greeting）
3. 如果都不明显匹配 → 按上面"工具使用原则"和"回复格式"默认回应，不强行套 skill

## 当前用户状态
{CONTEXT}
"""

# create_coach_agent —— tools list 加 load_skill

def create_coach_agent():
    """Create the growth coach agent with pull-based context + progressive skill loading.

    NOTE: system_prompt 留 None，运行时由 supervisor 动态构造 SystemMessage 注入
    （BASE_IDENTITY 里的 {SKILL_CATALOG} 和 {CONTEXT} 占位符由 supervisor 填充）。
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
            # Skill loading tool (Progressive Disclosure)
            load_skill,
            # Action tools (明确请求时执行)
            search_real_jd,
            recommend_jobs,
            search_jobs,
        ],
        name="coach_agent",
        system_prompt=None,
    )
```

**import 更新**（文件头部）：

```python
from agent.tools.coach_context_tools import (
    get_user_profile, get_career_goal, get_market_signal, get_memory_recall,
    load_skill,  # 新增
)
```

**T3 验证脚本**：

```python
python -c "
from agent.agents.coach_agent import create_coach_agent, BASE_IDENTITY
assert '{SKILL_CATALOG}' in BASE_IDENTITY
assert '{CONTEXT}' in BASE_IDENTITY
assert '{AVAILABLE_SKILLS}' not in BASE_IDENTITY  # 旧占位符必须已删
assert 'load_skill' in BASE_IDENTITY  # 使用说明里提到 load_skill

agent = create_coach_agent()
print(f'[T3] coach agent built: {type(agent).__name__}')
"
```

---

### T4：微改 `agent/supervisor.py`

**目标**：coach 分支从 `format_skills_for_prompt()` 换成 `format_catalog_for_prompt()`，占位符从 `{AVAILABLE_SKILLS}` 换到 `{SKILL_CATALOG}`。

**改动位置**：`supervisor.py:642-653` 的 coach 分支

**改后代码**：

```python
# ── 构造 SystemMessage（coach 分支特殊处理）─────────────────
if agent_name == "coach_agent":
    from agent.agents.coach_agent import BASE_IDENTITY
    from agent.skills.loader import format_catalog_for_prompt

    skill_catalog = format_catalog_for_prompt()
    sys_prompt = BASE_IDENTITY.replace(
        "{SKILL_CATALOG}", skill_catalog
    ).replace(
        "{CONTEXT}", context
    )
    if handoff_context:
        sys_prompt += handoff_context
else:
    sys_prompt = context + handoff_context
```

**T4 验证脚本**：

```python
python -c "
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from langchain_core.messages import HumanMessage
from agent.supervisor import build_context_summary
from agent.agents.coach_agent import BASE_IDENTITY
from agent.skills.loader import format_catalog_for_prompt

# 模拟 coach 拿到的完整 SystemMessage
ctx = build_context_summary(
    {'messages': [HumanMessage(content='你好')], 'user_profile': {}, 'user_stage': 'lost'},
    agent_name='coach_agent'
)
prompt = BASE_IDENTITY.replace('{SKILL_CATALOG}', format_catalog_for_prompt()).replace('{CONTEXT}', ctx)

print(f'coach SystemMessage 冷启动长度: {len(prompt)} chars (~{len(prompt)//4} tokens)')
# 目标: < 2500 chars / 625 tokens（升级前冷启动约 8000+ chars / 2000+ tokens）
assert len(prompt) < 3500, f'catalog 版 prompt 仍过大: {len(prompt)}'
print('[T4] PASS — SystemMessage 冷启动 <', len(prompt), 'chars')
"
```

---

### T5：更新 `agent/skills/__init__.py` + `test_e2e_coach_skill.py`

**`agent/skills/__init__.py`** — 改 export：

```python
"""Coach skill system — Progressive Disclosure."""
from agent.skills.loader import (  # noqa: F401
    SkillLoader,
    SkillCatalogEntry,
    format_catalog_for_prompt,
)
```

**`test_e2e_coach_skill.py`** — 改引用（line 14 + 55 附近）：

```python
# 原
from agent.skills.loader import format_skills_for_prompt
# ...
skills = format_skills_for_prompt()

# 改为
from agent.skills.loader import format_catalog_for_prompt, SkillLoader
# ...
skills_catalog = format_catalog_for_prompt()
# 如果原断言依赖 full body，改成对 SkillLoader.load_full(name) 的调用
```

---

### T6：E2E 回归 + 容量验证

**完整验证脚本**（Kimi 完成 T1-T5 后必跑，必全绿）：

```python
python -c "
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from agent.skills.loader import SkillLoader, format_catalog_for_prompt
from agent.tools.coach_context_tools import load_skill
from agent.agents.coach_agent import BASE_IDENTITY, create_coach_agent
from agent.supervisor import build_context_summary

# ── 1. Catalog 加载 ──
SkillLoader.load_catalog()
catalog = SkillLoader.all_catalog()
assert len(catalog) >= 9, f'expected >=9 catalog entries, got {len(catalog)}'
print(f'[1] catalog={len(catalog)} skills')

# ── 2. Catalog prompt 轻量 ──
cp = format_catalog_for_prompt()
assert len(cp) < 3000, f'catalog should be lightweight, got {len(cp)} chars'
print(f'[2] catalog prompt={len(cp)} chars (~{len(cp)//4} tokens)')

# ── 3. load_skill tool 可用 + dynamic docstring ──
assert isinstance(load_skill, BaseTool)
assert 'coach-greeting' in load_skill.description
body = load_skill.invoke({'skill_name': 'coach-greeting'})
assert len(body) > 100
print(f'[3] load_skill(coach-greeting) returned {len(body)} chars')

# ── 4. 无效 skill 名保护 ──
bad = load_skill.invoke({'skill_name': 'nonexistent'})
assert '未找到' in bad and 'coach-' in bad  # error 消息包含有效清单
print(f'[4] invalid skill handled gracefully')

# ── 5. Cache 生效 ──
b1 = SkillLoader.load_full('coach-greeting')
b2 = SkillLoader.load_full('coach-greeting')
assert b1 is b2 or b1 == b2
print(f'[5] cache works')

# ── 6. SystemMessage 冷启动容量 ──
state = {'messages': [HumanMessage(content='你好')], 'user_profile': {'skills': [{'name': 'C++'}]}, 'user_stage': 'lost'}
ctx = build_context_summary(state, agent_name='coach_agent')
sys_prompt = BASE_IDENTITY.replace('{SKILL_CATALOG}', cp).replace('{CONTEXT}', ctx)
assert 'C++' not in sys_prompt  # 冷启动画像不泄漏（已有行为保留）
print(f'[6] cold-start SystemMessage = {len(sys_prompt)} chars')
assert len(sys_prompt) < 3500, f'cold-start should be <3500 chars, got {len(sys_prompt)}'

# ── 7. coach agent 构造 ──
agent = create_coach_agent()
print(f'[7] coach agent type: {type(agent).__name__}')

# ── 8. 占位符清理（旧名不能残留）──
assert '{AVAILABLE_SKILLS}' not in BASE_IDENTITY
print('[8] old placeholder cleared')

# ── 9. format_skills_for_prompt 已删 ──
try:
    from agent.skills.loader import format_skills_for_prompt
    assert False, 'format_skills_for_prompt should be removed'
except ImportError:
    print('[9] old format_skills_for_prompt removed')

print()
print('=== ALL 9 CHECKS PASS ===')
"
```

---

## 五、解耦原则（Kimi 严格遵守）

1. **`load_skill` tool 只调 `SkillLoader.load_full()`，不直接读文件**。所有文件 IO 封装在 loader 层。

2. **`SkillLoader` 保持无状态单例**（class-level cache）。不要引入 Redis / LRU 等过度工程 — 9 个 skill 的 body 全 memoize 在进程内存 < 100KB。

3. **Dynamic docstring 注入必须在模块加载时执行一次**（`_inject_load_skill_docstring()` 在 import 时跑），不要运行时反复刷新。如果 skill 文件热加载场景出现（未来），再做显式 refresh API。

4. **不保留兼容层**：`format_skills_for_prompt` 直接删除，不做 deprecation 过渡。老代码里已找到的 3 处引用（supervisor / __init__ / test）同步改完，没有其他外部依赖。

5. **BASE_IDENTITY 的占位符只允许 `{SKILL_CATALOG}` 和 `{CONTEXT}`**。如未来再加占位符需先同步 supervisor.py 的 replace 逻辑。

6. **`load_skill` 错误提示返回有效 skill 名清单**（T2 代码已含），让 LLM 重试时有修正方向，不要只返回 "not found"。

---

## 六、E2E 场景验收（完成 T1-T6 后用户验收）

| 场景 | 用户消息 | 预期行为 |
|---|---|---|
| A · 纯问候 | "你好" | LLM 读 catalog 判断匹配 greeting，**可能**调 `load_skill(coach-greeting)` 拿规则，也可能直接按 BASE_IDENTITY 回 |
| B · 情感崩溃 | "撑不下去了，室友都拿 offer 了" | LLM 必调 `load_skill(coach-emotional-support)`，按"共情+落地+低门槛问题"回复 |
| C · 具体请求 | "帮我看看简历" | LLM 必调 `load_skill(coach-resume-review)` + `get_user_profile`，按面试官视角 3 问题格式回 |
| D · 数据问题 | "AI 方向前景咋样" | LLM 必调 `load_skill(coach-market-signal)` + `get_market_signal('AI')`，基于数据回 |
| E · 确认词 | "好" / "嗯" | LLM 必调 `load_skill(coach-confirmation)` 或直接按规则回 1-2 句推进，**禁止**误调 search_real_jd |

**Token 实测（用户侧，通过后端日志确认）**：
- 冷启动 `/api/chat` 请求，SystemMessage tokens 应 **< 700 tokens**
- 升级前同场景 **~2000 tokens**
- **节省 ≥ 60%** 才算达成目标

---

## 七、交付 checklist（Kimi 自查）

完成所有以下项目后再交付：

- [ ] T1 — `loader.py` 重写完成，验证脚本 PASS
- [ ] T2 — `load_skill` tool + dynamic docstring 注入，验证脚本 PASS
- [ ] T3 — `coach_agent.py` 占位符 + tools list 更新，验证脚本 PASS
- [ ] T4 — `supervisor.py` 换函数调用，验证脚本 PASS
- [ ] T5 — `__init__.py` export 更新、`test_e2e_coach_skill.py` 引用更新
- [ ] T6 — 9 项 E2E 检查全部绿
- [ ] **清理确认**：`format_skills_for_prompt` / `load_all` / `all_skills` / 旧 `Skill` dataclass / `{AVAILABLE_SKILLS}` 占位符全部移除
- [ ] **无新增依赖** — 不要引入新 package（yaml 已在）
- [ ] **日志完整** — `SkillLoader.load_catalog()` 启动日志、`load_skill` 的 warning 日志都在

---

## 八、未来扩展点（本次不做，留参考）

1. **按 agent 过滤 skill**：如果之后 navigator / growth 也做 skill 化，在 `SkillCatalogEntry` 加 `agents: list[str]` 字段，`format_catalog_for_prompt(agent_name)` 过滤
2. **Skill 热加载**：加 `SkillLoader.reload()` API，用文件 mtime 判断是否需重读 catalog
3. **Skill 使用频次日志**：在 `load_skill` tool 里埋点，统计哪些 skill 最常被加载（帮 owner 判断砍哪些 skill）

---

## 附录 · 参考资料

- [Pessini 2026-02 · Stop Stuffing Your System Prompt: Build Scalable Agent Skills in LangGraph](https://pessini.medium.com/stop-stuffing-your-system-prompt-build-scalable-agent-skills-in-langgraph-a9856378e8f6)
- [Anthropic 官方 skills 仓库](https://github.com/anthropics/skills)
- 本仓库前序迁移文档：`docs/coach-skill-system-implementation.md`
