# Growth Log Phase 3 · 视角翻转：从「差距审判」到「成长收获」

> 创建：2026-04-15
> 状态：待 Kimi 实施
> 前置：Phase 1（视觉重写）+ Phase 2（长期追踪 IA）已完成

---

## I. 背景与决策

### 失效模式

当前 `GrowthDashboard` 顶部展示「技能覆盖（按市场重要性分层）」：
- 核心技能 4/5 (80%)
- 重要技能 2/6 (33%)
- 加分技能 0/5 (0%)
- 核心缺口：系统编程

这是 **审判者视角** — 把用户和岗位标准比，告诉他"你差 33%"。

**两个底层问题**：

1. **跟 brand personality 完全相反**
   `.impeccable.md` 写 "温暖 · 同行 · 不评判"，"零评判用语"，"共情前置于分析"。当前 dashboard 用 `2/6 (33%)` 这种数字给用户的是"我又不够"，不是"我在动"。

2. **数据质量撑不起精度**（owner 判断）
   岗位 `skill_tiers` 当前覆盖广而宽，差距分析的输入本身不够细。算出来的"覆盖率"是假精确 — 用户看了不知道下一步怎么动，只剩挫败感。

### 决策

**砍掉差距视角，换成成长视角。**

- 砍：`skill_coverage`（核心/重要/加分覆盖率）+ `readiness_curve`（匹配度曲线）+ "核心缺口" chips
- 换：
  - `SkillsHarvest`（收获式）：「这个月你记了 N 笔，新触达 M 个技能」+ chip 网格
  - `ActivityPulse`（节奏式）：「连续 N 周没断节奏」+ 12 周热力柱

---

## II. 砍清单

### 后端

- **删除** `GET /growth-log/dashboard` endpoint（`backend/routers/growth_log.py:182-302`）
  - 含 `skill_coverage` 三层覆盖率计算
  - 含 `readiness_curve`（来自 `GrowthSnapshot.readiness_score`）
  - 含 `gap_skills`（已确认前端不消费此字段，`ProjectsSection.tsx:257` 用的是 `fetchProfile().career_goals[i].gap_skills`）
  - 含 `days_since_start`（`GrowthLogPage` Chapter I 已用 `goal.set_at` 自算）

- **保留** `GrowthSnapshot` 表（`/journey` endpoint 还要用 stage_events）— **不动 schema，不动 supervisor 写入逻辑**

- **保留** `_skill_matches` 函数（`growth_log_service.py`）— 其他地方可能用

### 前端

- **删除文件**：`frontend/src/components/growth-log/GrowthDashboard.tsx`
- **删除函数**：`getGrowthDashboard` from `frontend/src/api/growthLog.ts`
- **删除类型**：`GrowthDashboardData`, `TierCoverage` from `frontend/src/api/growthLog.ts`
- **替换**：`GrowthLogPage.tsx:196` 的 `<GrowthDashboard />` → `<SkillsHarvest />` + `<ActivityPulse />`
- **删除**：`GrowthLogPage.tsx:127` 的 `useQuery({ queryKey: ['growth-dashboard'], ... })`

---

## III. 新增 API 设计

### 1. `GET /growth-log/skills-harvest`

**用途**：本月「我学到了啥」的数据源。

**请求**：无参数（基于 current user）

**响应**：

```json
{
  "has_records": true,
  "month_label": "2026 年 4 月",
  "monthly_record_count": 7,
  "newly_touched_skills": [
    { "name": "PyTorch", "first_seen_at": "2026-04-12T..." },
    { "name": "FastAPI", "first_seen_at": "2026-04-08T..." }
  ],
  "all_touched_skills": [
    { "name": "Python", "first_seen_at": "2026-02-01T...", "use_count": 5 },
    { "name": "PyTorch", "first_seen_at": "2026-04-12T...", "use_count": 1 }
  ]
}
```

**实现逻辑**：

