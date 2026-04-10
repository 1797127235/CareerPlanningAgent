# Gemini 前端任务：画像页匹配方向重构

## 背景

画像页 (ProfilePage.tsx) 的"匹配方向"区域需要重构。当前实现有以下问题：
- 之前是自动加载，现在改为点击按钮触发
- 之前展示一堆红色英文模块名，打击用户信心
- 需要改为：摘要卡片 + 点击跳转独立详情页

## 后端接口

### 1. 触发匹配分析
```
POST /api/recommendations/match-analysis
Authorization: Bearer <token>

Response:
{
  "results": [
    {
      "role_id": "rust",
      "label": "Rust 工程师",
      "channel": "entry" | "growth" | "explore",
      "zone": "safe" | "leverage" | "transition" | "danger",
      "coverage_pct": 33,          // 0-100, 已掌握比例
      "mastered_count": 5,
      "gap_count": 10,
      "total_modules": 15,
      "top_mastered": ["模块A", "模块B"],   // 最多3个
      "top_gaps": [
        {"module": "模块X", "reason": "为什么需要学", "priority": "high"}
      ],                                      // 最多3个
      "reason": "推荐理由一句话"
    }
  ]
}
```

### 2. 获取详情（详情页用）
```
GET /api/recommendations/match-analysis/{roleId}
Authorization: Bearer <token>

Response:
{
  "role_id": "rust",
  "mastered": [
    {"module": "模块名", "reason": "为什么算掌握"}
  ],
  "gaps": [
    {"module": "模块名", "reason": "为什么需要学", "priority": "high|medium|low"}
  ],
  "mastered_count": 5,
  "gap_count": 10,
  "coverage_pct": 33
}
```

## 前端需求

### Part 1: 画像页匹配方向区域 (ProfilePage.tsx)

**当前位置**：ProfilePage.tsx 第 476-583 行左右，`{/* 6. 匹配方向 */}` 区域

**三个状态**：

#### 状态 1：未开始（默认）
- 显示引导文案 + "开始匹配分析" 按钮
- 文案：基于你的技能画像，AI 为你匹配最适合的发展方向

#### 状态 2：加载中
- 点击按钮后调用 `POST /api/recommendations/match-analysis`
- 显示 loading 状态："AI 正在分析你的职业匹配方向..."
- 注意：这个接口会调 LLM，需要 20-60 秒，loading 要明确告知用户

#### 状态 3：结果展示
- 渐进式展示摘要卡片（results 数组）
- 每张卡片展示：
  - 角色名 + 匹配度（coverage_pct%）
  - channel 标签（🎯起步岗位 / 📈成长目标 / 🧭探索方向）
  - zone 标签（安全区/杠杆区/过渡区/危险区）
  - 已掌握 N 个模块（正面，绿色）
  - 建议学习的 top 3 模块（中性，amber/蓝色，正面语气）
  - 推荐理由（reason）
- 点击卡片 → 跳转到 `/profile/match/{roleId}` 详情页
- 底部有"重新分析"链接

**设计规范**：
- 卡片用 `bg-white/50 rounded-xl border border-white/70` 风格，和页面其他卡片一致
- 匹配度用蓝色粗体
- 已掌握用 emerald/green 色系
- 建议学习用 amber 色系（不是红色！）
- 不要出现任何负面措辞（不说"缺失"、"不足"，说"建议补充"、"学习...可以帮你..."）

### Part 2: 匹配详情页（新页面）

**路由**：`/profile/match/:roleId`

**数据获取**：`GET /api/recommendations/match-analysis/{roleId}`

**页面结构**：

```
┌─────────────────────────────────────┐
│ ← 返回画像                           │
│                                     │
│ Rust 工程师              匹配度 33%  │
│ 🎯 起步岗位 · 杠杆区                 │
│                                     │
│ ── 已掌握的模块 (5/15) ────────────  │
│                                     │
│ ✓ 模块A                             │
│   你的 xx 项目经验证明了相关能力       │
│ ✓ 模块B                             │
│   技能列表中包含相关技术              │
│ ...                                 │
│                                     │
│ ── 建议学习 (10个模块) ────────────  │
│                                     │
│ 🔴 高优先级                          │
│ • 模块X — 学习理由                   │
│ • 模块Y — 学习理由                   │
│                                     │
│ 🟡 建议补充                          │
│ • 模块Z — 学习理由                   │
│                                     │
│ 🟢 锦上添花                          │
│ • 模块W — 学习理由                   │
│                                     │
│ [去图谱查看该岗位]  [查看学习资源]     │
└─────────────────────────────────────┘
```

**设计细节**：
- 已掌握模块：绿色背景卡片，带 ✓ 图标，展示 reason
- 高优先级 gap：amber 背景，带圆点标记
- 建议补充：浅灰背景
- 锦上添花：更浅灰背景
- 底部两个 CTA 按钮：跳图谱 (`/graph?node={roleId}`) 和学习资源 (`/explore/{roleId}/learning`)
- 返回按钮回到画像页

### Part 3: 路由注册

在 App.tsx 中添加路由：
```tsx
<Route path="/profile/match/:roleId" element={<MatchDetailPage />} />
```

## TypeScript 类型

```typescript
// api/recommendations.ts 新增

export interface MatchAnalysisResult {
  role_id: string
  label: string
  channel: 'entry' | 'growth' | 'explore'
  zone: string
  coverage_pct: number
  mastered_count: number
  gap_count: number
  total_modules: number
  top_mastered: string[]
  top_gaps: Array<{ module: string; reason: string; priority: string }>
  reason: string
}

export interface MatchAnalysisResponse {
  results: MatchAnalysisResult[]
}

export interface MatchDetail {
  role_id: string
  mastered: Array<{ module: string; reason: string }>
  gaps: Array<{ module: string; reason: string; priority: string }>
  mastered_count: number
  gap_count: number
  coverage_pct: number
}

// API functions
export async function startMatchAnalysis(): Promise<MatchAnalysisResponse> {
  return rawFetch('/recommendations/match-analysis', { method: 'POST' })
}

export async function fetchMatchDetail(roleId: string): Promise<MatchDetail> {
  return rawFetch(`/recommendations/match-analysis/${roleId}`)
}
```

## 注意事项

1. **不要自动加载**：只在用户点击按钮时才调用接口
2. **loading 要明确**：接口调 LLM 需要 20-60 秒，loading 文案要告知用户
3. **正面语气**：所有展示都用积极正面的措辞，不打击用户信心
4. **已有代码**：ProfilePage.tsx 第 476-583 行的"匹配方向"区域需要替换，其中 `handleStartMatch`、`skillMatches`、`loadingSkillMatch` 等 state 可以复用或替换
5. **清理**：删除 `gapAnalyses`、`loadingGaps`、`fetchGapAnalysis` 相关的 import 和 state，它们已经不再需要
6. **风格一致**：和页面其他 glass 卡片保持一致，参考专业技能、知识领域等区块的样式
