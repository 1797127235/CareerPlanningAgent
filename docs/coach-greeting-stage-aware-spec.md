# Spec：智析教练 · 阶段感知式问候

## 背景

打开画像页，智析教练的开场白目前在两个地方有问题：

1. **LLM 走 `coach-greeting` skill** 生成的开场（用户说"你好"时），会默认追问"想先了解市场情况，还是想聊聊具体怎么准备面试？"—— 这是**求职冲刺期**的选项，但实际用户可能还在探索方向阶段。
2. **`/chat/greeting` 端点的 templated 问候**走旧的 6 阶段系统（`backend/services/stage.py` 的 `compute_stage`），与我们新建的 4 阶段系统（`backend/services/career_stage.py` 的 `determine_stage`）不对接。

用户明确反馈：对一个**刚上传简历、还没选目标**的本科生，默认把他当成"要面试、要看市场"的求职者是场景错配。

## 目标

把问候的 **follow-up 问题/CTA chip** 按**新 4 阶段**（`exploring / focusing / job_hunting / sprinting`）分化：

| 阶段 | 判定 | 默认 follow-up |
|---|---|---|
| **exploring** | 无 profile OR 无 target_node_id | "要不要先对比几个方向的差别？" + 跳 `/explore` |
| **focusing** | 有 profile + target + 至少 1 份报告，未有面试 | "来聊聊目标岗位的差距还在哪" |
| **job_hunting** | 有 1-2 次面试记录 | "最近面试有什么想复盘的？"或"我帮你看看薄弱环节" |
| **sprinting** | ≥3 次面试 OR 有 offer | "offer 要比较吗？还是下一场面试准备？" |

**开场白文本本身保持通用**（不反引用 stage/画像，遵守原有 skill 设计原则），只**动态选择 follow-up 的语气和选项**。

## 非目标

- ❌ 不改 `coach-greeting` skill 的触发规则（依然是"用户只说问候语（≤10 字）时触发"）
- ❌ 不改 `coach-greeting` 的 "**禁止反引用画像细节**" 原则（技能/项目/偏好不出现在回复文本里）
- ❌ 不改 `coach_agent` 的 BASE_IDENTITY 主体（只在 CONTEXT 里补 stage）
- ❌ 不改 `/chat/greeting` 的 templated 分支逻辑（那套 6 阶段已经跑着，先不动）—— 本 spec 只改 LLM 回复路径
- ❌ 不引入弹窗/通知告诉用户"你现在处于 X 阶段"（阶段保持静默）
- ❌ 不新增路由、不加状态管理库、不动前端 ChatPanel

## 改动清单

### 1. `agent/supervisor.py` — 注入新 4 阶段到 state

当前 state 的 `user_stage` 是旧 6 阶段。改成用新 `determine_stage`。

**定位**：`_build_full_context` 函数大约在第 214 行：
```python
stage = state.get("user_stage", "unknown")
stage_labels = {
    "no_profile": "未建画像",
    "has_profile": "已有画像，未做JD诊断",
    "first_diagnosis": "已做首次JD诊断",
    ...
}
```

**改动**：
1. 找到 state 里写入 `user_stage` 的位置（可能在 `state_builder.py` 或 `navigator_agent.py`，grep `user_stage`）。把 `compute_stage` 调用换成 `determine_stage(user_id, db)`。
2. 更新 `stage_labels` 字典为新 4 阶段：

```python
stage_labels = {
    "exploring":  "探索方向（未选目标或未生成报告）",
    "focusing":   "已选目标，技能补齐中",
    "job_hunting": "求职中（面试 1-2 次）",
    "sprinting":  "冲刺期（面试 ≥3 次 或 有 offer）",
}
```

3. 兼容期：如果还有代码路径写入旧 stage 值，加一层映射（见下文"映射表"）。

**映射表**（万一短期内还有旧值）：
```python
_OLD_TO_NEW_STAGE = {
    "no_profile": "exploring",
    "has_profile": "exploring",     # 没 target 也算
    "first_diagnosis": "job_hunting",
    "training": "job_hunting",
    "growing": "sprinting",
    "report_ready": "sprinting",
}
# 读取时：stage = _OLD_TO_NEW_STAGE.get(raw_stage, raw_stage)
```

### 2. `agent/skills/coach-greeting/SKILL.md` — 加阶段条件

当前内容：
```markdown
## 规则
- 简单友好的问候 + 一个开放性问题
- **禁止**引用系统给你的用户画像细节
- ...

## 参考回复模式
- "你好呀，今天想聊点什么？"
- "嗨，最近有什么进展或者困扰我可以帮你看看？"
- "在的，你想从哪里开始？"
```

**改成**：

