# Kimi 执行计划：教练引导建档（无简历入口）

## 背景

当前系统极度依赖简历上传才能建立画像。大一大二学生可能没有简历，系统对他们无用。
需要增加一条"教练问答建档"路径：教练通过 5-6 个问题收集信息，直接写入 profile，
触发推荐流程，用户无需上传任何文件。

## 架构总览

```
用户在教练面板说"我没有简历" / 点击"对话建档"chip
  → 教练加载 coach-profile-builder skill
  → 逐步提问（专业、技能、项目、偏好）
  → 每轮积累数据，最后调 save_profile_from_chat tool 写入
  → 后台自动跑 _auto_locate_on_graph（和简历上传后完全一样）
  → 画像页 + 推荐方向立即可用
```

---

## 任务 1：新增 coach tool — `save_profile_from_chat`

**文件**: `agent/tools/coach_context_tools.py`

在现有 tools 之后新增：

```python
@tool
def save_profile_from_chat(profile_data: str) -> str:
    """将教练对话中收集的用户信息保存为画像。

    参数:
        profile_data: JSON 字符串，包含教练从对话中收集的画像数据。
                      格式：{"education": {"degree": "本科", "major": "计算机科学", "school": "XX大学"},
                             "skills": [{"name": "Python", "level": "familiar"}, ...],
                             "projects": ["项目描述1", ...],
                             "job_target": "后端开发",
                             "experience_years": 0,
                             "knowledge_areas": ["数据结构", ...],
                             "preferences": {"work_style": "tech", ...}}

    何时调用：
    - 教练通过问答收集完用户信息后，一次性保存
    - 用户确认信息无误后再调用

    何时不调用：
    - 还在提问过程中（信息不完整）
    - 用户没有确认
    """
    user_id = _ctx_user_id.get()
    if not user_id:
        return "用户未登录，无法保存画像"

    try:
        import json as _json
        data = _json.loads(profile_data)
    except (json.JSONDecodeError, TypeError):
        return "数据格式错误，请检查 JSON 格式"

    # 标记来源
    data["source"] = "chat_guided"

    try:
        from backend.db import SessionLocal
        from backend.db_models import Profile
        from backend.routers.profiles import _get_or_create_profile
        from backend.services.profile_service import ProfileService
        from backend.routers._profiles_graph import _auto_locate_on_graph

        db = SessionLocal()
        try:
            profile = _get_or_create_profile(user_id, db)

            # Merge with existing profile (don't overwrite resume data if any)
            existing = _json.loads(profile.profile_json or "{}")
            if existing.get("skills"):
                # 已有简历数据，合并模式
                from backend.routers._profiles_helpers import _merge_profiles
                merged = _merge_profiles(existing, data)
            else:
                merged = data

            profile.profile_json = _json.dumps(merged, ensure_ascii=False)
            quality_data = ProfileService.compute_quality(merged)
            profile.quality_json = _json.dumps(quality_data, ensure_ascii=False)
            db.commit()
            db.refresh(profile)

            # 后台跑图谱定位 + 推荐（和简历上传后完全一样）
            import threading
            _pid, _uid = profile.id, user_id
            _final = _json.loads(profile.profile_json)

            def _bg():
                _bg_db = SessionLocal()
                try:
                    _auto_locate_on_graph(_pid, _uid, _final, _bg_db)
                except Exception:
                    pass
                finally:
                    _bg_db.close()

            threading.Thread(target=_bg, daemon=True).start()

            skill_count = len(merged.get("skills", []))
            return f"画像已保存！识别到 {skill_count} 项技能。系统正在后台生成推荐方向，刷新画像页即可查看。"
        finally:
            db.close()
    except Exception as e:
        logger.warning("save_profile_from_chat failed for user=%s: %s", user_id, e)
        return f"保存画像失败：{e}"
```

**同时在 `coach_agent.py` 的 tools 列表里注册这个新 tool**：

