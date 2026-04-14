# Coach Memo v2 + Heartbeat + Personality 实现规范

> **目标**：借鉴 DeepTutor 的「持久化学习者画像 + Heartbeat 主动推进」思路，将现有 `coach_memo` 从自由文本升级为结构化演化画像，并加入按用户阶段切换教练人格与主动 check-in 机制。
>
> **项目根目录**：`C:\Users\liu\Desktop\CareerPlanningAgent`
>
> **启动命令**：
> - 后端：`python -m uvicorn backend.app:app --reload`
> - 前端：`cd frontend && npm run dev`
>
> **本文档读者**：Kimi / 其他实施 Agent。所有代码片段可以直接复用，路径与现状均已核对过。

---

## 一、整体拉通

### 1.1 核心目标

4 项改动，**按依赖顺序**分 3 个 Sprint 交付：

| # | 模块 | 依赖 | 改动量 | Sprint |
|---|---|---|---|---|
| M1 | Personality by Stage（教练人格按用户阶段切换） | 无 | ~100 行 prompt | 1 |
| M2 | Heartbeat 主动 check-in | 无 | ~250 行 | 1 |
| M3 | Coach Memo 结构化（v2） | 无 | ~150 行 | 2 |
| M4 | Pattern Analyzer（决策模式抽象） | **依赖 M3** | ~300 行 | 3 |

### 1.2 项目背景（实施必须知道的最小上下文）

- **项目定位**：职业规划 Web 应用「职途智析」。多 Agent 架构（LangGraph），围绕用户画像 + 职业图谱做规划建议。
- **已有 Agent**：`coach_agent` / `profile_agent` / `navigator_agent` / `search_agent` / `jd_agent` / `growth_agent`，见 `agent/agents/`
- **已有持久记忆**：
  - `Profile.coach_memo`（`backend/db_models.py:87-89`）：Text 字段，500 字自然语言 memo
  - `GrowthSnapshot` 表（`db_models.py:416`）：结构化能力快照
  - `SkillUpdate` 表（`db_models.py:437`）：技能变更日志
- **已有 scheduler**：`backend/scheduler.py` + `backend/services/reminder_service.py`（APScheduler + filelock 单 worker）
- **Supervisor 路由**：`agent/supervisor.py` 三层路由（正则 → 语义 → LLM），本次改动**不需要动路由层**

### 1.3 不准做的事（硬约束）

- ❌ 不要改 `agent/supervisor.py` 的路由逻辑
- ❌ 不要改 6 个 agent 的工具集（tools 层完全不动）
- ❌ 不要重命名任何现有字段/表
- ❌ 不要引入新的 agent 框架（LangGraph 保持）
- ❌ 不要写一次性迁移脚本覆盖老数据——用"双写兼容期"过渡

---

## 二、模块 M1 — Personality by Stage

### 2.1 目标

根据 `Profile.profile_json.preferences.current_stage` 自动切换 coach_agent 的 SystemPrompt，避免对"迷茫期学生"用"直给型"话术、对"行动期学生"还在共情。

### 2.2 当前 stage 枚举（已有）

见 `agent/supervisor.py:168-175` 的 `pref_labels`：
```
lost         → 方向迷茫
know_gap     → 有方向但技能不足
ready        → 技能够但找不到机会
not_started  → 刚开始考虑就业
```

### 2.3 改动文件（1 个）

**`agent/agents/coach_agent.py`** — 把单一 `SYSTEM_PROMPT` 拆成 `BASE_PROMPT` + 4 个 stage 片段 + 拼接函数。

### 2.4 代码模板

