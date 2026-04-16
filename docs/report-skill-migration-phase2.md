# Report Pipeline — Phase 2：行为驱动的动态报告 + 可溯源下一步

> **状态**：草案 v1（交接给 Kimi 执行前的最终版）
> **前置依赖**：Phase 1 已完成（commit `d48cb37` + `ad3b837`）。`backend/skills/` 下 5 个 SKILL.md 可用，`load_skill / invoke_skill` 已稳。
> **目标读者**：接手执行的后端工程师（Kimi）
> **预计改动**：~800 行（新增 + 重写），集中在 `backend/services/report/`、`backend/skills/`、`backend/routers/profiles.py`

---

## §0 背景与动机

Phase 1 只搬了 prompt 的"住址"，没动行为。报告仍然只消费：简历提取的技能/项目、成长档案的 `ProjectRecord name/description`、市场数据。以下成长档案/画像里的字段**完全没进 LLM prompt**：

| 字段 | 承载什么 |
|---|---|
| `ProjectLog`（表） | 项目周进展笔记 / 真实增长痕迹 |
| `ProjectRecord.reflection` | 项目完成后的感悟 |
| `ProjectRecord.skills_used / status / gap_skill_links` | 项目补的是哪个 gap、做完了没 |
| `InterviewRecord + InterviewDebrief` | 面试记录 + AI 复盘（痛点信号） |
| `JobApplication` | 投递漏斗、方向分布 |
| `Profile.coach_memo` | coach 跨会话积累的用户自然语言备忘（**敏感**） |
| `GrowthSnapshot.four_dim_detail` 历史 | 四维走势 |

同时现有 `backend/services/action_plan_llm.py` 的行动计划（第四章"下一步"）只看粗粒度统计（skills / app_count / top_missing），看不到任何行为信号——导致：
- 用户上周刚在 ProjectLog 里写"epoll 搞通了"，下一步还在建议"学 epoll"
- 用户最近 3 次面试都挂在 Linux IPC 细节，下一步看不到这个信号，给的是泛泛的"补高并发"
- 上一份报告说"做个 Redis 项目"，用户真做了，这次报告还在说一样的话

**Phase 2 要解决的根本问题**：报告要能随行为**动态变**，下一步建议要**基于已发生的事实**，且**永远不重复已完成**。

---

## §1 架构变化（before → after）

### Before（Phase 1 结束状态）

```
raw tables (ProjectRecord, Profile) 
     ↓ 直接散装喂
narrative / diagnosis / career-alignment / action_plan_llm.py
     ↓
ReportV2Data
```

- 每个 skill / 模块各自从 `profile_data` / `projects` 里拿自己需要的片段
- `action_plan_llm.py` 完全独立，不是 skill，不看 ProjectLog / InterviewRecord
- `coach_memo` 无人读取
- 没有跨报告 delta（只有 `match_score` 的差，没有"上次建议 → 这次完成"的闭环）

### After（Phase 2 目标）

```
raw tables (ProjectRecord, ProjectLog, InterviewRecord, InterviewDebrief,
            JobApplication, GrowthSnapshot, Profile, SkillUpdate)
           +
prev_report (Report.data_json 最新一份)
     ↓
backend/services/report/summarize.py  ← 新增
     ↓
{
  "window": {...},
  "milestones": [...],        # 时间序事件（项目进展/完成/技能/投递/面试）
  "skill_deltas": {...},      # 上次报告后新掌握 / 仍只声明未练 / 本期练过
  "signals": {
    "interview": {...},       # 次数 + 痛点（抽自 content_summary，由 LLM 做）
    "application": {...},     # 漏斗 + 方向分布
    "project_momentum": {...} # 活跃 / 停滞 / 完成
  },
  "completed_since_last_report": [...],   # 上次报告后做完了什么
  "prev_report_recommendations": [...],   # 上次的下一步建议
}
     ↓ 中间 JSON
narrative / diagnosis / career-alignment / action-plan (4 个 skill 都只读这个 JSON)
     ↓
ReportV2Data
```

**关键原则**：
1. **中间 JSON 是唯一数据源**。下游 skill 不再读 raw 表，不再从 `profile_data` 里挑字段。
2. **coach_memo 永远不进任何 report skill 的 prompt**。它归属 coach 自己的 surface，硬隔离。
3. **时间窗口**：默认 `now - 90 天`；老数据只进 skill_deltas 的 summary，不进 milestones。
4. **可溯源**：每个 milestone / signal 带 `source` 字段（如 `project_log:42`）供前端未来展开。本期前端不显示，只写入 JSON 为未来 UI 留接口。

---

## §2 中间 JSON Schema（严格定义）

**文件位置**：由 `backend/services/report/summarize.py::build_report_summary()` 返回。

