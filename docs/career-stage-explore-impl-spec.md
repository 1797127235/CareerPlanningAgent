# Spec：职业阶段感知 + 对比探索页 · 实施方案

## 背景

本 spec 把 `docs/career-stage-and-explore-spec.md` 里规划的东西落地。数据侧已全部就绪（15 个核心岗位有 `contextual_narrative` 6 字段叙事），只差打通后端端点 + 前端页面让用户看到。

## 目标（本版做什么）

1. **后端**：`/me/stage` 端点，基于 profile + report + growth_log 信号自动判定 4 阶段
2. **后端**：`/graph/*` 节点返回里透出 `contextual_narrative` 字段
3. **前端**：新路由 `/explore` 对比探索页，两两岗位并排 + 6 字段叙事 + "选它"CTA
4. **前端**：首页按阶段切第一屏 CTA（`exploring` 阶段推 /explore，其它阶段保持现状）
5. **前端**：`/graph` 卡片和 `/roles/:roleId` 页面加跳转入口到 `/explore`

## 非目标（不要做）

- ❌ 不要把 `/graph` / `/profile` / `/report` 现有页面的主体流程改掉——只加入口
- ❌ 不要加阶段提示弹窗（"你进入 X 阶段了！"）——阶段变化静默发生
- ❌ 不要对比卡里出现分数、百分比、雷达图、进度条——liu 明确反对 gamification
- ❌ 不要自己改 graph.json 或添加新字段——数据已就绪
- ❌ 不要引入新的 state 管理库（zustand/jotai 之类），用现有的 React Query + URLSearchParams 就够
- ❌ 不要引入动画库或 Framer Motion——普通 CSS transition 即可
- ❌ 不要把对比扩到 3 个、4 个岗位——就两两对比
- ❌ 不要做"对比前的引导问题"漏斗——MVP 不做

## 依赖（开工前确认）

- [x] `data/graph.json` 里 15 个核心岗位都有 `contextual_narrative`（6 子字段）
- [x] DB 已同步（`scripts/sync_graph_to_db`）
- [x] 现有的 `rawFetch<T>()` 可用（`frontend/src/api/client.ts`）
- [x] 现有的 React Query + React Router v6 架构

跑一下确认数据：
```bash
python -c "
import json
d = json.load(open('data/graph.json', encoding='utf-8'))
has_cn = [n['node_id'] for n in d['nodes'] if n.get('contextual_narrative')]
print(f'{len(has_cn)}/45 岗位有 contextual_narrative')
print(has_cn)
"
# 期望：15/45，列表包含 java/frontend/ai-engineer/... 等 15 个
```

---

## Part A：后端改造

### A.1 新增 `backend/services/career_stage.py`

创建新文件：

```python
"""Determine the user's current career-planning stage from persisted signals.

Stages (inferred from actions, not user-declared):
  exploring     - Profile absent OR no target_node_id set
  focusing      - Has profile + target + at least 1 report; no interview yet
  job_hunting   - Has at least 1 interview entry in growth_log
  sprinting     - Has ≥3 interviews or any offer entry
"""
from __future__ import annotations

import json
import logging
from typing import Literal

from sqlalchemy.orm import Session

from backend.db_models import Profile, Report

logger = logging.getLogger(__name__)

Stage = Literal['exploring', 'focusing', 'job_hunting', 'sprinting']


def determine_stage(user_id: int, db: Session) -> Stage:
    """Return the current career stage based on the user's persisted signals."""
    # 1. profile + target
    profile = db.query(Profile).filter_by(user_id=user_id).first()
    has_profile = profile is not None and bool(profile.profile_json)
    target_node_id = None
    if has_profile:
        try:
            target_node_id = json.loads(profile.profile_json).get('target_node_id')
        except Exception:
            target_node_id = None

    if not has_profile or not target_node_id:
        return 'exploring'

    # 2. report count
    report_count = db.query(Report).filter_by(user_id=user_id).count()

    # 3. interview / offer signals
    # ⚠️ 开工前校准：成长档案 v2 的 entry 表模型名和 kind 字段需跟现有代码对齐。
    #    先在 backend/db_models.py 里搜 "GrowthEntry" 或 "growth_log" 确认实际模型名，
    #    如果模型/字段名不是 `kind`，改成 tag 匹配。
    try:
        from backend.db_models import GrowthEntry  # 调整为实际模型名
        interview_count = (
            db.query(GrowthEntry)
            .filter_by(user_id=user_id)
            .filter(GrowthEntry.kind == 'interview')
            .count()
        )
        offer_count = (
            db.query(GrowthEntry)
            .filter_by(user_id=user_id)
            .filter(GrowthEntry.kind == 'offer')
            .count()
        )
    except ImportError:
        logger.warning("GrowthEntry model not found - stage determination will skip interview/offer signals")
        interview_count = 0
        offer_count = 0

    # 4. 分档
    if offer_count > 0 or interview_count >= 3:
        return 'sprinting'
    if interview_count >= 1:
        return 'job_hunting'
    if report_count >= 1:
        return 'focusing'
    return 'focusing'
```

