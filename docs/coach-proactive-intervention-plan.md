# 成长教练主动交互改造计划

> 状态：草案  
> 背景：当前成长教练是被动问答式的侧边栏聊天，用户不打开面板就不交互。本计划将教练改造为"事件驱动的主动介入者"。

---

## 1. 现状诊断

### 1.1 核心问题：教练被"架空"

| 问题 | 现状 | 后果 |
|------|------|------|
| 被动等待 | Coach 缩在 `ChatPanel` 浮动面板里，等用户主动打开 | 80% 以上的用户可能从不打开面板 |
| 功能可替代 | 画像/图谱/JD诊断/报告/成长档案/模拟面试 都有独立页面 | 用户绕过 coach 就能完成全部核心流程 |
| 只读不写 | Coach agent 没有修改 `ActionPlanV2` / `CareerGoal` 的工具 | 对话不产生状态变更，建议停留在空气里 |
| 引导分流 | `guidance.py` 已有一套阶段感知引导系统（`HeartbeatBanners`） | Coach 的"阶段感知"仅存于 greeting 文案，价值被稀释 |
| 结果不沉淀 | `coach_agent` 的回复不会被保存为 `CoachResult`（仅其他 agent 会保存） | 闲聊/建议/情绪支持聊完就散，无资产沉淀 |
| 兜底定位 | Intent Router 把未匹配意图全丢给 `coach_agent` | Coach = "其他"分类，不是核心驱动者 |

### 1.2 关键代码证据

- `supervisor.py:556`：未匹配意图默认路由到 `coach_agent`
- `chat.py:1184`：自动保存 `CoachResult` 的 agent 列表不含 `coach_agent`
- `backend/routers/interview.py`：模拟面试是**完全独立**的路由和页面，不经过 coach
- `backend/routers/guidance.py`：`_build_guidance` 与 `_build_greeting` 阶段逻辑高度重复
- `agent/tools/coach_context_tools.py`：**无任何写入 ActionPlan 的工具**

---

## 2. 设计目标

### 2.1 一句话目标

> 让成长教练从"被动回答的聊天机器人"变成"事件驱动的状态推进者"。

### 2.2 成功标准

| 指标 | 现状（推测） | 目标 |
|------|-------------|------|
| 教练面板打开率 | 低 | 不追求提高，追求"用户不打开也能收到教练输入" |
| 教练触达的用户比例 | 仅主动聊天用户 | **100% 用户在关键节点收到至少 1 次 coach 介入** |
| 对话→状态变更转化率 | ~0% | **教练建议可直接写入 ActionPlan / CareerGoal** |
| 阶段推进引导来源 | Guidance Banners + Coach Greeting（两套） | **统一为 CoachIntervention 单一来源** |

---

## 3. 架构设计

### 3.1 核心概念：CoachIntervention（教练介入事件）

当系统中发生关键事件时，后端生成一个"教练介入任务"，以前端 Banner / Inline Card / Chat Highlight 的形式推送给用户。

```
系统事件（画像完成 / JD诊断完成 / 阶段变化 / 任务逾期 / 投递被拒）
    ↓
Intervention Generator（后端规则引擎 + 可选 LLM 生成文案）
    ↓
CoachIntervention 表（pending → displayed → engaged / dismissed）
    ↓
前端轮询 / SSE 推送
    ↓
CoachBanner（页面顶部）/ CoachInline（页面内嵌）/ ChatPrompt（面板高亮）
    ↓
用户点击 CTA
    ↓
[navigate] 跳转页面 / [open_chat] 打开对话 / [execute] 直接执行写操作
```

### 3.2 与现有系统的关系

