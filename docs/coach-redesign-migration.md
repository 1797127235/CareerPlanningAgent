# v1 → v2 迁移任务书（给 Kimi 的增量 Delta）

> **关系说明**：
> - `docs/coach-memo-v2-spec.md`（v1）— **已由 Kimi 实施完毕**，代码已落地
> - `docs/coach-redesign-spec.md`（v2）— 完整重构方案，内容较长
> - **本文（migration）** — 从 v1 现状到 v2 目标的**增量任务书**，Kimi 直接按本文做即可
>
> **Kimi 的工作方式**：
> 1. 先读本文（~500 行）
> 2. 本文里引用 v2 某章节时，再去查 v2 对应章节
> 3. 不需要从头读 v2

---

## 一、现状盘点（本节告诉 Kimi 别重复劳动）

### ✅ 已完成（必须保留，不要动）

| 组件 | 文件 | 状态 |
|---|---|---|
| UserNotification 表 | `backend/db_models.py` | ✅ 已建 |
| Heartbeat 规则引擎 | `backend/services/heartbeat_service.py` | ✅ 已建 |
| Pattern Analyzer 规则层 | `backend/services/pattern_analyzer.py` | ✅ `analyze_user()` 已建，规则层保留 |
| Scheduler jobs | `backend/scheduler.py` | ✅ `daily-heartbeat` + `weekly-pattern-analysis` 已注册 |
| Heartbeat API | `backend/routers/guidance.py` | ✅ `/heartbeat` + `/heartbeat/dismiss` 已建 |
| 前端 Banner | `frontend/src/pages/HomePage.tsx` | ✅ HeartbeatBanners 已建 |

**铁律**：以上 6 个组件的**结构/接口/字段**一律不改。只改其中的**文案**（任务 G）和**数据写入目标**（任务 D）。

### ⚠️ 待废弃（本次迁移必须清理）

| 组件 | 文件 | 处理方式 |
|---|---|---|
| CoachMemoV2 Pydantic schema | `backend/models/coach_memo.py` | **整个文件删除** |
| 自研 JSON patch 逻辑 | `backend/routers/chat.py:817-968` 的 `_update_coach_memo` / `_extract_memo_patch` / `_apply_memo_patch` 三个函数 | **重写**（见任务 C） |
| Pattern 写入 coach_memo 字段 | `backend/services/pattern_analyzer.py` 的 `run_pattern_analysis_all()` | **改写数据源**（见任务 D） |
| supervisor 读 coach_memo 的逻辑 | `agent/supervisor.py` 里 `parse_memo` 相关代码 | **改为 Mem0.search**（任务 C 一并处理） |

### ❌ 未做（本次迁移新增）

| 任务 | 核心内容 |
|---|---|
| **M0 苏格拉底范式** | 重写 `agent/agents/coach_agent.py` 的 SYSTEM_PROMPT，改为 GROW + 苏格拉底 |
| **M1 Confirmation 路由修复** | `agent/supervisor.py` 加"上一轮是否有疑问句"检查 |
| **Mem0 基础设施** | 装依赖 + 封装服务 + 数据迁移 |
| **文案问题化** | Heartbeat 推送文案改成苏格拉底风格 |

---

## 二、任务清单（按依赖顺序）

### 任务 A · 装 Mem0 + 封装服务 | 优先级 🔴 最先做

**为什么先做**：任务 C/D 都依赖这个封装层。

**步骤**：

1. **装依赖**
   ```bash
   pip install mem0ai
   ```
   
   在 `requirements.txt` 追加：
   ```
   mem0ai>=0.1.0
   ```

2. **`.gitignore` 追加**
   ```
   data/mem0_qdrant/
   ```

3. **新建 `backend/services/coach_memory.py`**
   代码完全按 **v2 spec 第 6.3 节**抄（`coach-redesign-spec.md` 搜 "新建 `backend/services/coach_memory.py`"）。
   
   **关键 API**（Kimi 要记住的）：
   ```python
   from backend.services.coach_memory import (
       get_memory, add_conversation, search_user_context,
       get_all_memories, migrate_legacy_memo,
   )
   ```

