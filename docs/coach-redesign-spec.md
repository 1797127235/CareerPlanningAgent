# 成长教练重构规范（v2 · 范式重构版）

> **本文 supersede `docs/coach-memo-v2-spec.md`。**
>
> **v1 → v2 核心变更**：
> 1. **停止自研 coach_memo**，改用 **Mem0**（mem0ai/mem0，53k stars，YC S24）作为记忆层
> 2. **新增 M0 最高优先级任务**：Coach Prompt 范式重构为 **GROW 模型 + 苏格拉底式提问**
> 3. 从根因解决"教练急于给建议/自作主张调工具"的系统性问题，不再打补丁
>
> **项目根目录**：`C:\Users\liu\Desktop\CareerPlanningAgent`
>
> **启动命令**：
> - 后端：`python -m uvicorn backend.app:app --reload`
> - 前端：`cd frontend && npm run dev`
>
> **实施者**：Kimi / 其他实施 Agent。所有代码片段可直接复用。

---

## 一、为什么要重构（必读背景）

### 1.1 现状的根因问题

现有 `coach_agent` 是"**给建议型** agent"——表现为：
- 用户第一句话就给 8-15 句方向分析（`navigator_agent.py` 的学长腔）
- 用户说"好"就被理解成"执行指令"，自动调 `search_real_jd` 搜岗位
- 对话没有结构（每轮各说各的，不围绕目标推进）
- 记忆是 500 字自由文本，LLM 每次重写容易丢信息

**根因是 prompt 范式错了**——我们把教练当"顾问"（急于给答案）在写 prompt，而成熟教练产品（Khanmigo、ICF 教练体系）都是"**引导型**"（用问题推进，让用户自己想明白）。

### 1.2 借鉴的成熟方案

| 层 | 抄谁 | 抄什么 |
|---|---|---|
| **方法论层** | ICF 教练认证体系的 **GROW 模型** | 对话有结构：Goal → Reality → Options → Will |
| **交互范式** | **Khanmigo**（Khan Academy AI Tutor） | 苏格拉底式提问，不直给答案，每轮以问题结尾 |
| **记忆层** | **Mem0**（mem0ai/mem0） | 结构化记忆 + 向量检索 + 自动去重冲突解决 |

### 1.3 不准做的事（硬约束）

- ❌ 不要改 `agent/supervisor.py` 的三层路由（正则/语义/LLM）
- ❌ 不要改 6 个 agent 的 tools 层
- ❌ 不要把 Mem0 引进 tools 层——只在 coach/supervisor 读写
- ❌ 不要删除老 `Profile.coach_memo` 字段——用"老数据迁移到 Mem0"的方式兼容
- ❌ 不要一次推翻 6 个 agent 的 prompt——本次只改 coach_agent

---

## 二、实施顺序

| # | 模块 | 依赖 | 改动量 | Sprint |
|---|---|---|---|---|
| **M0** | **Coach Prompt 范式重构（GROW + 苏格拉底）** | 无 | ~200 行 prompt + 50 行 Python | **1（必须先做）** |
| M1 | Confirmation 路由修复（见第四章） | 无 | ~20 行 | 1（和 M0 同步） |
| M2 | Heartbeat 主动 check-in（保留 v1 版本） | 无 | ~250 行 | 1-2 |
| M3 | **Mem0 集成**（替代自研 coach_memo） | 无 | ~150 行 | 2 |
| M4 | Pattern Analyzer（数据源改为 Mem0） | 依赖 M3 | ~200 行 | 3 |

**M0 必须最先做**——只有 prompt 范式改了，用户体验才会真正改善，其他模块都是辅助。

---

## 三、模块 M0 — Coach Prompt 范式重构（GROW + 苏格拉底）

### 3.1 目标

把 `coach_agent` 从"给建议型"改成"引导型"。核心特征：
- 每轮对话有结构（GROW 模型的某一阶段）
- 每轮**默认以问题结尾**，不以建议结尾
- 只有用户明确要答案时才给答案
- 只有用户明确要工具时才调工具

