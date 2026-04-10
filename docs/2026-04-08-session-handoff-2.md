# Session Handoff — 2026-04-08 (第二轮)

## 分支
`feat/kinetic-archive-redesign`，所有改动未提交。

## 本轮完成的工作

### 后端改动

| 文件 | 改动 |
|------|------|
| `backend/services/gap_analyzer.py` | **新文件**。LLM gap 分析，精简 prompt，2次重试 × 90s 超时，失败返回 `failed: true` 标记 |
| `backend/services/recommendation_service.py` | **新文件**。图谱感知推荐算法：skill affinity × graph proximity × family bonus × level direction，3通道（entry/growth/explore） |
| `backend/routers/recommendations.py` | **新文件**。`POST /match-analysis`（并行 ThreadPoolExecutor），`GET /match-analysis/{roleId}`（返回 label），失败结果不缓存 |
| `backend/llm.py` | 模型 `qwen-turbo` → `qwen3.6-plus`（fast/router/default 全部） |
| `backend/routers/profiles.py` | `_auto_locate_on_graph` 不再自动设 `target_node_id`；名字同步仅在 `profile.name` 为空时 |
| `backend/routers/guidance.py` | `app_count` 排除 `pending` 状态 |

### 前端改动

| 文件 | 改动 |
|------|------|
| `frontend/src/api/recommendations.ts` | **新文件**。`MatchAnalysisResult`（含 `failed?`）、`MatchDetail`（含 `label?`, `failed?`）类型，`fetchMatchDetail` 60s 前端超时 |
| `frontend/src/pages/MatchDetailPage.tsx` | **新文件**。方案B双栏对比布局（Gemini 实现），glass 背景，4状态处理（loading/error/failed/success），`setData(null)` 防旧数据残留 |
| `frontend/src/pages/ProfilePage.tsx` | 匹配结果 sessionStorage 持久化；失败卡片灰显点击重匹配；SJT 改全屏遮罩；布局 8:4；紫色→蓝色；grid `content-center` + `py-6` |
| `frontend/src/components/Layout.tsx` | 命名弹窗仅在 `!profile.name` 时显示 |
| `frontend/src/hooks/useResumeUpload.ts` | `justUploaded` 在 `await onSuccess()` 之后设置 |

### 数据改动

| 文件 | 改动 |
|------|------|
| `data/graph.json` | 34 节点 + 111 边（92 related + 19 promotion），每个节点有 `soft_skills` 和 `promotion_path` |
| `data/sjt_templates.json` | 25 个模板（5维度 × 5），维度：communication/learning/collaboration/innovation/resilience |

### 新增文档/demo

| 文件 | 用途 |
|------|------|
| `docs/prompt-gemini-match-analysis.md` | Gemini 前端提示词（ProfilePage 匹配方向区域）|
| `docs/prompt-gemini-match-detail-redesign.md` | Gemini 前端提示词（MatchDetailPage 方案B重写）|
| `demos/match-detail-A.html` | 方案A demo（环形图+紧凑列表）|
| `demos/match-detail-B.html` | **方案B demo（双栏对比，用户选中）** |
| `demos/match-detail-C.html` | 方案C demo（时间线学习路径）|

## 已知问题

1. **前端死代码未清理** — 上一轮识别了 7 个未用组件（510 行）+ 11 个未用 API 函数，未删除
2. **SJT 文案** — `SjtCtaCard.tsx` 内部的生成中/提交中文案可能仍有"15道"字样需检查
3. **匹配结果 sessionStorage** — 刷新页面保留、关闭标签页清除。如果用户更新了画像但没重新匹配，会看到旧结果
4. **gap_cache 内存缓存** — 服务器重启后清空。如果 batch 成功但服务器重启后点详情，会重新调 LLM

## 下一步：目标岗位选择 + 动态成长闭环

### 一、目标岗位选择器

**现状**：`target_node_id` 已不自动设置，但用户没有手动选择入口。

**方案**：
- ProfilePage 右上"目标岗位"卡片改为可交互选择器
- 点击弹出岗位列表面板，来源：图谱 34 节点 + 匹配推荐结果
- 后端：`PUT /profiles/career-goal` 已存在
- 联动：选定后 `target_ids` 自动纳入推荐算法

**涉及文件**：
- `frontend/src/pages/ProfilePage.tsx`（目标岗位卡片区域，约第 332-370 行）
- `backend/routers/profiles.py`（career-goal 端点已有）
- `backend/routers/graph.py`（提供节点列表）

### 二、动态成长数据回流

**目标**：形成闭环 —— 选目标 → gap分析 → 学习/练习 → 成长数据更新 → coverage 变化

**需要做**：
1. **技能变更事件** — 用户编辑技能/完成SJT/完成面试后，清除对应 gap_cache
2. **动态 fitness** — `GET /recommendations/fitness?target={nodeId}` 已有，需接入首页成长曲线
3. **首页成长看板** — GrowthChart 接入目标岗位 coverage 变化数据

**涉及文件**：
- `backend/routers/recommendations.py`（fitness 端点）
- `backend/services/gap_analyzer.py`（缓存失效逻辑）
- `frontend/src/components/growth/GrowthChart.tsx`（成长曲线）
- `frontend/src/pages/HomePage.tsx`（首页看板）

### 三、竞赛合规缺口

根据选题要求，以下仍需补充：
- **证书数据** — 各岗位节点的相关证书字段未填充
- **"实习能力"维度** — 竞赛要求的维度，当前未建模
- **≥10 个岗位画像** — 当前 34 个节点已满足
- **职业发展报告** — 已有，但需确保包含"当前能力水平"、"推荐发展路径"、"学习资源"

## 架构要点备忘

- 推荐算法：`recommendation_service.py`，评分公式 `affinity*0.35 + proximity*0.25 + family*0.20 + level*0.20`
- LLM 配置：`llm.py`，当前全部用 `qwen3.6-plus`，DashScope API
- 图谱数据：`data/graph.json`（34 CS 岗位节点，基于 developer-roadmap）
- 技能数据：`data/roadmap_skills.json`（每个岗位的 topics/must_skills）
- 前端状态：匹配结果存 `sessionStorage('match_analysis_results')`
- 后端缓存：`_gap_cache` dict（内存，按 `(profile_hash, role_id)` 键）