**类型**：`dict[str, Any]`（不强制 pydantic，但字段名 / 嵌套结构必须严格遵守下表）。

```json
{
  "version": "2.0",

  "window": {
    "since_iso": "2026-01-16",
    "now_iso": "2026-04-16",
    "days": 90
  },

  "milestones": [
    {
      "id": "M-001",
      "date_iso": "2026-04-10",
      "source": "project_log:42",
      "category": "project_progress",
      "title": "高并发内存池完成基于线程的 TCP 并发测试",
      "detail": "QPS 从 12k 提升到 38k，主要瓶颈是 malloc 热点",
      "skills_touched": ["C++", "Linux", "性能优化"]
    }
  ],

  "skill_deltas": {
    "practiced_in_window": ["epoll", "Redis 持久化"],
    "gained_since_last_report": ["epoll"],
    "still_claimed_only": ["Docker", "Kubernetes"],
    "four_dim_trend": {
      "foundation": [62, 64, 68],
      "skills": [45, 52, 58],
      "potential": [70, 72, 75]
    }
  },

  "signals": {
    "interview": {
      "count_in_window": 3,
      "total_ever": 7,
      "latest": {
        "company": "美团",
        "position": "后端开发",
        "round": "技术一面",
        "self_rating": "medium",
        "result": "pending",
        "date_iso": "2026-04-05"
      },
      "pain_points": [
        "Linux IPC 细节（pipe/fifo/信号量）追问卡壳",
        "epoll 边缘触发 vs 水平触发的区别讲不清"
      ]
    },
    "application": {
      "count_in_window": 8,
      "total_ever": 12,
      "funnel": {
        "applied": 5, "screening": 2, "interviewed": 1,
        "offer": 0, "rejected": 2, "withdrawn": 0
      },
      "directions": [
        {"label": "C++ 后端", "count": 6},
        {"label": "Linux 服务端", "count": 2}
      ]
    },
    "project_momentum": {
      "active_count": 2,
      "completed_in_window_count": 1,
      "stalled_ids": [15, 18]
    }
  },

  "completed_since_last_report": [
    "Redis 基础",
    "epoll 边缘触发 demo"
  ],

  "prev_report_recommendations": [
    "做一个 Redis 项目",
    "补量化数据"
  ]
}
```

### 字段约定 & 硬规则

- **所有字符串字段禁止含 `coach_memo` 内容**。`summarize.py` 必须在构造 JSON 时显式跳过 `profile.coach_memo`（详见 §8）。
- **`milestones.category` 取值**（枚举）：`project_progress | project_complete | skill_claim | interview | application | reflection`。
- **`milestones.source` 格式**：`<table>:<id>` 或 `<table>:multi` 若跨多条。表名限定：`project_log | project_record | interview_record | job_application | skill_update | growth_snapshot`。
- **`milestones` 上限**：最多 20 条，按 `date_iso desc` 排序，超出的丢到 `skill_deltas` 的汇总里。
- **`pain_points` 上限**：最多 5 条，由 `extract-interview-signals` skill 产出（见 §4）。
- **`window.days` 默认 90**，可以被环境变量 `REPORT_SUMMARY_WINDOW_DAYS` 覆盖。
- **空用户保障**：成长档案/画像完全空时，返回所有字段存在但为空列表 / 0 / null 的 JSON。下游 skill 必须在模板里对空值做"若有/若无"分支（用 `{xxx}` 占位符时，formatter 保证不是 None）。

---

## §3 `backend/services/report/summarize.py`（新增）

**职责**：读 raw 表 → 输出 §2 的 JSON。大部分逻辑纯 Python；仅 `pain_points` 抽取调 `extract-interview-signals` skill（详见 §4）。

**完整接口签名**：

