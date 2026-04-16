# 成长档案 v2 — 统一记录 + 计划

> **状态**：草案，待确认后实施
> **目标**：将项目进展、面试复盘、学习笔记、时间计划统一到一条流里
> **参考**：Flomo（单流 + 标签）+ 滴答清单（计划 + 完成状态）

---

## §1 核心设计

### 设计原则

1. **统一时间线** — 项目、面试、学习、计划全在一条流里
2. **录入按类型分** — 学习笔记轻量（一句话），面试/项目保留结构化表单
3. **标签体系** — 预设 `#项目` `#面试` `#学习` + 用户自由标签
4. **计划可追踪** — pending → done / dropped
5. **每条可问 AI** — 点击获取针对性建议，建议可转计划
6. **和报告挂钩** — 所有记录自动流入报告 milestones / signals

### 三种记录的录入差异

| 类型 | 录入方式 | 字段 |
|---|---|---|
| **学习笔记** | Flomo 式：常驻输入框写一句话 | content + tags |
| **面试复盘** | 结构化表单 | company, position, round, questions[], self_rating, result, reflection |
| **项目记录** | 结构化表单 | name, description, skills_used, github_url, status |

三种在时间线里**统一展示**，但点"新建"时根据选择的类型进入不同的录入界面。

---

## §2 数据模型

### 新增 `GrowthEntry` 表

不改动现有 `ProjectRecord` / `InterviewRecord` / `ProjectLog` 表。
`GrowthEntry` 是统一入口，通过 `category` + `structured_data` 覆盖所有类型。

```sql
CREATE TABLE growth_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),

    -- 内容
    content     TEXT    NOT NULL,            -- 正文（学习笔记=全部内容；面试/项目=摘要）
    category    VARCHAR(32) DEFAULT NULL,    -- project | interview | learning | NULL
    tags        JSON    DEFAULT '[]',        -- 预设 + 自由标签 ["面试", "字节", "算法"]

    -- 结构化数据（面试/项目用，学习笔记为 NULL）
    structured_data JSON DEFAULT NULL,
    -- 面试: {"company":"字节","position":"后端","round":"技术二面",
    --        "questions":[{"q":"Redis持久化","a":"答得不好，混淆了RDB和AOF"}],
    --        "self_rating":"bad","result":"pending","reflection":"..."}
    -- 项目: {"name":"网络库","description":"...","skills_used":["C++","epoll"],
    --        "github_url":"...","status":"in_progress"}

    -- 计划相关（记录型为 NULL）
    is_plan     BOOLEAN DEFAULT FALSE,
    status      VARCHAR(16) DEFAULT 'done',  -- done | pending | dropped
    due_type    VARCHAR(16) DEFAULT NULL,     -- daily | weekly | monthly | custom
    due_at      DATETIME DEFAULT NULL,

    -- AI 建议（点击后填充）
    ai_suggestions JSON DEFAULT NULL,        -- [{"text":"...","category":"..."}]

    -- 关联（可选，链接到旧表数据）
    linked_project_id     INTEGER DEFAULT NULL REFERENCES project_records(id),
    linked_application_id INTEGER DEFAULT NULL REFERENCES job_applications(id),

    -- 时间
    completed_at DATETIME DEFAULT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ge_user_created ON growth_entries(user_id, created_at DESC);
CREATE INDEX idx_ge_user_status  ON growth_entries(user_id, status);
```

### structured_data 示例

**面试复盘**：
```json
{
  "company": "字节跳动",
  "position": "后端开发实习",
  "round": "技术二面",
  "questions": [
    { "q": "Redis 持久化机制", "a": "只说了 RDB，忘了 AOF 和混合持久化" },
    { "q": "TCP 三次握手", "a": "答上来了" },
    { "q": "手撕：反转链表", "a": "写出来了但时间复杂度分析卡了" }
  ],
  "self_rating": "medium",
  "result": "pending",
  "reflection": "基础还行但 Redis 那块真得补"
}
```

