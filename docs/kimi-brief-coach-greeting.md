# Kimi 执行提示词：智析教练 · 阶段感知式问候

## 背景

用户说"你好"时，成长教练会走 `coach-greeting` skill 生成开场白。当前问题：

1. 开场白默认问"想了解市场情况，还是聊怎么准备面试？"——对还在探索方向的用户是场景错配
2. `user_stage` 用的是旧 6 阶段系统（`compute_stage`），但我们已经有新 4 阶段系统（`determine_stage`）

**目标**：把 `user_stage` 切换到新 4 阶段（exploring/focusing/job_hunting/sprinting），让 coach-greeting skill 根据阶段选择合适的追问句。

**完整 spec 见**：`docs/coach-greeting-stage-aware-spec.md`

---

## 改动清单（共 2 个文件）

### 改动 1：`backend/routers/chat.py`（约第 225-297 行）

**目的**：把 `user_stage` 的值从旧 6 阶段换成新 4 阶段。

**当前代码**（第 225 行、第 288-297 行）：

```python
from backend.services.stage import compute_stage

# ... 中间省略 ...

# 4. Compute journey stage
profile_count = db.query(func.count(Profile.id)).filter_by(user_id=user.id).scalar() or 0
jd_count = db.query(func.count(JDDiagnosis.id)).filter_by(user_id=user.id).scalar() or 0
project_count = db.query(func.count(ProjectRecord.id)).filter_by(user_id=user.id).scalar() or 0
app_count = db.query(func.count(JobApplication.id)).filter_by(user_id=user.id).scalar() or 0
interview_count = db.query(func.count(InterviewRecord.id)).filter_by(user_id=user.id).scalar() or 0
activity_count = project_count + app_count + interview_count
report_count = db.query(func.count(Report.id)).filter_by(user_id=user.id).scalar() or 0

state["user_stage"] = compute_stage(profile_count, jd_count, activity_count, report_count)
```

**改成**：

```python
from backend.services.career_stage import determine_stage

# ... 中间省略 ...

# 4. Compute journey stage (新 4 阶段)
state["user_stage"] = determine_stage(user.id, db)
```

**注意**：
- 删掉第 225 行的 `from backend.services.stage import compute_stage`（文件顶部或局部 import 位置）
- 删掉第 289-296 行那 7 行 count 查询（`profile_count`, `jd_count`, `project_count`, `app_count`, `interview_count`, `activity_count`, `report_count`）——这些都不再需要，`determine_stage` 内部自己查
- 把第 297 行替换成 `state["user_stage"] = determine_stage(user.id, db)`
- 加上新的 import：`from backend.services.career_stage import determine_stage`
- `compute_stage` 这个 import 如果没有其他地方用了就删掉（grep 确认下）
- `report_count` 如果后面还有用到（搜索 `report_count`），需要保留那一行或重新查询。搜一下确认

### 改动 2：`agent/supervisor.py`（第 214-222 行）

**目的**：更新 `_build_full_context` 里的 `stage_labels` 字典，把旧 6 阶段标签换成新 4 阶段标签，并加一个兼容映射。

**当前代码**（第 214-222 行）：

```python
stage = state.get("user_stage", "unknown")
stage_labels = {
    "no_profile": "未建画像",
    "has_profile": "已有画像，未做JD诊断",
    "first_diagnosis": "已做首次JD诊断",
    "training": "面试训练中",
    "growing": "持续成长中",
    "report_ready": "可生成报告",
}
parts.append(f"- 当前阶段: {stage_labels.get(stage, stage)}")
```

**改成**：

```python
_OLD_TO_NEW_STAGE = {
    "no_profile": "exploring",
    "has_profile": "exploring",
    "first_diagnosis": "job_hunting",
    "training": "job_hunting",
    "growing": "sprinting",
    "report_ready": "sprinting",
}

raw_stage = state.get("user_stage", "unknown")
stage = _OLD_TO_NEW_STAGE.get(raw_stage, raw_stage)

stage_labels = {
    "exploring": "探索方向（未选目标或未生成报告）",
    "focusing": "已选目标，技能补齐中",
    "job_hunting": "求职中（面试 1-2 次）",
    "sprinting": "冲刺期（面试 ≥3 次 或 有 offer）",
}
parts.append(f"- 当前阶段: {stage_labels.get(stage, stage)}")
```

**注意**：
- `_OLD_TO_NEW_STAGE` 字典可以定义为模块级常量（放在文件顶部附近），不需要每次调用都创建
- light context 分支（第 95-96 行）也读了 `user_stage`，也需要同样加映射。找到这段：

```python
# 第 94-96 行
if human_count <= 4:
    stage = state.get("user_stage", "unknown")
    lines = [f"- 当前阶段：{stage}"]
```

改成：

```python
if human_count <= 4:
    raw_stage = state.get("user_stage", "unknown")
    stage = _OLD_TO_NEW_STAGE.get(raw_stage, raw_stage)
    lines = [f"- 当前阶段：{stage_labels.get(stage, stage)}"]
```