```markdown
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

⚠ **关键约束**：回复**文本本身**不要出现 "exploring/focusing/job_hunting/sprinting" 这些英文词，也不要出现 "探索期/冲刺期"等系统概念名，只**选择**对应的追问语气，用户感知层面是自然对话。

### 3. 验证 `CONTEXT` 里确实有 stage（supervisor.py）

查 `_build_full_context` / `_build_light_context`：确认每次生成 context 时都把新 stage 写进去，格式类似 `- 当前阶段: exploring（探索方向：未选目标或未生成报告）` 这种便于 LLM 读。

开工前跑一下确认：
```bash
grep -n "当前阶段" agent/supervisor.py
```
期望至少 2-3 个命中（light context + full context + triage context）。

### 4. 不需要改的

- ❌ `agent/agents/coach_agent.py` —— BASE_IDENTITY 已经通过 `{CONTEXT}` 注入 stage 信息，skill 会读到
- ❌ `backend/routers/chat.py` 的 `/chat/greeting` 端点 —— 那是 templated 路径，本 spec 不涉及
- ❌ 前端 `ChatPanel.tsx`

---

## 验收标准

### 后端行为
1. **exploring 阶段**（新账号、刚注册，没 profile）：
   - 用户输入"你好"
   - LLM 回复类似："你好呀，要不要先对比几个方向看看哪个适合你？"
   - **不出现**"了解市场情况"、"准备面试"

2. **focusing 阶段**（有画像 + 已设 target_node_id + 有报告，无面试）：
   - 用户输入"你好"
   - LLM 回复类似："嗨，想聊聊目标岗位的差距吗？"

3. **job_hunting 阶段**（成长档案里有 1-2 次 `category='interview'` 的 entry）：
   - 用户输入"你好"
   - LLM 回复类似："在的。最近面试有什么想复盘的吗？"

4. **sprinting 阶段**（≥3 次 interview 或有 offer）：
   - 用户输入"你好"
   - LLM 回复类似："有 offer 要比较吗？还是在准备下一场面试？"

### 守住设计原则
- 回复**不引用**用户具体技能（C++/Linux/项目名都不出现）
- 回复**不引用** stage 英文/中文名字本身（"exploring"、"探索期"不出现）
- 2-3 句，不用 markdown，不用 emoji

### 兼容
- 老账号（旧 stage 值写入过 state）仍能正常工作（映射表兜底）
- 不破坏现有 `/chat/greeting` 的 templated 分支
- 不影响其它 skill（market-signal、navigator 等）的使用

---

## 开工前校准

1. **确认 `determine_stage` 的签名**：
   ```bash
   grep -n "def determine_stage" backend/services/career_stage.py
   ```
   spec 里写的是 `determine_stage(user_id, db)`，实际核对一下

2. **找出所有写 `user_stage` 的位置**：
   ```bash
   grep -rn "user_stage" agent/ 2>/dev/null
   ```
   全部改成调 `determine_stage`，或者加映射

3. **确认 CONTEXT 注入了 stage**：
   ```bash
   grep -n "当前阶段" agent/supervisor.py
   ```

4. **GrowthEntry 模型字段名校准**（之前踩过的坑）：
   ```bash
   grep -n "class Growth" backend/db_models.py
   ```
   确认 `determine_stage` 里用的字段名（`category` / `kind` / `tags`）跟现有模型对上

---

## 工期估算

- 单人（熟后端 + 熟 agent skill 架构）：**2-3 小时**
  - 改 supervisor.py 映射 + 新 stage 注入：1 小时
  - 改 coach-greeting skill：30 分钟
  - 手测 4 阶段的回复：1 小时

---

## 完成后的交付物

```
修改：
  agent/supervisor.py               (注入新 stage，映射兼容旧值)
  agent/skills/coach-greeting/SKILL.md  (加 4 阶段 follow-up)
  可能：agent/state_builder.py 或 navigator_agent.py（看 user_stage 写入点在哪）

无新增文件。无数据库变更。无前端改动。
```

## 常见坑 & 提示

1. **LLM 的随机性**：即便 skill 里写清楚 "exploring 阶段问 X"，LLM 偶尔会回复 "了解市场还是准备面试"。如果测试中仍抽风，把反面教材写得更具体（明确列出"了解市场"这句不许出现）
2. **Skill 选择优先级**：确保 `coach-greeting` 在用户说"你好"时被选中，而不是 fall through 到其它 skill。可以在 description 里显式列出触发词
3. **阶段判定的边界**：`job_hunting` 和 `sprinting` 的分界是 "3 次面试"，这个阈值如果业务需要调整，改 `determine_stage` 一处即可
4. **不要给应届生推 sprinting 的 follow-up**：如果 `determine_stage` 错判成 sprinting，应届生看到 "offer 比较" 会懵。但判定逻辑本身 (有≥3 次 interview 或 offer) 应该是可信的
5. **不要改 coach-greeting 的 description 行**：只改 body。description 决定 skill 何时被选中，body 决定怎么回复
