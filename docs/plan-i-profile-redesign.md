# Plan I — 画像页重构规格文档

> 执行方：Gemini  
> 文件：`frontend/src/pages/ProfilePage.tsx`  
> 参考 demo：`demo-profile-redesign.html`（项目根目录，双击浏览器查看）

---

## 一、背景与目标

当前画像页存在以下问题：
1. Bento grid 强制等高，左右列内容量悬殊导致大片空白
2. 职业方向空状态占用整块区域，价值密度极低
3. Header 一行信息过载（头像+步骤+KPI+3个按钮）
4. `quality.dimensions[]`、`salary_p50`、`safety_gain`、`total_hours` 等有效数据从未展示
5. SjtCtaCard 放在右侧栏，交互异常突兀且高度不稳定

重构目标：信息层级清晰、内容自然流动、关键数据全面展示。

---

## 二、数据结构（勿猜，严格按此读取）

```typescript
// profile.career_goals: CareerGoal[]
interface CareerGoal {
  id: number
  target_node_id: string
  target_label: string          // 岗位名称
  target_zone: string           // 'safe' | 'transition' | 'danger' | 'leverage'
  from_node_id: string
  from_node_label: string       // 当前岗位（简历识别）
  gap_skills: string[]          // 差距技能列表（冻结快照）
  total_hours: number           // 预计学习时长
  safety_gain: number           // 安全系数（0~1 float）
  salary_p50: number            // 薪资涨幅（元/月）
  is_primary: boolean           // 是否主目标
  is_active: boolean
}

// profile.quality.dimensions: CompetencyDimension[]
interface CompetencyDimension {
  key?: string
  label?: string
  name?: string
  score: number                 // 0~100
}

// 软技能检测：
const hasSjtData = softSkills?._version === 2 &&
  ['communication','learning','collaboration'].some(k => softSkills?.[k] != null)
```

**系统匹配数据来源**：调用 `GET /graph/escape-routes?node_id={from_node_id}`，返回：
```typescript
interface EscapeRoute {
  target_node_id: string
  target_label: string
  target_zone: string
  gap_skills: string[]
  estimated_hours: number
  safety_gain: number
  salary_p50: number
  tag: string
}
```
> `from_node_id` 取自 `profile.graph_position.from_node_id` 或 `careerGoals[0].from_node_id`

---