```
┌─────────────────────────────────────────────────────────────┐
│                        现有系统层                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ Profile │ │JD Diag  │ │GrowthLog│ │ Interview/Mock  │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────────┬────────┘   │
│       │           │           │                │            │
│       └───────────┴───────────┴────────────────┘            │
│                   │                                         │
│                   ▼                                         │
│         ┌─────────────────┐                                 │
│         │  Event Hooks    │  ← 在各路由写操作后触发          │
│         │  (新增)         │                                 │
│         └────────┬────────┘                                 │
└──────────────────┼──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    Intervention Layer（新增）                 │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │ Intervention    │    │ LLM Copilot（可选）            │   │
│  │ Generator       │◄───│ 复杂场景生成个性化文案         │   │
│  │ （规则引擎）     │    └──────────────────────────────┘   │
│  └────────┬────────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │ CoachIntervention│    │ Stage Change Detector        │   │
│  │ （DB 表）        │◄───│ （复用 compute_stage）        │   │
│  └─────────────────┘    └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    前端展示层（新增/改造）                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │CoachBanner  │  │CoachInline  │  │ChatPrompt（面板内）  │ │
│  │(页面顶部)   │  │(页面内嵌)   │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**关键决策：不删 ChatPanel，而是让 Coach 拥有"面板外"的触达能力。**

---

## 4. 数据模型

### 4.1 CoachIntervention（新增表）

```python
# backend/db_models.py

class CoachIntervention(Base):
    __tablename__ = "coach_interventions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    # ── 触发来源 ──
    trigger_type: Mapped[str] = mapped_column(String(32))
    # stage_changed | data_ready | action_needed | insight | milestone | reminder

    # ── 关联业务对象 ──
    ref_type: Mapped[str | None] = mapped_column(String(32))
    # profile | jd_diagnosis | report | action_plan | application | interview | goal
    ref_id: Mapped[int | None] = mapped_column(Integer)

    # ── 展示内容 ──
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text)
    cta_text: Mapped[str] = mapped_column(String(64), default="")
    cta_action: Mapped[str] = mapped_column(String(32), default="")
    # open_chat | navigate | execute | dismiss

    # ── Coach 展开对话时使用的上下文 ──
    context_json: Mapped[str | None] = mapped_column(Text)
    # 例如：{"prompt": "帮我分析...", "route": "/profile", "highlight": "gaps"}

    # ── 路由匹配 ──
    target_pages: Mapped[str] = mapped_column(String(128), default="global")
    # global | home,profile,jd,growth-log,report

    # ── 生命周期 ──
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # pending → displayed → engaged | dismissed | expired

    priority: Mapped[int] = mapped_column(Integer, default=1)
    # 0=低 1=中 2=高 3=紧急

    expires_at: Mapped[datetime | None]
    created_at: Mapped[datetime]
    displayed_at: Mapped[datetime | None]
    engaged_at: Mapped[datetime | None]
    dismissed_at: Mapped[datetime | None]
```

### 4.2 索引设计

```sql
-- 按用户+状态+优先级查询未读介入
CREATE INDEX ix_coach_interventions_user_status_priority
    ON coach_interventions(user_id, status, priority DESC, created_at DESC);

-- 按过期时间清理
CREATE INDEX ix_coach_interventions_expires
    ON coach_interventions(expires_at) WHERE expires_at IS NOT NULL;