这里 `_OLD_TO_NEW_STAGE` 和 `stage_labels` 都需要在函数外或文件顶部定义，让两处都能访问。

### 改动 3：`agent/skills/coach-greeting/SKILL.md`

**目的**：在 skill 的规则和参考回复模式中加入 4 阶段匹配逻辑。

**当前全文**（25 行）在 `agent/skills/coach-greeting/SKILL.md`。

**完整替换为以下内容**（保持 frontmatter description 行不变）：

```markdown
---
name: coach-greeting
description: "当用户本轮消息只是纯问候语（你好/嗨/hi/hello/hey/在吗/喂/哈喽 等），通常不超过 10 字，没有其他具体问题或请求时使用。应用本 skill：简单友好问候 + 一个开放性问题，禁止反引用系统里的用户画像细节（技能/项目/stage/偏好），不调用任何工具。"
---

## 场景
用户刚开口对话，只说了问候语。系统虽然知道用户画像/偏好/历史，但**不要反引用**。

## 规则
- 简单友好的问候 + **一个阶段匹配的开放性问题**
- **禁止**引用系统给你的用户画像细节（技能/项目/偏好/stage 名字本身）
- **禁止**假设用户情绪（迷茫/焦虑）
- **不调用任何工具**
- 2-3 句足够

## 阶段匹配（从 CONTEXT 的 "当前阶段" 字段读取）

按当前用户的 career_stage（CONTEXT 里有）选对应的 follow-up 问题；**问候语本身保持通用**，只变换追问：

- **exploring（探索方向）** → "要不要先对比几个方向看看？" 或 "想先了解几个岗位真实是什么样的吗？"
- **focusing（已选目标）** → "想聊聊目标岗位的差距，还是看看怎么快速补齐？"
- **job_hunting（求职中）** → "最近面试有什么想复盘的？"或 "需要帮你看看接下来哪里该集中准备吗？"
- **sprinting（冲刺）** → "是 offer 需要比较，还是在准备下一场面试？"
- **未知阶段** → "今天想聊点什么？有什么困扰我可以帮你看看。"

## 参考回复模式（exploring 示例）
- "你好呀，要不要先对比几个方向看看哪个适合你？"
- "嗨，今天想从哪聊起？可以先看看你推荐里几个方向的差别。"

## 参考回复模式（job_hunting 示例）
- "在的。最近面试有什么想复盘吗？"
- "你好，最近有场面试没？我可以帮你看看哪里还能加强。"

## 反面教材（不要这样）
- ❌ "看到你 C++ 基础很扎实..."（反引用技能画像）
- ❌ "你现在处于 exploring 阶段..."（反引用 stage 名字本身）
- ❌ "想先了解市场情况，还是聊聊具体怎么准备面试？"（对 exploring 用户是场景错配）
```

**关键约束**：回复文本不要出现 exploring/focusing/job_hunting/sprinting 这些英文词，也不要出现"探索期/冲刺期"等系统概念名。

---

## 不需要改的文件

- ❌ `agent/agents/coach_agent.py` — BASE_IDENTITY 通过 `{CONTEXT}` 注入 stage，不用动
- ❌ `backend/routers/chat.py` 的 `/chat/greeting` 端点 — 那是 templated 路径，不涉及
- ❌ 前端任何文件
- ❌ `backend/services/stage.py` — 旧文件保留不删（可能别处还用）
- ❌ `backend/services/career_stage.py` — 已经写好，不用改

---

## 执行前确认清单

1. **确认 `determine_stage` 签名**：
   ```bash
   grep -n "def determine_stage" backend/services/career_stage.py
   ```
   期望输出：`24:def determine_stage(user_id: int, db: Session) -> Stage:`

2. **确认 `compute_stage` 是否还有其他调用者**：
   ```bash
   grep -rn "compute_stage" backend/ agent/ 2>/dev/null
   ```
   如果只在 `chat.py` 的 import 和调用处出现，可以安全删掉 import。如果别处还用，保留旧文件。

3. **确认 `report_count` 后续没有被引用**：
   ```bash
   grep -n "report_count" backend/routers/chat.py
   ```
   如果除了第 295-297 行外还有用到，需要保留那行查询。

4. **改完后跑服务确认**：
   ```bash
   python -m uvicorn backend.app:app --reload
   ```
   打开聊天页，输入"你好"，确认回复：
   - 新账号（exploring）→ 不出现"了解市场情况"或"准备面试"
   - 有画像+目标+报告（focusing）→ "聊聊差距"类追问
   - 有面试记录（job_hunting）→ "复盘面试"类追问

---

## 总结

| # | 文件 | 改动 |
|---|------|------|
| 1 | `backend/routers/chat.py` | import 换成 `determine_stage`，删 7 行 count 查询，1 行赋值替换 |
| 2 | `agent/supervisor.py` | `stage_labels` 换成新 4 阶段 + `_OLD_TO_NEW_STAGE` 兼容映射（2 处） |
| 3 | `agent/skills/coach-greeting/SKILL.md` | 全文替换，加 4 阶段 follow-up + 反面教材 |

无新增文件。无数据库变更。无前端改动。