⚠️ **一定要跟现有成长档案 v2 模型对齐**：开工前先 `grep -rn "class Growth" backend/db_models.py` 找出实际的 entry 模型名和字段名。如果现有模型没有 `kind` 字段，用 `tags` 包含 `面试` / `offer` 匹配也可以。

### A.2 新增 `/me/stage` 端点

在 **`backend/routers/user.py`**（或现有的用户路由文件——跑 `grep -rn "@router.get.*me" backend/routers/` 确认）里加：

```python
from backend.services.career_stage import determine_stage

@router.get("/me/stage")
def get_career_stage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's current career-planning stage.

    Used by the frontend to conditionally render homepage CTA and gate
    access to the /explore flow.
    """
    return {"stage": determine_stage(user.id, db)}
```

### A.3 `graph` 端点透出 `contextual_narrative`

**`backend/routers/graph.py`** 大约第 109 行附近（上次改 zone 时也在这块），加一行：

```python
# 找到类似这样的节点序列化 dict，在里面加一行：
{
    # ...
    "zone": node.get("zone", "transition"),
    "human_ai_leverage": node.get("human_ai_leverage", 50),
    "contextual_narrative": node.get("contextual_narrative"),  # ← 新增
    # ...
}
```

同样处理所有返回节点的端点（`/graph/nodes`、`/graph/map`、`/graph/node/{id}` 等，用 grep 找全）。

### A.4 后端验收

```bash
python -m uvicorn backend.app:app --reload

# 1. stage 端点
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/me/stage
# 期望: {"stage": "exploring"} 或其它阶段

# 2. graph 节点返回 contextual_narrative
curl http://localhost:8000/graph/nodes | python -m json.tool | grep -A2 contextual_narrative | head -20
# 期望: 15 个节点的 contextual_narrative 非 null
```

---

## Part B：前端改造

### B.1 扩展类型 `frontend/src/types/graph.ts`

在 `GraphNode` 接口里加字段：

```typescript
export interface ContextualNarrative {
  what_you_actually_do: string
  what_drains_you: string
  three_year_outlook: string
  who_fits: string
  ai_impact_today: string
  common_entry_path: string
}

export interface GraphNode {
  node_id: string
  label: string
  role_family: string
  zone: Zone
  replacement_pressure: number
  human_ai_leverage: number
  salary_p50?: number
  career_level: number
  must_skills?: string[]
  skill_count?: number
  degree?: number
  soft_skills?: Record<string, number>
  promotion_path?: Array<{ level: number; title: string }>
  contextual_narrative?: ContextualNarrative  // ← 新增（可选）
}
```

### B.2 新增 API 函数

在 **`frontend/src/api/user.ts`**（或 `api/report.ts` 末尾，你们仓库哪个合适放哪个）加：

```typescript
import { rawFetch } from './client'

export type CareerStage = 'exploring' | 'focusing' | 'job_hunting' | 'sprinting'

export async function fetchCareerStage(): Promise<{ stage: CareerStage }> {
  return rawFetch<{ stage: CareerStage }>('/me/stage')
}
```

### B.3 新增 hook `frontend/src/hooks/useCareerStage.ts`