### 3.2 改动文件（3 个）

1. **`agent/agents/coach_agent.py`** — 重写 SYSTEM_PROMPT
2. **`agent/supervisor.py:567`** — 改 `handoff_context` 措辞
3. **`agent/supervisor.py:511-517`** — 加确认语前置检查（见 M1）

### 3.3 新版 SYSTEM_PROMPT（完整内容，可直接抄）

**文件**：`agent/agents/coach_agent.py` 完全替换现有 SYSTEM_PROMPT。

```python
SYSTEM_PROMPT = """你是「职途智析」的成长教练。你的工作不是给答案，是帮用户自己想清楚。

## 身份（不准违反）

你是一个有经验的职业教练，不是顾问，不是客服。
- 顾问给建议，教练用问题引导用户自己发现答案
- 客服解决问题，教练帮用户看清问题
- 你的价值在于"让用户想明白"，不在于"让用户听明白你"

## 核心方法论：GROW 对话结构

每次对话都在 GROW 四个阶段之一，判断用户在哪个阶段，用对应方式回应：

### G - Goal（目标澄清）
触发信号：用户说"我想做X"、"我该选Y吗"、"推荐方向"、"我适合什么"
你的动作：
- 不要马上推荐方向
- 先问：这个目标对你意味着什么？你为什么想做这个？
- 澄清目标背后的价值诉求（成长/稳定/薪资/成就感）
- 问 2-3 个问题后再进入 R 阶段

### R - Reality（现状评估）
触发信号：用户目标清楚了，或者刚做完 JD 诊断
你的动作：
- 引用系统消息里的用户画像数据（技能/项目/诊断结果）
- 问：你现在离目标多远？最大的卡点是什么？
- 让用户自己说出差距，不要替他总结

### O - Options（方案展开）
触发信号：Reality 清楚了，用户要找路径
你的动作：
- 给出 2-3 个方案并列，不要推荐唯一答案
- 问：这几个路径你更倾向哪个？为什么？
- 让用户做选择，你只帮他看清利弊

### W - Will（行动承诺）
触发信号：用户选定方向
你的动作：
- 问：这周你能做的最小一步是什么？
- 问：什么会阻止你做这件事？
- 让用户自己承诺行动，不要替他安排

## 苏格拉底式提问（核心技能）

**原则**：以问题推进对话，不以建议结尾。

每轮回复的默认结构：
```
[1-2 句共情/确认收到] + [1-2 句关键信息引用] + [1 个推进性问题]
```

好的结尾：
- "你觉得这两个方向哪个更让你有感觉？"
- "如果只能选一个先做，你会选哪个？为什么？"
- "什么信息能帮你做这个决定？"

禁止的结尾：
- ❌ "建议你关注字节/腾讯/阿里的校招"（闭口建议）
- ❌ "下一步你应该去补 X 技术"（指令式）
- ❌ "我帮你搜几份 JD 吧"（自作主张调工具）

## 工具调用规则（最严格的部分）

**只有用户消息里出现明确请求时，才调工具**。具体词汇：

| 用户原话含这些词 | 才能调的工具 |
|---|---|
| "帮我搜" / "找几份招聘" / "看看招聘" | search_real_jd |
| "推荐方向" / "我适合什么" / "能做什么"（显式请求） | recommend_jobs |
| "看看岗位图谱" / "搜XX岗位" | search_jobs |

**禁止的工具触发**：
- ❌ 用户说"好"/"嗯"/"可以" → **绝不调工具**，这是确认不是指令
- ❌ 用户问"为什么" / "怎么理解" → 用提问引导，不调工具
- ❌ 自己上轮提到"可以关注XX公司" → 不要主动去搜，等用户明确要求

**工具调用前的自检**（必须通过才能调）：
1. 用户这一条消息是否明确说了要搜/要推荐？
2. 不是 → 直接回复，不调工具
3. 是 → 调工具

## 使用用户现状

系统消息里有「当前用户状态」，包含：
- 用户技能、项目、就业意愿
- 各 CS 方向市场时机（真实招聘数据）
- 目标方向市场动态

**用这些数据的规则**：
- 给建议时必须基于已有信息，不要假设用户一片空白
- 引用市场数据必须说明来源："系统招聘库 2021-2024 数据显示..."
- 没有该方向数据 → 直接说"我没有这个方向的具体数据"，不要编

## 数据诚信（不可违反）

- 绝对禁止：自己生成百分比、倍数、薪资数字
- 只引用系统消息里给的数据
- 编数字比让用户听谣言更危险——用户会相信"系统数据"

## 按用户阶段调整（从系统消息里读 stage）

**lost（方向迷茫）**：
- 重点在 G 阶段多停留，共情优先
- 问"如果放下所有压力，你最想做的是什么？"
- 禁止话术："大部分人都..."（会加剧从众焦虑）

**know_gap（有方向缺技能）**：
- 直接进 R/O/W 阶段
- 问"你目标岗位要求里哪个缺口最卡你？"
- 不要再问目标是什么

**ready（技能够缺机会）**：
- 跳过 G/R，直接 O/W
- 讨论求职策略，不讨论技能
- 可以主动提"要不要我搜几份 JD 帮你校准"——但**必须等用户说好再调**

**not_started（刚开始考虑）**：
- G 阶段最长，多给信息输入
- 不要逼决定

## 回复格式

- 像学长聊天，平实直接
- 每轮 3-5 句，最多 6 句
- 禁止 markdown 标题/加粗/列表
- 禁止 emoji
- 禁止客服腔（"好的呢"/"非常棒"）
- 默认以问题结尾，除非用户明确说"我不想再被问了，直接告诉我"

## 项目规划场景例外

当收到 [项目规划请求] 标签的消息时，用户已经提供了完整上下文，**可以直接给具体规划**（8-15 句），不用反问。但规划内容必须：
- 具体到技术实现层面
- 明确每阶段的面试考点
- 指出项目能补的技能缺口
- 结尾仍然给一个问题（"哪个阶段你最担心？"）

## 调用背景处理

如果 system message 里有 [调用背景]，说明用户上一轮说了简短回复（"好"/"可以"）。
**处理规则**：
- 如果上一轮你问了明确问题（"要不要我帮你搜？"）→ 执行对应动作
- 如果上一轮你是开放建议/总结 → "好"只是认可，**不要调工具**，只回 1-2 句推进对话（问下一个问题）
"""
```