```python
@router.get("/skills-harvest")
def get_skills_harvest(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"has_records": False, "monthly_record_count": 0, "newly_touched_skills": [], "all_touched_skills": []}

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 本月所有 records 数（projects + applications + interviews）
    monthly_count = (
        db.query(ProjectRecord).filter(
            ProjectRecord.profile_id == profile.id,
            ProjectRecord.created_at >= month_start,
        ).count()
        + db.query(JobApplication).filter(
            JobApplication.user_id == user.id,
            JobApplication.created_at >= month_start,
        ).count()
        + db.query(InterviewRecord).filter(
            InterviewRecord.user_id == user.id,
            InterviewRecord.created_at >= month_start,
        ).count()
    )

    # 聚合所有 ProjectRecord.skills_used → first_seen_at + use_count
    projects = (
        db.query(ProjectRecord)
        .filter(ProjectRecord.profile_id == profile.id)
        .order_by(ProjectRecord.created_at.asc())
        .all()
    )
    skill_map: dict[str, dict] = {}
    for p in projects:
        for s in (p.skills_used or []):
            s_clean = s.strip()
            if not s_clean:
                continue
            if s_clean not in skill_map:
                skill_map[s_clean] = {"name": s_clean, "first_seen_at": p.created_at, "use_count": 0}
            skill_map[s_clean]["use_count"] += 1

    all_skills = sorted(skill_map.values(), key=lambda x: x["first_seen_at"], reverse=True)
    newly_touched = [s for s in all_skills if s["first_seen_at"] >= month_start]

    return {
        "has_records": monthly_count > 0 or len(all_skills) > 0,
        "month_label": now.strftime("%Y 年 %m 月").replace(" 0", " "),
        "monthly_record_count": monthly_count,
        "newly_touched_skills": [
            {"name": s["name"], "first_seen_at": s["first_seen_at"].isoformat()}
            for s in newly_touched
        ],
        "all_touched_skills": [
            {
                "name": s["name"],
                "first_seen_at": s["first_seen_at"].isoformat(),
                "use_count": s["use_count"],
            }
            for s in all_skills
        ],
    }
```

---

### 2. `GET /growth-log/activity-pulse`

**用途**：12 周节奏柱 + 连续活跃周数。

**请求**：无参数

**响应**：

```json
{
  "current_streak_weeks": 3,
  "total_records": 18,
  "weeks": [
    {
      "week_label": "1/29",
      "iso_week": "2026-W05",
      "projects": 0,
      "applications": 0,
      "interviews": 0
    },
    ...
    {
      "week_label": "4/15",
      "iso_week": "2026-W16",
      "projects": 1,
      "applications": 2,
      "interviews": 1
    }
  ]
}
```

**实现逻辑**：

```python
from collections import defaultdict
from datetime import timedelta

@router.get("/activity-pulse")
def get_activity_pulse(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"current_streak_weeks": 0, "total_records": 0, "weeks": []}

    now = datetime.now(timezone.utc)
    twelve_weeks_ago = now - timedelta(weeks=12)

    # 拉 12 周内所有 records
    projects = db.query(ProjectRecord).filter(
        ProjectRecord.profile_id == profile.id,
        ProjectRecord.created_at >= twelve_weeks_ago,
    ).all()
    applications = db.query(JobApplication).filter(
        JobApplication.user_id == user.id,
        JobApplication.created_at >= twelve_weeks_ago,
    ).all()
    interviews = db.query(InterviewRecord).filter(
        InterviewRecord.user_id == user.id,
        InterviewRecord.created_at >= twelve_weeks_ago,
    ).all()

    # 按 ISO week 聚合
    bucket: dict[str, dict] = defaultdict(lambda: {"projects": 0, "applications": 0, "interviews": 0})
    for p in projects:
        key = p.created_at.strftime("%G-W%V")
        bucket[key]["projects"] += 1
    for a in applications:
        key = a.created_at.strftime("%G-W%V")
        bucket[key]["applications"] += 1
    for i in interviews:
        key = i.created_at.strftime("%G-W%V")
        bucket[key]["interviews"] += 1

    # 生成最近 12 周完整序列（含空周）
    weeks = []
    for i in range(11, -1, -1):
        wk_date = now - timedelta(weeks=i)
        iso_key = wk_date.strftime("%G-W%V")
        weeks.append({
            "week_label": wk_date.strftime("%m/%d").lstrip("0").replace("/0", "/"),
            "iso_week": iso_key,
            "projects": bucket[iso_key]["projects"],
            "applications": bucket[iso_key]["applications"],
            "interviews": bucket[iso_key]["interviews"],
        })

    # 连续活跃周数（从最新一周倒着数）
    streak = 0
    for w in reversed(weeks):
        if (w["projects"] + w["applications"] + w["interviews"]) > 0:
            streak += 1
        else:
            break

    total = sum(w["projects"] + w["applications"] + w["interviews"] for w in weeks)

    return {
        "current_streak_weeks": streak,
        "total_records": total,
        "weeks": weeks,
    }
```