```python
# agent/agents/coach_agent.py
from __future__ import annotations

from langchain.agents import create_agent as create_react_agent
from agent.llm import get_chat_model
from agent.tools.graph_tools import recommend_jobs, search_jobs
from agent.tools.search_tools import search_real_jd


# ── 基础人格（所有 stage 共享）────────────────────────────────────────────────
BASE_PROMPT = """你是「职途智析」的成长教练。
... [保留现有 1-25 行的基础定义：你是谁、工作原则、使用用户现状、数据诚信、回复规则]
"""


# ── Stage 特化片段 ───────────────────────────────────────────────────────────
STAGE_LOST = """
## 当前用户状态：方向迷茫（lost）

这个学生不知道往哪走。你的重点：
1. **先共情再给建议**——不要一上来就推方向
2. 先帮他缩小选择范围（3 选 1 而不是全景扫描）
3. 引用系统消息里的「各CS方向市场时机」用真实数据打破焦虑
4. 每次结尾只给 1 个最小动作（"先去画像页填 5 分钟意愿问卷"），不要给超过 3 步
5. 禁止话术：不要说"很多人都..."、"大部分同学..."（会加剧从众焦虑）
"""

STAGE_KNOW_GAP = """
## 当前用户状态：有方向但技能不足（know_gap）

这个学生目标清楚，差在执行。你的重点：
1. 不要再讨论方向选择，直接聊怎么补缺口
2. 优先引用「目标方向市场动态」里的具体数据
3. 给可验证的项目建议（而不是"去学 X 技术"）
4. 如果看到「正在做的项目」：必须基于这些项目延伸，不要推荐从零开始
"""

STAGE_READY = """
## 当前用户状态：技能够但找不到机会（ready）

这个学生技能到位但在求职环节卡住。你的重点：
1. 不要评估他的技能（他已经够了），直接聊求职策略
2. 主动建议用 search_real_jd 工具搜真实校招
3. 如果看到「正在追踪的岗位」：针对具体公司给建议（面试准备、投递时机）
4. 帮他做 JD 诊断提高命中率
"""

STAGE_NOT_STARTED = """
## 当前用户状态：刚开始考虑就业（not_started）

这个学生还在探索期，不急于决策。你的重点：
1. 多介绍方向的日常工作、前景、适合什么人（信息输入型）
2. 不要逼他做决定
3. 引导他先建立画像（上传简历），再聊具体方向
"""

STAGE_PROMPT_MAP = {
    "lost": STAGE_LOST,
    "know_gap": STAGE_KNOW_GAP,
    "ready": STAGE_READY,
    "not_started": STAGE_NOT_STARTED,
}


def _build_system_prompt(user_stage: str = "") -> str:
    """根据用户 stage 拼接 SystemPrompt。未知 stage 返回基础版。"""
    stage_ext = STAGE_PROMPT_MAP.get(user_stage, "")
    if stage_ext:
        return f"{BASE_PROMPT}\n\n{stage_ext}"
    return BASE_PROMPT


def create_coach_agent():
    """Create and return the growth coach chat agent.
    
    注意：SystemPrompt 在 supervisor._make_agent_node 里每次注入 context summary 时
    已经通过 SystemMessage 注入，所以这里的 system_prompt 只是底层默认值。
    stage 特化通过 context summary 里的「当前用户状态」字段自然引导即可。
    """
    model = get_chat_model(temperature=0.5)
    return create_react_agent(
        model=model,
        tools=[search_real_jd, recommend_jobs, search_jobs],
        name="coach_agent",
        system_prompt=_build_system_prompt(""),  # 基础版，运行时 context 会补充 stage
    )
```

### 2.5 验收标准

- [ ] `create_coach_agent()` 签名不变，向后兼容
- [ ] 4 个 stage 片段各自独立，方便调 prompt 不影响其他
- [ ] 单元测试：`_build_system_prompt("lost")` 返回包含"方向迷茫"的字符串
- [ ] 手动测试：用 4 种 stage 用户账号各聊 3 轮，观察话术差异

### 2.6 坑位提示

- ⚠️ **不要真的根据 stage 改 `system_prompt` 参数**——`create_react_agent` 的 system_prompt 是创建时绑定，一个 agent 实例只能绑一个。stage 特化**通过 supervisor 的 `build_context_summary()` 在 SystemMessage 里动态注入已经够用**（见 `agent/supervisor.py:226-235`，context 里已经有 stage 标签）。本模块的价值是**让 coach_agent 的 prompt 知道不同 stage 要不同行为**——所以 BASE_PROMPT 里要加一段"根据上下文里的 stage 调整策略"的元指令，4 个 stage 片段作为 prompt 里的参考章节嵌入 BASE_PROMPT 即可，不需要运行时动态拼接。
- ✅ **最简实现**：把 4 个 STAGE_* 片段全部平铺拼到 BASE_PROMPT 末尾，让 LLM 根据 context 里的 stage 自己挑对应段落执行。

---

## 三、模块 M2 — Heartbeat 主动 check-in

### 3.1 目标

把"JD 诊断后 3 天没投递"、"追踪公司有新 JD"、"一周未活跃"等信号转成主动推送，在前端首页 banner 区展示。复用已有 `scheduler` + `guidance` banner 机制。

### 3.2 改动文件（5 个）

1. **新建** `backend/services/heartbeat_service.py`
2. **新建** `backend/db_models.py` 里加 `UserNotification` 表（在文件末尾追加）
3. **修改** `backend/scheduler.py` 注册新 job
4. **修改** `backend/routers/guidance.py` 在现有 banner response 里拼 heartbeat
5. **修改** `frontend/src/pages/HomePage.tsx` 渲染 heartbeat banner

### 3.3 数据库 Schema（追加到 `backend/db_models.py` 末尾）

```python
class UserNotification(Base):
    """主动推送消息。由 heartbeat scheduler 生成，前端轮询拉取。"""
    __tablename__ = "user_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # 'jd_followup' | 'inactive_nudge' | 'milestone_due' | 'tracked_company_update'
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    cta_label: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "去投递" / "去更新"
    cta_route: Mapped[str | None] = mapped_column(String(128), nullable=True)  # "/growth-log" 等
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
```

**迁移方式**：不写 Alembic，依赖 `init_db()` 里的 `create_all` 自动建表（SQLite 开发环境足够；生产环境后续 PR 补 Alembic 迁移）。

### 3.4 Heartbeat Service

**文件**：`backend/services/heartbeat_service.py`（新建）