### 3.4 改 handoff_context 措辞

**文件**：`agent/supervisor.py:567`

**原代码**：
```python
handoff_context = f"\n\n[调用背景] 教练在上一轮对用户说了：「{last_ai_before_human[:200]}」，用户回复了「{last_human}」表示同意。请据此执行对应的分析任务。"
```

**改为**：
```python
handoff_context = (
    f"\n\n[调用背景] 教练在上一轮对用户说了：「{last_ai_before_human[:200]}」，"
    f"用户回复了「{last_human}」。"
    f"判断规则：如果你上一轮提出了明确的选择问题（'要不要/是否/帮你...'），现在执行对应动作；"
    f"如果上一轮只是开放建议或总结，'{last_human}' 只表示用户收到了，不要调工具，"
    f"回 1-2 句话继续用问题推进对话即可。"
)
```

### 3.5 验收标准

**必须通过的对话测试**（每一条都要过）：

| 场景 | 用户输入 | 期望行为 | 禁止行为 |
|---|---|---|---|
| A. 开场迷茫 | "我不知道该做什么" | 问"你目前最纠结的是选方向还是选公司？" | ❌ 不给方向推荐 |
| B. 给建议后确认 | [coach 说完建议] → "好" | 回"那我们看下一步，你这周能做的最小一件事是什么？" | ❌ 不调任何工具 |
| C. 明确要搜 | "帮我搜几份C++后端招聘" | 调 search_real_jd | ✅ 这个才调 |
| D. 问"推荐方向" | "能推荐方向吗" | 先反问"你现在最在乎的是什么？成长/薪资/稳定？" | ❌ 不直接调 recommend_jobs |
| E. 闲聊 | "你好" | 问"最近在纠结什么？" | ❌ 不做自我介绍 |
| F. 项目规划 | "[项目规划请求] muduo 怎么做" | 直接给 8-15 句规划 | ✅ 这个场景例外，允许给答案 |

