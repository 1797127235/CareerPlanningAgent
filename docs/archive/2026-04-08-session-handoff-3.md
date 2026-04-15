# Session Handoff — 2026-04-08 (第三轮)

**分支**: `feat/kinetic-archive-redesign`
**目标**: 下一个会话继续重构推荐与画像模块

---

## 一、系统定位

**职业规划系统**（非招聘平台）。用户关心"怎么成长"而非"找什么工作"。

核心流程：上传简历 → 解析画像 → 推荐方向 → 选择目标 → 差距分析 → 学习成长

技术栈：React + TS + TailwindCSS / FastAPI + SQLAlchemy + SQLite / DashScope Qwen LLM

---

## 二、本轮完成的工作

### 2.1 推荐系统 LLM 化 + DB 持久化
- `GET /recommendations` — LLM 生成 5 个推荐（entry/growth/explore），结果存 `Profile.cached_recs_json`
- `POST /recommendations/refresh` — 强制重新生成
- `GET /recommendations/match-analysis/{role_id}` — gap 分析结果存 `Profile.cached_gaps_json`
- 缓存按 `profile_hash` 失效（画像变→缓存自动失效）

### 2.2 已删除的文件
- `frontend/src/pages/ProfilePage.tsx` — **已删除，需重写**
- `HomePage.tsx` 中的 `HomeRecommendations` 组件 — 已删除
- `backend/services/skill_match_service.py` — 547 行 token 匹配，已删
- `backend/services/recommendation_service.py` — 已删

### 2.3 Coverflow 文案修正
"锁定"→"设定"，目标可更改

---

## 三、Party Mode 讨论结论（PM + Architect + UX）

### 核心问题
用户点推荐卡片→等 60-90 秒 LLM gap 分析→全是加载中。**信息分层搞反了——用户还没决定选哪个，系统就在做选后的重活。**

### 共识方案

**1. 推荐卡片本身包含足够的决策信息（零额外 LLM 调用）**

推荐接口已返回 `gap_skills`（但没展示）。需要后端补齐 `matched_skills` 和 `gap_hours`。

卡片设计：
```
┌──────────────────────────────────────┐
│ C++ 工程师                     [95]  │  ← 环形图
│ 核心技能完全匹配...                   │
│                                      │
│ ✓ 已具备 12 项  · ✗ 需补齐 3 项      │  ← 成长距离
│ STL · 多线程 · CMake                  │  ← 具体 gap
│ ≈ 40h 学习量                         │
│                                      │
│              [ 设为目标 → ]           │  ← 唯一 CTA
└──────────────────────────────────────┘
```

**2. Gap 分析只在设为目标后异步触发**
- 设目标 → toast "正在生成详细分析" → 后台调 LLM → 存 DB
- 目标卡片中出现"查看差距分析"按钮（数据就绪时启用）
- MatchDetailPage 只从目标卡片进入

**3. 职业规划视角**
- 核心信息："我离这个方向有多远？需要学什么？要多久？"
- "已具备 X 项 · 需补齐 Y 项"比纯百分比更有规划感
- 薪资是次要信息

---

## 四、后端需补齐的数据

### `matched_skills` — 在 `_generate_recommendations()` 中补计算

```python
# roadmap_skills.json 中每个 role 有 must_skills（4-6 个）
role_must = set(node.get("must_skills", []))
user_skills_lower = {s.lower() for s in user_skills}
matched = [s for s in role_must if s.lower() in user_skills_lower]
```

### `gap_hours` — 基于 gap 数量估算

```python
gap_count = len(role_must) - len(matched)
gap_hours = gap_count * 15  # 每个 gap skill ~15h
```

当前代码位置：`backend/routers/recommendations.py` 的 `_generate_recommendations()` 函数，enriched 循环中 `matched_skills` 写死为 `[]`，`gap_hours` 写死为 `0`。

---

## 五、ProfilePage 重写规格

### 布局（12 列 grid，max-w-1000）

| 区块 | 位置 | 数据来源 |
|------|------|---------|
| 身份卡 | col-3, row-2 | profile.name, quality.completeness/competitiveness, skills.length |
| AI 诊断 | col-5 | primaryGoal.gap_skills + competitiveness 动态文案 |
| 目标岗位 | col-4 | career_goals[primary], graph_position |
| 推荐方向 | col-8 | `GET /recommendations`，**按新卡片设计** |
| 软技能评估 | col-4 | profile.soft_skills（SJT v2 三维度） |
| 技能标签 | col-4~9 | profile.skills[] |
| 知识领域 | col-5 | profile.knowledge_areas[] |
| 项目经历 | col-7 | profile.projects[] |

### 可复用组件
- `GoalPickerModal` — 目标选择模态
- `profile/ManualProfileForm` — 编辑画像
- `profile/UploadProgress` — 上传进度
- `profile/ProfileSkeleton` — 加载骨架
- `profile/ProfileEmptyState` — 空状态
- `profile/SjtCtaCard` — SJT 入口
- `shared/ScoreRing` — 环形分数图

### Hooks
- `useProfileData(token)` — 画像加载/编辑
- `useResumeUpload(loadProfile)` — 简历上传
- `useAuth()` — token

### 关键 state
- `recs: Recommendation[]` — 推荐列表
- `recsLoading: boolean`
- `settingGoalId: string | null`
- `showGoalPicker: boolean`
- `showSjtInline: boolean`
- `showAllSkills: boolean`

---

## 六、关键 API

| 接口 | 方法 | 用途 |
|------|------|------|
| `/api/profiles` | GET | 获取画像（含 career_goals, graph_position） |
| `/api/profiles` | PUT | 更新画像 |
| `/api/recommendations` | GET | 获取推荐（DB 缓存，秒返回） |
| `/api/recommendations/refresh` | POST | 强制重新生成 |
| `/api/recommendations/match-analysis/{role_id}` | GET | 深度 gap 分析 |
| `/api/graph/career-goal` | PUT | 设定/更换目标 |

---

## 七、前端路由状态

| 路由 | 状态 |
|------|------|
| `/` | 正常（推荐区块已删） |
| `/profile` | **已删除，需重写** |
| `/profile/match/:roleId` | 正常 |
| `/graph` | 正常 |
| 其他 | 正常 |

---

## 八、数据文件

- `data/graph.json` — 34 节点 + 130 边（zone, salary, career_level, must_skills, topics）
- `data/roadmap_skills.json` — 34 角色 × 60-180 技能（topics 列表，来自 developer-roadmap）
- `data/sjt_templates.json` — SJT 情境题模板

---

## 九、设计原则

1. **职业规划系统**，不是招聘平台
2. 全站 SaaS 简洁风 + 图谱页 3D 沉浸暗色
3. 功能串联成整体体验，不堆孤岛模块
4. 先理清用户流程再写代码
5. 方案先审查再实现
6. 未经用户许可不写代码
7. 写代码不能让现有代码变乱

---

## 十、下一步优先级

| 优先级 | 任务 | 范围 |
|--------|------|------|
| P0 | 后端补 `matched_skills` + `gap_hours` | `recommendations.py` |
| P0 | 重写 ProfilePage | 新建 `ProfilePage.tsx` |
| P1 | 设为目标后异步触发 gap 分析 + toast | 前端 + 后端 |
| P2 | GoalPickerModal 统一新卡片设计 | 组件更新 |
| P2 | 首页目标卡片增强 | HomePage |
