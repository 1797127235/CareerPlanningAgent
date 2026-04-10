# Gemini 前端任务：Gap Analysis 模块集成

## 背景
职业规划系统的画像页（ProfilePage）有一个"匹配方向"区域，展示用户技能与各岗位的匹配度。现在后端新增了 LLM 驱动的 gap analysis API，需要替换原来的"还需学习"展示逻辑。

## 技术栈
- React 18 + TypeScript
- Tailwind CSS（设计风格：SaaS 简洁，glass morphism 卡片）
- API 请求用 `rawFetch` from `@/api/client`
- 路由：react-router-dom v6

## 需求

### 1. 画像页"匹配方向"卡片改造

**当前文件**: `frontend/src/pages/ProfilePage.tsx` (约 line 454-500, Panel 6 "匹配方向")

**当前效果**:
```
C++ 工程师  48%
已掌握: [STL] [Linux系统编程] [多线程编程]
还需学习: [auto (自动类型推导)] [参数依赖查找] +5
```

**目标效果**:
```
C++ 工程师  90%  ← 覆盖率来自 gap-analysis API
已掌握: 18/20 模块
还需学习:
  🔴 Exception Handling — 高性能场景需特殊处理   [我已掌握 ✓]
  🟡 Package Managers — 未提及包管理工具经验      [我已掌握 ✓]
```

**交互**:
- 每个 gap 模块右侧有"我已掌握"按钮
- 点击后调 confirm API，该模块移到已掌握列表，覆盖率更新
- 可展开/折叠查看已掌握模块列表及每个的判断依据

### 2. API 接口

**获取 gap 分析**:
```typescript
GET /api/recommendations/gap-analysis?role_id={roleId}

Response: {
  role_id: string
  mastered: Array<{ module: string, reason: string }>
  gaps: Array<{ module: string, reason: string, priority: "high" | "medium" | "low" }>
  mastered_count: number
  gap_count: number
  coverage_pct: number
}
```

**确认已掌握**:
```typescript
POST /api/recommendations/gap-analysis/confirm
Body: { role_id: string, module: string }
Response: { ok: boolean, module: string, role_id: string }
```

### 3. 前端 API 文件

在 `frontend/src/api/recommendations.ts` 中已有部分类型，需补充：

```typescript
// 新增类型
export interface GapModule {
  module: string
  reason: string
  priority?: 'high' | 'medium' | 'low'
}

export interface GapAnalysis {
  role_id: string
  mastered: GapModule[]
  gaps: GapModule[]
  mastered_count: number
  gap_count: number
  coverage_pct: number
}

// 新增 API 函数
export async function fetchGapAnalysis(roleId: string): Promise<GapAnalysis> {
  return rawFetch<GapAnalysis>(`/recommendations/gap-analysis?role_id=${encodeURIComponent(roleId)}`)
}

export async function confirmMastered(roleId: string, module: string): Promise<{ ok: boolean }> {
  return rawFetch('/recommendations/gap-analysis/confirm', {
    method: 'POST',
    body: JSON.stringify({ role_id: roleId, module }),
  })
}
```

### 4. 设计要求

**优先级颜色**:
- `high` → 红色系 (bg-red-50 text-red-600)
- `medium` → 琥珀色 (bg-amber-50 text-amber-600) 
- `low` → 灰色 (bg-slate-50 text-slate-500)

**Loading 状态**:
- gap analysis API 需要 5-10 秒（LLM 处理）
- 先展示 skeleton loading 占位
- 加载完毕后淡入显示

**"我已掌握"按钮**:
- 默认为半透明小按钮，hover 显现
- 点击后该 gap 项有一个消失动画，覆盖率数字动态更新
- 乐观更新（点击立即移除，不等后端返回）

**已掌握模块折叠**:
- 默认折叠，显示 "18/20 模块已掌握"
- 点击展开，列出每个模块名 + LLM 判断依据（reason）
- 依据文字用小字灰色显示

**响应式**:
- 桌面端 3 列卡片布局（同现有）
- 每张卡片内部堆叠：覆盖率 → gap 列表 → 已掌握折叠

### 5. 现有代码参考

**ProfilePage 的 skill-match 调用** (当前逻辑，需要替换为 gap-analysis):
```typescript
// 目前在 ProfilePage.tsx 约 line 138-151
useEffect(() => {
  if (!profile?.id) return
  fetchSkillMatch(3).then(r => setSkillMatches(r.matches)).catch(() => {})
}, [profile?.id])
```

替换逻辑：
1. 仍用 fetchSkillMatch(3) 获取匹配的 role 列表（role_id, label, affinity_pct）
2. 对每个匹配的 role，异步调 fetchGapAnalysis(role_id) 获取模块级 gap
3. gap 数据到达后替换显示

**API client 用法**:
```typescript
import { rawFetch } from '@/api/client'
// rawFetch 自动带 token header，返回 JSON
```

**设计参考 — 现有卡片风格**:
```tsx
<div className="glass p-6">
  <div className="g-inner">
    {/* glass + g-inner 是全站统一的磨砂卡片风格 */}
  </div>
</div>
```

### 6. 文件清单

需要修改的文件：
1. `frontend/src/api/recommendations.ts` — 补充类型和 API 函数
2. `frontend/src/pages/ProfilePage.tsx` — 改造"匹配方向"Panel 6

不需要创建新文件，改现有文件即可。
