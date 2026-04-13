# 成长档案页重构 — 前端实现规范

> 本文档为完整的前端重构指令，执行者可直接按此文档编码实现。

## 1. 背景与目标

**当前问题**：成长档案页使用 4 个 tab（概览/项目/面试/学习），概览页信息稀疏，tab 之间跳来跳去割裂。

**目标**：取消 tab，改为 Notion 数据库模板风格的**单页统一时间线**。所有记录类型在一个列表里，用筛选 chip 区分。

**产品定位**：这是一个"回顾型"页面——学生打开后看"我最近都做了些啥"。AI 建议由右侧常驻的成长教练 panel 负责，此页面只展示事实。

---

## 2. 页面结构

```
┌────────────────────────────────────────────────────┐
│  GoalBar                                           │
│  当前方向: [目标名称]  ·  已坚持 XX 天              │
│  (无目标时: 引导链接 → /graph)                      │
├────────────────────────────────────────────────────┤
│  [+ 新记录]          [全部] [项目] [实战] [学习]    │
├────────────────────────────────────────────────────┤
│  今天                                              │
│  ┌──────────────────────────────────────────────┐  │
│  │ 🟠 项目  muduo网络库  进行中        3小时前   │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ 🟢 学习  Redis持久化机制            5小时前   │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  本周                                              │
│  ┌──────────────────────────────────────────────┐  │
│  │ 🔵 实战  字节跳动 前端开发  已面试    3天前   │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ 🟠 项目  个人博客  已完成            5天前    │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  更早                                              │
│  ...                                               │
└────────────────────────────────────────────────────┘
```

---

## 3. 技术栈与约束

| 项目 | 值 |
|------|------|
| 框架 | React 18 + TypeScript |
| 样式 | Tailwind CSS v4（`@utility` 语法） |
| 构建 | Vite |
| 状态 | React Query (`@tanstack/react-query`) |
| 动画 | Framer Motion |
| 图标 | Lucide React |
| 路由 | React Router v6 |

### 样式规范（重要）

- **必须使用 `glass-static` 工具类**作为容器样式，不要用 shadcn 的 `Card` 组件（它的默认样式和玻璃主题冲突）
- `glass-static` = 毛玻璃卡片（`rgba(255,255,255,0.30)` + `backdrop-blur(32px)` + `border-radius: 20px`）
- `glass` = 带 hover 上浮效果的毛玻璃卡片（适合可点击项）
- `g-inner` = 玻璃卡片内部内容的 z-index 提升（`position: relative; z-index: 1`）
- 背景色：`#E8ECF1`，有多个 radial-gradient 光晕
- 字体：`Plus Jakarta Sans` + `Noto Sans SC`
- 主色：`#2563EB`（蓝），文字：`#0f172a` / `#334155` / `#64748b`
- 不要使用 emoji 作为图标，全部用 Lucide 的 SVG 图标
- 所有可点击元素加 `cursor-pointer`

### 已有组件（不要重写）

以下组件已经完成且质量良好，**直接复用**：

| 组件 | 路径 | 用途 |
|------|------|------|
| ProjectsSection | `src/components/growth-log/ProjectsSection.tsx` | 项目卡片网格 + 创建表单 + 详情 Modal + 进展日志 |
| PursuitsSection | `src/components/growth-log/PursuitsSection.tsx` | 实战经历卡片网格 + 管道进度条 + 详情 Modal |
| PursuitDetailModal | `src/components/growth-log/PursuitDetailModal.tsx` | 实战经历详情弹窗 |

---

## 4. 数据源与 API

### 4.1 已有 API（直接使用）

所有 API 通过 `rawFetch` 调用，基础路径 `/api`。

```typescript
// src/api/growthLog.ts
listProjects()          // GET /api/growth-log/projects → { projects: ProjectRecord[] }
listInterviews()        // GET /api/growth-log/interviews → { interviews: InterviewRecord[] }
getGrowthDashboard()    // GET /api/growth-log/dashboard → GrowthDashboardData

// src/api/applications.ts
listApplications()      // GET /api/applications → JobApplication[]
```

### 4.2 新建 API：学习记录

后端已实现，前端 API 函数已写好（在 `src/api/growthLog.ts` 底部）：