```python
# backend/services/report/summarize.py

from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any
import logging
import os

from sqlalchemy.orm import Session

from backend.db_models import (
    Profile, ProjectRecord, ProjectLog, InterviewRecord,
    InterviewDebrief, JobApplication, GrowthSnapshot, SkillUpdate, Report,
)

logger = logging.getLogger(__name__)

_WINDOW_DAYS = int(os.getenv("REPORT_SUMMARY_WINDOW_DAYS", "90"))


def build_report_summary(
    user_id: int,
    profile: Profile,
    db: Session,
    prev_report: Report | None = None,
) -> dict:
    """构造报告的中间 JSON。纯 Python + 一次可选 LLM 调用（抽面试痛点）。

    Args:
        user_id: 用户 id
        profile: 已加载的 Profile ORM 对象
        db: SQLAlchemy Session
        prev_report: 上一份 Report（若有），用于算 delta / completed_since_last_report /
                     prev_report_recommendations

    Returns:
        dict，严格遵守 §2 schema。永不返回 None。
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=_WINDOW_DAYS)

    # ── 1. milestones ──────────────────────────────────────────────────
    milestones = _build_milestones(user_id, profile.id, db, since)

    # ── 2. skill_deltas ────────────────────────────────────────────────
    skill_deltas = _build_skill_deltas(user_id, profile, db, since, prev_report)

    # ── 3. signals ─────────────────────────────────────────────────────
    signals = {
        "interview": _build_interview_signal(user_id, db, since),
        "application": _build_application_signal(user_id, db, since),
        "project_momentum": _build_project_momentum(user_id, db, since),
    }

    # ── 4. prev report delta ───────────────────────────────────────────
    completed_since_last, prev_recs = _build_prev_delta(prev_report, db)

    return {
        "version": "2.0",
        "window": {
            "since_iso": since.isoformat(),
            "now_iso": now.isoformat(),
            "days": _WINDOW_DAYS,
        },
        "milestones": milestones,
        "skill_deltas": skill_deltas,
        "signals": signals,
        "completed_since_last_report": completed_since_last,
        "prev_report_recommendations": prev_recs,
    }


# ── Helpers（全部私有，不 export）─────────────────────────────────────────

def _build_milestones(user_id: int, profile_id: int, db: Session,
                      since: datetime) -> list[dict]:
    """合并 ProjectLog / ProjectRecord 完成 / InterviewRecord / JobApplication /
    SkillUpdate，按时间倒序取 20 条。每条带 source + category。"""
    ...


def _build_skill_deltas(user_id: int, profile: Profile, db: Session,
                        since: datetime, prev_report: Report | None) -> dict:
    """
    - practiced_in_window: 读 ProjectLog + ProjectRecord.skills_used（window 内）
    - gained_since_last_report: 对比上一份 Report.data_json 的 skill_gap.matched_skills
    - still_claimed_only: profile_json.skills 中，本期和历史都没在 practiced 里出现过的
    - four_dim_trend: 读 GrowthSnapshot.four_dim_detail 取最近 3 个快照
    """
    ...


def _build_interview_signal(user_id: int, db: Session, since: datetime) -> dict:
    """读 InterviewRecord + InterviewDebrief。
    调用 invoke_skill('extract-interview-signals', ...) 从 content_summary / raw_input
    抽 pain_points（最多 5 条）。失败时 pain_points=[]。"""
    ...


def _build_application_signal(user_id: int, db: Session, since: datetime) -> dict:
    """读 JobApplication，聚合 funnel + directions（按 position 字段聚类）。"""
    ...


def _build_project_momentum(user_id: int, db: Session, since: datetime) -> dict:
    """
    - active_count: status='in_progress' 且最近 14 天有 ProjectLog 的项目
    - completed_in_window_count: completed_at 在 window 内的项目
    - stalled_ids: status='in_progress' 且 >30 天无 ProjectLog 的项目
    """
    ...


def _build_prev_delta(prev_report: Report | None,
                      db: Session) -> tuple[list[str], list[str]]:
    """从 prev_report.data_json 解出：
    - completed_since_last_report: 上次报告的 prev_report_recommendations 中，
      现在已经在 skill_deltas.practiced 或 milestones 中出现过的 → 标记完成
    - prev_report_recommendations: 上次报告 action_plan.stages[*].items[*].text 中
      type 为 skill / project 的条目
    若 prev_report 为 None，返回 ([], [])。"""
    ...
```

**落地要求**：
- 所有 helper 失败（DB query 异常 / JSON 解析错）→ 返回空值（空 list / 0 / None），**不 raise**。顶层调用必须永远能拿到一个完整 JSON。
- Helper 之间**禁止互相依赖**。每个 helper 独立读 DB，独立捕获异常。这样一个 helper 挂不会影响其他字段。
- `_build_interview_signal` 里的 LLM 调用超时 ≤15 秒，失败时 `pain_points` 为空列表，其余字段照常返回。

---

## §4 新增 skill: `extract-interview-signals`

**目的**：从 `InterviewRecord.content_summary`（自由文本）+ `InterviewDebrief.raw_input`（嵌套 JSON）里抽出 pain_points（面试挂点/反复卡壳的知识点）。

**文件**：`backend/skills/extract-interview-signals/SKILL.md`

```markdown
---
name: extract-interview-signals
description: 从面试记录的自由文本抽出学生的知识盲点/反复卡壳点，最多 5 条
model: fast
temperature: 0.2
max_tokens: 500
output: json
---

## System

你是一位面试复盘分析师。你的任务是从学生提交的面试自述文本里，提炼出"明确卡壳、回答不出、反复被追问"的具体知识点。

硬约束：
- 只提炼**具体的技术点**（如 "Linux IPC 的 pipe/fifo 区别"），不提炼抽象类别（如 "Linux 基础"）。
- 最多 5 条，最少 0 条。宁缺毋滥。
- 学生只说"表现一般"没给具体问题 → 返回空列表，不要编。
- 只输出 JSON 数组，不要 markdown 代码块，不要解释文字。

## User

以下是学生最近 N 次面试的自述（每条含公司、轮次、自评、结果、内容摘要 / 答题原文）：

{interviews_json}

请输出形如下面的 JSON 数组（最多 5 条）：

["pain_point 1", "pain_point 2", ...]

如果文本里没有具体技术卡壳点，输出 []。
```