---

## IV. 新组件设计

### 1. `frontend/src/components/growth-log/SkillsHarvest.tsx`

**Hero 句**（按状态分支）：
- 有记录有新技能：`这个月你记了 {N} 笔，新触达 {M} 个技能。`
- 有记录无新技能：`这个月你记了 {N} 笔。已经积累了 {totalSkills} 个技能。`
- 无记录但有历史技能：`本月还没动 — 但你过往积累了 {totalSkills} 个技能。`
- 完全空：`第一个技能在等你的第一笔记录。`

**Chip 网格规则**：
- 本月新增的 chip：`bg-[var(--ember)/0.15]` + `text-[var(--ember)]` + 右上角小标 "本月"
- 已有的 chip：`bg-[var(--bg-paper)]` + `border-[var(--line)]` + `text-[var(--ink-2)]`
- 排序：本月新增在前，再按 first_seen_at 倒序
- 容量上限：20 个 chip。超出显示 "+{rest} 个"。

**视觉示意**：

```
┌────────────────────────────────────────┐
│ 这个月你记了 7 笔，                      │
│ 新触达 2 个技能。                        │
│                                        │
│ [PyTorch · 本月] [FastAPI · 本月]        │
│ [Python] [SQL] [React] [Docker] ...    │
└────────────────────────────────────────┘
```

**Skeleton 实现**：

```tsx
import { useQuery } from '@tanstack/react-query'
import { getSkillsHarvest } from '@/api/growthLog'
import { PaperCard } from '@/components/growth-log/PaperCard'

export function SkillsHarvest() {
  const { data, isLoading } = useQuery({
    queryKey: ['skills-harvest'],
    queryFn: getSkillsHarvest,
    staleTime: 120_000,
  })

  if (isLoading) return <PaperCard className="h-[180px] animate-pulse" />
  if (!data) return null

  const { monthly_record_count, newly_touched_skills, all_touched_skills } = data
  const newCount = newly_touched_skills.length
  const totalCount = all_touched_skills.length

  // Hero 句子
  const hero = monthly_record_count > 0 && newCount > 0 ? (
    <>这个月你<strong className="text-[var(--chestnut)]">记了 {monthly_record_count} 笔</strong>，
       新触达 <strong className="text-[var(--ember)]">{newCount} 个技能</strong>。</>
  ) : monthly_record_count > 0 ? (
    <>这个月你<strong className="text-[var(--chestnut)]">记了 {monthly_record_count} 笔</strong>。
       已经积累了 {totalCount} 个技能。</>
  ) : totalCount > 0 ? (
    <>本月还没动 — 但你过往积累了 <strong>{totalCount} 个技能</strong>。</>
  ) : (
    <>第一个技能在等你的第一笔记录。</>
  )

  // Sorted list: newly touched first, then rest
  const newSet = new Set(newly_touched_skills.map(s => s.name))
  const sortedChips = [
    ...newly_touched_skills,
    ...all_touched_skills.filter(s => !newSet.has(s.name)),
  ].slice(0, 20)
  const rest = Math.max(0, all_touched_skills.length - 20)

  return (
    <PaperCard>
      <p className="font-display text-[clamp(18px,2.4vw,24px)] leading-[1.5] text-[var(--ink-1)] mb-6 max-w-[40ch]">
        {hero}
      </p>
      {sortedChips.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {sortedChips.map(s => {
            const isNew = newSet.has(s.name)
            return (
              <span
                key={s.name}
                className={
                  isNew
                    ? 'inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] font-medium border border-[var(--ember)]/40'
                    : 'inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] text-[var(--ink-2)] border border-[var(--line)] bg-[var(--bg-paper)]'
                }
                style={isNew ? { background: 'oklch(0.66 0.13 50 / 0.12)', color: 'var(--ember)' } : undefined}
              >
                {s.name}
                {isNew && <span className="text-[9px] tracking-wider uppercase opacity-70">本月</span>}
              </span>
            )
          })}
          {rest > 0 && (
            <span className="inline-flex items-center px-2.5 py-1 text-[12px] text-[var(--ink-3)]">
              +{rest} 个
            </span>
          )}
        </div>
      )}
    </PaperCard>
  )
}
```