```

---

## 5. API 设计

### 5.1 后端路由（新增 `backend/routers/coach_interventions.py`）

```python
@router.get("/pending")
def get_pending_interventions(
    page: str = Query("global"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前页面应该展示的未读介入事件（最多 3 条）。"""

@router.post("/{intervention_id}/engage")
def engage_intervention(intervention_id: int, ...):
    """用户点击了 CTA。返回 action + context，前端决定如何响应。"""

@router.post("/{intervention_id}/dismiss")
def dismiss_intervention(intervention_id: int, ...):
    """用户关闭/忽略。"""

@router.get("/history")
def list_intervention_history(limit: int = 20, ...):
    """用户查看历史介入记录（可选）。"""
```

### 5.2 前端 API Client

```typescript
// frontend/src/api/coach.ts
export function fetchPendingInterventions(page: string) {
  return rawFetch(`/coach/interventions/pending?page=${page}`)
}

export function engageIntervention(id: number) {
  return rawFetch(`/coach/interventions/${id}/engage`, { method: 'POST' })
}

export function dismissIntervention(id: number) {
  return rawFetch(`/coach/interventions/${id}/dismiss`, { method: 'POST' })
}
```

---

## 6. 触发器清单

### Phase 1：高价值、低实现成本（立即做）

| # | 触发器 | 触发时机 | 介入内容 | CTA | 优先级 |
|---|--------|---------|---------|-----|--------|
| 1 | `recommendations_ready` | 画像上传后，后台推荐计算完成 | "方向推荐已更新，前三个最匹配的方向准备好了" | 查看推荐 → `/profile` | 2 |
| 2 | `stage_no_profile→has_profile` | 首次建立画像 | "画像分析完成。我发现几个方向和你很匹配，要看看吗？" | 查看分析 → `/profile` | 2 |
| 3 | `stage_has_profile→first_diagnosis` | 完成第一份 JD 诊断 | "第一份诊断完成。一份 JD 不够真实，建议再诊断 2-3 份" | 继续诊断 → `/jd` | 2 |
| 4 | `stage_growing→report_ready` | 数据积累足够 | "可以生成职业报告了，帮你系统梳理差距和路径" | 生成报告 → `/report` | 2 |

### Phase 2：业务事件驱动

| # | 触发器 | 触发时机 | 介入内容 | CTA | 优先级 |
|---|--------|---------|---------|-----|--------|
| 5 | `jd_diagnosis_complete` | 每次 JD 诊断完成后 | "匹配度 X%，Y 个缺口。要我直接生成补强计划吗？" | 生成计划 → `execute` | 2 |
| 6 | `application_rejected` | 投递状态变为 rejected | "投递结果更新了。要一起复盘看看哪里可以调整吗？" | 和教练聊聊 → `open_chat` | 2 |
| 7 | `interview_scheduled` | 面试安排确定（24h/2h 前） | "X 公司面试即将到来，要做一轮模拟面试吗？" | 开始模拟 → `/interview` | 3 |
| 8 | `action_plan_overdue` | 行动计划任务逾期 3 天 | "你的 Redis 任务已经延期了，需要调整计划节奏吗？" | 调整计划 → `open_chat` | 2 |

### Phase 3：洞察驱动（需要数据分析）

| # | 触发器 | 触发时机 | 介入内容 | CTA |
|---|--------|---------|---------|-----|
| 9 | `jd_pattern_insight` | 诊断 3+ 份 JD 后发现共同缺口 | "我注意到你诊断的 JD 都在要求 X，但你的画像里这块较弱" | 制定补强计划 |
| 10 | `readiness_stuck` | 准备度连续 2 周无变化 | "你的准备度停留在 X% 两周了。要检查一下进度哪里卡住了吗？" | 查看成长档案 |
| 11 | `goal_conflict` | 用户频繁切换目标方向 | "你最近看了几个不同方向，还在纠结吗？我可以帮你做对比" | 方向对比 → `open_chat` |

---

## 7. 前端组件设计

### 7.1 CoachBanner（页面顶部横幅）

```
┌─────────────────────────────────────────────────────────────────┐
│ [🤖]  画像分析完成。我发现前三个推荐方向已经准备好，要看看吗？    │
│                                                   [查看] [×]   │
└─────────────────────────────────────────────────────────────────┘
```

- 位置：`Layout.tsx` 全局挂载，`<main>` 上方
- 样式：渐变色背景（与系统主色调一致），高度 `auto`，可关闭
- 过滤：只展示 `target_pages` 匹配当前路由且未过期的介入
- 最多同时展示 **1 条**（取最高 priority）

### 7.2 CoachInline（页面内嵌卡片）

用于特定页面的深度引导，例如：
- JD 诊断结果页下方："诊断完成，要我帮你把缺口加到追踪目标吗？"
- 成长档案空状态："还没有记录。最近有做什么项目或学习吗？告诉我，我帮你记录。"

### 7.3 ChatPrompt（聊天面板内高亮）

当用户主动打开 `ChatPanel` 时，greeting 区域除了现有阶段文案外，高亮展示当前最高优先级的 pending intervention：

```
智析教练
─────────────────────────────
[📌 待处理] 你有一份 JD 诊断结果还没复盘
           匹配度 62%，4 个技能缺口
           [开始复盘] [稍后处理]
─────────────────────────────
分析完了！根据你的背景...
```

---

## 8. 与现有系统的集成策略

### 8.1 吸收 Guidance 系统（长期）

当前 `backend/routers/guidance.py` 的 `_build_guidance` + `HeartbeatBanners` 与本计划功能重叠。

**迁移路径：**
1. Week 1：保持 Guidance 系统运行，CoachIntervention 并行上线
2. Week 2：将 Guidance 的 `_build_guidance` 改造为写入 `CoachIntervention` 表
3. Week 3：`/guidance/heartbeat` 接口改为查询 `CoachIntervention`，前端 `HeartbeatBanners` 替换为 `CoachBanner`
4. Week 4：删除 `UserNotification` 表和相关代码

### 8.2 改造 useCoachTrigger（前端）

当前 `useCoachTrigger.ts` 的 `dispatchCoachTrigger` 通过 CustomEvent 发消息给 ChatPanel。

**改造方案：**
- 保留 `dispatchCoachTrigger` 用于即时聊天场景
- 新增 `dispatchCoachIntervention` 用于生成介入事件（或直接由后端生成）
- **推荐做法**：触发逻辑移到后端。前端只需在关键操作后调一次 `POST /coach/interventions/refresh` 触发后端重新评估

### 8.3 复用阶段计算逻辑

```python
# backend/services/stage.py

# 新增：进程内缓存 + 变化检测
_user_stage_cache: dict[int, str] = {}

def detect_stage_change(user_id: int, db: Session) -> tuple[str | None, str | None]:
    new_stage = compute_stage(...)
    old_stage = _user_stage_cache.get(user_id) or get_cached_stage_from_db(user_id)
    
    if old_stage != new_stage:
        _user_stage_cache[user_id] = new_stage
        cache_stage_in_db(user_id, new_stage)
        return old_stage, new_stage
    return None, None
```

在以下位置调用：
- `chat.py` 的 `_hydrate_state`（每次对话时检测）
- `backend/routers/profile.py` 画像创建/更新后
- `backend/routers/jd.py` JD 诊断保存后
- `backend/routers/growth_log.py` 项目/投递/面试记录变更后

---

## 9. Coach Agent 能力升级（配套改造）

主动交互只是"触达"，要让教练不可替代，还需要给它"权力"。

### 9.1 新增 Action Tools

```python
# agent/tools/coach_action_tools.py

@tool
def add_action_plan_item(user_id: int, text: str, skill_name: str = "", priority: str = "medium") -> str:
    """向用户的行动计划中添加一项任务。"""

@tool
def mark_gap_skill_in_progress(user_id: int, skill_name: str) -> str:
    """将某个缺口技能标记为"正在学习"。"""

@tool
def log_project_milestone(user_id: int, project_name: str, milestone: str) -> str:
    """为用户记录一个项目里程碑。"""

@tool
def create_application_tracking(user_id: int, company: str, position: str, job_url: str = "") -> str:
    """在实战追踪中创建一条投递记录。"""
```

### 9.2 阶段门禁（Skill 可用性控制）

```python
# agent/skills/loader.py 或 coach_agent.py

_STAGE_SKILL_MAP = {
    "exploring": [
        "coach-greeting", "coach-direction-scaffold", "coach-exploring-guide",
        "coach-decision-socratic", "coach-concern-direct", "coach-emotional-support",
        "coach-profile-builder",
    ],
    "focusing": [
        "coach-greeting", "coach-request-deliver", "coach-resume-review",
        "coach-project-planning", "coach-market-signal", "coach-progress-report",
        "coach-concern-direct", "coach-emotional-support",
    ],
    "job_hunting": [
        "coach-greeting", "coach-interview-prep", "coach-resume-review",
        "coach-market-signal", "coach-request-deliver", "coach-progress-report",
        "coach-emotional-support", "coach-comparison-detox",
    ],
    "sprinting": [
        "coach-greeting", "coach-interview-prep", "coach-decision-socratic",
        "coach-request-deliver", "coach-emotional-support", "coach-concern-direct",
    ],
}
```

在 `supervisor.py` 注入 prompt 时，根据当前阶段过滤可用 skill 列表。

---

## 10. 实施路线图

### Phase 1：MVP — 教练会说第一句话（2 周）

**目标：用户在画像完成后，即使不打开聊天面板，也能在首页看到教练的推荐。**

| 天数 | 任务 | 涉及文件 |
|------|------|---------|
| 1-2 | 创建 `CoachIntervention` 模型 + migration | `backend/db_models.py`, `alembic` |
| 2-3 | 实现 Intervention Generator（规则引擎） | `backend/services/coach_intervention.py` |
| 3-4 | 新增 `coach_interventions.py` 路由 | `backend/routers/coach_interventions.py`, `backend/app.py` |
| 4-5 | 前端 `CoachBanner` 组件 + hook | `frontend/src/components/CoachBanner.tsx`, `frontend/src/hooks/useCoachInterventions.ts` |
| 5-6 | 在 `Layout.tsx` 挂载 Banner | `frontend/src/components/Layout.tsx` |
| 6-8 | 接入 2 个触发器：`recommendations_ready` + `no_profile→has_profile` | `backend/routers/profile.py`, `backend/services/stage.py` |
| 8-10 | 集成测试 + 前端样式调优 | - |

### Phase 2：深度介入 — 把关键流程串起来（2 周）

| 任务 | 说明 |
|------|------|
| JD 诊断后主动推补强计划 | 诊断完成后生成 intervention，CTA 为"生成计划" |
| 投递状态变化介入 | `application_rejected` / `interview_scheduled` |
| Action Plan 逾期提醒 | 定时任务扫描逾期任务 |
| ChatPanel greeting 展示 pending intervention | 打开面板时高亮待处理事项 |
| Guidance → Intervention 迁移 | 将 `_build_guidance` 逻辑逐步迁移 |

### Phase 3：教练获得权力 — 对话即操作（2 周）

| 任务 | 说明 |
|------|------|
| 新增 `add_action_plan_item` tool | Coach 可在对话中直接写入行动计划 |
| 新增 `mark_gap_skill_in_progress` tool | Coach 可更新缺口技能状态 |
| 新增 `create_application_tracking` tool | Coach 可帮用户记录投递 |
| 阶段门禁实现 | 按阶段过滤可用 skill |
| Insight 驱动介入 | `jd_pattern_insight`, `readiness_stuck` 等 |

---

## 11. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 触发过于频繁，用户感到骚扰 | 用户关闭/忽略率上升 | 每个用户同类型干预 7 天内最多触发 1 次；支持 dismiss 后 7 天不再触发同类 |
| 文案模板化，缺乏个性化 | 用户觉得像推送通知 | Phase 1 用模板，Phase 2 引入轻量 LLM 基于 context 生成文案 |
| 前端轮询增加服务器压力 | QPS 上升 | 轮询间隔 30s；后续可迁移到 SSE 或 WebSocket |
| 与 Guidance 系统并行导致冲突 | 用户同时看到两套 Banner | Week 1-2 保持并行但互斥：如果 CoachBanner 有内容，隐藏 HeartbeatBanner |
| 阶段变化检测延迟 | 用户已经完成操作但 coach 没反应 | 在写操作路由中同步调用 `detect_stage_change`，不依赖聊天触发 |

---

## 12. 待对齐问题

1. **是否保留 `ChatPanel` 的浮动形态？** 还是改为固定右侧边栏？
2. **模拟面试是否收回到 Coach 对话流中？** 当前是完全独立页面。
3. **Guidance 系统的废弃时间表？** 是否同意 Phase 1 并行、Phase 2 迁移、Phase 3 废弃？
4. **LLM 生成介入文案的成本？** Phase 1 用硬编码模板，Phase 2 再引入 LLM，是否接受？
5. **定时任务基础设施？** 当前是否有 Celery / APScheduler / Cron？逾期提醒需要定时扫描。

---

## 附录：关键文件变更清单

### 新增文件
- `backend/db_models.py` — `CoachIntervention` 模型
- `backend/routers/coach_interventions.py` — 介入管理路由
- `backend/services/coach_intervention.py` — Intervention Generator
- `backend/services/stage.py` — 阶段变化检测（扩展）
- `frontend/src/components/CoachBanner.tsx`
- `frontend/src/hooks/useCoachInterventions.ts`
- `frontend/src/api/coach.ts`

### 修改文件
- `backend/app.py` — 注册新路由
- `backend/routers/profile.py` — 插入触发器钩子
- `backend/routers/jd.py` — 插入触发器钩子
- `backend/routers/growth_log.py` — 插入触发器钩子
- `backend/routers/chat.py` — `_hydrate_state` 中调用阶段检测
- `frontend/src/components/Layout.tsx` — 挂载 CoachBanner
- `frontend/src/components/ChatPanel.tsx` — greeting 区域展示 pending intervention
- `frontend/src/pages/HomePage.tsx` — 替换/隐藏 HeartbeatBanners

### 废弃文件（Phase 3）
- `backend/routers/guidance.py` — 能力合并到 Intervention Generator
- `frontend/src/hooks/useGuidance.ts` — 被 `useCoachInterventions` 替代