```typescript
// src/api/growthLog.ts — 已实现
export interface LearningNote {
  id: number
  title: string           // "Redis 持久化机制"
  summary: string         // "搞清楚了 RDB 和 AOF 的区别..."
  tags: string[]          // ["Redis", "数据库"]
  linked_skill: string | null  // 关联目标岗位技能树
  created_at: string
}

listLearningNotes()                    // GET /api/growth-log/learning-notes
createLearningNote(data)               // POST /api/growth-log/learning-notes
updateLearningNote(id, data)           // PATCH /api/growth-log/learning-notes/:id
deleteLearningNote(id)                 // DELETE /api/growth-log/learning-notes/:id
```

直接使用即可，无需 mock。

### 4.3 统一列表的数据合并

三种数据源需要在前端合并为统一时间线：

```typescript
type RecordType = 'project' | 'pursuit' | 'learning'

interface UnifiedRecord {
  id: string              // 加前缀防冲突: "proj-1", "app-3", "learn-5"
  type: RecordType
  title: string           // 项目名 / 公司+岗位 / 学习标题
  subtitle: string        // 描述 / 状态 / 摘要
  status?: string         // 项目状态 / 投递状态
  tags?: string[]         // 技能标签
  date: string            // ISO 时间，用于排序
  raw: ProjectRecord | JobApplication | LearningNote  // 原始数据
}
```

合并逻辑：

```typescript
function mergeRecords(
  projects: ProjectRecord[],
  applications: JobApplication[],
  learningNotes: LearningNote[]
): UnifiedRecord[] {
  const records: UnifiedRecord[] = [
    ...projects.map(p => ({
      id: `proj-${p.id}`,
      type: 'project' as const,
      title: p.name,
      subtitle: p.description || '',
      status: p.status,
      tags: p.skills_used,
      date: p.created_at,
      raw: p,
    })),
    ...applications.map(a => ({
      id: `app-${a.id}`,
      type: 'pursuit' as const,
      title: `${a.company || '未知公司'} · ${a.position || a.jd_title || '未命名岗位'}`,
      subtitle: '',
      status: a.status,
      tags: [],
      date: a.created_at,
      raw: a,
    })),
    ...learningNotes.map(l => ({
      id: `learn-${l.id}`,
      type: 'learning' as const,
      title: l.title,
      subtitle: l.summary,
      tags: l.tags,
      date: l.created_at,
      raw: l,
    })),
  ]
  // 按时间倒序
  return records.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
}
```

---

## 5. 组件设计

### 5.1 文件结构

```
src/pages/GrowthLogPage.tsx          ← 完全重写（主页面）
src/components/growth-log/
  ├── GoalBar.tsx                    ← 新建（从旧页面提取）
  ├── RecordRow.tsx                  ← 新建（统一列表行组件）
  ├── FilterChips.tsx                ← 新建（筛选 chip 组）
  ├── NewRecordDialog.tsx            ← 新建（+ 新记录弹窗）
  ├── LearningNoteForm.tsx           ← 新建（学习记录创建表单）
  ├── ProjectsSection.tsx            ← 保留不动
  ├── PursuitsSection.tsx            ← 保留不动
  └── PursuitDetailModal.tsx         ← 保留不动
```

### 5.2 GrowthLogPage.tsx（主页面）

```tsx
export default function GrowthLogPage() {
  // 状态
  const [filter, setFilter] = useState<'all' | 'project' | 'pursuit' | 'learning'>('all')
  const [showNewDialog, setShowNewDialog] = useState(false)

  // 数据
  const { data: projectsData } = useQuery({ queryKey: ['growth-projects'], queryFn: listProjects })
  const { data: appsData } = useQuery({ queryKey: ['pursuits-apps'], queryFn: listApplications })
  // const { data: notesData } = useQuery({ queryKey: ['learning-notes'], queryFn: listLearningNotes })

  const projects = projectsData?.projects ?? []
  const applications = appsData ?? []
  const learningNotes: LearningNote[] = [] // TODO: 后端就绪后替换

  // 合并 + 筛选
  const allRecords = mergeRecords(projects, applications, learningNotes)
  const filtered = filter === 'all' ? allRecords : allRecords.filter(r => r.type === filter)

  // 按日期分组
  const groups = groupByDate(filtered)

  return (
    <div className="max-w-[900px] mx-auto px-4 py-5 md:px-8">
      <GoalBar />

      {/* 操作栏 */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={() => setShowNewDialog(true)} className="...">
          <Plus /> 新记录
        </button>
        <FilterChips value={filter} onChange={setFilter} />
      </div>

      {/* 统一时间线 */}
      {groups.length === 0 ? (
        <EmptyState />
      ) : (
        groups.map(group => (
          <div key={group.label}>
            <p className="text-[11px] font-bold text-slate-400 uppercase mb-2 mt-5">
              {group.label}
            </p>
            <div className="space-y-2">
              {group.items.map(record => (
                <RecordRow key={record.id} record={record} />
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
```