```python
"""Heartbeat service — 生成主动 check-in 消息。

规则驱动（非 LLM），限频：同一 (user_id, kind) 7 天内只发 1 条。

由 scheduler 每天 09:00 调用一次。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ── 限频规则 ────────────────────────────────────────────────────────────────
# 同一 user + kind 在这个时间窗内不能重复推
_DEDUP_WINDOW_DAYS = 7


def _recently_sent(db: Session, user_id: int, kind: str) -> bool:
    """检查该 user+kind 是否在去重窗口内已发过。"""
    from backend.db_models import UserNotification
    cutoff = datetime.now(timezone.utc) - timedelta(days=_DEDUP_WINDOW_DAYS)
    exists = (
        db.query(UserNotification.id)
        .filter(
            UserNotification.user_id == user_id,
            UserNotification.kind == kind,
            UserNotification.created_at >= cutoff,
        )
        .first()
    )
    return exists is not None


def _emit(db: Session, user_id: int, kind: str, title: str, body: str,
          cta_label: str | None = None, cta_route: str | None = None) -> None:
    """写一条 UserNotification，带限频检查。"""
    from backend.db_models import UserNotification
    if _recently_sent(db, user_id, kind):
        return
    db.add(UserNotification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        cta_label=cta_label,
        cta_route=cta_route,
    ))


# ── 规则 1：JD 诊断后 3 天没有对应投递 ─────────────────────────────────────
def _rule_jd_followup(db: Session) -> int:
    """诊断过 JD 但 3 天没建 JobApplication → 提醒。"""
    from backend.db_models import JDDiagnosis, JobApplication
    cutoff_min = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_max = datetime.now(timezone.utc) - timedelta(days=3)
    
    candidates = (
        db.query(JDDiagnosis)
        .filter(
            JDDiagnosis.created_at >= cutoff_min,
            JDDiagnosis.created_at <= cutoff_max,
        )
        .all()
    )
    count = 0
    for diag in candidates:
        # 检查这条诊断有没有关联的 JobApplication
        has_app = (
            db.query(JobApplication.id)
            .filter(JobApplication.user_id == diag.user_id)
            .filter(JobApplication.position.ilike(f"%{(diag.jd_title or '')[:20]}%"))
            .first()
        )
        if has_app:
            continue
        _emit(
            db, diag.user_id,
            kind="jd_followup",
            title="那份 JD 还在看吗",
            body=f"你 3 天前诊断了「{diag.jd_title[:30]}」，匹配度 {diag.match_score}%，还没建追踪。要不要去投一下？",
            cta_label="去追踪",
            cta_route="/growth-log",
        )
        count += 1
    return count


# ── 规则 2：一周未活跃 ─────────────────────────────────────────────────────
def _rule_inactive_nudge(db: Session) -> int:
    """7 天没任何活动（chat/诊断/档案更新）→ 推"你在追踪的公司有新动态"。"""
    from backend.db_models import User, ChatMessage, JDDiagnosis, JobApplication
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    
    users = db.query(User).all()
    count = 0
    for u in users:
        last_chat = (
            db.query(ChatMessage.created_at)
            .join(ChatMessage.session)  # 需要确认 ChatSession 有 user_id 关联
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        last_diag = (
            db.query(JDDiagnosis.created_at)
            .filter(JDDiagnosis.user_id == u.id)
            .order_by(JDDiagnosis.created_at.desc())
            .first()
        )
        last_active = max(
            (last_chat[0] if last_chat else datetime.min.replace(tzinfo=timezone.utc)),
            (last_diag[0] if last_diag else datetime.min.replace(tzinfo=timezone.utc)),
        )
        if last_active >= cutoff:
            continue
        
        # 有追踪公司的才推
        tracked = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == u.id,
                ~JobApplication.status.in_(["withdrawn", "rejected"]),
            )
            .count()
        )
        if tracked == 0:
            continue
        _emit(
            db, u.id,
            kind="inactive_nudge",
            title="好久没来了",
            body=f"你追踪的 {tracked} 家公司最近可能有新动态，来看看？",
            cta_label="查看追踪",
            cta_route="/growth-log",
        )
        count += 1
    return count


# ── 规则 3：项目里程碑到期 ─────────────────────────────────────────────────
def _rule_milestone_due(db: Session) -> int:
    """ProjectRecord 有 deadline 字段的 → 临近 3 天提醒。
    
    注意：当前 ProjectRecord 没有 deadline 字段。此规则暂留占位，
    等 ProjectRecord 加 deadline 字段后再启用。
    """
    return 0


# ── 主入口 ───────────────────────────────────────────────────────────────
def run_heartbeat() -> dict:
    """扫所有规则，写 UserNotification。返回 {rule_name: emitted_count}."""
    from backend.db import SessionLocal
    db = SessionLocal()
    try:
        stats = {
            "jd_followup": _rule_jd_followup(db),
            "inactive_nudge": _rule_inactive_nudge(db),
            "milestone_due": _rule_milestone_due(db),
        }
        db.commit()
        logger.info("Heartbeat done: %s", stats)
        return stats
    except Exception:
        db.rollback()
        logger.exception("Heartbeat failed")
        return {}
    finally:
        db.close()
```

### 3.5 Scheduler 注册

**文件**：`backend/scheduler.py` 修改 `start_scheduler()` 函数。