**调用方**：`summarize.py::_build_interview_signal`。

**input 格式**（`{interviews_json}` 占位符内容示例）：
```json
[
  {"company":"美团","round":"技术一面","self_rating":"medium","result":"pending",
   "summary":"被问到 epoll 边缘触发时没讲清楚，然后问 pipe 和 fifo 的区别我只说了一个","reflection":"得去翻 man 7 pipe"},
  {"company":"字节","round":"技术二面","self_rating":"bad","result":"failed",
   "summary":"系统设计让我设计一个抢红包，我只画了单机版的架构图","reflection":""}
]
```

---

## §5 新增 skill: `action-plan`（替换 `action_plan_llm.py`）

**目的**：消费 §2 的中间 JSON + 目标岗位信息，生成三阶段行动计划。与旧版 `action_plan_llm.py` 的本质区别：
- 看得到 `completed_since_last_report` → 不重复建议已完成的事
- 看得到 `signals.interview.pain_points` → 下一步可以挂钩面试痛点
- 看得到 `skill_deltas.practiced_in_window` → 避免建议"学 X"但用户已练过
- 看得到 `prev_report_recommendations` → 显式承接（"上次说 Y，这次你做完了 Z，下一步是 W"）

**文件**：`backend/skills/action-plan/SKILL.md`

```markdown
---
name: action-plan
description: 基于中间 JSON（行为信号 + 上期建议 delta）生成三阶段行动计划
model: strong
temperature: 0.3
max_tokens: 2500
output: json
---

## System

你是一位职业观察员。你的任务是基于学生"这段时间做了什么 + 上次报告说了什么"，给一份承接式的三阶段行动计划。

硬约束：
1. **不重复 completed_since_last_report 里的事**。若学生已完成 X，不可再建议"学 X"。
2. **必须至少 2 条建议挂钩具体行为信号**：引用 `milestones` 里某个具体事件、或 `pain_points` 中某个具体技术点、或 `skill_deltas.still_claimed_only` 中某个技能。
3. **观察句**，禁止祈使句。禁止以"完成/搭建/实现/编写/学习/掌握/阅读/深入/用/通过/进行/梳理/配置/部署"开头。
4. **不绑定具体项目名**。可以引用"你在某个项目里遇到的情况"，但不许说"在 XX 项目基础上加 Y"。
5. **三阶段固定**：
   - stage 1（0-2 周，求职准备类，2 条 items）
   - stage 2（2-6 周，技能补强类，2-4 条 items）
   - stage 3（6-12 周，项目冲刺/求职推进，2-3 条 items）
6. 每条 text 60-150 字，要有"为什么"和"会怎样"。
7. 输出严格 JSON，不要 markdown 代码块。

输出格式（严格）：

{
  "stages": [
    {
      "stage": 1,
      "label": "立即整理",
      "duration": "0-2周",
      "milestone": "一句话里程碑",
      "items": [
        {
          "id": "item-1-1",
          "type": "skill|project|job_prep",
          "text": "观察句，60-150 字",
          "tag": "短标签",
          "priority": "high|medium|low",
          "phase": 1,
          "evidence_ref": "M-003"
        }
      ]
    },
    { "stage": 2, ... },
    { "stage": 3, ... }
  ]
}

其中 `evidence_ref` 指向 milestones.id 或 pain_points 的索引字符串（如 "pain:0"）或 skill_deltas 字段名（如 "still_claimed_only:Docker"）。如果某条建议没有特定证据，evidence_ref 为空字符串。

## User

目标岗位：{target_label}
岗位要求摘要：{node_requirements_line}
市场信号：{market_line}

## 本期活动摘要（中间 JSON）

{summary_json}

## 上次报告的下一步建议（用于承接，不要重复）

{prev_recommendations_block}

## 本期已完成的事（禁止再次建议）

{completed_block}

请输出三阶段计划 JSON。
```

**调用方**：`backend/services/report/pipeline.py::generate_report`，取代现有的 `build_action_plan_with_llm` 调用（§7 详述）。

**旧文件处理**：`backend/services/action_plan_llm.py` **删除**（不保留兼容层）。

**Fallback**：LLM 调用失败时，使用 `backend/services/report/action_plan.py` 里的规则引擎 `_build_action_plan` 作为兜底（已存在，保持不动）。