### 5.3 GoalBar.tsx

从旧 `GrowthLogPage.tsx` 中提取 `GoalBar` 函数，独立为组件。逻辑不变：

- 有目标：显示目标名称 + 天数 + 左侧蓝色竖线
- 无目标：引导链接到 `/graph`
- 使用 `useQuery` 调用 `getGrowthDashboard`
- 样式：`glass-static rounded-2xl p-4 mb-4`

### 5.4 FilterChips.tsx

```tsx
const FILTERS = [
  { key: 'all',      label: '全部' },
  { key: 'project',  label: '项目',  icon: FolderGit2 },
  { key: 'pursuit',  label: '实战',  icon: Briefcase },
  { key: 'learning', label: '学习',  icon: BookOpen },
]

function FilterChips({ value, onChange }) {
  return (
    <div className="flex gap-1">
      {FILTERS.map(f => (
        <button
          key={f.key}
          onClick={() => onChange(f.key)}
          className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-all cursor-pointer ${
            value === f.key
              ? 'bg-slate-800 text-white shadow-sm'
              : 'text-slate-500 hover:text-slate-800 hover:bg-white/50'
          }`}
        >
          {f.icon && <f.icon className="w-3 h-3 inline mr-1" />}
          {f.label}
        </button>
      ))}
    </div>
  )
}
```

### 5.5 RecordRow.tsx（核心组件）

每条记录在列表中的展示行。**使用 `glass` 类**（带 hover 上浮），点击触发详情。

```tsx
const TYPE_CONFIG = {
  project:  { label: '项目', color: '#EA580C', icon: FolderGit2 },
  pursuit:  { label: '实战', color: '#2563EB', icon: Briefcase },
  learning: { label: '学习', color: '#16A34A', icon: BookOpen },
}

const STATUS_TEXT: Record<string, string> = {
  // 项目状态
  planning: '计划中', in_progress: '进行中', completed: '已完成',
  // 投递状态
  pending: '待投递', applied: '已投递', screening: '筛选中',
  scheduled: '已约面', interviewed: '已面试', debriefed: '已复盘',
  offer: 'Offer', rejected: '未通过', withdrawn: '已放弃',
}

function RecordRow({ record }: { record: UnifiedRecord }) {
  const cfg = TYPE_CONFIG[record.type]
  const [detailOpen, setDetailOpen] = useState(false)

  return (
    <>
      <div
        onClick={() => setDetailOpen(true)}
        className="glass px-4 py-3 flex items-center gap-3 cursor-pointer"
      >
        {/* 类型图标 */}
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: `${cfg.color}15` }}
        >
          <cfg.icon className="w-4 h-4" style={{ color: cfg.color }} />
        </div>

        {/* 内容 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="text-[10px] font-bold shrink-0"
              style={{ color: cfg.color }}
            >
              {cfg.label}
            </span>
            <p className="text-[13px] font-semibold text-slate-800 truncate">
              {record.title}
            </p>
          </div>
          {record.subtitle && (
            <p className="text-[11px] text-slate-500 truncate mt-0.5">
              {record.subtitle}
            </p>
          )}
        </div>

        {/* 右侧：状态 + 时间 */}
        <div className="flex items-center gap-2 shrink-0">
          {record.status && (
            <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-slate-100/80 text-slate-600">
              {STATUS_TEXT[record.status] || record.status}
            </span>
          )}
          <span className="text-[11px] text-slate-400 tabular-nums w-12 text-right">
            {fmtRelative(record.date)}
          </span>
        </div>
      </div>

      {/* 详情弹窗/跳转 */}
      {detailOpen && record.type === 'project' && (
        // 打开项目详情 Modal（复用 ProjectsSection 中的 Modal）
        // 或者导航到项目详情页
      )}
      {detailOpen && record.type === 'pursuit' && (
        <PursuitDetailModal
          appId={(record.raw as JobApplication).id}
          onClose={() => setDetailOpen(false)}
          onRefresh={() => {/* invalidate queries */}}
        />
      )}
      {/* 学习记录的详情处理 */}
    </>
  )
}
```

### 5.6 日期分组工具函数

```typescript
interface DateGroup {
  label: string    // "今天" / "昨天" / "本周" / "更早"
  items: UnifiedRecord[]
}

