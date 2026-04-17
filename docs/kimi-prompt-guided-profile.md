# Kimi 执行提示词：教练引导建档

## 你的任务

在"职途智析"项目中新增**教练对话建档**功能，让没有简历的学生也能通过和教练聊天建立画像。改动 5 个文件，不涉及数据库变更。

详细计划在 `docs/kimi-brief-guided-profile.md`，请先完整阅读。

---

## 改动清单（按顺序执行）

### 1. `agent/tools/coach_context_tools.py` — 新增 `save_profile_from_chat` tool

在文件末尾（`get_recommended_roles` 函数之后）新增一个 `@tool` 函数 `save_profile_from_chat`。

参考计划中"任务 1"的完整代码。核心逻辑：
- 接收 `profile_data: str`（JSON 字符串）
- 从 `_ctx_user_id` ContextVar 获取 user_id
- 用 `_get_or_create_profile` 创建/获取 profile
- 如果已有 skills 数据，用 `_merge_profiles` 合并；否则直接写入
- 设 `source = "chat_guided"`
- 计算 quality、commit
- 开后台线程跑 `_auto_locate_on_graph`（和简历上传后一样）
- 返回成功消息

### 2. `agent/agents/coach_agent.py` — 注册新 tool

在 import 行加 `save_profile_from_chat`：
```python
from agent.tools.coach_context_tools import (
    get_user_profile, get_career_goal, get_market_signal, get_memory_recall,
    get_recommended_roles, save_profile_from_chat,
)
```

在 `create_coach_agent()` 的 `tools=[]` 列表里加上 `save_profile_from_chat`。

### 3. `agent/skills/coach-profile-builder/SKILL.md` — 新建 skill 文件

创建目录 `agent/skills/coach-profile-builder/`，新建 `SKILL.md`。

完整内容见计划中"任务 2"。这是一个引导式问答 skill：
- 5-6 步：专业 → 技能 → 项目 → 兴趣 → 意向 → 确认
- 每次只问一个问题
- 最后确认后调 `save_profile_from_chat`
- 禁止在建档过程中推荐方向

### 4. `backend/routers/chat.py` — greeting 返回 `has_profile`

在 `_build_greeting` 函数中：

（a）在 return dict（约第 714 行）里加一个字段 `has_profile`。

判断逻辑：用现有的 `stage` 变量——`stage != "no_profile"` 即表示有画像。
或者更精确：`skill_count > 0 or bool(profile_data.get("projects"))`。

最简单的方式：
```python
"has_profile": stage != "no_profile",
```

加在 return dict 的 `"processing"` 行后面即可。

### 5. `frontend/src/components/ChatPanel.tsx` — 无画像时显示"对话建档"chip

（a）在 `GreetingData` interface（约第 96 行）加字段：
```typescript
has_profile?: boolean
```

（b）在 chips 渲染区域（约第 439-449 行），在现有 chips 列表后面追加一个条件 chip：

找到这段代码：
```tsx
<div className="flex flex-wrap justify-center gap-2 px-2">
  {(greetingData?.chips ?? defaultChips).map((chip) => (
    ...
  ))}
</div>
```

在 `</div>` 之前（map 之后），加入：
```tsx
{greetingData && !greetingData.has_profile && (
  <button
    onClick={() => sendMessage('我没有简历，想通过对话建立画像')}
    className="chip text-[12px] font-medium text-[var(--text-2)] hover:text-[var(--text-1)] active:scale-[0.97] transition-transform"
  >
    没简历？对话建档
  </button>
)}
```

---

## 关键参考代码位置

| 需要看的文件 | 位置 | 用途 |
|---|---|---|
| `agent/tools/coach_context_tools.py` | 全文 | 理解现有 tool 模式、ContextVar 用法 |
| `agent/agents/coach_agent.py` | L10-15, L52-66 | 理解 tool 注册方式 |
| `agent/skills/coach-greeting/SKILL.md` | 全文 | 参考现有 skill 格式 |
| `backend/routers/profiles.py` | L225-279 | `update_profile` 函数，理解 profile 写入逻辑 |
| `backend/routers/_profiles_helpers.py` | `_merge_profiles` | 合并逻辑 |
| `backend/routers/_profiles_graph.py` | `_auto_locate_on_graph` | 后台推荐生成 |
| `backend/routers/chat.py` | L432-720 | `_build_greeting` 完整逻辑 |
| `frontend/src/components/ChatPanel.tsx` | L96, L439-449 | GreetingData 类型 + chips 渲染 |

---

## 验收标准

1. 新用户（无画像）打开教练面板 → 能看到"没简历？对话建档"按钮
2. 点击后教练开始逐步提问（每次一个问题）
3. 5-6 轮后教练列出信息让用户确认
4. 确认后画像保存成功，画像页能看到数据
5. 推荐方向自动生成（后台线程）
6. 已有画像的用户看不到"对话建档"按钮
7. 代码无 TypeScript 编译错误，后端 import 正常

---

## 不要做的事

- 不改数据库 schema
- 不改 `PUT /profiles` 端点逻辑
- 不改现有的简历上传流程
- 不在 skill 里写死方向推荐（建完档后由系统 LLM 推荐）
- 不加新的 npm 依赖