---

## §6 修改现有 3 个 skill 的 user template

**核心规则**：三个 skill 的 user template **完全不读 raw 表字段**，只读中间 JSON 的几个字段 + 目标岗位基础信息。

### 6.1 `backend/skills/narrative/SKILL.md`

**保留**：
- System 区不动（"观察手记体，400-600 字"的硬规则保留）
- Frontmatter 不动

**重写 User template**：

```markdown
## User

目标方向：{target_label}

## 学生这段时间的活动摘要

**最近做的事**（milestones，最多 5 条）：
{milestones_line}

**本期新练过的技能**：{practiced_in_window}
**上次报告后刚掌握的**：{gained_since_last_report}
**还只是简历上的（没有项目证据）**：{still_claimed_only}

## 市场侧

{market_line}

## 教育背景

{education_line}

请基于以上**具体行为信号**，写一封 400-600 字的观察手记。必须至少引用 2 条具体的 milestone 或技能名，不要停留在空话。
```

**Formatter 规则**：`narrative._generate_narrative` 签名变成：

```python
def _generate_narrative(
    target_label: str,
    summary: dict,          # 中间 JSON，来自 summarize.build_report_summary
    education_line: str,
    market_line: str,
) -> str:
    milestones_line = _format_milestones(summary["milestones"][:5])
    practiced = ", ".join(summary["skill_deltas"]["practiced_in_window"]) or "（暂无）"
    gained = ", ".join(summary["skill_deltas"]["gained_since_last_report"]) or "（暂无）"
    claimed = ", ".join(summary["skill_deltas"]["still_claimed_only"][:5]) or "（暂无）"
    return invoke_skill(
        "narrative",
        target_label=target_label,
        milestones_line=milestones_line,
        practiced_in_window=practiced,
        gained_since_last_report=gained,
        still_claimed_only=claimed,
        market_line=market_line,
        education_line=education_line,
    )
```

**移除**：原来的 `_format_projects_for_prompt` / `_format_delta_line`（被 summary JSON 里的字段取代）。保留 `_format_education` / `_format_market`。

**新增 helper**：

```python
def _format_milestones(milestones: list[dict]) -> str:
    if not milestones:
        return "（这段时间档案里还没留下具体记录）"
    return "\n".join(
        f"- [{m['date_iso'][:10]}] {m['title']}（{m.get('detail','')[:80]}）"
        for m in milestones
    )
```

### 6.2 `backend/skills/diagnosis/SKILL.md`

**改动 User template**：`projects_json` 里每个项目附上 `logs` 字段（最近 3 条 log 文本）。System 区新增一行："优先基于 logs 里的具体进展给改进建议，不要仅凭 description 猜测。"

调用方 `narrative._diagnose_profile` 要新增 `logs` 查询：

```python
# 对每个 item_to_check，若 source_type=growth_log，查最近 3 条 ProjectLog
for it in items_to_check:
    if it["source_type"] == "growth_log":
        logs = db.query(ProjectLog).filter(
            ProjectLog.project_id == it["source_id"]
        ).order_by(ProjectLog.created_at.desc()).limit(3).all()
        it["logs"] = [l.content[:200] for l in logs]
    else:
        it["logs"] = []
```

注意：`_diagnose_profile` 现在没有 `db` 参数，要加一个。上游 `pipeline.py::generate_report` 里传入。

### 6.3 `backend/skills/career-alignment/SKILL.md`

**改动 User template**：在现有内容后追加两段：

```markdown
## 本期行为信号（来自中间摘要）

**面试情况**：{interview_line}
**投递方向分布**：{application_directions}
**面试痛点**（你被问过但答不好的）：{pain_points_line}
```

**System 区新增约束**：
- "alignments 的 evidence 字段若能引用面试痛点 / 投递方向分布，优先引用（比技能名更硬）"
- "若 pain_points 指向某个方向的核心技能，alignments 的 gap 字段要明确指出"

**Formatter 改动**：`_build_career_alignment` 签名加一个 `summary: dict` 参数，把 interview / application / pain_points 格式化后传给 skill。

---

## §7 `backend/services/report/pipeline.py` 调用改动

### 7.1 顶部 import 增加

```python
from backend.services.report import summarize
```

### 7.2 `generate_report` 函数内，在计算完 `four_dim / match_score / market_info` 之后、调用 narrative 之前，插入：

```python
# ── 新增：构造中间 JSON ─────────────────────────────────────────
prev_report = (
    db.query(Report)
    .filter(Report.user_id == user_id)
    .order_by(Report.created_at.desc())
    .first()
)
summary = summarize.build_report_summary(
    user_id=user_id,
    profile=profile,
    db=db,
    prev_report=prev_report,
)
```

### 7.3 改造下游调用

