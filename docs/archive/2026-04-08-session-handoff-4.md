# Session Handoff — 2026-04-08 (第四轮)

**分支**: `feat/kinetic-archive-redesign`
**目标**: 学习路径 P0 实现 + 画像页已完成的改造

---

## 一、本轮完成的工作

### 1.1 ProfilePage 重写
- 方案 A：左侧身份栏（sticky）+ 右侧内容流
- 左栏：头像/姓名、画像完整度环（去掉了竞争力）、目标岗位+gap概览、软技能迷你状态、操作按钮
- 右栏：推荐方向（按 entry/growth/explore 分组）、技能+项目（双列）、教育+软技能（双列）
- 上传功能接入 useResumeUpload hook

### 1.2 RoleDetailDrawer 新增
- 推荐卡片 CTA 从"设为目标"改为"了解这个方向→"
- 点击打开右侧抽屉（glass 风格，slide-in）
- 抽屉内容：岗位介绍（中文，来自 role_intros.json）+ AI 趋势（替代压力/协作空间进度条，数据来源 Anthropic Economic Index）+ 已具备/需补齐技能（前端计算 must_skills ∩ user_skills）+ 确认设为目标按钮
- 两步确认流程：了解→确认，避免轻率决策

### 1.3 GoalPickerModal 移除
- Layout.tsx 不再弹 GoalPicker
- 上传简历确认姓名后直接跳 /profile
- 推荐在画像页右栏自然加载，用户准备好了在抽屉里确认

### 1.4 数据文件新增/更新
- `data/role_intros.json` — 34 个岗位中文介绍（从 developer-roadmap 英文翻译，DashScope qwen-turbo）
- `data/learning_paths.json` — 59 个角色结构化学习路径（31 当前 + 28 扩展预留）
  - 结构：role_id → topics[] → subtopics[]，每个 subtopic 有 description + resources
  - 从 developer-roadmap 的 roadmap JSON（edge + 空间位置）+ content/*.md 提取

### 1.5 后端改动
- `/graph/node/{id}` 返回增加 `intro` 字段（从 role_intros.json 读）
- `mock_interview_sessions` 表加 `application_id` 列（DB migration）
- 竞争力字段前端不再展示（后端保留不删）

### 1.6 前端改动
- HomePage：去掉竞争力指标，进度条改为完整度驱动
- ProfilePage：去掉竞争力环，保留完整度单环
- 薪资相关数据全部标注"不展示"

---

## 二、设计决策记录

### 用户流程共识
```
我是谁（画像）→ 能去哪（推荐）→ 选哪个（抽屉确认）→ 差什么（gap分析）→ 怎么补（学习路径）→ 跟踪成长（闭环）
```

### 去掉的东西
- 竞争力字段 — 无真实客户数据做基准，误导学生
- 薪资展示 — 职业规划系统不是招聘平台
- GoalPickerModal 弹窗 — 不逼用户在上传后立即选目标
- gap_hours（预计学习量）— 拍脑袋数据

### 数据源确认
- 岗位图谱基于 developer-roadmap 83 个路线图
- AI 替代度来自 Anthropic Economic Index + O*NET
- 岗位介绍从 developer-roadmap 的 question.description/briefDescription 翻译

---

## 三、下一步：P0 学习路径实现

### Party Mode 审核共识

**MVP 范围**（John/PM）：
- 展示 gap topics 的 subtopic 列表 + content + 资源链接
- 完成标记（存 DB）
- 进度百分比展示
- 回写画像和覆盖率更新作为 P1

**后端**（Winston/Architect）：
- 扩展现有 LearningService，加载 learning_paths.json（singleton，启动时加载）
- 新增 `get_learning_path(role_id, gap_topics)` 方法
- API：
  - `GET /learning-path/{role_id}?gap_topics=topic1,topic2` — 返回过滤后 topics + subtopics + 完成状态
  - `POST /learning-path/progress` `{ topic_id, completed }` — 写入完成标记
- DB 表：
  ```sql
  learning_progress:
    profile_id   INT
    role_id      VARCHAR(64)
    topic_id     VARCHAR(128)  -- roadmap subtopic node id
    completed    BOOLEAN
    completed_at DATETIME
  ```

**前端**（Sally/UX）：
- 入口：画像页左栏目标区块加"查看学习路径→"CTA
- 路由：`/profile/learning`（或 `/learning/{role_id}`）
- 展示：
  - 顶部：总进度条 + 鼓励文案
  - 默认折叠，只展开第一个 gap topic
  - 每个 topic 卡片显示"3/12 已完成"
  - 手风琴展开 subtopic：描述 + 资源链接（按类型分）+ [标记已完成]
- 微交互：标记完成 → 勾变绿 → topic 进度更新 → 最后一个完成时自动展开下一个

---

## 四、关键文件索引

| 文件 | 用途 |
|------|------|
| `frontend/src/pages/ProfilePage.tsx` | 画像页（左栏+右栏布局） |
| `frontend/src/components/RoleDetailDrawer.tsx` | 岗位详情右侧抽屉 |
| `frontend/src/components/Layout.tsx` | 上传后跳 /profile，不弹 GoalPicker |
| `frontend/src/pages/HomePage.tsx` | 首页（去掉竞争力） |
| `data/role_intros.json` | 34 个岗位中文介绍 |
| `data/learning_paths.json` | 59 个角色结构化学习路径 |
| `data/graph.json` | 34 节点岗位图谱 |
| `backend/routers/graph.py` | /graph/node/{id} 含 intro 字段 |
| `backend/services/learning_service.py` | 待扩展：加载 learning_paths.json |
| `docs/spec-profile-page.md` | ProfilePage + RoleDetailDrawer 实现规格 |

---

## 五、数据质量已知问题

- learning_paths.json 空间匹配有少量噪音（如 C++ Build Systems 吸收了不属于它的节点）
- 后续可加 `data/learning_path_overrides.json` 手动修正
- devsecops、kotlin、docker、golang 缺少 roadmap JSON 或结构不兼容，暂无学习路径数据
