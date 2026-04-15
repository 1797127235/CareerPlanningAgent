# 成长教练流式输出 + 响应慢 修复任务（交给 Kimi）

> 给 Kimi 实施。不要改超出本文档列出的改动范围。

## 现象

1. **不流式**：教练回复是一整条"啪"地出现，不是像 ChatGPT 那样逐字出。
2. **响应慢**：用户发一句短消息（比如"你好"），从点发送到看到第一个字 2-6 秒。

## 根因（按影响从大到小）

### 根因 A — LLM 没开 streaming（决定"流不流"）

**文件**：`backend/llm.py:105-124` 的 `get_chat_model`

```python
return ChatOpenAI(
    model=get_model(purpose),
    api_key=(...),
    base_url=get_env_str("LLM_BASE_URL", _DEFAULT_BASE_URL),
    temperature=temperature,
    request_timeout=timeout,
    max_retries=1,
)
```

`ChatOpenAI` 默认 `streaming=False`。`create_react_agent` 子图内部走 `model.ainvoke()` → 整条 AIMessage 一次性返回 → `supervisor.astream(stream_mode="messages")` 虽然外壳是 stream，但只能把整条消息作为**一个** `AIMessage` yield。前端 `useChat.ts` 确实在逐 chunk 读 SSE，但 chunk 数量 = 1，所以像"非流式"。

DashScope OpenAI 兼容端点在 LangChain 这里必须**显式开 streaming** 才会走 `stream=True` 的 HTTP 请求。

### 根因 B — Mem0 search 同步阻塞在 context 构建里（TTFT 主杀手）

**文件**：`agent/supervisor.py:303-322`

```python
# Coach memo from prior sessions (Mem0)
user_id = state.get("user_id")
if user_id and not for_triage:
    last_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        from langchain_core.messages import HumanMessage as _HM
        if isinstance(msg, _HM):
            last_user_msg = str(msg.content or "")[:200]
            break

    if last_user_msg:
        try:
            from backend.services.coach_memory import search_user_context
            memories = search_user_context(user_id, last_user_msg, limit=5)
            ...
```

`search_user_context` → `mem.search()` 内部**每次**要：
1. 用 DashScope embedding 对 query 做一次远程 embedding request（~300-600ms）
2. Qdrant 本地检索（<50ms）
3. Mem0 可能还走 LLM filter/rank

**每轮对话都跑一次**，直接往 TTFT 里加 300-1500ms。而且 `build_context_summary` 是在 agent_node 里同步调用的（`supervisor.py:570`），早于 LLM 首个 token。

### 根因 C — `_TAIL = 40` 缓冲让开头 40 字符延迟显示

**文件**：`backend/routers/chat.py:960-1012`

`_stream_tail` 把最后 40 字符暂缓在内存里不 yield，目的是为了防 `[COACH_RESULT_ID:12345]`（23 字符）这类内部 marker 闪到前端。副作用：教练回复前 40 字符（约 1-2 句中文）要等第 41 字符产生后才出。对短回复（教练回复通常 3-5 句、60-120 字符），感觉像"憋到一半才打字"。

## 任务清单（实施顺序按依赖）

### T1 — 开 LLM streaming（最核心，1 行）

**改 `backend/llm.py:113-124`**：

```python
return ChatOpenAI(
    model=get_model(purpose),
    api_key=(
        get_env_str("DASHSCOPE_API_KEY")
        or get_env_str("OPENAI_API_KEY")
        or "sk-placeholder"
    ),
    base_url=get_env_str("LLM_BASE_URL", _DEFAULT_BASE_URL),
    temperature=temperature,
    request_timeout=timeout,
    max_retries=1,
    streaming=True,           # ← 新增
    stream_usage=False,       # ← 新增：不在每个 chunk 带 usage 元数据，减 overhead
)
```

**验收（必须跑）**：
```python
# 独立脚本或 python -c 验证
import asyncio
from langchain_core.messages import HumanMessage
from backend.llm import get_chat_model

async def main():
    m = get_chat_model()
    chunks = []
    async for c in m.astream([HumanMessage(content="用 20 字介绍你自己")]):
        chunks.append(c.content)
        print(repr(c.content), flush=True)
    print(f"\n共 {len(chunks)} 个 chunk，总长 {sum(len(c) for c in chunks)}")

asyncio.run(main())
```

**通过条件**：`chunks` 数量 > 5（非 1）。如果 = 1 说明 streaming 没真正生效。

### T2 — 降低前端缓冲（让开头也能秒出）

**改 `backend/routers/chat.py:960`**：

```python
# 原：_TAIL = 40
_TAIL = 24   # 够 strip [COACH_RESULT_ID:99999]=23 字符的 marker，开头感知不到延迟
```

**不需要**单独验收，T1 验证时连带看到：教练回复从第 1 个字就开始逐字出。