```python
from agent.tools.coach_context_tools import (
    get_user_profile, get_career_goal, get_market_signal, get_memory_recall,
    get_recommended_roles, save_profile_from_chat,
)

# 在 create_coach_agent() 的 tools= 列表里加上:
save_profile_from_chat,
```

---

## 任务 2：新增 skill — `coach-profile-builder`

**文件**: `agent/skills/coach-profile-builder/SKILL.md`

```markdown
---
name: coach-profile-builder
description: "当用户没有简历、想通过对话建立画像时使用。触发条件：用户说'我没有简历/帮我建画像/不知道怎么写简历'，或 CONTEXT 显示无画像 + 用户表达想了解方向。边界：已有画像的用户走其他 skill。"
---

## 场景
用户没有简历，或不想上传简历，想通过和教练对话来建立基础画像。

## 核心任务
通过 5-6 个问题收集用户的关键信息，构建一份基础画像，然后调 save_profile_from_chat 保存。

## 提问流程

按以下顺序提问，每次只问一个问题，等用户回答后再问下一个。
语气自然，像朋友聊天，不要像填表。

### 第 1 问：专业背景
"你是什么专业的？大几了？"
→ 提取: education.major, education.degree, experience_years

### 第 2 问：技术技能
"你目前会哪些编程语言或技术？不用谦虚，了解过的也算。"
→ 提取: skills[] (用户说的每个技能，根据描述判断 level: beginner/familiar/intermediate/proficient/expert)

### 第 3 问：项目经历
"做过什么项目吗？课程设计、个人项目、比赛作品都算。简单说说做了什么就行。"
→ 提取: projects[]
→ 如果用户说没有，跳过，不强求

### 第 4 问：兴趣方向
"你对哪类工作比较感兴趣？比如写代码、做产品、搞数据、还是没想好？"
→ 提取: preferences.work_style (tech/product/data/management)

### 第 5 问：求职意向
"有没有特别想做的岗位方向？比如后端、前端、算法之类的。没想好也没关系。"
→ 提取: job_target (如果用户说没想好，设为空字符串)

### 第 6 问（可选）：确认
把收集到的信息简要列出来，问用户"这些信息对吗？我帮你建档。"
→ 用户确认后，调 save_profile_from_chat

## 数据组装规则

收集完后，组装成 JSON 调 save_profile_from_chat：

```json
{
  "education": {"degree": "本科", "major": "计算机科学与技术"},
  "experience_years": 0,
  "skills": [
    {"name": "Python", "level": "familiar"},
    {"name": "C", "level": "beginner"}
  ],
  "projects": ["用 Python 写了一个简单的爬虫，抓取豆瓣电影 Top250"],
  "job_target": "",
  "knowledge_areas": ["数据结构", "操作系统"],
  "preferences": {"work_style": "tech"}
}
```

## 技能等级判断指南
- "学过/了解过/课上学的" → beginner
- "用过/做过小项目" → familiar
- "比较熟/经常用" → intermediate
- "很熟练/大量使用" → proficient
- "精通/深入研究过源码" → expert

## 回复风格
- 每次只问一个问题，不要一次问多个
- 用户回答后给一句简短回应（"不错"/"好的"），然后问下一个
- 不要评价用户技能强不强，客观记录
- 最后确认时，列出关键信息（不要列 JSON），让用户看着自然

## 禁止
- 一次问多个问题
- 评判用户水平（"你的技能比较基础"）
- 推荐方向（建完档后由系统推荐，不是教练编）
- 跳过确认步骤直接保存
```

---

## 任务 3：前端 — 教练面板增加"对话建档"入口

**文件**: `frontend/src/components/ChatPanel.tsx`

### 3.1 在空状态（无画像）时显示"对话建档"chip

找到 `defaultChips` 数组（约第 31 行），不需要改它。

找到教练面板的空状态区域（约第 401-451 行），在 greeting 没有数据且用户无画像时，
增加一个专门的引导 chip：

```typescript
// 在 greeting/chips 渲染区域，增加判断：
// 如果 greetingData 的 greeting 包含"上传简历"或"了解你"相关内容，
// 追加一个"对话建档"chip
```