function groupByDate(records: UnifiedRecord[]): DateGroup[] {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterdayStart = new Date(todayStart.getTime() - 86400000)
  const weekStart = new Date(todayStart.getTime() - todayStart.getDay() * 86400000)

  const groups: Record<string, UnifiedRecord[]> = {
    '今天': [], '昨天': [], '本周': [], '更早': [],
  }

  records.forEach(r => {
    const d = new Date(r.date)
    if (d >= todayStart) groups['今天'].push(r)
    else if (d >= yesterdayStart) groups['昨天'].push(r)
    else if (d >= weekStart) groups['本周'].push(r)
    else groups['更早'].push(r)
  })

  return Object.entries(groups)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }))
}
```

### 5.7 NewRecordDialog.tsx（新记录弹窗）

点击 `+ 新记录` 后弹出，让用户选择创建哪种类型：

```tsx
function NewRecordDialog({ open, onClose }) {
  const navigate = useNavigate()

  const options = [
    {
      type: 'project',
      icon: FolderGit2,
      color: '#EA580C',
      title: '记录项目',
      desc: '记录一个正在做或已完成的项目',
      // 点击后关闭弹窗，设置 URL 参数触发 ProjectsSection 的创建表单
      // 或者直接导航到 /growth-log?create=project
    },
    {
      type: 'pursuit',
      icon: Briefcase,
      color: '#2563EB',
      title: '追踪岗位',
      desc: '记录投递的公司和岗位进展',
    },
    {
      type: 'learning',
      icon: BookOpen,
      color: '#16A34A',
      title: '学习记录',
      desc: '记录今天学了什么、心得总结',
    },
  ]

  // 使用 AnimatePresence + motion.div 做弹窗动画
  // 样式：glass-static 背景的居中弹窗
  // 三个选项是可点击的行/卡片
}
```

### 5.8 EmptyState

当列表完全为空时（新用户）：

```tsx
function EmptyState() {
  return (
    <div className="glass-static rounded-2xl py-16 text-center">
      <FolderKanban className="w-10 h-10 text-slate-300 mx-auto mb-4" />
      <p className="text-[15px] font-semibold text-slate-700 mb-1.5">
        还没有任何记录
      </p>
      <p className="text-[12px] text-slate-500 mb-5 max-w-[280px] mx-auto">
        记录你的项目、投递和学习，在这里看到完整的成长轨迹
      </p>
      <div className="flex justify-center gap-3">
        <a href="/graph" className="px-4 py-2 rounded-xl bg-slate-800 text-white text-[12px] font-semibold hover:bg-slate-700 cursor-pointer transition-colors">
          选方向
        </a>
        <button className="px-4 py-2 rounded-xl bg-white/60 text-slate-700 text-[12px] font-semibold border border-slate-200 hover:bg-white/80 cursor-pointer transition-colors">
          + 新记录
        </button>
      </div>
    </div>
  )
}
```

---

## 6. 路由变更

### App.tsx 修改

```tsx
// 删除
import GrowthLogDemo from '@/pages/GrowthLogDemo'
// 删除
<Route path="/demo" element={<GrowthLogDemo />} />