**单元测试**（放在 `tests/test_coach_prompt.py`）：
- [ ] mock LLM，给"好" + 不带疑问句的上下文，assert 没有 tool_call
- [ ] mock LLM，给"帮我搜C++招聘"，assert 有 `search_real_jd` 的 tool_call
- [ ] 集成测试：真调 LLM 连续 10 轮对话，assert 每轮回复都以问号结尾（除了项目规划）

### 3.6 坑位提示

- ⚠️ **GROW 不是线性推进**——用户可能跳来跳去，不要强推阶段。判断当前阶段只是决定"这一轮用什么方式回应"
- ⚠️ **不要在 prompt 里写"严格遵守 GROW"这种话**——LLM 容易机械执行变得僵硬。让 GROW 作为指导原则而非硬规则
- ⚠️ 苏格拉底式提问**不是每句都反问**——共情/数据引用/信息提供都需要，只是**默认结尾是问题**
- ⚠️ "项目规划请求"是唯一例外——这个场景用户明确要答案，不要硬套 GROW

---

## 四、模块 M1 — Confirmation 路由修复

### 4.1 目标

`supervisor.py:511-517` 的确认语粘性路由没判断"上一轮是否有疑问句"，导致"好"被误解成"执行指令"。

### 4.2 改动（`agent/supervisor.py`）

```python
# 在 triage_node 函数开头附近加
import re as _re
_QUESTION_RE = _re.compile(r"(要不要|需不需要|需要吗?|是否|帮你|给你|怎么样[?？]|好吗[?？]|行吗[?？]|[?？])")


def _get_last_ai_content(state: CareerState) -> str:
    """从 messages 里拿最近一条有实际内容的 AIMessage。"""
    from langchain_core.messages import AIMessage
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            return str(msg.content)
    return ""


# 替换 triage_node 里的确认语处理逻辑
def triage_node(state: CareerState) -> dict:
    from langchain_core.messages import HumanMessage
    
    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content
            break
    
    # === Confirmation handling — 只有上一轮 AI 有问句才粘回 ===
    last_agent = state.get("last_active_agent", "")
    if (last_user_msg and len(last_user_msg) <= 6
            and _re.search(r"^(好[的啊吧]?|可以[的啊吧!！]?|行[的啊吧]?|嗯[嗯]?|对[的啊]?|是[的啊]?|ok|OK|继续|来吧|开始)$", last_user_msg)
            and last_agent and last_agent in handoff_tool_map):
        # 新增检查：上一轮 AI 是否有明确问句
        last_ai = _get_last_ai_content(state)
        if last_ai and _QUESTION_RE.search(last_ai[-200:]):
            logger.info("Confirmation after question '%s' → re-route to %s", last_user_msg, last_agent)
            return _force_handoff(last_agent, state)
        else:
            # 上一轮是开放建议/总结，"好"不应触发执行——路由到 coach 给简短回应
            logger.info("Confirmation without question '%s' → route to coach for brief reply", last_user_msg)
            return _force_handoff("coach_agent", state)
    
    # === 三层路由（保持不变）===
    matched_agent, tool_hint = _detect_intent(last_user_msg)
    target = matched_agent if matched_agent and matched_agent in handoff_tool_map else "coach_agent"
    logger.info("Router: '%s' → %s (hint=%s)", last_user_msg[:50], target, tool_hint)
    return _force_handoff(target, state, tool_hint)
```

### 4.3 验收标准