**narrative**（替换现有调用）：
```python
narrative_text = narrative._generate_narrative(
    target_label=goal.target_label,
    summary=summary,
    education_line=narrative._format_education(profile_data.get("education")),
    market_line=narrative._format_market(market_info),
)
```

**diagnosis**（新增 db 参数）：
```python
diagnosis = narrative._diagnose_profile(
    profile_data=profile_data,
    projects=projects,
    node_label=goal.target_label,
    db=db,  # 新增
)
```

**career-alignment**（新增 summary 参数）：
```python
career_alignment_data = career_alignment._build_career_alignment(
    profile_data=profile_data,
    projects=projects,
    graph_nodes=loaders._load_graph_nodes(),
    target_node_id=node_id,
    summary=summary,  # 新增
)
```

**action-plan**（完全替换原 `build_action_plan_with_llm` 调用）：

```python
# 原代码（删除）：
# if _USE_LLM_ACTION_PLAN:
#     try:
#         from backend.services.action_plan_llm import build_action_plan_with_llm
#         ...
#     except Exception as e:
#         action_plan_data = action_plan._build_action_plan(...)

# 新代码：
try:
    from backend.skills import invoke_skill
    action_plan_data = invoke_skill(
        "action-plan",
        target_label=goal.target_label,
        node_requirements_line=_format_node_requirements(node),
        market_line=narrative._format_market(market_info),
        summary_json=json.dumps(summary, ensure_ascii=False),
        prev_recommendations_block=_format_prev_recs(summary["prev_report_recommendations"]),
        completed_block=_format_completed(summary["completed_since_last_report"]),
    )
    # action-plan skill 输出就是 stages 格式，做一次 validate_and_coerce 防御
    action_plan_data = _coerce_action_plan(action_plan_data)
except Exception as e:
    logger.warning("action-plan skill failed, fallback to rule-based: %s", e)
    action_plan_data = action_plan._build_action_plan(
        gap_skills=goal.gap_skills or [],
        top_missing=_skill_gap.get("top_missing", []) if _skill_gap else [],
        node_id=node_id,
        node_label=goal.target_label,
        profile_data=profile_data,
        current_readiness=current_readiness,
        claimed_skills=claimed_skills,
        projects=merged_projects,
        applications=applications,
        profile_proj_descs=profile_proj_descs,
    )
```

**新增 helpers** 放在 `pipeline.py` 底部（或拆到 `narrative.py` 里都行）：

```python
def _format_node_requirements(node: dict) -> str:
    tiers = node.get("skill_tiers", {})
    core = [s.get("name") if isinstance(s, dict) else s for s in tiers.get("core", [])][:5]
    return f"核心技能：{', '.join(core) or '（未定义）'}"

def _format_prev_recs(recs: list[str]) -> str:
    if not recs:
        return "（这是第一份报告，无上次建议）"
    return "\n".join(f"- {r}" for r in recs[:6])

def _format_completed(items: list[str]) -> str:
    if not items:
        return "（本期无已完成的旧建议）"
    return "\n".join(f"- {it}" for it in items)

def _coerce_action_plan(raw: dict) -> dict:
    """确保 raw 至少有 stages[3]，每个 stage 有 items。缺的补空。"""
    stages = raw.get("stages", [])
    while len(stages) < 3:
        stages.append({
            "stage": len(stages) + 1,
            "label": ["立即整理", "技能补强", "项目冲刺与求职"][len(stages)],
            "duration": ["0-2周", "2-6周", "6-12周"][len(stages)],
            "milestone": "",
            "items": [],
        })
    return {
        "stages": stages[:3],
        # 兼容字段：skills/project/job_prep 从 stages 里展平
        "skills": [it for s in stages for it in s.get("items", []) if it.get("type") == "skill"],
        "project": [it for s in stages for it in s.get("items", []) if it.get("type") == "project"],
        "job_prep": [it for s in stages for it in s.get("items", []) if it.get("type") == "job_prep"],
    }
```

### 7.4 ReportV2Data payload 新增字段

在 `report_data = {...}` 里加一项：

```python
"summary": summary,  # 中间 JSON 也进最终报告，供前端未来用（本期不显示）
```

**不改**：`match_score / four_dim / narrative / diagnosis / market / skill_gap / growth_curve / action_plan / delta / soft_skills / career_alignment / differentiation_advice / ai_impact_narrative / project_recommendations / generated_at`。

---

## §8 `coach_memo` 硬隔离规则

**硬规则**：
1. **`summarize.py` 全文禁止读 `profile.coach_memo`**。在文件顶部加一条注释明示：
   ```python
   # NOTE: coach_memo is intentionally NOT read anywhere in this module.
   # It's a cross-session memo owned by the coach agent and may contain
   # sensitive/personal content. It belongs to the coach-facing surface only.
   ```