```python
def start_scheduler() -> None:
    # ... [保留现有的 lock 逻辑] ...
    
    scheduler.add_job(
        _rescore_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily-rescore",
        replace_existing=True,
    )
    
    # 新增：每天 09:00 跑 heartbeat
    scheduler.add_job(
        _heartbeat_job,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily-heartbeat",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Scheduler started — daily rescore at 03:00, heartbeat at 09:00")


async def _heartbeat_job() -> None:
    await asyncio.to_thread(_sync_heartbeat)


def _sync_heartbeat() -> None:
    from backend.services.heartbeat_service import run_heartbeat
    run_heartbeat()
```

### 3.6 API 端点

**文件**：`backend/routers/guidance.py` — 加一个端点 + 修改现有 banner response 拼上 heartbeat。

```python
# 在 guidance.py 末尾加

from pydantic import BaseModel
from backend.db_models import UserNotification


class HeartbeatDismissBody(BaseModel):
    notification_id: int


@router.get("/heartbeat")
def get_heartbeat(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """拉取未读的 heartbeat 通知，最多 3 条。"""
    notes = (
        db.query(UserNotification)
        .filter(
            UserNotification.user_id == user.id,
            UserNotification.dismissed == False,  # noqa: E712
        )
        .order_by(UserNotification.created_at.desc())
        .limit(3)
        .all()
    )
    return {
        "notifications": [
            {
                "id": n.id,
                "kind": n.kind,
                "title": n.title,
                "body": n.body,
                "cta_label": n.cta_label,
                "cta_route": n.cta_route,
                "created_at": n.created_at.isoformat(),
            }
            for n in notes
        ]
    }


@router.post("/heartbeat/dismiss")
def dismiss_heartbeat(
    body: HeartbeatDismissBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户点关闭 → 标记 dismissed。"""
    note = (
        db.query(UserNotification)
        .filter(
            UserNotification.id == body.notification_id,
            UserNotification.user_id == user.id,
        )
        .first()
    )
    if not note:
        raise HTTPException(404, "通知不存在")
    note.dismissed = True
    note.dismissed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}
```

### 3.7 前端集成

**文件**：`frontend/src/pages/HomePage.tsx` 顶部加 heartbeat banner 区。

```tsx
// 在 HomePage 组件里
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'  // 假设已有 axios 封装

function HeartbeatBanners() {
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['heartbeat'],
    queryFn: async () => (await api.get('/api/guidance/heartbeat')).data,
    staleTime: 60_000,
  })
  
  const dismiss = useMutation({
    mutationFn: async (id: number) =>
      api.post('/api/guidance/heartbeat/dismiss', { notification_id: id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['heartbeat'] }),
  })
  
  const notes = data?.notifications ?? []
  if (notes.length === 0) return null
  
  return (
    <div className="mb-4 space-y-2">
      {notes.map((n: any) => (
        <div key={n.id} className="rounded-lg border border-amber-200 bg-amber-50 p-3 flex items-start justify-between">
          <div>
            <div className="font-medium text-amber-900">{n.title}</div>
            <div className="text-sm text-amber-700 mt-1">{n.body}</div>
            {n.cta_label && n.cta_route && (
              <a href={n.cta_route} className="text-sm text-amber-800 underline mt-2 inline-block">
                {n.cta_label} →
              </a>
            )}
          </div>
          <button
            onClick={() => dismiss.mutate(n.id)}
            className="text-amber-600 hover:text-amber-800 ml-3"
            aria-label="关闭"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}

// 在 HomePage 主 return 里顶部放 <HeartbeatBanners />
```

### 3.8 验收标准

- [ ] `UserNotification` 表能建成，`GET /api/guidance/heartbeat` 能返回 `{"notifications": []}`
- [ ] 手动触发：`python -c "from backend.services.heartbeat_service import run_heartbeat; print(run_heartbeat())"` 能跑通返回 dict
- [ ] 造测试数据：创建一条 3 天前的 JDDiagnosis（无对应 JobApplication），跑 heartbeat 后能看到新 notification
- [ ] 重复跑两次 heartbeat，第二次不应新增（限频生效）
- [ ] 前端 banner 能显示，点 × 能关闭，刷新后不再出现
- [ ] 单元测试：`_recently_sent` 在 7 天内返回 True，7 天外返回 False

### 3.9 坑位提示

- ⚠️ `_rule_inactive_nudge` 里 `ChatMessage.session.user_id` 关联要先核对现有 `ChatSession` 表结构——如果 `ChatSession` 没有 `user_id` 字段（通过 `profile_id` 间接关联），要改写 query。先跑一下 `backend/db_models.py` 里 `ChatSession` 的定义确认。
- ⚠️ heartbeat 规则**必须幂等**——同一输入多次跑结果一致。限频保证了这点，但规则内部逻辑也要检查。
- ⚠️ **不要在 scheduler 里直接调 LLM**——规则引擎纯代码，避免长尾阻塞定时任务。
- ⚠️ filelock 机制下 heartbeat job 只会在一个 worker 上跑，不用担心多 worker 重复发送。

---

## 四、模块 M3 — Coach Memo v2（结构化演化画像）

### 4.1 目标

`Profile.coach_memo` 从自由文本（500 字字符串）升级为结构化 JSON，按维度累积，避免 LLM 重写时丢信息。

### 4.2 Schema 定义

**文件**：**新建** `backend/models/coach_memo.py`（纯 Pydantic，不是 DB 模型）