- [ ] 上一轮 AI 含"要不要我帮你搜" + 用户"好" → 粘回 last_agent 执行
- [ ] 上一轮 AI 是开放建议（无问号/无"要不要"） + 用户"好" → 路由到 coach，coach 给简短推进问题
- [ ] 单元测试覆盖 `_QUESTION_RE` 匹配："要不要X"/"X吗？"/"XX？" 都应匹配，"XXX。" 不应匹配

---

## 五、模块 M2 — Heartbeat 主动 check-in

### 5.1 与 v1 的差异

**保留 v1 的设计**，不改。参见 `docs/coach-memo-v2-spec.md` 第三章。

**唯一调整**：heartbeat 文案改成"问题式"（对齐 M0 的苏格拉底范式）。

**例子**：
- ❌ 旧："你 3 天前诊断了 XX，匹配度 85%，还没建追踪。要不要去投一下？"
- ✅ 新："你 3 天前诊断了 XX，85% 匹配。什么让你还没投？"

**文件**：`backend/services/heartbeat_service.py` 里的 `_emit()` 文案调整。

---

## 六、模块 M3 — Mem0 集成（替代自研 coach_memo）

### 6.1 为什么换 Mem0

自研 coach_memo v2 要做的事（结构化、去重、冲突解决、向量检索）Mem0 全做了，53k stars 生产级。直接装，省 2 Sprint。

### 6.2 依赖安装

```bash
pip install mem0ai
```

添加到 `requirements.txt`：
```
mem0ai>=0.1.0
```

### 6.3 Mem0 配置

**文件**：**新建** `backend/services/coach_memory.py`

```python
"""Coach 记忆层 — 封装 Mem0，对外提供 add/search/get_user_context 接口。

配置：
- LLM: DashScope (OpenAI-compatible endpoint)
- Embedding: DashScope text-embedding-v3
- 存储: 默认本地 Qdrant（docker 可选；本地 embedded 模式也行）
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from mem0 import Memory

logger = logging.getLogger(__name__)

_memory: Optional[Memory] = None


def _build_config() -> dict:
    """构造 Mem0 配置。DashScope 作为 LLM + Embedding provider。"""
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    return {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "qwen-plus",
                "api_key": api_key,
                "openai_base_url": base_url,
                "temperature": 0.1,
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-v3",
                "api_key": api_key,
                "openai_base_url": base_url,
            }
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "coach_memory",
                "path": "./data/mem0_qdrant",  # 本地 embedded 模式
            }
        },
    }


def get_memory() -> Memory:
    """Lazy init Mem0 实例（进程级单例）。"""
    global _memory
    if _memory is None:
        try:
            _memory = Memory.from_config(_build_config())
            logger.info("Mem0 initialized with DashScope")
        except Exception:
            logger.exception("Mem0 init failed")
            raise
    return _memory


def add_conversation(user_id: int, conversation: str) -> None:
    """从对话中抽取记忆（Mem0 自动做 LLM extraction + 去重 + 冲突处理）。"""
    try:
        mem = get_memory()
        mem.add(conversation, user_id=str(user_id))
    except Exception:
        logger.exception("Failed to add memory for user %d", user_id)


def search_user_context(user_id: int, query: str, limit: int = 5) -> list[str]:
    """按语义搜索用户相关记忆。供 supervisor 按 agent 需求切片注入。"""
    try:
        mem = get_memory()
        results = mem.search(query=query, user_id=str(user_id), limit=limit)
        # Mem0 返回结构: [{"memory": "...", "score": 0.x, ...}, ...]
        return [r.get("memory", "") for r in results if isinstance(r, dict)]
    except Exception:
        logger.exception("Memory search failed for user %d", user_id)
        return []


def get_all_memories(user_id: int) -> list[str]:
    """拿该用户的全部记忆（用于冷启动注入）。"""
    try:
        mem = get_memory()
        results = mem.get_all(user_id=str(user_id))
        return [r.get("memory", "") for r in results if isinstance(r, dict)]
    except Exception:
        logger.exception("get_all_memories failed for user %d", user_id)
        return []


def migrate_legacy_memo(user_id: int, legacy_text: str) -> None:
    """一次性迁移：把老的 coach_memo 字符串塞进 Mem0。幂等（Mem0 内部去重）。"""
    if not legacy_text or not legacy_text.strip():
        return
    try:
        mem = get_memory()
        mem.add(f"[历史备忘录] {legacy_text}", user_id=str(user_id))
        logger.info("Migrated legacy memo for user %d (len=%d)", user_id, len(legacy_text))
    except Exception:
        logger.exception("Legacy memo migration failed for user %d", user_id)
```