// 以下重定向保留，但去掉 tab 参数（不再有 tab）
<Route path="/jd" element={<Navigate to="/growth-log" replace />} />
<Route path="/applications" element={<Navigate to="/growth-log" replace />} />
```

---

## 7. 需要删除的文件

| 文件 | 原因 |
|------|------|
| `src/pages/GrowthLogDemo.tsx` | Demo 页面，不再需要 |
| `src/components/growth-log/GrowthBento.tsx` | 旧 bento 布局实验，已废弃 |
| `src/components/growth-log/EventTimeline.tsx` | 旧时间线组件，已废弃 |

---

## 8. 点击行为

| 记录类型 | 点击行为 |
|----------|----------|
| 项目 | 打开项目详情 Modal（复用 `ProjectsSection` 中已有的详情 Modal） |
| 实战经历 | 打开 `PursuitDetailModal`（直接传 `appId`） |
| 学习记录 | 展开行内详情（显示 summary 全文 + tags），或打开简单 Modal |

---

## 9. 交互细节

### 筛选 chip
- 默认选中"全部"
- 切换时列表平滑过渡（`AnimatePresence` + `motion.div layout`）
- 筛选状态同步到 URL query：`?filter=project`

### 新记录按钮
- 位置：GoalBar 下方，筛选 chip 左侧
- 点击弹出类型选择弹窗
- 选择后根据类型：
  - 项目 → 弹出项目创建表单（复用 ProjectsSection 的 AddProjectForm）
  - 实战 → 弹出实战创建表单（复用 PursuitsSection 的 AddPursuitForm）
  - 学习 → 弹出学习记录创建表单（新建）

### 列表行 hover
- 使用 `glass` 工具类自带的 hover 上浮效果
- 右侧显示时间
- 移动端：无 hover 效果，直接 tap

### 日期分组
- 分组标题：小字灰色，`text-[11px] font-bold text-slate-400 uppercase`
- 组与组之间 `mt-5` 间距

---

## 10. 空状态策略

| 场景 | 显示 |
|------|------|
| 完全空（新用户） | 大空状态卡片 + "选方向"/"新记录"按钮 |
| 有记录但当前筛选为空 | "没有{类型}记录" + 创建按钮 |
| 学习记录后端未就绪 | 学习筛选 chip 正常显示，列表为空时显示"即将上线" |

---

## 11. 关键类型定义参考

```typescript
// src/api/growthLog.ts — ProjectRecord
interface ProjectRecord {
  id: number
  name: string
  description: string | null
  skills_used: string[]
  gap_skill_links: string[]
  github_url: string | null
  status: 'planning' | 'in_progress' | 'completed'
  linked_node_id: string | null
  reflection: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

// src/types/application.ts — JobApplication
interface JobApplication {
  id: number
  jd_diagnosis_id: number | null
  jd_title: string | null
  company: string | null
  position: string | null
  job_url: string | null
  status: ApplicationStatus  // 'pending'|'applied'|'screening'|...|'offer'|'rejected'|'withdrawn'
  applied_at: string | null
  interview_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
  debrief: ApplicationDebrief | null
  jd_diagnosis: JdDiagnosisSummary | null
  mock_sessions: MockSessionSummary[]
}
```

---

## 12. 后端状态（已完成）

以下后端变更已全部完成：

1. **`LearningNote` 表** — `learning_notes`（id, user_id, profile_id, title, summary, tags, linked_skill, created_at）— 已创建
2. **CRUD 路由** — GET / POST / PATCH / DELETE `/api/growth-log/learning-notes` — 已实现
3. **`GrowthEvent` 整个系统已删除** — 8 个文件清理完毕，零残留
4. **前端 API 函数** — `listLearningNotes`, `createLearningNote`, `updateLearningNote`, `deleteLearningNote` — 已写入 `src/api/growthLog.ts`

---

## 13. 验收标准

- [ ] 页面无 tab，是单页统一时间线
- [ ] GoalBar 正常显示（有/无目标两种状态）
- [ ] 筛选 chip 切换正常工作
- [ ] 项目记录从 `listProjects` 拉取并显示在列表中
- [ ] 实战经历从 `listApplications` 拉取并显示在列表中
- [ ] 点击项目行打开项目详情
- [ ] 点击实战行打开 `PursuitDetailModal`
- [ ] `+ 新记录` 弹窗能选择类型并跳转到对应创建流程
- [ ] 列表按日期分组（今天/昨天/本周/更早）
- [ ] 空状态正确显示
- [ ] 所有可点击元素有 `cursor-pointer`
- [ ] 样式使用 `glass` / `glass-static`，不使用 shadcn Card
- [ ] 页面在 375px / 768px / 1440px 宽度下响应式正常
- [ ] 无 TypeScript 编译错误
- [ ] 无 emoji 图标（全部用 Lucide SVG）