**项目记录**：
```json
{
  "name": "基于 epoll 的高并发网络库",
  "description": "用 C++ 实现了 Reactor 模式的网络框架",
  "skills_used": ["C++", "Linux", "epoll", "多线程"],
  "github_url": "https://github.com/xxx/net-lib",
  "status": "in_progress"
}
```

**学习笔记**：`structured_data = NULL`，内容全在 `content` 字段。

---

## §3 与报告系统挂钩

### 当前报告数据流

```
summarize.py 读取:
  ProjectRecord / ProjectLog → milestones (project_progress / project_complete)
  InterviewRecord            → milestones (interview) + signals.interview
  JobApplication             → milestones (application) + signals.application
  SkillUpdate                → milestones (skill_update) + skill_deltas
```

### 新增 GrowthEntry 接入点

`summarize.py._build_milestones()` 末尾新增：

```python
# ── GrowthEntry (unified log) ──
entries = (
    db.query(GrowthEntry)
    .filter(
        GrowthEntry.user_id == user_id,
        GrowthEntry.status == "done",
        GrowthEntry.created_at >= since,
    )
    .order_by(GrowthEntry.created_at.desc())
    .limit(20)
    .all()
)
for entry in entries:
    counter += 1
    sd = entry.structured_data or {}
    if entry.category == "interview":
        title = f"{sd.get('company','')} {sd.get('round','面试')}"
        detail = entry.content[:200]
        skills = []  # 面试痛点由 extract-interview-signals skill 处理
    elif entry.category == "project":
        title = sd.get("name", entry.content[:40])
        detail = sd.get("description", "")[:200]
        skills = sd.get("skills_used", [])
    else:
        title = entry.content[:60]
        detail = entry.content[:200]
        skills = []

    items.append({
        "id": f"M-{counter:03d}",
        "date_iso": _iso(entry.completed_at or entry.created_at),
        "source": f"growth_entry:{entry.id}",
        "category": {"project": "project_progress", "interview": "interview",
                      "learning": "learning_note"}.get(entry.category, "note"),
        "title": title,
        "detail": detail,
        "skills_touched": skills,
    })
```

### 面试复盘 → 面试信号

`_build_interview_signal()` 新增读取 `GrowthEntry(category='interview')` 的 `structured_data.questions`，
合并进 `extract-interview-signals` skill 的输入，提取知识盲点。

### 计划 → 行动项闭环

- 报告 action-plan 建议 → 用户一键转 GrowthEntry 计划
- 用户完成计划 → 下次报告 `completed_since_last_report` 出现
- 用户未完成的计划 → 报告 action-plan 参考

---

## §4 后端 API

### 端点

```
POST   /api/growth-log/entries              创建
GET    /api/growth-log/entries              列表 (?status=pending&category=interview&tag=算法)
PATCH  /api/growth-log/entries/:id          更新
DELETE /api/growth-log/entries/:id          删除
POST   /api/growth-log/entries/:id/ai-suggest   获取 AI 建议
```

### 创建 — 学习笔记

```json
POST /api/growth-log/entries
{
  "content": "今天搞懂了动态规划的状态转移",
  "category": "learning",
  "tags": ["算法", "DP"]
}
```

### 创建 — 面试复盘

```json
POST /api/growth-log/entries
{
  "content": "字节二面，Redis 和链表答得不好",
  "category": "interview",
  "tags": ["字节", "面试"],
  "structured_data": {
    "company": "字节跳动",
    "position": "后端开发实习",
    "round": "技术二面",
    "questions": [
      { "q": "Redis 持久化", "a": "只说了 RDB，AOF 没答上来" },
      { "q": "反转链表", "a": "写出来了但复杂度分析卡了" }
    ],
    "self_rating": "medium",
    "result": "pending"
  }
}
```

### 创建 — 项目记录

```json
POST /api/growth-log/entries
{
  "content": "网络库 epoll 模块写完了",
  "category": "project",
  "tags": ["项目", "C++"],
  "structured_data": {
    "name": "高并发网络库",
    "skills_used": ["C++", "epoll", "Linux"],
    "status": "in_progress"
  }
}
```