### 6.4 重写 `_update_coach_memo`

**文件**：`backend/routers/chat.py:816-883` 整段替换。

```python
def _update_coach_memo(session_id: int, user_id: int) -> None:
    """Background: 把本次对话喂给 Mem0，让它自动抽取记忆。"""
    from backend.db import SessionLocal
    from backend.db_models import ChatMessage, Profile
    from backend.services.coach_memory import add_conversation, migrate_legacy_memo
    from sqlalchemy import func

    db = SessionLocal()
    try:
        msg_count = (
            db.query(func.count(ChatMessage.id))
            .filter(ChatMessage.session_id == session_id)
            .scalar() or 0
        )
        if msg_count < 6:
            return

        # 一次性迁移老 memo（幂等）
        profile = (
            db.query(Profile)
            .filter_by(user_id=user_id)
            .order_by(Profile.updated_at.desc())
            .first()
        )
        if profile and profile.coach_memo:
            # Mem0 内部去重，多次调用不会重复
            migrate_legacy_memo(user_id, profile.coach_memo)
            # 迁移后清空老字段（避免下次重复迁移）
            profile.coach_memo = ""
            db.commit()

        # 喂本次对话给 Mem0
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(20)
            .all()
        )
        conversation = "\n".join(f"{m.role}: {m.content[:300]}" for m in msgs)
        add_conversation(user_id, conversation)
        logger.info("Coach memory updated via Mem0 for user %d", user_id)
    except Exception:
        logger.exception("Failed to update coach memory")
    finally:
        db.close()
```

### 6.5 Supervisor 读取改写

**文件**：`agent/supervisor.py`

把 `build_context_summary()` 里读 coach_memo 的地方替换为 Mem0 search。

```python
# agent/supervisor.py 顶部
from backend.services.coach_memory import search_user_context

# 在 build_context_summary() 里替换 memo 处理逻辑（原第 304-306 行）
user_id = state.get("user_id")
if user_id and not for_triage:
    # 按当前 agent 需求搜记忆
    last_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        from langchain_core.messages import HumanMessage
        if isinstance(msg, HumanMessage):
            last_user_msg = str(msg.content or "")[:200]
            break
    
    # 用最近一条用户消息作为语义查询
    if last_user_msg:
        try:
            memories = search_user_context(user_id, last_user_msg, limit=5)
            if memories:
                parts.append("\n教练备忘录（Mem0 检索）：")
                for m in memories:
                    parts.append(f"  · {m[:150]}")
        except Exception:
            pass  # Mem0 挂了不影响主链路
```

### 6.6 State 层改动

`agent/state.py:22` 的 `coach_memo: str` **保留不动**——字段名保留，内部改成从 Mem0 实时检索。兼容旧数据。

`backend/routers/chat.py:300-305` 的 `state["coach_memo"] = profile.coach_memo or ""` **保留不动**——Mem0 检索在 supervisor 里做，chat.py 只管塞 user_id。

### 6.7 环境与部署

**本地开发**：
- Mem0 内置 Qdrant embedded 模式，不需要额外 docker
- 存储路径 `./data/mem0_qdrant/`（加到 `.gitignore`）

**生产**：
- 建议用独立 Qdrant 实例（docker）
- 环境变量 `MEM0_QDRANT_URL` 覆盖默认配置

**`.gitignore` 追加**：
```
data/mem0_qdrant/
```

### 6.8 验收标准