```typescript
import { useQuery } from '@tanstack/react-query'
import { fetchCareerStage, type CareerStage } from '@/api/user'

export function useCareerStage() {
  return useQuery<{ stage: CareerStage }>({
    queryKey: ['career-stage'],
    queryFn: fetchCareerStage,
    staleTime: 5 * 60 * 1000,  // 5 分钟内不重取
  })
}

// 辅助：默认兜底为 focusing（未加载时避免闪第一屏）
export function useCurrentStage(): CareerStage {
  const { data } = useCareerStage()
  return data?.stage ?? 'focusing'
}

export type { CareerStage }
```

### B.4 新增路由（`frontend/src/App.tsx`）

在 `<Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>` 块里加：

```tsx
<Route path="/explore" element={<ExplorePage />} />
```

在文件顶部加 import：

```tsx
import ExplorePage from '@/pages/ExplorePage'
```

### B.5 新增 `frontend/src/pages/ExplorePage.tsx`

这是最大的文件（~150 行），实现两两岗位对比：

```tsx
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchGraphMap } from '@/api/graph'
import type { GraphNode } from '@/types/graph'
import { JobPickerButton } from '@/components/explore/JobPickerButton'
import { ComparisonRow } from '@/components/explore/ComparisonRow'

const FIELD_ORDER: Array<{ key: keyof NonNullable<GraphNode['contextual_narrative']>; label: string }> = [
  { key: 'what_you_actually_do', label: '你每天真正在做的事' },
  { key: 'what_drains_you',      label: '什么会耗尽你' },
  { key: 'three_year_outlook',   label: '3 年后这岗位的样子' },
  { key: 'who_fits',             label: '什么样的人适合' },
  { key: 'ai_impact_today',      label: 'AI 今天在这岗位里做什么' },
  { key: 'common_entry_path',    label: '学生怎么切进去' },
]

export default function ExplorePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  // 左右岗位 id，同步到 URL 以便分享
  const leftId = searchParams.get('left') ?? ''
  const rightId = searchParams.get('right') ?? ''

  const { data: graphData, isLoading } = useQuery({
    queryKey: ['graph-map'],
    queryFn: fetchGraphMap,
    staleTime: 10 * 60 * 1000,
  })

  // 只保留有 contextual_narrative 的节点作为可选项
  const availableNodes = useMemo(
    () => (graphData?.nodes ?? []).filter(n => n.contextual_narrative),
    [graphData?.nodes],
  )

  // 全部节点（含没叙事的）——用于显示"叙事建设中"灰态
  const allNodes = graphData?.nodes ?? []

  const leftNode = allNodes.find(n => n.node_id === leftId) ?? null
  const rightNode = allNodes.find(n => n.node_id === rightId) ?? null

  const setLeft = (nid: string) => {
    searchParams.set('left', nid)
    setSearchParams(searchParams)
  }
  const setRight = (nid: string) => {
    searchParams.set('right', nid)
    setSearchParams(searchParams)
  }

  const chooseAsTarget = async (nid: string) => {
    try {
      // 把 target_node_id 写到 profile
      const { rawFetch } = await import('@/api/client')
      await rawFetch('/profile', {
        method: 'PATCH',
        body: JSON.stringify({ target_node_id: nid }),
      })
      navigate('/profile')
    } catch (e) {
      console.error('设置目标失败', e)
      alert('设置目标失败，请稍后重试')
    }
  }

  if (isLoading) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <p className="text-[13px] text-slate-400">加载岗位信息…</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-[880px]">
        <header className="mb-10">
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-400 mb-3">
            EXPLORE
          </p>
          <h1 className="text-[32px] md:text-[40px] font-extrabold text-slate-900 leading-[1.1] tracking-[-0.02em]">
            并排看两个方向。
          </h1>
          <p className="mt-3 text-[13px] text-slate-500 max-w-[56ch]">
            先弄懂每个岗位真实的样子，再决定往哪走。{availableNodes.length} 个方向可对比。
          </p>
        </header>

        <div className="grid grid-cols-2 gap-6 mb-10">
          <JobPickerButton
            label="左"
            selectedNode={leftNode}
            availableNodes={availableNodes}
            allNodes={allNodes}
            onSelect={setLeft}
          />
          <JobPickerButton
            label="右"
            selectedNode={rightNode}
            availableNodes={availableNodes}
            allNodes={allNodes}
            onSelect={setRight}
          />
        </div>

        {leftNode?.contextual_narrative && rightNode?.contextual_narrative && (
          <>
            <div className="space-y-8 mb-10">
              {FIELD_ORDER.map(({ key, label }) => (
                <ComparisonRow
                  key={key}
                  label={label}
                  leftText={leftNode.contextual_narrative![key]}
                  rightText={rightNode.contextual_narrative![key]}
                />
              ))}
            </div>

            <div className="grid grid-cols-2 gap-6 pt-8 border-t border-slate-200">
              <button
                onClick={() => chooseAsTarget(leftNode.node_id)}
                className="text-[13px] font-semibold text-slate-900 border border-slate-900 py-3 px-4 hover:bg-slate-900 hover:text-white transition-colors cursor-pointer"
              >
                选 {leftNode.label} 作为我的目标 →
              </button>
              <button
                onClick={() => chooseAsTarget(rightNode.node_id)}
                className="text-[13px] font-semibold text-slate-900 border border-slate-900 py-3 px-4 hover:bg-slate-900 hover:text-white transition-colors cursor-pointer"
              >
                选 {rightNode.label} 作为我的目标 →
              </button>
            </div>
          </>
        )}

        {(!leftNode || !rightNode) && (
          <div className="text-center py-16">
            <p className="text-[13px] text-slate-400">
              在上方选择两个岗位开始对比。
            </p>
          </div>
        )}
      </div>
    </main>
  )
}
```