```python
"""Coach Memo v2 结构化 schema.

存在 Profile.coach_memo 字段里（继续用 Text，内容是 JSON 字符串）。
向后兼容：legacy_text 字段承接老自由文本 memo。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PivotEvent(BaseModel):
    """关键转折事件。"""
    date: str  # ISO 日期
    event: str  # "改目标从后端转算法"
    trigger: str = ""  # 为什么改：诊断低/面试挂/新兴趣


class OpenThread(BaseModel):
    """未闭环的对话线索 —— 驱动 heartbeat 主动跟进。"""
    topic: str  # "C++ 项目选型"
    last_mentioned: str  # ISO 日期
    followup: str = ""  # "问他 muduo 做到哪一步了"


class CoachMemoV2(BaseModel):
    """结构化教练备忘录。

    每个字段都是可独立更新的列表/值，LLM upsert 时只改有变化的部分。
    """
    version: Literal[2] = 2
    
    # 决策偏好（低频变化）
    decision_patterns: list[str] = Field(default_factory=list)
    # 例: ["反复对比才能决定", "重视数据而非经验"]
    
    # 焦虑触发点（对话中显式出现的）
    anxiety_triggers: list[str] = Field(default_factory=list)
    # 例: ["AI 替代担忧", "同辈压力"]
    
    # 对话风格偏好
    preferred_style: str = ""
    # 例: "喜欢直给数据不要鸡汤"
    
    # 关键转折事件
    pivot_events: list[PivotEvent] = Field(default_factory=list)
    
    # 未闭环话题（heartbeat 用）
    open_threads: list[OpenThread] = Field(default_factory=list)
    
    # 最后更新时间
    updated_at: str = ""
    
    # 兼容老数据
    legacy_text: str = ""


def parse_memo(raw: str) -> CoachMemoV2:
    """从 DB 字段解析。空字符串 / 老文本 / 新 JSON 都能处理。"""
    import json
    if not raw:
        return CoachMemoV2()
    raw = raw.strip()
    # 尝试当 JSON 解析
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if data.get("version") == 2:
                return CoachMemoV2(**data)
        except Exception:
            pass
    # 回退：老自由文本 → 塞到 legacy_text
    return CoachMemoV2(legacy_text=raw[:600])


def serialize_memo(memo: CoachMemoV2) -> str:
    """序列化存 DB。"""
    return memo.model_dump_json()
```

### 4.3 改写 `_update_coach_memo`

**文件**：`backend/routers/chat.py:816-883` 整段替换。

```python
def _update_coach_memo(session_id: int, user_id: int) -> None:
    """Background: 分维度 upsert coach memo v2."""
    from backend.db import SessionLocal
    from backend.llm import get_model, llm_chat
    from backend.db_models import Profile, ChatMessage
    from backend.models.coach_memo import CoachMemoV2, parse_memo, serialize_memo
    from sqlalchemy import func
    from datetime import datetime, timezone
    import json

    db = SessionLocal()
    try:
        msg_count = (
            db.query(func.count(ChatMessage.id))
            .filter(ChatMessage.session_id == session_id)
            .scalar() or 0
        )
        if msg_count < 6:
            return

        profile = (
            db.query(Profile)
            .filter_by(user_id=user_id)
            .order_by(Profile.updated_at.desc())
            .first()
        )
        if not profile:
            return

        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(20)
            .all()
        )
        conversation = "\n".join(f"{m.role}: {m.content[:200]}" for m in msgs)
        
        current_memo = parse_memo(profile.coach_memo or "")
        
        # 调 LLM 生成 JSON patch
        patch_json = _extract_memo_patch(conversation, current_memo)
        
        if not patch_json:
            return
        
        # 应用 patch
        updated_memo = _apply_memo_patch(current_memo, patch_json)
        updated_memo.updated_at = datetime.now(timezone.utc).isoformat()
        
        profile.coach_memo = serialize_memo(updated_memo)
        db.commit()
        logger.info("Updated coach_memo v2 for user %d", user_id)
    except Exception:
        logger.exception("Failed to update coach memo v2")
    finally:
        db.close()


_MEMO_EXTRACT_PROMPT = """分析以下对话，抽取需要记入用户画像的信息。只输出 JSON，不加任何解释。

输出 schema：
{
  "new_decision_patterns": [],
  "new_anxiety_triggers": [],
  "preferred_style": "",
  "new_pivot_events": [{"date": "ISO日期", "event": "...", "trigger": "..."}],
  "new_open_threads": [{"topic": "...", "last_mentioned": "ISO日期", "followup": "..."}],
  "closed_threads": []
}

规则：
- 只抽取本次对话里**新出现**的信息，已有的不重复
- 任何字段没有新信息就返回空列表/空字符串
- 不输出 version/updated_at/legacy_text 字段

当前已知：
{current_summary}

对话：
{conversation}

JSON:"""


def _extract_memo_patch(conversation: str, current: CoachMemoV2) -> dict | None:
    """让 LLM 输出 JSON patch。坏格式时返回 None（不污染 memo）。"""
    from backend.llm import get_model, llm_chat
    import json
    
    current_summary = (
        f"偏好: {current.preferred_style or '未知'}; "
        f"已知触发点: {current.anxiety_triggers[:3]}; "
        f"已知模式: {current.decision_patterns[:3]}"
    )
    try:
        resp = llm_chat(
            [
                {"role": "system", "content": "你是画像抽取器。严格按 JSON schema 输出。"},
                {"role": "user", "content": _MEMO_EXTRACT_PROMPT.format(
                    current_summary=current_summary,
                    conversation=conversation,
                )},
            ],
            model=get_model("fast"),
            temperature=0.1,
            timeout=15,
            response_format={"type": "json_object"},  # DashScope 兼容 OpenAI
        )
        data = json.loads(resp)
        return data if isinstance(data, dict) else None
    except Exception:
        logger.exception("Memo patch extraction failed")
        return None


def _apply_memo_patch(current: CoachMemoV2, patch: dict) -> CoachMemoV2:
    """把 patch 合并到现有 memo，返回新实例。幂等。"""
    from backend.models.coach_memo import CoachMemoV2, PivotEvent, OpenThread
    
    # append 类字段去重后追加
    new_patterns = [x for x in patch.get("new_decision_patterns", []) if x not in current.decision_patterns]
    new_triggers = [x for x in patch.get("new_anxiety_triggers", []) if x not in current.anxiety_triggers]
    new_pivots = [PivotEvent(**e) for e in patch.get("new_pivot_events", []) if isinstance(e, dict)]
    new_threads = [OpenThread(**t) for t in patch.get("new_open_threads", []) if isinstance(t, dict)]
    
    # 闭环：从 open_threads 移除被关闭的
    closed_topics = set(patch.get("closed_threads", []))
    remaining_threads = [t for t in current.open_threads if t.topic not in closed_topics]
    
    # 上限：每个 list 最多留 10 条，超了丢最早的
    _LIMIT = 10
    
    return CoachMemoV2(
        version=2,
        decision_patterns=(current.decision_patterns + new_patterns)[-_LIMIT:],
        anxiety_triggers=(current.anxiety_triggers + new_triggers)[-_LIMIT:],
        preferred_style=patch.get("preferred_style") or current.preferred_style,
        pivot_events=(current.pivot_events + new_pivots)[-_LIMIT:],
        open_threads=(remaining_threads + new_threads)[-_LIMIT:],
        legacy_text=current.legacy_text,  # 保留
    )
```