具体做法：在 chips 渲染的 `(greetingData?.chips ?? defaultChips)` 之后，
追加一个固定 chip：

```tsx
{!hasProfile && (
  <button
    onClick={() => sendMessage('我没有简历，能通过聊天帮我建立画像吗？')}
    className="chip text-[12px] font-medium text-[var(--text-2)] hover:text-[var(--text-1)] active:scale-[0.97] transition-transform"
  >
    没简历？对话建档
  </button>
)}
```

### 3.2 需要知道 hasProfile 状态

ChatPanel 目前不知道用户是否有画像。需要从外部传入或内部查询。

**方案 A（推荐）**：在 `ChatPanel` 的 `greetingData` 里增加 `has_profile` 字段，
后端 greeting 接口已有 profile 信息，只需返回一个布尔值。

**后端改动**（`backend/routers/chat.py` 的 `_build_greeting` 函数）：

在 return dict 里加一个字段：

```python
return {
    "greeting": greeting,
    "chips": chips,
    "market_card": market_card,
    "processing": processing,
    "has_profile": has_profile,  # 新增
}
```

`has_profile` 的值在 `_build_greeting` 里已经有了（约第 439 行的 `profile` 变量判断）。

**前端改动**：

```typescript
// GreetingData interface 加字段
interface GreetingData {
  greeting: string;
  chips: Chip[];
  market_card?: MarketCardData;
  processing?: boolean;
  has_profile?: boolean;  // 新增
}

// 渲染 chip 时判断
{!greetingData?.has_profile && (
  <button
    onClick={() => sendMessage('我没有简历，想通过对话建立画像')}
    className="chip text-[12px] font-medium text-[var(--text-2)] hover:text-[var(--text-1)] active:scale-[0.97] transition-transform"
  >
    没简历？对话建档
  </button>
)}
```

---

## 任务 4：后端 greeting 返回 has_profile

**文件**: `backend/routers/chat.py`

在 `_build_greeting` 函数的 return dict 里加 `has_profile`。

找到函数里判断 profile 的位置（约第 439 行）：
```python
has_profile = profile is not None and bool(profile.profile_json and profile.profile_json != '{}')
```

在最终 return 的 dict 里加上：
```python
"has_profile": has_profile,
```

---

## 验证清单

1. **无画像用户**：打开教练面板 → 看到"没简历？对话建档"chip → 点击 → 教练开始逐步提问
2. **5-6 轮问答**：教练依次问专业、技能、项目、兴趣、意向 → 最后列出信息让用户确认
3. **保存画像**：用户确认后教练调 save_profile_from_chat → 画像页出现数据
4. **推荐生成**：保存后后台跑 _auto_locate_on_graph → 刷新画像页能看到推荐方向
5. **已有画像用户**：不显示"对话建档"chip → 教练不会主动走建档流程
6. **教练 + 画像页数据一致**：教练说的推荐方向和画像页显示的完全一致

---

## 文件改动清单

| 文件 | 改动 |
|------|------|
| `agent/tools/coach_context_tools.py` | 新增 `save_profile_from_chat` tool |
| `agent/agents/coach_agent.py` | tools 列表注册新 tool |
| `agent/skills/coach-profile-builder/SKILL.md` | 新建 skill 文件 |
| `backend/routers/chat.py` | `_build_greeting` 返回 `has_profile` |
| `frontend/src/components/ChatPanel.tsx` | 空状态增加"对话建档"chip |

---

## 注意事项

- `save_profile_from_chat` 里用 `_get_or_create_profile` 而不是手动查 DB，确保逻辑和 PUT /profiles 一致
- 用 `_merge_profiles` 合并已有数据，不要覆盖简历解析的结果
- `source` 字段设为 `"chat_guided"` 以便后续区分数据来源
- 教练 skill 的 level 判断要保守（用户说"学过" → beginner，不要高估）
- 教练不要在建档过程中推荐方向，建完后由系统推荐