### B.6 新增 `frontend/src/components/explore/JobPickerButton.tsx`

```tsx
import { useState } from 'react'
import type { GraphNode } from '@/types/graph'

interface Props {
  label: string
  selectedNode: GraphNode | null
  availableNodes: GraphNode[]  // 有叙事的可选节点
  allNodes: GraphNode[]         // 全部节点（含灰态）
  onSelect: (nodeId: string) => void
}

export function JobPickerButton({ label, selectedNode, availableNodes, allNodes, onSelect }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full border border-slate-300 py-3 px-4 text-left hover:border-slate-900 transition-colors cursor-pointer"
      >
        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
          {label}
        </div>
        <div className="text-[15px] font-semibold text-slate-900">
          {selectedNode ? selectedNode.label : '选一个岗位 ↓'}
        </div>
      </button>

      {open && (
        <div className="absolute left-0 right-0 mt-1 border border-slate-200 bg-white shadow-lg z-10 max-h-[400px] overflow-y-auto">
          {availableNodes.map(n => (
            <button
              key={n.node_id}
              onClick={() => { onSelect(n.node_id); setOpen(false) }}
              className="block w-full text-left px-4 py-2.5 text-[14px] text-slate-900 hover:bg-slate-100 cursor-pointer"
            >
              {n.label}
              <span className="text-[11px] text-slate-400 ml-2">· {n.role_family}</span>
            </button>
          ))}
          {/* 灰态：有但还没叙事的岗位 */}
          {allNodes.filter(n => !availableNodes.includes(n)).length > 0 && (
            <div className="border-t border-slate-200 pt-2 pb-1 px-4 text-[10px] uppercase tracking-widest text-slate-400">
              叙事建设中
            </div>
          )}
          {allNodes.filter(n => !availableNodes.includes(n)).map(n => (
            <div
              key={n.node_id}
              className="block w-full text-left px-4 py-2 text-[13px] text-slate-300 cursor-not-allowed"
            >
              {n.label}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

### B.7 新增 `frontend/src/components/explore/ComparisonRow.tsx`

```tsx
interface Props {
  label: string
  leftText: string
  rightText: string
}

export function ComparisonRow({ label, leftText, rightText }: Props) {
  return (
    <div>
      <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500 mb-4">
        {label}
      </p>
      <div className="grid grid-cols-2 gap-6">
        <p className="text-[14px] leading-relaxed text-slate-900">{leftText}</p>
        <p className="text-[14px] leading-relaxed text-slate-900">{rightText}</p>
      </div>
    </div>
  )
}
```

### B.8 首页 `HomePage.tsx` 按阶段切 CTA

在 HomePage.tsx 里引入 hook，在主 CTA 位置加条件渲染：

```tsx
import { useCurrentStage } from '@/hooks/useCareerStage'
import { Link } from 'react-router-dom'