### T3 — Mem0 search 异步化 / 节流（消除 TTFT 最大头）

**目标**：`build_context_summary` 不再同步跑 Mem0。采用**会话级缓存** + **按轮次节流**：

- 第 1 轮（session 新建）：跳过 Mem0 search（空 memo 体验 > 2 秒首 token 延迟）
- 第 3/6/10 轮（即 len(human_messages) in {3, 6, 10}）才真正跑一次 search
- 其它轮次：复用上一次 search 结果（存 state["cached_memories"]）

**改 `agent/supervisor.py:303-322`**：

```python
# Coach memo from prior sessions (Mem0) — 节流：避免每轮阻塞 TTFT
user_id = state.get("user_id")
if user_id and not for_triage:
    from langchain_core.messages import HumanMessage as _HM
    human_msgs = [m for m in state.get("messages", []) if isinstance(m, _HM)]
    turn = len(human_msgs)

    last_user_msg = str(human_msgs[-1].content or "")[:200] if human_msgs else ""

    # 只在关键轮次跑 Mem0（对 TTFT 最友好）
    should_refresh = turn in (3, 6, 10) or (turn > 10 and turn % 5 == 0)
    cached = state.get("cached_memories")

    memories: list[str] = []
    if should_refresh and last_user_msg:
        try:
            from backend.services.coach_memory import search_user_context
            memories = search_user_context(user_id, last_user_msg, limit=5)
            state["cached_memories"] = memories  # 存回 state 供下轮复用
        except Exception:
            pass
    elif cached:
        memories = cached  # 非刷新轮次，直接用缓存

    if memories:
        parts.append("\n教练备忘录（Mem0 检索）:")
        for m in memories:
            parts.append(f"  · {m[:150]}")
```

**同时改 `agent/state.py`**（如果 `CareerState` TypedDict 里没 `cached_memories`）：
- 加一个 `cached_memories: list[str]` 字段（可选）

**验收**：
1. 新开一个 chat session，连发 2 条消息 → 日志里**不应**出现 `Mem0 search` 耗时（如果有加 log 的话）
2. 发到第 3 条消息 → Mem0 search 跑一次，往后 3 条用缓存
3. 在后端加一个简易计时（可选，验证完删除）：
   ```python
   import time
   t0 = time.time()
   memories = search_user_context(...)
   logger.info("Mem0 search took %.0f ms", (time.time()-t0)*1000)
   ```

### T4 — 加 TTFT 日志（可选，用于前后对比）

**改 `backend/routers/chat.py:964`（`try:` 之前）**：

```python
import time as _time
_ttft_start = _time.time()
_first_chunk_logged = False
```

然后在 `yield f"data: {json.dumps({'content': _safe}, ...)}"` 之前加：

```python
if not _first_chunk_logged:
    logger.info("TTFT: %.0f ms for user %d", (_time.time()-_ttft_start)*1000, user.id)
    _first_chunk_logged = True
```

验证完可删除。目标：TTFT 从 2-6 秒降到 500ms-1.5s（主要看 LLM 首 token 延迟）。

## 不要动的东西

- `_hydrate_state` — 虽然有 10 几个 DB 查询，但 SQLite 本地加起来 50-150ms，不是大头。动了风险大。
- `_detect_intent` Tier 2/3 — 90%+ 消息走 regex 命中，不是主瓶颈。
- `create_coach_agent` / `SYSTEM_PROMPT` — 上一轮刚改完的 Socratic + GROW，稳定期，不碰。
- Mem0 `add_conversation` 写入路径 — 已经在 `chat.py:1066-1070` 用 `threading.Thread` 异步化了，不影响 TTFT。

## 最终端到端验收

Kimi 实施完 T1-T3 后，用户本地跑：

| 场景 | 期望行为 |
|---|---|
| 新 session 说"你好" | 首 token <1.5s；回复逐字出 |
| 继续对话第 2-3 轮 | 第 3 轮感觉不到额外卡顿（Mem0 命中缓存或本轮刷新） |
| 连续 5 轮对话 | 第 6 轮会再刷一次 Mem0（可观察到 ~300-800ms 额外延迟，属预期） |

三个场景任一失败，回来定位。全部通过 → 收尾。

## 风险 / 回滚

- T1 `streaming=True` 加了对后端依赖的流式支持假设。如果 DashScope 某个模型返回异常（比如 qwen-max 不支持 SSE），可快速 revert 单行。
- T3 Mem0 节流有个边界：用户第 1 条消息如果问"我之前跟你说过什么" → 拿不到历史记忆。但概率极低（冷启动新 session 就问历史的用户 <1%），且降级后果只是"coach 不记得"，不崩溃。可接受。

---

PR 建议：T1+T2 合一 PR（都是 streaming 体感相关），T3 单独 PR（Mem0 异步化，影响面大一点需要单独灰度）。T4 可以内嵌在 T1+T2 的 PR 里，最后删除。