2. **所有 report skill 的 user template 禁止含 `{coach_memo*}` 占位符**。
3. 在 `backend/skills/` 下新增一份 `PRIVACY_BOUNDARY.md`（只是说明文档，不是 SKILL）记录："coach_memo 不可进入任何 report skill 的 prompt"。

**验证手段**：新增一条 unit test `tests/services/report/test_summary_privacy.py`：

```python
def test_summary_never_contains_coach_memo(db_session, user_factory):
    user = user_factory()
    profile = ...  # with coach_memo = "敏感内容：我在偷偷面试字节"
    summary = summarize.build_report_summary(user.id, profile, db_session, None)
    blob = json.dumps(summary, ensure_ascii=False)
    assert "敏感内容" not in blob
    assert "偷偷面试字节" not in blob
```

---

## §9 `backend/routers/profiles.py::reset_profile` 加强（可选但建议）

**现状**：已显式 delete 9 张表（ProjectLog、InterviewRecord、InterviewDebrief、JobApplication、ProjectRecord、Report、JDDiagnosis、CoachResult、SjtSession、CareerGoal）。

**加强**（防止未来加表又漏）：改用 `sqlalchemy.inspect` 自动枚举所有 FK 指向 `users.id` 或 `profiles.id` 的表：

```python
from sqlalchemy import inspect, delete

def _enumerate_user_owned_tables(metadata):
    """返回所有 FK 指向 users.id 或 profiles.id 的表名列表。"""
    tables = []
    for table_name, table in metadata.tables.items():
        for col in table.columns:
            for fk in col.foreign_keys:
                if fk.column.table.name in ("users", "profiles"):
                    tables.append((table_name, col.name))
                    break
    return tables
```

然后遍历 delete。**保留**现有的显式 delete 列表作为"确定性清单"，自动枚举作为**日志警告**——发现新表但没在显式清单里时打 warning，不直接 delete（安全）。

```python
# 在 reset_profile 末尾加：
_auto = _enumerate_user_owned_tables(Base.metadata)
_known = {"project_logs", "interview_records", "interview_debriefs",
          "job_applications", "project_records", "reports", "jd_diagnoses",
          "coach_results", "sjt_sessions", "career_goals"}
_missing = [t for t, _ in _auto if t not in _known]
if _missing:
    logger.warning("reset_profile: tables FK-linked to user/profile but NOT in explicit list: %s", _missing)
```

这样未来加新表 → 日志里会喊出来 → 人工补到显式清单。

---

## §10 Cache 机制（减轻延迟）

中间 JSON 可复用：如果上一份 Report 生成后成长档案/投递/面试都没新增，直接复用上次报告里的 `summary` 字段。

**实现**：`summarize.build_report_summary` 顶部加：

```python
def build_report_summary(user_id, profile, db, prev_report=None):
    if prev_report is not None:
        latest_change = _latest_user_activity_time(user_id, db)
        if latest_change and prev_report.created_at >= latest_change:
            prev_data = json.loads(prev_report.data_json or "{}")
            if prev_data.get("summary", {}).get("version") == "2.0":
                logger.info("Reusing prev report summary (no new activity)")
                return prev_data["summary"]
    # else 走正常构造流程
    ...


def _latest_user_activity_time(user_id: int, db: Session) -> datetime | None:
    """返回所有"活动表"里 max(created_at/updated_at)。"""
    from sqlalchemy import func
    queries = [
        db.query(func.max(ProjectLog.created_at)).join(ProjectRecord).filter(ProjectRecord.user_id == user_id),
        db.query(func.max(ProjectRecord.updated_at)).filter(ProjectRecord.user_id == user_id),
        db.query(func.max(InterviewRecord.updated_at)).filter(InterviewRecord.user_id == user_id),
        db.query(func.max(JobApplication.updated_at)).filter(JobApplication.user_id == user_id),
        db.query(func.max(SkillUpdate.created_at)).join(Profile).filter(Profile.user_id == user_id),
    ]
    times = [q.scalar() for q in queries if q.scalar()]
    return max(times) if times else None
```

---

## §11 回归 checklist（§12 完工证据要对照此表逐条给结果）

1. `python -c "from backend.services.report.summarize import build_report_summary"` 无 import 错误。
2. 所有 5 + 2 = 7 个 skill 都能 `load_skill()` 成功。
3. `POST /api/report/generate`（空档案用户）返回正常，`summary` 字段存在，`milestones/pain_points` 为空列表。
4. `POST /api/report/generate`（有成长档案 + 面试记录的用户）返回中：
   - `summary.milestones` ≥ 1 条
   - `summary.signals.interview.pain_points` 反映 content_summary 里的内容（≥ 0 条，不要瞎编）
   - `narrative` 里至少引用 1 条 milestone 或 skill delta 里的技能名
   - `action_plan.stages` 共 3 段，items 总数 ≥ 6，且**不包含** `completed_since_last_report` 里的任何项
   - `action_plan` 里至少 2 条 item 的 `evidence_ref` 非空