### 4.4 Context 注入改写

**文件**：`agent/supervisor.py:303-306` 替换 `memo = state.get("coach_memo", "")` 相关逻辑。

```python
# agent/supervisor.py 顶部加
from backend.models.coach_memo import parse_memo

# 在 build_context_summary 里替换
memo_raw = state.get("coach_memo", "")
if memo_raw:
    # v2 结构化注入：只取对当前 agent 有用的切片
    memo = parse_memo(memo_raw)
    memo_lines = []
    if memo.preferred_style:
        memo_lines.append(f"  · 对话偏好: {memo.preferred_style}")
    if memo.anxiety_triggers:
        memo_lines.append(f"  · 焦虑点: {', '.join(memo.anxiety_triggers[:3])}")
    if memo.decision_patterns:
        memo_lines.append(f"  · 决策模式: {', '.join(memo.decision_patterns[:3])}")
    if memo.open_threads:
        thread_strs = [f"「{t.topic}」({t.followup})" for t in memo.open_threads[:2]]
        memo_lines.append(f"  · 未闭环话题: {' / '.join(thread_strs)}")
    if memo.legacy_text and not memo_lines:
        # 老用户兜底
        memo_lines.append(f"  · 历史备忘: {memo.legacy_text[:300]}")
    if memo_lines:
        parts.append("\n教练备忘录：")
        parts.extend(memo_lines)
```

### 4.5 State 层改动

**文件**：`agent/state.py:22`

```python
# 类型改成 str（JSON 字符串），不要改成 dict——避免 LangGraph 序列化问题
# 保持现有声明 coach_memo: str 不动。parse_memo 在需要时按需解析。
```

**文件**：`backend/routers/chat.py:300-305` 读取逻辑保持不变：

```python
state["coach_memo"] = profile.coach_memo or ""  # 继续传 str，消费方自己 parse
```

### 4.6 验收标准

- [ ] 老用户（`coach_memo` 是纯字符串）登录后不报错，`parse_memo` 把旧文本塞进 `legacy_text`
- [ ] 聊 3 轮后 `coach_memo` 变成 JSON 格式，`decision_patterns` 等字段有值
- [ ] LLM 返回坏 JSON 时（mock 一个坏响应），memo 保持不变（不污染）
- [ ] 单元测试：`_apply_memo_patch` 幂等（同一个 patch 跑 2 次结果相同）
- [ ] 单元测试：`parse_memo("")` / `parse_memo("旧的自由文本")` / `parse_memo('{"version":2,...}')` 三种输入都能解析

### 4.7 坑位提示

- ⚠️ **DashScope 的 `response_format={"type": "json_object"}` 需要模型支持**——用 `get_model("fast")` 前确认模型列表，若 fast 模型不支持 JSON mode，改用 `get_model("default")` 或手动在 prompt 里强制"只输出 JSON"并加 `json.loads` 容错
- ⚠️ **不要一次性改 LangGraph State 类型为 dict**——会和 `add_messages` 等 reducer 冲突。保持 str 传递，消费方按需 parse 是最稳的
- ⚠️ 列表上限 10 防止 memo 无限膨胀——超过后丢最早的
- ⚠️ `_apply_memo_patch` 必须对所有 list 字段去重，否则会累积重复项