export default function HomePage() {
  const stage = useCurrentStage()
  // ...现有逻辑...

  // 找到"生成你的职业发展报告"主按钮附近，加：
  if (stage === 'exploring') {
    return (
      <main className="min-h-screen px-6 py-10">
        {/* ...现有导航区域保留... */}
        <div className="text-center max-w-md mx-auto py-20">
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400 mb-3">
            START HERE
          </p>
          <h1 className="text-[32px] md:text-[40px] font-extrabold text-slate-900 leading-[1.1] tracking-[-0.02em]">
            不知道选什么？
          </h1>
          <p className="mt-3 text-[13px] text-slate-500 max-w-[36ch] mx-auto leading-relaxed">
            先弄懂几个方向真实的样子，再决定你的目标岗位。
          </p>
          <Link
            to="/explore"
            className="mt-6 inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer"
          >
            去对比探索 →
          </Link>
        </div>
      </main>
    )
  }
  // 其它阶段保持现有 HomePage 逻辑
  // ...
}
```

⚠️ 注意：HomePage 现有结构我没看全，具体插入点由前端开发决定。核心原则：**exploring 阶段的第一屏大 CTA 指向 /explore，其它阶段不变**。

### B.9 `Coverflow.tsx` 卡片加"对比看看"入口

在 `frontend/src/components/explorer/Coverflow.tsx` 的卡片渲染里（找到显示 node label / zone / skills 的那块），追加：

```tsx
import { Link } from 'react-router-dom'

// 在卡片底部合适位置：
{node.contextual_narrative && (
  <Link
    to={`/explore?left=${node.node_id}`}
    className="text-[11px] text-slate-500 hover:text-blue-600 mt-2 inline-block"
  >
    跟别的方向对比看看 →
  </Link>
)}
```

**只对有 `contextual_narrative` 的 15 个节点显示**，其它卡片不渲染这个链接。

### B.10 `RoleDetailPage.tsx` 底部加"对比相似方向"

```tsx
{data.contextual_narrative && (
  <div className="mt-12 text-center">
    <Link
      to={`/explore?left=${data.node_id}`}
      className="text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700"
    >
      对比相似方向 →
    </Link>
  </div>
)}
```

---

## 验收标准

### 后端

```bash
# 启动
python -m uvicorn backend.app:app --reload

# 1. 未登录 → 401
curl -i http://localhost:8000/me/stage | head -1
# 期望 HTTP/1.1 401

# 2. 登录后拿到 stage
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/me/stage
# 期望 {"stage": "exploring"} 或其它 3 个值