## 三、页面布局结构

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER BAR（全宽 glass 条）                                  │
├─────────────────────────────────────┬────────────────────────┤
│  LEFT COLUMN（flex-col，自然高度）   │  RIGHT COLUMN（300px） │
│  · 主目标卡（有目标时）              │  · 专业技能             │
│  · 系统匹配（section）               │  · 知识领域             │
│  · 能力维度图（section）             │  · 背景+项目            │
│                                     │  · AI 诊断结论          │
│  无目标时：左列整体替换为系统匹配选择 │                        │
└─────────────────────────────────────┴────────────────────────┘
```

**布局 CSS**：
- 外层 `grid grid-cols-[1fr_300px] gap-3 items-start`（**items-start，不用 items-stretch**）
- 左列 `flex flex-col gap-3`，内容驱动高度，不强制撑满
- 页面整体 `flex flex-col gap-3 pb-8`

---

## 四、Header Bar

```
[头像] [姓名 + 来源·日期] | [进行中 badge] [第N步 — 步骤描述 →] | [竞争力 | 完整度 | 技能项] | [上传简历] [编辑] [重置]
```

- 步骤文字可点击，点击后跳转对应动作：
  - 步骤 0-3 → `setEditingId(profile.id)`（打开编辑表单）
  - 步骤 4（软技能评估）→ `document.getElementById('sjt-section')?.scrollIntoView()`（已有逻辑，保留）
  - 全部完成 → `navigate('/applications')`

---

## 五、左列 — 有主目标状态

### 5.1 主目标卡

```
┌──────────────────────────────────────────────────┐
│  主目标                                           │
│  高级后端工程师  [过渡区]                          │
│                                                  │
│  [差距 8 项]  [预计 320h]  [薪资↑¥28k]  [安全82%]│
│                                                  │
│  需要补充的技能                                   │
│  [系统设计] [Kubernetes] [gRPC] [+5项]            │
│                                                  │
│  [移除目标]                  [查看完整学习路径 →] │
└──────────────────────────────────────────────────┘
```

数据映射：
| 显示内容 | 字段 |
|---|---|
| 岗位名称 | `primaryGoal.target_label` |
| 区域 badge | `primaryGoal.target_zone` |
| 差距 N 项 | `primaryGoal.gap_skills.length` |
| 预计 Xh | `primaryGoal.total_hours` |
| 薪资↑¥Y | `primaryGoal.salary_p50`（元/月，格式化为 ¥X,XXX 或 ¥Xk） |
| 安全系数 | `primaryGoal.safety_gain * 100`（%） |
| gap skills chips | `primaryGoal.gap_skills.slice(0, 4)`，超出显示 `+N 项` |
| 查看路径 | `navigate('/graph?node=' + encodeURIComponent(primaryGoal.target_node_id))` |

### 5.2 系统匹配（Section）

**Section label**：`系统匹配`

**数据来源**：调用 `/graph/escape-routes?node_id={from_node_id}`，**过滤掉已设为主目标的节点**，取前 3 条。

**每张匹配卡**（3列 grid）：

```
┌────────────────────┐
│ 全栈工程师  [安全区] │
│ 差距 5项 · 180h    │
│ 薪资 ↑ ¥15,000     │
│ [React] [TS] [+3]  │
│ [设为主目标]        │
└────────────────────┘
```

「设为主目标」按钮调用已有的 `POST /graph/career-goals` 接口（`set_as_primary: true`），成功后刷新 `loadProfile()`。

### 5.3 能力维度（Section）

**Section label**：`能力评估`

**数据来源**：`profile.quality.dimensions[]`

**渲染规则**：
- 每个维度渲染一条横向进度条
- `score` 范围 0~100，直接作为进度条宽度 %
- 分数颜色规则：≥70 蓝色、≥50 绿色、<50 橙色
- 维度标签优先读 `dim.label ?? dim.name ?? dim.key`

**软技能行**（固定附加在 dimensions 末尾）：
- 条件：`!hasSjtData`（未完成 SJT 评估）
- 渲染：灰色虚线行 + 锁图标 + "完成情境评估后解锁" + 「开始评估 →」按钮
- 「开始评估 →」点击：`document.getElementById('sjt-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' })`
- 条件：`hasSjtData`（已完成）→ 从 `soft_skills` 里读 communication/learning/collaboration 分数，正常渲染为进度条

---

## 六、左列 — 无主目标状态（首次上传画像后）

**触发条件**：`careerGoals.length === 0` 或 `!hasActiveGoals`

整个左列替换为一张大卡：

```
┌──────────────────────────────────────────────────┐
│  选择你的目标方向                                  │
│  系统根据你的画像匹配了以下方向，选一个设为主目标   │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐               │
│  │ 高级后端工程 │  │ 全栈工程师  │               │
│  │ 差距8项 320h│  │ 差距5项 180h│               │
│  │ 薪资↑¥28k  │  │ 薪资↑¥15k  │               │
│  │ [设为主目标]│  │ [设为主目标]│               │
│  └─────────────┘  └─────────────┘               │
│  ┌─────────────┐  ┌─────────────┐               │
│  │ DevOps工程  │  │ 系统架构师  │               │
│  │ 差距4项 140h│  │ 差距11项 …  │               │
│  └─────────────┘  └─────────────┘               │
│                                                  │
│           [在图谱中探索更多方向 →]                │
└──────────────────────────────────────────────────┘
```

- 2×2 网格展示前 4 条 escape routes
- 数据来源同 5.2，取前 4 条
- 若 escape routes 接口加载中，显示 skeleton
- 若无 from_node_id（极端情况），展示"去图谱探索方向"引导

---

## 七、右列（固定，两种状态相同）

顺序：
1. **专业技能卡** — `skills.slice(0, 8)` + `+N` 展示，带精通/熟悉/了解 dot 图例
2. **知识领域卡** — `knowledgeAreas.slice(0, 8)` + `+N`
3. **背景卡** — 学历、院校、项目经历前 3 条
4. **AI 诊断卡** — `aiDiagText`（现有逻辑保留）+ 「查看详细报告 →」

**移除**：SjtCtaCard 和 SoftSkillsCard 不再放在右列。软技能入口已整合进左列能力维度图。

> 注意：SjtCtaCard / SoftSkillsCard 组件本身不删除，只是从右列移走。`id="sjt-section"` 的锚点可以加在能力维度图卡片上，供步骤 CTA 滚动定位使用。

---

## 八、Zone Badge 颜色规则

| zone 值 | 中文 | 颜色 |
|---|---|---|
| `safe` | 安全区 | 绿色 `bg-green-50 text-green-700 border-green-200` |
| `transition` | 过渡区 | 橙色 `bg-amber-50 text-amber-700 border-amber-200` |
| `danger` | 风险区 | 红色 `bg-red-50 text-red-700 border-red-200` |
| `leverage` | 杠杆区 | 蓝色 `bg-blue-50 text-blue-700 border-blue-200` |

---

## 九、接口调用新增

画像页需要新增一个数据请求：

```typescript
// 在 ProfilePage 内，当 profile 加载完成后触发
const fromNodeId = profile?.graph_position?.from_node_id
  ?? profile?.career_goals?.[0]?.from_node_id

// GET /graph/escape-routes?node_id={fromNodeId}
// 返回 EscapeRoute[]，存入 state: escapeRoutes
// 用于：系统匹配 section + 无目标状态左列
```

建议用 `useEffect` + `useState` 在已有 `profile` 加载后触发，参考项目内其他 hook 写法（如 `useDashboard`）。

---

## 十、不需要改动的部分

- Header 的 step 逻辑（`buildChecklist`、`handleStepAction`）保留原有实现
- `ManualProfileForm` 编辑态不变
- `ProfileEmptyState`（无画像态）不变
- 上传/重置逻辑不变
- 后端所有接口不变

---

## 十一、视觉规范

沿用全站 glass morphism 风格：
- 卡片：`background: rgba(255,255,255,0.55); backdrop-filter: blur(20px) saturate(180%); border: 1px solid rgba(255,255,255,0.70); border-radius: 18px;`
- Section 小标签：`text-[9px] font-bold uppercase tracking-[0.12em] text-slate-400`
- 主按钮：`bg-[var(--blue)] text-white rounded-xl px-4 py-2 text-[12px] font-bold`
- 参考 demo 文件 `demo-profile-redesign.html` 中的完整样式

---

*文档版本：2026-04-07*