---

## 五、模块 M4 — Pattern Analyzer（决策模式抽象）

### 5.1 目标

不依赖 LLM，从 `JDDiagnosis` / `JobApplication` / `ChatMessage` 的行为数据反推出"搜索型 vs 锚定型"、"项目驱动 vs 信息驱动"等决策模式，写回 `CoachMemoV2.decision_patterns`。

### 5.2 前置依赖

**必须 M3 完成**才能做本模块。

### 5.3 改动文件

1. **新建** `backend/services/pattern_analyzer.py`
2. **修改** `backend/scheduler.py` — 加周度 job
3. **修改** `backend/routers/chat.py` 的 `_update_coach_memo` — 接入 pattern

### 5.4 Pattern Analyzer

**文件**：`backend/services/pattern_analyzer.py`（新建）

```python
"""用户决策模式分析器 — 基于行为数据的规则推理。

不用 LLM，避免长尾阻塞和 token 成本。规则简单可解释可测试。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def analyze_user(db: Session, user_id: int) -> list[str]:
    """分析单个用户，返回决策模式标签列表。
    
    标签词汇表（固定，便于 coach prompt 对齐）：
    - "搜索型决策" / "锚定型决策"
    - "项目驱动" / "信息驱动"
    - "快速决策" / "反复纠结"
    - "数据不足"（冷启动用户）
    """
    from backend.db_models import JDDiagnosis, JobApplication, ProjectRecord, ChatSession, ChatMessage
    from sqlalchemy import func
    
    patterns: list[str] = []
    
    # 数据量检查
    diag_count = db.query(func.count(JDDiagnosis.id)).filter_by(user_id=user_id).scalar() or 0
    app_count = db.query(func.count(JobApplication.id)).filter_by(user_id=user_id).scalar() or 0
    project_count = db.query(func.count(ProjectRecord.id)).filter_by(user_id=user_id).scalar() or 0
    
    if diag_count < 3 and app_count < 2 and project_count < 1:
        return ["数据不足"]
    
    # 规则 1：搜索型 vs 锚定型
    # 搜索型：诊断过 5+ 不同岗位
    distinct_titles = (
        db.query(func.count(func.distinct(JDDiagnosis.jd_title)))
        .filter_by(user_id=user_id)
        .scalar() or 0
    )
    if distinct_titles >= 5:
        patterns.append("搜索型决策")
    elif diag_count >= 3 and distinct_titles <= 2:
        patterns.append("锚定型决策")
    
    # 规则 2：项目驱动 vs 信息驱动
    # 项目驱动：project_count / diag_count >= 0.5
    if diag_count > 0:
        ratio = project_count / diag_count
        if ratio >= 0.5 and project_count >= 2:
            patterns.append("项目驱动")
        elif diag_count >= 5 and project_count <= 1:
            patterns.append("信息驱动")
    
    # 规则 3：快速决策 vs 反复纠结
    # 反复纠结：同一岗位 title 诊断过 3+ 次
    max_repeat = (
        db.query(func.count(JDDiagnosis.id))
        .filter_by(user_id=user_id)
        .group_by(JDDiagnosis.jd_title)
        .order_by(func.count(JDDiagnosis.id).desc())
        .limit(1)
        .scalar() or 0
    )
    if max_repeat >= 3:
        patterns.append("反复纠结")
    elif distinct_titles >= 3 and max_repeat == 1:
        patterns.append("快速决策")
    
    return patterns


def run_pattern_analysis_all() -> int:
    """扫所有用户，更新 coach_memo 的 decision_patterns 字段。
    
    由 scheduler 每周日 04:00 跑一次。
    """
    from backend.db import SessionLocal
    from backend.db_models import User, Profile
    from backend.models.coach_memo import parse_memo, serialize_memo
    from datetime import datetime, timezone
    
    db = SessionLocal()
    count = 0
    try:
        users = db.query(User).all()
        for u in users:
            patterns = analyze_user(db, u.id)
            if not patterns or patterns == ["数据不足"]:
                continue
            
            profile = (
                db.query(Profile)
                .filter_by(user_id=u.id)
                .order_by(Profile.updated_at.desc())
                .first()
            )
            if not profile:
                continue
            
            memo = parse_memo(profile.coach_memo or "")
            # 合并去重
            existing = set(memo.decision_patterns)
            for p in patterns:
                if p not in existing:
                    memo.decision_patterns.append(p)
            # 只保留最新 10 条
            memo.decision_patterns = memo.decision_patterns[-10:]
            memo.updated_at = datetime.now(timezone.utc).isoformat()
            
            profile.coach_memo = serialize_memo(memo)
            count += 1
        db.commit()
        logger.info("Pattern analysis updated %d users", count)
        return count
    except Exception:
        db.rollback()
        logger.exception("Pattern analysis failed")
        return 0
    finally:
        db.close()
```

### 5.5 Scheduler 注册