4. **环境变量确认**
   - `DASHSCOPE_API_KEY`（项目已有）
   - `LLM_BASE_URL`（项目已有）
   
   不需要新增任何环境变量。

**验收**：
- [ ] `python -c "from backend.services.coach_memory import get_memory; get_memory()"` 不报错
- [ ] `python -c "from backend.services.coach_memory import add_conversation, search_user_context; add_conversation(9999, 'user: 我想做C++\nassistant: 为什么？'); print(search_user_context(9999, '用户偏好'))"` 能返回非空结果

**坑位**：
- ⚠️ Windows 下 Qdrant embedded 首次启动会下载文件到 `data/mem0_qdrant/`，耐心等 1 分钟
- ⚠️ 如果 `pip install mem0ai` 报 pydantic 版本冲突，看 `pip show pydantic` 是否 >= 2.0，本项目已是
- ⚠️ DashScope 对应的 Mem0 config key 是 `openai` provider（兼容模式），不是 `dashscope` provider

---

### 任务 B · 作废 CoachMemoV2 Pydantic schema | 优先级 🔴

**步骤**：

1. **删文件**
   ```bash
   rm backend/models/coach_memo.py
   ```
   
   如果 `backend/models/` 目录变空，也可以删掉，但看下 `__init__.py` 有没有别的东西再决定。

2. **扫引用**（确保删完没有悬挂 import）
   ```bash
   grep -rn "from backend.models.coach_memo" backend/ agent/
   grep -rn "CoachMemoV2\|parse_memo\|serialize_memo\|PivotEvent\|OpenThread" backend/ agent/
   ```
   
   应该只在以下两个文件里看到残留（任务 C 和 D 会处理）：
   - `backend/routers/chat.py`（`_update_coach_memo` 函数内）
   - `agent/supervisor.py`（`build_context_summary` 里）

**验收**：
- [ ] `backend/models/coach_memo.py` 不存在
- [ ] `grep -rn "CoachMemoV2" backend/ agent/` 无结果（任务 C/D 完成后）

---

### 任务 C · 重写 `_update_coach_memo` 改调 Mem0 | 优先级 🔴

**当前位置**：`backend/routers/chat.py:817-968`（`_update_coach_memo` + `_extract_memo_patch` + `_apply_memo_patch` 三个函数）

**操作**：**三个函数一起删，用一个新函数替换**。

**步骤**：

1. **删除**当前 `chat.py:817-968` 的三个函数整段
2. **替换为**（直接抄 v2 spec 第 6.4 节，或用下面这段）：