# 3. graph 节点返回 contextual_narrative
curl http://localhost:8000/graph/nodes | python -c "
import json, sys
data = json.load(sys.stdin)
has_cn = [n for n in data if n.get('contextual_narrative')]
print(f'{len(has_cn)}/{len(data)} 节点带 contextual_narrative')
assert len(has_cn) == 15, '应有 15 个节点有叙事'
print('OK')
"
```

### 前端（手动 walkthrough）

1. **新用户首次登录**（未上传 profile 或未设 target）
   - 首页主 CTA 显示"不知道选什么？→ 去对比探索"
   - 点击跳转到 `/explore`
2. **`/explore` 默认空态**
   - 显示"在上方选择两个岗位开始对比"
3. **选左侧岗位**
   - 下拉菜单显示 15 个可选岗位（如 Java 工程师 / AI 工程师 / 前端工程师 ...）
   - 菜单底部有"叙事建设中"灰色区域列出剩余 30 个节点
   - 选中后左侧按钮显示岗位名，URL 变成 `/explore?left=<node_id>`
4. **选右侧岗位后**
   - 6 行对比内容渲染出来，每行左右两列并排
   - 底部出现两个"选它作为我的目标"按钮
5. **点击"选 AI 工程师作为我的目标"**
   - 后端 profile 的 target_node_id 被更新为 ai-engineer
   - 跳转到 `/profile`
   - 回到首页，主 CTA 已变成现有的"生成报告"（因为 stage 已是 focusing）
6. **/graph 页面**
   - 点开 AI 工程师卡片，看到"跟别的方向对比看看 →"链接
   - 点击跳转 `/explore?left=ai-engineer`
   - 其它没叙事的岗位卡片不显示这个链接
7. **/roles/ai-engineer 页面**
   - 页面底部出现"对比相似方向 →"按钮

### 样式核查

- [ ] 对比卡里没有**任何**分数、百分比、进度条、雷达图
- [ ] 使用现有冷色玻璃美学（slate-900 text / slate-200 border / white bg），没有暖色纸质风
- [ ] 两个"选它"按钮视觉平级，不暗示哪个更好
- [ ] 叙事内容用 `leading-relaxed` 的正文段落样式，不是 bullet / 卡片堆叠

---

## 常见坑 & 提示

1. **`GrowthEntry` 模型名校准**：spec 里用的名字可能不精确，先 grep 现有代码再写。如果现有架构用 `tags` 做面试标记而没有专门的 `kind` 字段，用 `tags.contains("面试")` 之类替代。
2. **URL sync 的重复渲染**：`setSearchParams` 会触发 React Query 重查，这不是问题（graph-map 有 staleTime 缓存），但如果遇到闪烁可以把 URL 更新包进 `useTransition`。
3. **灰态岗位不可点**：`JobPickerButton` 里的 `allNodes.filter(...).map(...)` 那段必须用 `<div>` 不是 `<button>`，避免用户点上去。
4. **`/profile` PATCH 请求**：如果现有 profile API 的 target 字段不叫 `target_node_id`，改成实际字段名。先跑 `grep -rn "target_node_id" backend/routers/profiles.py`。
5. **对比卡溢出**：长叙事（如 common_entry_path ~160 字）在窄屏可能超出列宽。测 375px 宽度下的渲染。
6. **页面无数据兜底**：如果 `graphData?.nodes` 为空数组（极端情况），JobPickerButton 的菜单会全灰色。加个"暂无可对比岗位，请稍后重试"兜底文案。

---

## 完成后的交付物

```
新增：
  backend/services/career_stage.py
  frontend/src/pages/ExplorePage.tsx
  frontend/src/components/explore/JobPickerButton.tsx
  frontend/src/components/explore/ComparisonRow.tsx
  frontend/src/hooks/useCareerStage.ts

修改：
  backend/routers/user.py (或对应的路由文件 — 新增 /me/stage)
  backend/routers/graph.py (透出 contextual_narrative)
  frontend/src/App.tsx (新增 /explore 路由)
  frontend/src/api/user.ts (或 report.ts — 新增 fetchCareerStage)
  frontend/src/types/graph.ts (GraphNode 加 contextual_narrative 字段)
  frontend/src/pages/HomePage.tsx (按阶段切 CTA)
  frontend/src/pages/RoleDetailPage.tsx (底部加对比入口)
  frontend/src/components/explorer/Coverflow.tsx (卡片加对比链接)

数据库：无 schema 变更，不用 migration
```

## 工期估算（熟手前端 + 熟手后端并行）

| 阶段 | 谁 | 工时 |
|---|---|---|
| 后端 career_stage 服务 + /me/stage | 后端 | 0.5 人日 |
| 后端 graph.py 透出字段 | 后端 | 1 小时 |
| 前端类型 + hook + API 层 | 前端 | 0.5 人日 |
| 前端 ExplorePage 主页 + 3 个组件 | 前端 | 1 人日 |
| 前端入口编织（HomePage/Coverflow/RoleDetail） | 前端 | 0.5 人日 |
| 联调 + UI 微调 | 一起 | 0.5 人日 |
| **总计** | | **~3 人日** |

代码量其实不大（后端 ~50 行新代码，前端 ~350 行新代码），大部分时间在联调和 UI 细节打磨。

## 最后一条提示

**联调时第一个要测的场景**：用一个全新账号（没上传 profile）登录 → 看首页是否变 CTA → 点进 /explore → 选两个岗位看对比是否渲染正确 → 选一个目标 → 看 target 是否真的保存到 profile → 回首页看 CTA 是否自动切回"生成报告"。

这条完整的 happy path 走通了，说明阶段判定 + 数据透出 + 对比页 + 目标设置 四个环节全联通了。