**文件**：`backend/scheduler.py`

```python
# 在 start_scheduler 里追加
scheduler.add_job(
    _pattern_analysis_job,
    trigger=CronTrigger(day_of_week="sun", hour=4, minute=0),
    id="weekly-pattern-analysis",
    replace_existing=True,
)


async def _pattern_analysis_job() -> None:
    await asyncio.to_thread(_sync_pattern_analysis)


def _sync_pattern_analysis() -> None:
    from backend.services.pattern_analyzer import run_pattern_analysis_all
    run_pattern_analysis_all()
```

### 5.6 验收标准

- [ ] 单元测试：造一个用户有 6 条不同 jd_title 诊断 → `analyze_user` 返回含"搜索型决策"
- [ ] 单元测试：造一个用户有 3 条相同 jd_title 诊断 → 返回含"反复纠结"
- [ ] 新用户（0 诊断 0 项目）→ 返回 `["数据不足"]`，不污染 memo
- [ ] 跑 `run_pattern_analysis_all()` 能更新真实用户 coach_memo，`decision_patterns` 字段有值
- [ ] 重复跑 2 次，decision_patterns 不应重复

### 5.7 坑位提示

- ⚠️ 规则阈值（5 / 3 / 0.5）是**首版拍脑袋**，需要根据真实数据调——上线后 1-2 周看结果再调
- ⚠️ 不要在 pattern 里写主观标签（"学生很焦虑"），只写行为模式——主观标签应该由 `_update_coach_memo` 从对话里抽
- ⚠️ `ChatSession` 表要确认有没有 `user_id` 字段，没有的话改从 `Profile → User` 间接获取

---

## 六、通用约束

### 6.1 代码风格
- Python 3.11+，使用 `from __future__ import annotations`
- SQLAlchemy 2.0 风格（`Mapped[]` 注解，已有代码基准）
- 前端 TypeScript strict，TanStack Query 管请求
- 所有新文件用 UTF-8，LF 行尾（跟项目已有约定）

### 6.2 错误处理
- 所有后台任务（scheduler job、`_update_coach_memo`）必须 try/except，**绝不抛到顶层**——保 scheduler 不挂
- LLM 调用必须有 timeout（默认 15s）
- DB 写入失败必须 rollback 再关连接

### 6.3 测试
- 4 个模块各自至少 3 个单元测试，放在 `tests/` 下
- 集成测试（可选）：用 pytest fixtures 造测试数据库跑完整链路

### 6.4 不要做的事
- ❌ 不要写 Alembic 迁移脚本（项目目前纯 `create_all`）
- ❌ 不要改 `requirements.txt` 除非真缺依赖（pydantic / APScheduler / SQLAlchemy 都已有）
- ❌ 不要动 `agent/supervisor.py` 的路由逻辑，只改 `build_context_summary` 里读 memo 的那段
- ❌ 不要把 `coach_memo` 字段重命名——保持 `Profile.coach_memo` 名字不变，只改内容格式
- ❌ 不要删除老 `_update_coach_memo` 后就直接发——先跑兼容性测试确认老用户不报错

---

## 七、交付清单

完成后 PR 应包含：

**新增文件**
- `backend/models/coach_memo.py`
- `backend/services/heartbeat_service.py`
- `backend/services/pattern_analyzer.py`
- `tests/test_coach_memo_v2.py`
- `tests/test_heartbeat_service.py`
- `tests/test_pattern_analyzer.py`

**修改文件**
- `backend/db_models.py`（+ UserNotification 表）
- `backend/scheduler.py`（+ 2 个 job）
- `backend/routers/chat.py`（重写 `_update_coach_memo`）
- `backend/routers/guidance.py`（+ heartbeat 端点）
- `agent/supervisor.py`（改 `build_context_summary` 读 memo 逻辑）
- `agent/agents/coach_agent.py`（拆 prompt 为 BASE + 4 stage 片段）
- `frontend/src/pages/HomePage.tsx`（+ HeartbeatBanners 组件）

**新增 API**
- `GET /api/guidance/heartbeat`
- `POST /api/guidance/heartbeat/dismiss`

**新增 scheduler job**
- `daily-heartbeat` (09:00)
- `weekly-pattern-analysis` (Sun 04:00)

---

## 八、回滚策略

每个模块可独立回滚：
- M1 回滚：还原 `coach_agent.py` 的 SYSTEM_PROMPT 为单一字符串
- M2 回滚：`backend/app.py` 里把 `daily-heartbeat` job 注释掉，前端 HeartbeatBanners 返回 null
- M3 回滚：`parse_memo` 在未知格式时返回 legacy_text，`_update_coach_memo` 临时改回旧版（git 历史有）
- M4 回滚：`weekly-pattern-analysis` job 注释掉，已写入的 patterns 保留不影响使用

数据库层面：`UserNotification` 表即使保留也不影响主链路——没数据就不推。

---

> **最后一点**：Kimi 实施时如果遇到文档没覆盖的决策点（比如 `ChatSession` 没有 `user_id` 字段的情况），按"最小惊讶原则"处理——选择和现有代码风格一致、改动面最小的方案，不要擅自引入新架构。不确定时在 PR 描述里列出"以下决策请 reviewer 确认"清单。
