# GrowthLog Phase 2 · 长期追踪 IA 升级

交付人：Kimi
审查 / 文档：Claude
日期：2026-04-15
前序：Phase 1 视觉重写已完成（owner 截图验收通过：Editorial Morning Light 风格落地，但 IA 仍是切片视图）

---

## 一、背景与目标

### 当前问题（owner 抓到的 IA 漏洞）
Phase 1 完成后 owner 反馈："这样设计似乎不支持长期追踪一个目标"。

实际证据（截图 + 代码扫描）：
- Chapter I 标题"你在哪" + "陪你 0 天了" — 是**静态切片**，没有"目标 × 时间纵深"
- Chapter II"这两周你做了什么" — **时间窗切片**（最近 14 天），不是"在【这个目标】下你走了什么"
- Readiness 曲线"数据不足" — 没把 GrowthSnapshot 的 `trigger`（initial / stage_complete / deep_reeval）作为叙事节点
- **如果用户换过目标**，老目标的 records 没有"曾走过的路"视图（CareerGoal 表有 `is_active` 和 `cleared_at` 字段就是为此设计的，但前端没用）

### Backend 现状（FACT-DRIVEN evidence）
- `CareerGoal` 表已支持多目标 + 历史归档（`is_active` / `set_at` / `cleared_at` / `is_primary`）
- `GrowthSnapshot` 表已支持 `target_node_id` + `trigger` + `stage_completed` + `four_dim_detail` 时间序列
- 但 `GET /growth-log/dashboard` 当前查 GrowthSnapshot **只 filter `profile_id`，不 filter `target_node_id`** → 用户换过目标会曲线混乱（line 250-254）
- **没有**列出 active + cleared goal 历史的 endpoint
- **没有**返回 GrowthSnapshot trigger / stage 事件的 endpoint（只取了 readiness_score）

### 目标
1. **Backend**：补 2 个新 endpoint + 修 1 个现有 endpoint，让长期追踪数据可消费
2. **Frontend**：升级 IA 为"目标 × 时间纵深"，章节叙事从"快照"转为"旅程"

### 非目标
- ❌ 不重做视觉（Phase 1 已落地，色板 / 字体 / Chapter / PaperCard 全部沿用）
- ❌ 不改数据 schema（CareerGoal / GrowthSnapshot 字段够用）
- ❌ 不动 backend service 业务逻辑（只加 endpoint 读现有 data）

---

## 二、Backend 改动（3 个）

### 2.1 修改 `GET /growth-log/dashboard` —— readiness_curve 按 target 过滤

**文件**：`backend/routers/growth_log.py:248-262`

**当前**（错）：
```python
snapshots = (
    db.query(GrowthSnapshot)
    .filter(GrowthSnapshot.profile_id == profile.id)
    .order_by(GrowthSnapshot.created_at.asc())
    .limit(12)
    .all()
)
```

**改后**：
```python
snapshots = (
    db.query(GrowthSnapshot)
    .filter(
        GrowthSnapshot.profile_id == profile.id,
        GrowthSnapshot.target_node_id == goal.target_node_id,  # 新增
    )
    .order_by(GrowthSnapshot.created_at.asc())
    .limit(24)  # 12 → 24（长期追踪需要更多点）
    .all()
)
```

**响应字段不变**（前端 GrowthDashboard 已消费这个 shape，零回归）。

### 2.2 新增 `GET /growth-log/journey` —— 当前目标的完整时间线

**文件**：`backend/routers/growth_log.py`（追加）

**用途**：返回当前 active goal 的完整 journey（snapshot 阶段事件 + records 按目标过滤）。