```python
def _update_coach_memo(session_id: int, user_id: int) -> None:
    """Background: 把本次对话喂给 Mem0，让它自动抽取记忆。
    
    Mem0 内置 LLM extraction + 去重 + 冲突合并，我们只负责喂对话。
    老的 profile.coach_memo 文本在首次调用时一次性迁移进 Mem0。
    """
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

        profile = (
            db.query(Profile)
            .filter_by(user_id=user_id)
            .order_by(Profile.updated_at.desc())
            .first()
        )
        
        # 迁移老 memo（幂等，Mem0 自动去重）
        if profile and profile.coach_memo:
            migrate_legacy_memo(user_id, profile.coach_memo)
            profile.coach_memo = ""  # 迁移后清空，避免重复
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

3. **改 supervisor 读取逻辑**
   
   **文件**：`agent/supervisor.py`
   
   找到 `build_context_summary` 里处理 `coach_memo` 的地方（搜 `memo = state.get("coach_memo"` 或搜 `parse_memo`），**替换为**：
   
   ```python
   # 替换原来读 state["coach_memo"] 并 parse_memo 的代码段
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
               if memories:
                   parts.append("\n教练备忘录（Mem0 检索）:")
                   for m in memories:
                       parts.append(f"  · {m[:150]}")
           except Exception:
               pass  # Mem0 挂了不影响主链路
   ```
   
   **注意**：原来代码里所有 `from backend.models.coach_memo import parse_memo` 的 import 全删。

4. **State 层不动**
   - `agent/state.py:22` 的 `coach_memo: str` **保持不变**
   - `backend/routers/chat.py:300-305` 的 `state["coach_memo"] = profile.coach_memo or ""` **保持不变**（Mem0 挂了时还有老数据兜底）

**验收**：
- [ ] `grep -rn "parse_memo\|CoachMemoV2\|_apply_memo_patch\|_extract_memo_patch" backend/ agent/` 无结果
- [ ] 起后端跑 3 轮对话，看 log 有 "Coach memory updated via Mem0" 输出
- [ ] 查 Mem0：`python -c "from backend.services.coach_memory import get_all_memories; print(get_all_memories(YOUR_USER_ID))"` 能看到抽取的记忆

---

### 任务 D · 改 `pattern_analyzer` 写入 Mem0 | 优先级 🟡

**当前**：`backend/services/pattern_analyzer.py` 的 `run_pattern_analysis_all()` 把 patterns 写进 `profile.coach_memo` 的 `decision_patterns` 字段。

**目标**：改成写进 Mem0。

**步骤**：

1. **保留 `analyze_user()` 不动**（规则逻辑复用）

2. **重写 `run_pattern_analysis_all()`**：

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
            patterns = analyze_user(db, u.id)
            if not patterns or patterns == ["数据不足"]:
                continue
            
            pattern_summary = f"[行为模式分析] 该用户的决策特征：{', '.join(patterns)}"
            try:
                mem.add(pattern_summary, user_id=str(u.id), metadata={"kind": "pattern_analysis"})
                count += 1
            except Exception:
                logger.exception("Failed to write pattern for user %d", u.id)
        logger.info("Pattern analysis updated %d users via Mem0", count)
        return count
    except Exception:
        logger.exception("Pattern analysis failed")
        return 0
    finally:
        db.close()
```

3. **删除旧函数里的 `parse_memo` / `serialize_memo` 引用**

**验收**：
- [ ] 手动跑 `python -c "from backend.services.pattern_analyzer import run_pattern_analysis_all; print(run_pattern_analysis_all())"` 无报错
- [ ] Mem0 里能搜到 `[行为模式分析]` 开头的记忆：`python -c "from backend.services.coach_memory import search_user_context; print(search_user_context(YOUR_USER_ID, '决策特征'))"`

---

### 任务 E · M0 苏格拉底范式 Prompt 重写 | 优先级 🔴（**本次重构的核心**）

**当前**：`agent/agents/coach_agent.py:11-101` 是"给建议型"的学长腔 prompt

**目标**：重写成 GROW + 苏格拉底引导型 prompt

**步骤**：

1. **完全替换 SYSTEM_PROMPT**
   
   直接抄 **v2 spec 第 3.3 节**的整段（`coach-redesign-spec.md` 搜 "3.3 新版 SYSTEM_PROMPT"，把里面 `SYSTEM_PROMPT = """..."""` 整段复制过来替换现有的）。
   
   **不要自己改写或压缩 prompt 内容**——prompt 工程非常敏感，每一段都是有设计意图的。

2. **不需要**实现 v1 spec 里的 `_build_system_prompt` 函数——直接用单一 SYSTEM_PROMPT（stage 相关指令已经嵌在 prompt 里了）

3. **保留 `create_coach_agent()` 函数签名不变**

**验收**：
- [ ] 启动后端，开一个新对话，发"你好" → coach 应该问问题（如"最近在纠结什么？"），**不应该做自我介绍**
- [ ] 发"推荐方向" → coach 应该先反问（"你现在最在乎的是什么？成长/薪资/稳定？"），**不应该立刻调 recommend_jobs**
- [ ] 发"帮我搜几份C++招聘" → coach 应该调 `search_real_jd`
- [ ] 连续聊 10 轮，grep 日志看每轮回复结尾是否带 `？` 或 `?`（项目规划场景除外）

**坑位**：
- ⚠️ 新 prompt 更长（~200 行），可能触发 token limit。用 `get_chat_model(temperature=0.5)` 默认即可，不要加 max_tokens 限制
- ⚠️ 不要省略"工具调用规则"章节——这是修「好→搜JD」bug 的关键
- ⚠️ 不要删"项目规划场景例外"章节——否则 `[项目规划请求]` 触发的对话会被苏格拉底化变得答非所问

---

### 任务 F · M1 Confirmation 路由修复 | 优先级 🔴

**文件**：`agent/supervisor.py`

**步骤**：

1. **顶部加正则**（`_SEARCH_JD_PATTERN` 附近）：

   ```python
   _QUESTION_RE = _re.compile(r"(要不要|需不需要|需要吗?|是否|帮你|给你|怎么样[?？]|好吗[?？]|行吗[?？]|[?？])")
   ```

2. **改 `triage_node` 里的确认语处理逻辑**
   
   直接抄 v2 spec 第 4.2 节的代码（搜 "Confirmation handling — 只有上一轮 AI 有问句才粘回"）

3. **改 handoff_context 措辞**
   
   在 `_make_agent_node` 里找到现在这行：
   ```python
   handoff_context = f"\n\n[调用背景] 教练在上一轮对用户说了：「{last_ai_before_human[:200]}」，用户回复了「{last_human}」表示同意。请据此执行对应的分析任务。"
   ```
   
   替换为（抄 v2 spec 第 3.4 节）：
   ```python
   handoff_context = (
       f"\n\n[调用背景] 教练在上一轮对用户说了：「{last_ai_before_human[:200]}」，"
       f"用户回复了「{last_human}」。"
       f"判断规则：如果你上一轮提出了明确的选择问题（'要不要/是否/帮你...'），现在执行对应动作；"
       f"如果上一轮只是开放建议或总结，'{last_human}' 只表示用户收到了，不要调工具，"
       f"回 1-2 句话继续用问题推进对话即可。"
   )
   ```

**验收**（必须跑的对话测试）：
- [ ] **关键 bug 回归**：coach 给完开放建议（无"要不要"问句），用户回"好" → 应路由到 coach（不是 last_agent），回 1-2 句继续对话，**无 tool_call**
- [ ] coach 问"要不要我帮你搜？"，用户回"好" → 应粘回 coach 并调 `search_real_jd`
- [ ] 单元测试：`_QUESTION_RE.search("我觉得你可以关注字节。")` 返回 None；`_QUESTION_RE.search("要不要我帮你搜？")` 返回匹配对象

---

### 任务 G · Heartbeat 文案苏格拉底化 | 优先级 🟢

**文件**：`backend/services/heartbeat_service.py`

**步骤**：

在每条 `_emit(...)` 调用里，把 body 从"建议式"改成"问题式"。

**对照表**（全局替换）：

| 规则 | 原文案 | 新文案 |
|---|---|---|
| jd_followup | "你 3 天前诊断了「X」，匹配度 Y%，还没建追踪。要不要去投一下？" | "你 3 天前诊断了「X」，Y% 匹配。什么让你还没投？" |
| inactive_nudge | "你追踪的 N 家公司最近可能有新动态，来看看？" | "你追踪的 N 家公司里，哪一家你最想先推进？" |
| milestone_due | (占位，未启用) | (占位，未启用) |

**验收**：
- [ ] 手动触发 `run_heartbeat()` 造一条通知，去前端 Banner 区看文案是否带问号

---

### 任务 H · 老数据迁移策略（不用写脚本） | 优先级 🟢

**说明**：
- 任务 C 的新 `_update_coach_memo` 里已经内置**幂等迁移逻辑**（`migrate_legacy_memo` 调用）
- 用户下次对话时老 memo 自动迁移进 Mem0 并清空 `profile.coach_memo`
- **不需要**跑一次性迁移脚本

**可选**：如果想主动预热所有老用户的 memo 迁移，可以写个管理命令：

```python
# backend/scripts/migrate_all_legacy_memos.py（可选，不强制）
from backend.db import SessionLocal
from backend.db_models import Profile
from backend.services.coach_memory import migrate_legacy_memo

def main():
    db = SessionLocal()
    try:
        profiles = db.query(Profile).filter(Profile.coach_memo != "").all()
        for p in profiles:
            migrate_legacy_memo(p.user_id, p.coach_memo)
            p.coach_memo = ""
        db.commit()
        print(f"Migrated {len(profiles)} profiles")
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

---

## 三、PR 拆分建议

| PR | 任务 | 说明 |
|---|---|---|
| PR-1 | A + B | 基础设施：装 Mem0 + 删 CoachMemoV2 |
| PR-2 | C + D | 数据层迁移：chat.py 和 pattern_analyzer 改用 Mem0 |
| PR-3 | E + F | 核心修复：苏格拉底 prompt + Confirmation 路由 |
| PR-4 | G + H | 文案调整 + 可选迁移脚本 |

**合并顺序**：PR-1 → PR-2 → PR-3 → PR-4（有依赖）

**可并行**：PR-3 的 E 和 F 可以拆成两个独立 PR 并行做

---

## 四、整体验收清单（全部完成后做一遍）

### 代码扫描
```bash
# 应该全部无结果
grep -rn "CoachMemoV2\|parse_memo\|serialize_memo\|_apply_memo_patch\|_extract_memo_patch\|PivotEvent\|OpenThread" backend/ agent/

# 应该能看到 Mem0 引用
grep -rn "from backend.services.coach_memory" backend/ agent/
```

### 关键对话回归
1. 新对话发"你好" → coach 反问，不自我介绍 ✅
2. 新对话发"推荐方向" → coach 反问澄清，不直接调工具 ✅
3. coach 给完开放建议，用户回"好" → coach 继续问，不调工具 ✅（**核心 bug 修复**）
4. coach 问"要不要我帮你搜？"，用户回"好" → coach 调 search_real_jd ✅
5. 发长 JD 文本 → jd_agent 正常诊断 ✅（路由未动）
6. 发"帮我搜C++后端招聘" → search_agent 正常搜 ✅

### Mem0 功能
1. 聊 3 轮后 Mem0 里有记忆：`search_user_context(user_id, "偏好")` 返回非空 ✅
2. 老用户首次对话后，`profile.coach_memo` 被清空，旧文本进了 Mem0 ✅
3. 重复聊同样内容 → Mem0 不重复存（它自己去重）✅
4. Mem0 挂了（mock 异常）→ 主对话不中断 ✅

### 基础设施回归
1. Heartbeat 首页 Banner 文案是问题式 ✅
2. Pattern Analyzer 周度 job 正常跑，写入 Mem0 ✅
3. `GET /api/guidance/heartbeat` 正常返回 ✅

---

## 五、常见问题（Kimi 可能会问）

**Q1: 老的 `profile.coach_memo` 字段要不要删？**
A: **不删**。字段保留，只是不再写入（除了任务 C 的"迁移后清空"）。迁移期有老用户还没触发对话，他们的老 memo 要保留着等迁移。半年后可以考虑 DB 层删字段，本次不做。

**Q2: v1 的 M1（Personality by Stage）还做吗？**
A: **不做**。v2 的 M0 苏格拉底 prompt 已经在内部按 stage 分支，不需要单独拆 4 个 prompt 片段。

**Q3: Mem0 免费的 self-hosted 够用吗？**
A: **够用**。我们用本地 Qdrant embedded 模式（零运维）。Mem0 的云服务是付费 Pro 功能，我们不需要。

**Q4: DashScope 的 qwen-plus 用在 Mem0 extraction 会幻觉严重吗？**
A: 实测看，简单的"从对话里抽取用户偏好"这类任务质量足够。如果实际效果差，先换成 `qwen-max`，成本可接受。

**Q5: 如果任务 E 改完 prompt，发现 coach 变得太"面试官"了（反问过度），怎么办？**
A: 不要自己改 prompt 结构。反馈问题回来，由 reviewer 决定如何调。苏格拉底式有学习曲线，不要第一次不满意就回退。

---

## 六、Kimi 开工前的最终检查

- [ ] 已读 `CLAUDE.md`
- [ ] 已扫 `docs/coach-redesign-spec.md` 目录（用 `head -100` 看章节结构）
- [ ] 已扫 `docs/coach-memo-v2-spec.md` 目录（了解 v1 的设计意图）
- [ ] 已运行 `pip show mem0ai` 确认未安装（任务 A 第一步去装）
- [ ] 已 `git status` 确认工作区干净（避免改动和其他未提交 WIP 冲突）

---

> **交付期望**：4 个 PR，每个独立可合并可回滚。总代码改动约 400 行（含删除 + 新增）。全部完成后：自研 coach_memo 基础设施下线、Mem0 上线、coach 对话范式从"顾问型"切换到"教练型"、核心 bug（"好"被误解）根治。