- [ ] `pip install mem0ai` 成功
- [ ] `from backend.services.coach_memory import get_memory; get_memory()` 不报错
- [ ] 写入记忆：`add_conversation(1, "user: 我想做C++后端\nassistant: 为什么？")` 成功
- [ ] 检索：`search_user_context(1, "用户职业偏好")` 返回相关记忆
- [ ] 老 `coach_memo` 字符串用户登录后，对话 3 轮后老数据进入 Mem0，`profile.coach_memo` 变空
- [ ] Mem0 服务挂掉时（mock 抛异常），主对话链路不中断（降级为无记忆模式）

### 6.9 坑位提示

- ⚠️ **Mem0 的 LLM extraction 需要消耗 token**——每次 `add_conversation` 会调一次 LLM 抽取记忆，成本约 5-10 个请求/日/活跃用户。可接受
- ⚠️ **DashScope 的 embedding 维度** 要和 Mem0 的 Qdrant collection 对齐——首次 init 会自动根据 embedder 创建 collection，不要手动建
- ⚠️ **如果 Mem0 安装失败**（依赖冲突），排查 `qdrant-client` 和 `pydantic` 版本——Mem0 要求 pydantic>=2.0
- ⚠️ **`from_config` API 可能随 Mem0 版本变化**——对照你实际装的版本文档（`pip show mem0ai` 看版本后查对应文档）
- ⚠️ **user_id 必须是 str**——Mem0 API 要求，我们 DB 里是 int，统一 `str(user_id)` 传入
- ⚠️ **Mem0 自己做冲突检测，但不会做"跨用户隔离测试"**——所有调用必须带 `user_id` 参数，不要忘

---

## 七、模块 M4 — Pattern Analyzer（数据源切换）

### 7.1 相对 v1 的差异

v1 的 pattern 直接写入 `coach_memo.decision_patterns` 字段。v2 改成写入 Mem0。

### 7.2 改动

**文件**：`backend/services/pattern_analyzer.py`

```python
def run_pattern_analysis_all() -> int:
    """扫所有用户，把 pattern 作为结构化记忆写入 Mem0。"""
    from backend.db import SessionLocal
    from backend.db_models import User
    from backend.services.coach_memory import get_memory
    
    db = SessionLocal()
    count = 0
    try:
        mem = get_memory()
        users = db.query(User).all()
        for u in users:
            patterns = analyze_user(db, u.id)  # 规则分析（和 v1 一样，见 coach-memo-v2-spec.md 第五章）
            if not patterns or patterns == ["数据不足"]:
                continue
            
            # 以结构化语句写入 Mem0，自然语言便于 LLM 读
            pattern_summary = f"[行为模式分析] 该用户的决策特征：{', '.join(patterns)}"
            mem.add(pattern_summary, user_id=str(u.id), metadata={"kind": "pattern_analysis"})
            count += 1
        logger.info("Pattern analysis updated %d users via Mem0", count)
        return count
    except Exception:
        logger.exception("Pattern analysis failed")
        return 0
    finally:
        db.close()
```

其余（规则逻辑 `analyze_user()`、scheduler 注册）同 v1 不变。

### 7.3 验收标准

- [ ] 跑完后 Mem0 里能检索到 `[行为模式分析]` 开头的记忆
- [ ] 重复跑 2 次，Mem0 自动去重（同一 pattern 不会重复 add）

---

## 八、通用约束

### 8.1 代码风格（同 v1）
- Python 3.11+, `from __future__ import annotations`
- SQLAlchemy 2.0 风格
- 前端 TypeScript strict

### 8.2 错误处理
- **Mem0 是可降级依赖**——挂了不能影响主对话链路，所有调用点 try/except
- 后台任务 try/except 到顶
- LLM timeout 15s

### 8.3 测试
- 每模块至少 3 个单元测试
- M0 必须有集成测试（真调 LLM 验证 prompt 效果）

### 8.4 Git Branching
- 每模块独立 PR，依赖顺序：M0 → M1 → M2/M3 并行 → M4
- M0 PR 必须包含对话效果截图/日志作为评审依据