```python
@router.get("/journey")
def get_goal_journey(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前 active goal 的完整旅程：阶段事件 + 关联 records。"""
    from backend.db_models import CareerGoal, GrowthSnapshot, ProjectRecord, JobApplication

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"has_goal": False}

    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user.id,
            CareerGoal.profile_id == profile.id,
            CareerGoal.is_active == True,
        )
        .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
        .first()
    )

    if not goal or not goal.target_node_id:
        return {"has_goal": False}

    # ── Stage events from GrowthSnapshot ──
    snapshots = (
        db.query(GrowthSnapshot)
        .filter(
            GrowthSnapshot.profile_id == profile.id,
            GrowthSnapshot.target_node_id == goal.target_node_id,
        )
        .order_by(GrowthSnapshot.created_at.asc())
        .all()
    )

    stage_events = [
        {
            "id": s.id,
            "trigger": s.trigger,                 # initial / stage_complete / deep_reeval
            "stage_completed": s.stage_completed,
            "readiness_score": round(s.readiness_score or 0, 1),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in snapshots
    ]

    # ── Records under this goal (按 goal.set_at 之后) ──
    projects = (
        db.query(ProjectRecord)
        .filter(
            ProjectRecord.profile_id == profile.id,
            ProjectRecord.created_at >= goal.set_at,
        )
        .order_by(ProjectRecord.created_at.asc())
        .all()
    )
    applications = (
        db.query(JobApplication)
        .filter(
            JobApplication.user_id == user.id,
            JobApplication.created_at >= goal.set_at,
        )
        .order_by(JobApplication.created_at.asc())
        .all()
    )

    return {
        "has_goal": True,
        "goal": {
            "id": goal.id,
            "target_node_id": goal.target_node_id,
            "target_label": goal.target_label,
            "set_at": goal.set_at.isoformat() if goal.set_at else None,
        },
        "stage_events": stage_events,
        "projects_under_goal": [
            {
                "id": p.id,
                "name": p.name,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
            }
            for p in projects
        ],
        "applications_under_goal": [
            {
                "id": a.id,
                "company": a.company,
                "position": a.position,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in applications
        ],
    }
```

### 2.3 新增 `GET /growth-log/goal-history` —— 所有目标历史

**用途**：列出该用户所有 career_goal（含 cleared 的），用于"曾走过的路"章节。

```python
@router.get("/goal-history")
def get_goal_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """所有 career_goal（active + cleared），按 set_at 降序。"""
    from backend.db_models import CareerGoal

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"goals": []}

    goals = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user.id,
            CareerGoal.profile_id == profile.id,
        )
        .order_by(CareerGoal.set_at.desc())
        .all()
    )

    return {
        "goals": [
            {
                "id": g.id,
                "target_node_id": g.target_node_id,
                "target_label": g.target_label,
                "is_active": g.is_active,
                "is_primary": g.is_primary,
                "set_at": g.set_at.isoformat() if g.set_at else None,
                "cleared_at": g.cleared_at.isoformat() if g.cleared_at else None,
                "duration_days": (
                    ((g.cleared_at or datetime.now(timezone.utc)) - g.set_at).days
                    if g.set_at else 0
                ),
            }
            for g in goals
        ],
    }
```

---

## 三、前端改动

### 3.1 新增组件 `JourneyTimeline.tsx`

**职责**：横向时间线，显示目标 set_at（起点） + stage_events（snapshot 阶段事件） + 现在（now）。

**视觉规格**：
- 横向 timeline，节点 = 阶段事件
- 起点节点：苔绿圆点 + "set_at" 日期 + "你选了 [target_label]"
- 阶段节点：橙土圆点 + trigger 文案（initial → "起步" / stage_complete → "完成第 N 阶段" / deep_reeval → "重新校准"）
- 现在节点：深栗圆形（空心）+ "今天"
- 节点之间：苔绿细线连接，等距分布
- 浅响应：horizontal scroll on mobile

**API**：
```tsx
interface JourneyTimelineProps {
  setAt: string                   // 目标设定时间
  stageEvents: StageEvent[]       // GrowthSnapshot 列表
}

interface StageEvent {
  id: number
  trigger: 'initial' | 'stage_complete' | 'deep_reeval'
  stage_completed: number
  readiness_score: number
  created_at: string
}

export function JourneyTimeline({ setAt, stageEvents }: JourneyTimelineProps) {
  // 渲染：起点 + 阶段事件 + 现在
  // ...
}
```

### 3.2 新增 API 客户端 `frontend/src/api/growthLog.ts` 增加方法

```ts
export interface GoalJourney {
  has_goal: boolean
  goal?: {
    id: number
    target_node_id: string
    target_label: string
    set_at: string
  }
  stage_events?: StageEvent[]
  projects_under_goal?: ProjectRecord[]
  applications_under_goal?: ApplicationRecord[]
}

export interface GoalHistoryItem {
  id: number
  target_node_id: string
  target_label: string
  is_active: boolean
  is_primary: boolean
  set_at: string
  cleared_at: string | null
  duration_days: number
}

export async function getGoalJourney(): Promise<GoalJourney> {
  return rawFetch('/growth-log/journey')
}

export async function getGoalHistory(): Promise<{ goals: GoalHistoryItem[] }> {
  return rawFetch('/growth-log/goal-history')
}
```

### 3.3 重写 `GrowthLogPage.tsx` 章节布局

**新章节地图**：