5. 连续生成两次报告（用户中间无任何新增）→ 第二次 `summary` 来自 cache（日志里出现 `Reusing prev report summary`）。
6. 连续生成两次报告（中间新加一条 ProjectLog）→ 第二次 `summary.milestones` 比第一次多 1 条。
7. `tests/services/report/test_summary_privacy.py` 通过：summary JSON 序列化后不含 coach_memo 内容。
8. 老报告 `GET /api/report/{id}`（在 Phase 2 migration 之前生成的）依然能正常读取——旧 data_json 里没有 `summary` 字段，前端要容忍。
9. `editReport / polishReport / deleteReport` 接口不回归。
10. `backend/services/action_plan_llm.py` 文件已删除。
11. `reset_profile` 调用后，用户所有 ProjectRecord / ProjectLog / InterviewRecord / JobApplication / Report 都被清空（现状已有，确认不回归）。

---

## §12 非目标（本期明确不做）

- **前端改动**：`summary` 字段进 ReportV2Data 但前端本期不读取不渲染。前端 ChapterIV 继续用 `action_plan.stages`（兼容字段不变）。
- **`skill_gap` 相关 prompt 迁移**：`backend/services/report/skill_gap.py` 里的两处直连 LLM 调用（`_generate_skill_actions` / `_infer_implicit_skills_llm`）**不动**。
- **新增数据库表或迁移**：`summary` 字段直接进 `Report.data_json` 的 JSON blob，不加表不改 schema。
- **ReportV2Data Pydantic schema 改动**：后端返回多一个字段前端会忽略，这是兼容的。
- **Coach skill 架构改动**：coach 自己的 skill 系统不受影响，memo 的读取/写入继续由 coach agent 负责。
- **Evidence-linked 的前端展开 UI**：milestones / evidence_ref 字段写入报告但前端不展示。这是为下个阶段预留的数据接口。

---

## §13 执行边界 & 求助规则

遇到以下情况**不要自己猜，写下问题先停**：

1. `summarize.py` 里某个 helper 不确定该返回什么结构时——参考 §2 schema 示例，仍不确定 → 停
2. 旧 `action_plan_llm.py` 里的 `_IMPERATIVE_PREFIXES` 过滤逻辑是否要搬进新 `action-plan` skill 的校验层——我的建议是**搬到 Python 侧做 post-process 校验**（不进 System prompt），如果 Kimi 有别的判断可以停下来沟通
3. `_latest_user_activity_time` 里是否要包含 InterviewDebrief 的时间——我的判断是不包含（Debrief 依赖 InterviewRecord，写入时间接近），但 Kimi 若发现边界 case 要停下来沟通
4. `reset_profile` 的自动枚举如果报 warning 但不删，这算"安全不操作"还是"bug"——我的判断是安全不操作，打 warning 足够

---

## §14 交付物

1. 新增文件：
   - `backend/services/report/summarize.py`
   - `backend/skills/extract-interview-signals/SKILL.md`
   - `backend/skills/action-plan/SKILL.md`
   - `backend/skills/PRIVACY_BOUNDARY.md`
   - `tests/services/report/test_summary_privacy.py`

2. 修改文件：
   - `backend/skills/narrative/SKILL.md`（user template 重写）
   - `backend/skills/diagnosis/SKILL.md`（user template + system 小改）
   - `backend/skills/career-alignment/SKILL.md`（user template 追加 + system 小改）
   - `backend/services/report/narrative.py`（`_generate_narrative` / `_diagnose_profile` 签名变）
   - `backend/services/report/career_alignment.py`（`_build_career_alignment` 签名加 `summary`）
   - `backend/services/report/pipeline.py`（流程改造 + 7 个新 helper）
   - `backend/routers/profiles.py`（`reset_profile` 加自动枚举 warning）

3. 删除文件：
   - `backend/services/action_plan_llm.py`

4. Commit message 建议：
   ```
   feat(report): Phase 2 behavior-driven dynamic report + action plan

   - New intermediate JSON layer (summarize.py) feeds all 4 report skills
   - New skills: extract-interview-signals, action-plan
   - action_plan_llm.py deleted; replaced by action-plan skill
   - coach_memo hard-isolated from report prompts (privacy boundary)
   - Summary cache: reuse if no user activity since prev report
   - reset_profile auto-enumerates FK tables (warning-only safety net)
   ```

---

## §15 开工前先回一句

收到 spec 后，先回："文档读完，准备开工"——如果有任何在 §13 里列出的不确定，同步提出。别急着动键盘。