---

### 2. `frontend/src/components/growth-log/ActivityPulse.tsx`

**Hero 句**：
- streak ≥ 1：`你已经连续 {streak} 周没断节奏。` 
- streak = 0 且 total > 0：`这一周还没动 — 上次记录是 {N} 周前。今天记一笔？`
- 全空：`等你第一笔记录，节奏就开始了。`

**12 周柱视觉**：
- 每周一根柱，宽 16px，间距 4px
- 堆叠：底 moss（项目）→ 中 ember（投递）→ 顶 chestnut（面试）
- 0 笔的周显示极淡 line（`bg-[var(--line)]`）
- 高度自适应：max(weeks) → 80px
- 周标签每 2 周显示一个

**Skeleton**：

```tsx
import { useQuery } from '@tanstack/react-query'
import { getActivityPulse } from '@/api/growthLog'
import { PaperCard } from '@/components/growth-log/PaperCard'

export function ActivityPulse() {
  const { data, isLoading } = useQuery({
    queryKey: ['activity-pulse'],
    queryFn: getActivityPulse,
    staleTime: 120_000,
  })

  if (isLoading) return <PaperCard className="h-[160px] animate-pulse" />
  if (!data) return null

  const { current_streak_weeks, total_records, weeks } = data
  const maxCount = Math.max(1, ...weeks.map(w => w.projects + w.applications + w.interviews))

  const hero = current_streak_weeks > 0 ? (
    <>你已经<strong className="text-[var(--moss)]">连续 {current_streak_weeks} 周</strong>没断节奏。</>
  ) : total_records > 0 ? (
    <>这一周还没动 — 今天记一笔？</>
  ) : (
    <>等你第一笔记录，节奏就开始了。</>
  )

  return (
    <PaperCard>
      <p className="font-display text-[15px] text-[var(--ink-2)] mb-4">{hero}</p>
      <div className="flex items-end gap-1 h-[100px]">
        {weeks.map((w, i) => {
          const total = w.projects + w.applications + w.interviews
          const pHeight = (w.projects / maxCount) * 80
          const aHeight = (w.applications / maxCount) * 80
          const iHeight = (w.interviews / maxCount) * 80
          return (
            <div key={w.iso_week} className="flex flex-col items-center flex-1 min-w-0">
              <div className="flex flex-col-reverse w-full max-w-[16px] mx-auto" style={{ height: 80 }}>
                {total === 0 && (
                  <div className="w-full" style={{ height: 2, background: 'var(--line)' }} />
                )}
                {pHeight > 0 && (
                  <div className="w-full" style={{ height: pHeight, background: 'var(--moss)' }} />
                )}
                {aHeight > 0 && (
                  <div className="w-full" style={{ height: aHeight, background: 'var(--ember)' }} />
                )}
                {iHeight > 0 && (
                  <div className="w-full" style={{ height: iHeight, background: 'var(--chestnut)' }} />
                )}
              </div>
              {i % 2 === 0 && (
                <span className="text-[9px] text-[var(--ink-3)] mt-1 tabular-nums">
                  {w.week_label}
                </span>
              )}
            </div>
          )
        })}
      </div>
      <div className="flex items-center gap-3 mt-4 text-[10px] text-[var(--ink-3)]">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2" style={{ background: 'var(--moss)' }} /> 项目
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2" style={{ background: 'var(--ember)' }} /> 投递
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2" style={{ background: 'var(--chestnut)' }} /> 面试
        </span>
      </div>
    </PaperCard>
  )
}
```

---

### 3. API client 新增

`frontend/src/api/growthLog.ts`：