```
┌──────────────────────────────────────────────────────────────┐
│ CHAPTER I · 你的旅程                                          │  ← 改名 from "你在哪"
│                                                              │
│ 你选了 [系统C++工程师]，                                      │  ← 引用 goal.target_label
│ 从那天到今天，14 天。                                         │  ← set_at → now
│                                                              │
│ ┌─ JourneyTimeline ────────────────────────────────────┐     │
│ │  ●——————●——————●——————○                             │     │  ← 阶段事件横向 timeline
│ │  起步    第1阶段   重新校准   今天                     │     │
│ └──────────────────────────────────────────────────────┘     │
│                                                              │
│ ┌─ Skill coverage + Readiness curve ──────────────────┐     │  ← 沿用现有 GrowthDashboard
│ │  ...                                                │     │
│ └──────────────────────────────────────────────────────┘     │
│                                                              │
├─────────────────  · II ·  ──────────────────────────────────┤
│ CHAPTER II · 在这条路上你走了什么                              │  ← 改名 from "这两周做了什么"
│                                                              │
│ ▸ 项目（4）                                                  │  ← projects_under_goal
│ ▸ 投递（12）                                                 │  ← applications_under_goal
│                                                              │
│ [按时间排列的 records]                                       │
│                                                              │
├─────────────────  · III ·  ─────────────────────────────────┤
│ CHAPTER III · 接下来想试试什么                                │  ← 沿用 RefineSection
│                                                              │
│ [Refine 内容]                                                │
│                                                              │
└──────────────────────────────────────────────────────────────┘

──────  仅当 goal_history.length > 1 时显示 ─────────────────

┌──────────────────────────────────────────────────────────────┐
│ CHAPTER IV · 曾走过的路                                       │  ← 条件渲染：有 cleared goal 时才显示
│                                                              │
│ 「这些是你曾经选过的方向。                                     │
│   不是错误，是你走过来的路。」                                 │
│                                                              │
│ ▸ 后端开发  · 2026-03-01 → 2026-03-25 · 24 天                │
│ ▸ 数据分析  · 2026-02-15 → 2026-03-01 · 14 天                │
└──────────────────────────────────────────────────────────────┘
```

### 3.4 文案改写（追加到 Phase 1 的对照表）

| Phase 1 文案 | Phase 2 文案 |
|---|---|
| "你在哪" | "你的旅程" |
| "陪你 0 天了" | "从那天到今天，N 天" |
| "这两周你做了什么" | "在这条路上你走了什么" |
| "每一件小事，都算数" | "在这条路上你做的每一步" |
| （新）目标历史标题 | "曾走过的路" |
| （新）目标历史引言 | "这些是你曾经选过的方向。不是错误，是你走过来的路。" |
| （新）阶段事件 trigger 翻译 | initial → "起步"; stage_complete → "完成第 N 阶段"; deep_reeval → "重新校准" |

### 3.5 数据消费整合

GrowthLogPage 需要并行拉 4 个 query：
```ts
const { data: dashboardData } = useQuery({ queryKey: ['growth-dashboard'], queryFn: getGrowthDashboard })
const { data: journeyData } = useQuery({ queryKey: ['goal-journey'], queryFn: getGoalJourney })
const { data: historyData } = useQuery({ queryKey: ['goal-history'], queryFn: getGoalHistory })
const { data: appsData } = useQuery({ queryKey: ['pursuits-apps'], queryFn: listApplications })
```

按目标 filter records 用 `journeyData.projects_under_goal` 和 `journeyData.applications_under_goal`，**不再**用 `listProjects` 全量拉。

---

## 四、Kimi 任务拆解（T1 → T6）

### T1 · Backend：修改 dashboard endpoint
- 改 `growth_log.py:248-262`：snapshot query 加 `target_node_id` filter；limit 12 → 24
- **T1 验证**：`pytest tests/services/test_profile_service.py`（保险，不应该影响） + 启动后端 + curl `/growth-log/dashboard` 确认 readiness_curve 按 target 过滤

### T2 · Backend：新增 `/journey` endpoint
- 在 `growth_log.py` 追加 `@router.get("/journey")` 函数（按第 2.2 节代码）
- **T2 验证**：curl `/growth-log/journey` 返回 stage_events + projects_under_goal + applications_under_goal

### T3 · Backend：新增 `/goal-history` endpoint
- 追加 `@router.get("/goal-history")` 函数（按第 2.3 节代码）
- **T3 验证**：curl `/growth-log/goal-history` 返回所有 goals（含 active + cleared）