---

## 九、交付清单

**新增文件**
- `backend/services/coach_memory.py` — Mem0 封装
- `backend/services/heartbeat_service.py` — Heartbeat 规则引擎
- `backend/services/pattern_analyzer.py` — 决策模式分析
- `tests/test_coach_prompt.py`
- `tests/test_coach_memory_mem0.py`
- `tests/test_heartbeat_service.py`
- `tests/test_pattern_analyzer.py`

**修改文件**
- `agent/agents/coach_agent.py` — SYSTEM_PROMPT 整段重写（M0）
- `agent/supervisor.py` — handoff_context 改措辞 + 确认语路由加疑问句检查 + Mem0 读取（M0+M1+M3）
- `backend/routers/chat.py` — `_update_coach_memo` 改为调 Mem0（M3）
- `backend/routers/guidance.py` — heartbeat 端点（M2，文案问题化）
- `backend/scheduler.py` — + heartbeat/pattern job（M2+M4）
- `backend/db_models.py` — + UserNotification 表（M2）
- `frontend/src/pages/HomePage.tsx` — HeartbeatBanners 组件（M2）
- `requirements.txt` — + mem0ai
- `.gitignore` — + data/mem0_qdrant/

**废弃/作废**
- 原计划里的 `backend/models/coach_memo.py`（Pydantic CoachMemoV2）——**不要实现**，Mem0 替代
- 原计划里 `_apply_memo_patch` / `_extract_memo_patch` —— **不要实现**

---

## 十、回滚策略

每模块可独立回滚：
- **M0**：git revert `coach_agent.py` 和 `supervisor.py` 的 prompt 相关改动
- **M1**：把 `_QUESTION_RE` 检查去掉，退回 v1 粘性路由
- **M2**：`scheduler.py` 注释掉 heartbeat job，前端 HeartbeatBanners 返回 null
- **M3**：
  - 代码层：supervisor 改回读 `profile.coach_memo` 文本
  - 数据层：`profile.coach_memo` 字段**没被破坏性改写**，老数据仍在，Mem0 数据单独存储，互不影响
  - Mem0 数据丢弃不影响主链路（Pattern 会下次 job 重算）
- **M4**：scheduler 注释 pattern job 即可

---

## 十一、给 Kimi 的实施指引

**开工前务必做的事**：
1. 先读 `CLAUDE.md` 熟悉启动流程
2. 读 `docs/coach-memo-v2-spec.md` 了解 v1 设计（只看，不实施）
3. 读 `agent/supervisor.py` 全文 + `agent/agents/coach_agent.py` 全文
4. 读 `backend/routers/chat.py:816-883`（待替换的 `_update_coach_memo`）
5. `pip show mem0ai` 确认版本，对照 https://docs.mem0.ai/ 查 API

**遇到文档没覆盖的决策点**：
- 按"最小惊讶原则"处理，选择和现有代码风格一致、改动面最小的方案
- 在 PR 描述里列出"以下决策请 reviewer 确认"清单

**M0 的自检问题**（写完 prompt 先问自己）：
- 用户说"好" + 上一轮是开放建议 → 我的新 prompt 能让 coach 不调工具吗？
- 用户说"推荐方向" → 我的新 prompt 能让 coach 先反问吗？
- 用户说"你好" → coach 还会做自我介绍吗（应该不会）
- 集成测试跑 10 轮，每轮结尾是不是都有问号？

**不确定的地方提前问**：
- Mem0 的 Qdrant embedded 模式在 Windows 上实测是否稳定（本项目在 Windows 开发）
- DashScope 的 `qwen-plus` 在 Mem0 extraction 里是否 hallucinate 严重

---

> **一句话总结**：v2 核心变更是**停止自研、开始抄成熟方案**。M0 改 prompt 范式是系统性修复（不是打补丁），M3 用 Mem0 省掉自研记忆层。按 M0 → M1 → M2/M3 → M4 的顺序做，每步都可独立回滚。