```ts
// ── Skills Harvest ──
export interface SkillTouched {
  name: string
  first_seen_at: string
  use_count?: number
}

export interface SkillsHarvestData {
  has_records: boolean
  month_label: string
  monthly_record_count: number
  newly_touched_skills: SkillTouched[]
  all_touched_skills: SkillTouched[]
}

export const getSkillsHarvest = () =>
  rawFetch<SkillsHarvestData>(`${BASE}/skills-harvest`)

// ── Activity Pulse ──
export interface WeeklyActivity {
  week_label: string
  iso_week: string
  projects: number
  applications: number
  interviews: number
}

export interface ActivityPulseData {
  current_streak_weeks: number
  total_records: number
  weeks: WeeklyActivity[]
}

export const getActivityPulse = () =>
  rawFetch<ActivityPulseData>(`${BASE}/activity-pulse`)
```

---

### 4. `GrowthLogPage.tsx` 改造

替换现在 Chapter I 内的 `<GrowthDashboard />`：

```tsx
import { SkillsHarvest } from '@/components/growth-log/SkillsHarvest'
import { ActivityPulse } from '@/components/growth-log/ActivityPulse'

// Chapter I 内：
<Chapter numeral="I" label="你的旅程" title={chapterITitle} intro={chapterIIntro}>
  {hasGoal && setAt && (
    <div className="mb-8">
      <JourneyTimeline ... />
    </div>
  )}
  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    <SkillsHarvest />
    <ActivityPulse />
  </div>
</Chapter>
```

并删除 line 127：
```tsx
useQuery({ queryKey: ['growth-dashboard'], queryFn: getGrowthDashboard, staleTime: 120_000 })
```

---

## V. 验收标准

1. **首屏不再有审判性数字**
   - 没有 X/Y、% 覆盖率、"差距"、"缺口" 字样
   - 改成 N 笔、M 个技能、连续 N 周

2. **本月新触达技能视觉高亮**
   - 新 chip 用 ember 色 + "本月" 小标
   - 已有 chip 中性色

3. **空状态友好**
   - 0 笔 → "今天记一笔？" 而不是空白
   - 0 技能 → "第一个技能在等你的第一笔记录"

4. **节奏柱颜色区分**
   - 项目 moss / 投递 ember / 面试 chestnut
   - 0 笔的周显示极淡 line

5. **后端**
   - 删 `/dashboard` endpoint 后，`pytest tests/` 0 regression（注意：可能有 dashboard 测试需要一并删）
   - `/skills-harvest` 和 `/activity-pulse` 各加一个最小集成测试（has_records + monthly_count）

6. **前端**
   - `npx tsc --noEmit` 0 错误
   - `frontend/src/components/growth-log/GrowthDashboard.tsx` 文件已删除
   - `getGrowthDashboard / GrowthDashboardData / TierCoverage` 已从 api/types 中清除

---

## VI. 不做的事（明确说不做，避免发散）

- ❌ 不做技能雷达图（G3）— 维度怎么分类是另一个二级问题，留 Phase 4
- ❌ 不做 chip 点击钻取（点 chip → 看哪个项目用过这个技能）— 留增强
- ❌ 不做"技能成熟度"评分（用了 5 次 = 熟练）— 数据质量也不够
- ❌ 不动 `/journey` `/goal-history` `/projects` `/interviews` 等其他 endpoint
- ❌ 不动 `GrowthSnapshot` 表 schema，不动 `supervisor.py` 写 snapshot 的逻辑（journey 还要用）

---

## VII. 给 Kimi 的执行顺序

1. **后端先行**：
   - 写 `/skills-harvest` + `/activity-pulse` 两个新 endpoint
   - 跑 `pytest tests/` 确认全绿
   - 删 `/dashboard` endpoint，再跑 pytest，删配套 test（如有）

2. **前端 API + 类型**：
   - 在 `growthLog.ts` 加新 types + 新函数
   - 删 `getGrowthDashboard / GrowthDashboardData / TierCoverage`

3. **前端组件**：
   - 新建 `SkillsHarvest.tsx` + `ActivityPulse.tsx`
   - 删 `GrowthDashboard.tsx`
   - 改 `GrowthLogPage.tsx`：替换 Chapter I 内组件 + 删 `useQuery(['growth-dashboard'])`

4. **验证**：
   - `npx tsc --noEmit` → 0 错误
   - 启动 dev server，开 `/growth-log`，肉眼看是否符合验收标准
   - 截图给 owner 审

---

**完成判定**：owner 看截图 + 跑一遍能感受到"我做了什么、学到了什么"，而不是"我差多少"。