### T4 · Frontend：新建 JourneyTimeline 组件 + API client 扩展
- 创建 `frontend/src/components/growth-log/JourneyTimeline.tsx`
- 扩展 `frontend/src/api/growthLog.ts` 加 `getGoalJourney` / `getGoalHistory` + 类型定义
- **T4 验证**：组件可独立 import；TypeScript build 通过

### T5 · Frontend：重写 GrowthLogPage 章节
- Chapter I 改名 + 嵌入 JourneyTimeline + 沿用 GrowthDashboard
- Chapter II 改名 + 用 journey 数据按目标过滤 records
- Chapter IV 条件渲染（仅 goal_history.length > 1）
- 文案表全替换
- **T5 验证**：tsc 通过；npm run build 通过

### T6 · 视觉验证 + 边缘场景
- owner 启动 dev 看实际效果
- 边缘场景：
  - 无 goal → Chapter I 显示 PROLOGUE（沿用 EmptyDashboard）
  - 有 goal 无 stage_events → JourneyTimeline 只显示 起点 + 现在
  - 有 goal 有 events → 完整 timeline
  - 多 goal 历史 → Chapter IV 显示
- **T6 验证**：截图发 owner 验收

---

## 五、红线（Kimi 严守）

1. **不改数据 schema** — CareerGoal / GrowthSnapshot 字段够用，不动 model
2. **不改 Phase 1 视觉规则** — 色板 / 字体 / Chapter / PaperCard / SectionDivider 沿用，不重新设计
3. **不引入新 npm 依赖**
4. **不破坏现有 query** — `listProjects` / `listApplications` 已有 React Query key 不动；新增的 query 用新 key (`goal-journey` / `goal-history`)
5. **新 endpoint 必须是 GET** — 只读，不引入写操作
6. **JourneyTimeline 用 PaperCard 包裹** — 沿用 Phase 1 容器规则；时间线节点不要用 emoji，用 svg 圆点
7. **空 `stage_events` 时 timeline 不渲染**（或只显示起点 + 现在两个节点） — 不要硬塞假数据
8. **每个 T 完成后**必跑对应验证脚本，贴输出证据
9. **绝对不要**用 emoji 做章节标签或时间线节点（Phase 1 已建立 serif label 规则）

---

## 六、验证策略

由于没有 GrowthLog 单元测试 baseline，验证靠：

1. **TypeScript build**：`cd frontend && npm run build` 通过
2. **Backend pytest 不 regress**：`pytest tests/ --ignore=tests/services/test_plan_service.py -q` 仍 ≥ 103 passed
3. **Endpoint 烟测**（owner 侧）：
   ```bash
   # 启动 backend
   python -m uvicorn backend.app:app --reload

   curl /api/growth-log/journey -H "Authorization: Bearer <token>"
   curl /api/growth-log/goal-history -H "Authorization: Bearer <token>"
   curl /api/growth-log/dashboard -H "Authorization: Bearer <token>"
   ```
4. **owner 视觉验收 4 状态**：
   - 无 goal → PROLOGUE
   - 有 goal 无 events → timeline 起点 + 现在
   - 有 goal 有 events → 完整 timeline + 三章节
   - 多 goal → Chapter IV 显示

---

## 七、交付 Checklist（Kimi 自查）

- [ ] T1 dashboard endpoint snapshot query 加 target_node_id filter
- [ ] T2 `/growth-log/journey` endpoint 新增，curl 返回正确 JSON
- [ ] T3 `/growth-log/goal-history` endpoint 新增
- [ ] T4 JourneyTimeline 组件 + API client + 类型定义就位
- [ ] T5 GrowthLogPage 章节布局重写：Chapter I 含 timeline + Chapter II 按 goal 过滤 + Chapter IV 条件渲染
- [ ] T6 文案对照表全部替换（"你在哪"→"你的旅程"等 6 处）
- [ ] `npm run build` 全绿
- [ ] `pytest` 不 regress
- [ ] 4 个边缘场景人眼验收
- [ ] 无 emoji 残留在 Chapter 标签 / timeline 节点
- [ ] 无新增 npm 依赖

---

## 附录 · 参考

- 设计上下文：[`.impeccable.md`](../.impeccable.md)
- Phase 1 doc：[`growth-log-bolder-ui-rewrite.md`](./growth-log-bolder-ui-rewrite.md)
- Backend 现状证据：`db_models.py:111-143` (CareerGoal) / `db_models.py:416-434` (GrowthSnapshot) / `growth_log.py:182-299` (dashboard endpoint)