### 创建 — 计划

```json
POST /api/growth-log/entries
{
  "content": "本周完成简历第二版",
  "is_plan": true,
  "due_type": "weekly",
  "due_at": "2026-04-20T23:59:59Z"
}
```

### 完成计划 / 更新状态

```json
PATCH /api/growth-log/entries/42
{ "status": "done" }
```

### AI 建议

```
POST /api/growth-log/entries/42/ai-suggest
```
请求体：无（后端读记录 + 画像 + 目标）

响应：
```json
{
  "suggestions": [
    { "text": "复习 RDB 和 AOF 的区别及触发机制", "category": "learning" },
    { "text": "LeetCode 206 反转链表，限时 10 分钟", "category": "learning" }
  ]
}
```

---

## §5 前端设计（v1 frontend）

### 页面结构

```
┌──────────────────────────────────────────┐
│ GoalBar（保留现有）                       │
├──────────────────────────────────────────┤
│ ┌──────────────────────────────────────┐ │
│ │  📝 写点什么…                [发送]  │ │  ← 常驻输入框（学习笔记）
│ │  #项目 #面试 #学习 +自定义    □计划  │ │
│ │              [面试复盘] [记录项目]    │ │  ← 结构化录入快捷入口
│ └──────────────────────────────────────┘ │
├──────────────────────────────────────────┤
│ ── 待完成的计划 ─────────────────────── │
│ □ 本周完成简历第二版         周日截止    │
│ □ 复习 RDB 和 AOF 区别       来自AI建议  │
├──────────────────────────────────────────┤
│ ── 今天 ─────────────────────────────── │
│ 搞懂了 TCP 三次握手          #学习      │
│                              [AI 建议]   │
│ ── 昨天 ─────────────────────────────── │
│ 字节跳动 · 技术二面           #面试      │
│  Q: Redis 持久化 → 只说了 RDB           │  ← 面试展开显示问答
│  Q: 反转链表 → 写出来了                 │
│  自评: 一般  结果: 待定                  │
│  AI: 1. 复习 RDB/AOF 区别 [转计划]      │
│      2. LeetCode 206 [转计划]           │
│ ── 更早 ─────────────────────────────── │
│ 网络库 epoll 模块写完了       #项目      │
│  技术栈: C++ · epoll · Linux            │  ← 项目展开显示技能
│  状态: 进行中                            │
└──────────────────────────────────────────┘
```

### 输入区域

常驻输入框支持两种模式：

**轻量模式**（默认）— 一个 textarea，写完发送，适合学习笔记和快速记录
**结构化模式** — 点击"面试复盘"或"记录项目"按钮后展开对应表单：

**面试复盘表单**：
```
公司名称:  [________]
岗位:      [________]
轮次:      [技术一面 ▼]
问了什么 & 我怎么答的:
  Q1: [________]  A1: [________]  [+ 加一题]
自评:      ○好  ●一般  ○差
结果:      ○通过  ○未通过  ●待定
复盘感受:  [________________]
                          [保存]  [取消]
```

**项目记录表单**：
```
项目名称:  [________]
简介:      [________________]
技术栈:    [React, Node.js, ...]
项目链接:  [________]（选填）
状态:      ○计划中  ●进行中  ○已完成
                          [保存]  [取消]
```

### 时间线卡片

三种类型的卡片样式不同：

**学习笔记** — 最简洁，就是文本 + 标签
```
搞懂了 TCP 三次握手的 SYN/ACK 过程     #学习 #网络
                                       [AI 建议]
```

**面试复盘** — 展开显示问答对
```
字节跳动 · 技术二面                     #面试
  Q: Redis 持久化 → 只说了 RDB，AOF 没答上来
  Q: 反转链表 → 写出来了但复杂度分析卡了
  自评: 一般  |  结果: 待定
  感受: 基础还行但 Redis 那块真得补
                                       [AI 建议]
```

**项目记录** — 显示技能和状态
```
网络库 epoll 模块写完了                  #项目
  高并发网络库 · C++ · epoll · Linux
  状态: 进行中
                                       [AI 建议]
```

### 和现有组件的关系

| 现有组件 | 处理方式 |
|---|---|
| `GoalBar` | 保留不变 |
| `FilterChips` | 改为：全部 / #项目 / #面试 / #学习 / 计划 |
| `RecordRow` | 扩展为 `EntryCard`，根据 category 渲染不同布局 |
| `NewRecordDialog` | 去掉，改为常驻输入框 + 结构化表单切换 |
| `AddProjectForm` | 内容迁移到新的结构化输入区 |
| `AddPursuitForm` | 替换为面试复盘表单 |
| 旧 `ProjectRecord` / `JobApplication` 数据 | `mergeRecords` 继续读，在时间线混排 |

### 空状态

输入框始终存在，页面不会空。时间线区域无记录时显示：
```
成长档案帮你把散落的经历串成时间线。
写点什么开始吧 —— 一句话、一次面试、一个项目，都算。
```

---

## §6 AI 建议功能

### 交互流程

1. 每条记录卡片上有 `[AI 建议]` 按钮
2. 点击 → 发送记录内容 + structured_data + 用户画像 + 目标方向 给 LLM
3. 返回 1-3 条建议，内联展示在卡片下方
4. 每条建议有 `[转为计划]` 按钮 → 创建 `GrowthEntry(is_plan=True)`

### 面试场景特殊处理

面试复盘的 AI 建议会针对每个没答好的问题给具体补强建议：
```
记录：字节二面，Redis 持久化答得不好
AI：1. 复习 RDB 快照 vs AOF 日志 vs 混合持久化的触发条件和优劣
    2. 手写一遍 LeetCode 206 反转链表，限时 10 分钟
    3. 整理"字节后端常考题"清单，重点看 Redis 和网络
         [转计划] [转计划] [转计划]
```

### Skill 文件

新增 `backend/skills/growth-suggest/SKILL.md`：
- 输入：记录内容 + structured_data + 用户技能列表 + 目标方向
- 输出：1-3 条具体可执行建议的 JSON
- 约束：必须具体（"复习 RDB/AOF 区别"），不能抽象（"加强 Redis 学习"）

---

## §7 迁移策略

不迁移旧数据。`ProjectRecord` / `InterviewRecord` / `JobApplication` / `ProjectLog` 继续存在，
`mergeRecords` 继续读它们。`GrowthEntry` 是增量，两者在时间线里混排。

报告系统同时读两边，不遗漏。

---

## §8 实施顺序

| 步骤 | 内容 | 影响范围 |
|---|---|---|
| 1 | `GrowthEntry` ORM model + DB migration | backend/db_models.py |
| 2 | CRUD API `/api/growth-log/entries` | backend/routers/growth_log.py |
| 3 | AI 建议 API + `growth-suggest` skill | backend + skills |
| 4 | `summarize.py` 接入 GrowthEntry | 报告系统 |
| 5 | 前端：常驻输入框 + 结构化表单切换 | frontend |
| 6 | 前端：`EntryCard` 三种布局 | frontend |
| 7 | 前端：计划区 + 时间线混排 | frontend |
| 8 | 前端：AI 建议交互 + 转计划 | frontend |

---

## §9 已确认的决策

1. **计划不循环** — 手动建立，完成后不自动重建
2. **标签 = 预设 + 自由输入** — 预设 `#项目` `#面试` `#学习`，用户可自建
3. **面试保留结构化** — 公司/轮次/问答对/自评/结果/复盘，不简化为纯文本
4. **项目保留结构化** — 项目名/技能/状态，不简化为纯文本
5. **学习笔记走轻量** — Flomo 式一句话
6. **每条记录可点 AI 建议** — 1-3 条具体建议，可转计划
7. **旧数据不迁移** — 新旧混排
