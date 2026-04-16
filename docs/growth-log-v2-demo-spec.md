# 成长档案 v2 Demo — 前端交付

> **目标**：用 mock 数据搭一个可交互的成长档案 v2 demo，先看效果再决定是否接后端
> **范围**：仅 frontend v1（`frontend/` 目录，**不是 frontend-v2**）
> **硬约束**：不动后端、不动现有 API、所有数据用本地 mock，新老代码可并存
> **完整设计文档**：`docs/growth-log-v2-spec.md`（优先级低于本文；本文是精简执行版）

---

## §0 你要做什么

在 `frontend/src/pages/GrowthLogPage.tsx` 旁边新建一个 **demo 页面**，
完整实现 v2 的交互骨架，**全部用本地 mock 数据**，不调用任何后端 API。

做完后，用户访问 `/growth-log-v2` 可以看到新版效果，
原有 `/growth-log` 页面**保持不动**，随时可切回。

---

## §1 文件结构

```
frontend/src/pages/
├── GrowthLogPage.tsx            ← 旧版，不动
└── GrowthLogV2Page.tsx          ← 新建，demo 页面

frontend/src/components/growth-log-v2/   ← 新建目录
├── QuickInput.tsx               ← 顶部常驻输入框
├── InterviewForm.tsx            ← 面试复盘结构化表单
├── ProjectForm.tsx              ← 项目记录结构化表单
├── EntryCard.tsx                ← 统一卡片，按 category 渲染不同布局
├── PlanRow.tsx                  ← 未完成计划条目（带 checkbox）
├── TagChips.tsx                 ← 标签选择器（预设 + 自定义输入）
├── AiSuggestions.tsx            ← AI 建议展示 + 转计划按钮
└── mockData.ts                  ← 所有假数据集中在这里
```

路由在 `frontend/src/App.tsx` 里新增一条：
```tsx
<Route path="/growth-log-v2" element={<GrowthLogV2Page />} />
```

---

## §2 数据模型（前端类型）

在 `frontend/src/components/growth-log-v2/mockData.ts` 定义：

```typescript
export type Category = 'learning' | 'interview' | 'project' | null

export interface InterviewQA {
  q: string          // 面试问题
  a: string          // 我怎么答的
}

export interface InterviewData {
  company: string
  position: string
  round: string                              // 技术一面/HR面/...
  questions: InterviewQA[]                   // 问答对列表
  self_rating: 'good' | 'medium' | 'bad'
  result: 'passed' | 'failed' | 'pending'
  reflection?: string
}

export interface ProjectData {
  name: string
  description?: string
  skills_used: string[]
  github_url?: string
  status: 'planning' | 'in_progress' | 'completed'
}

export interface AiSuggestion {
  text: string
  category?: Category
}

export interface GrowthEntry {
  id: number
  content: string                            // 正文摘要
  category: Category
  tags: string[]                             // ["面试", "字节", "算法"]
  structured_data: InterviewData | ProjectData | null

  is_plan: boolean
  status: 'done' | 'pending' | 'dropped'
  due_type: 'daily' | 'weekly' | 'monthly' | 'custom' | null
  due_at: string | null                      // ISO datetime
  completed_at: string | null
  created_at: string

  ai_suggestions: AiSuggestion[] | null
}
```

---

## §3 Mock 数据

`mockData.ts` 里放至少 **10 条假数据**，覆盖所有场景：

- 3 条学习笔记（纯文本）
- 2 条面试复盘（其中 1 条已复盘带 AI 建议，1 条没点过 AI）
- 2 条项目记录（1 进行中、1 已完成）
- 2 条计划（1 pending 今天到期、1 pending 本周）
- 1 条完成的计划（showing how it moves to timeline after done）

**必须有的样例**（直接抄进 mock 里）：

```typescript
export const mockEntries: GrowthEntry[] = [
  // 学习笔记
  {
    id: 1,
    content: '今天搞懂了 TCP 三次握手的 SYN/ACK 过程，原来 Server 收到 SYN 后发的是 SYN+ACK 合并包。',
    category: 'learning',
    tags: ['学习', '网络'],
    structured_data: null,
    is_plan: false, status: 'done',
    due_type: null, due_at: null, completed_at: null,
    created_at: '2026-04-16T10:30:00Z',
    ai_suggestions: null,
  },
  // 面试复盘 — 带 AI 建议
  {
    id: 2,
    content: '字节二面，Redis 和链表答得不好',
    category: 'interview',
    tags: ['面试', '字节'],
    structured_data: {
      company: '字节跳动',
      position: '后端开发实习',
      round: '技术二面',
      questions: [
        { q: 'Redis 持久化机制', a: '只说了 RDB，忘了 AOF 和混合持久化' },
        { q: 'TCP 三次握手', a: '答上来了' },
        { q: '手撕：反转链表', a: '写出来了但时间复杂度分析卡了' },
      ],
      self_rating: 'medium',
      result: 'pending',
      reflection: '基础还行但 Redis 那块真得补',
    },
    is_plan: false, status: 'done',
    due_type: null, due_at: null, completed_at: null,
    created_at: '2026-04-15T14:00:00Z',
    ai_suggestions: [
      { text: '复习 RDB 快照 vs AOF 日志 vs 混合持久化的触发条件和优劣', category: 'learning' },
      { text: 'LeetCode 206 反转链表，限时 10 分钟手写一遍', category: 'learning' },
      { text: '整理"字节后端常考题"清单，重点看 Redis 和网络', category: 'learning' },
    ],
  },
  // 项目记录 — 进行中
  {
    id: 3,
    content: '网络库 epoll 模块写完了',
    category: 'project',
    tags: ['项目', 'C++'],
    structured_data: {
      name: '基于 epoll 的高并发网络库',
      description: '用 C++ 实现 Reactor 模式的网络框架',
      skills_used: ['C++', 'Linux', 'epoll', '多线程'],
      github_url: 'https://github.com/example/net-lib',
      status: 'in_progress',
    },
    is_plan: false, status: 'done',
    due_type: null, due_at: null, completed_at: null,
    created_at: '2026-04-14T20:15:00Z',
    ai_suggestions: null,
  },
  // 计划 — pending 本周
  {
    id: 4,
    content: '本周完成简历第二版',
    category: 'project',
    tags: ['计划', '简历'],
    structured_data: null,
    is_plan: true, status: 'pending',
    due_type: 'weekly', due_at: '2026-04-20T23:59:59Z',
    completed_at: null,
    created_at: '2026-04-14T09:00:00Z',
    ai_suggestions: null,
  },
  // 计划 — pending 今天
  {
    id: 5,
    content: '复习 RDB 和 AOF 区别',
    category: 'learning',
    tags: ['计划', '来自AI建议'],
    structured_data: null,
    is_plan: true, status: 'pending',
    due_type: 'daily', due_at: '2026-04-16T23:59:59Z',
    completed_at: null,
    created_at: '2026-04-15T14:30:00Z',
    ai_suggestions: null,
  },
  // 更多学习笔记、项目完成、已完成计划…
  // （你可以按需再加 5 条）
]
```

`mockData.ts` 还要导出**操作函数**（直接改内存数组，配合 React state 重渲染）：

```typescript
export function addEntry(entry: Omit<GrowthEntry, 'id' | 'created_at'>): GrowthEntry
export function updateEntry(id: number, patch: Partial<GrowthEntry>): void
export function deleteEntry(id: number): void
export function getMockAiSuggestions(entry: GrowthEntry): Promise<AiSuggestion[]>
  // ↑ 返回 mock 建议（带 500ms setTimeout 模拟加载）
```

---

## §4 页面布局

`GrowthLogV2Page.tsx` 整体结构：

```
┌──────────────────────────────────────────┐
│ [GoalBar — 直接复用 frontend/src/components/growth-log/GoalBar]
├──────────────────────────────────────────┤
│ [QuickInput]                             │
├──────────────────────────────────────────┤
│ [FilterChips — 可复用或新做]             │
│   全部 / #项目 / #面试 / #学习 / 计划    │
├──────────────────────────────────────────┤
│ ── 待完成的计划 ──                        │
│ [PlanRow × N]                            │
├──────────────────────────────────────────┤
│ ── 今天 / 昨天 / 本周 / 更早 ──           │
│ [EntryCard × N]                          │
└──────────────────────────────────────────┘
```

分组用 `groupByDate`（抄 `GrowthLogPage.tsx` 的 `groupByDate` 函数）。

---

## §5 组件细节

### §5.1 QuickInput

```
┌────────────────────────────────────────────┐
│ 📝 写点什么…                               │
│                                            │
│                                            │
├────────────────────────────────────────────┤
│ #项目 #面试 #学习  [+自定义]    □计划     │
│                                            │
│ [面试复盘]  [记录项目]          [发送]     │
└────────────────────────────────────────────┘
```

- 默认：一个 textarea（3 行高）+ 下方标签区 + 计划开关 + 按钮组
- 标签预设 3 个（项目/面试/学习），点击切换选中；`[+自定义]` 点开一个小 input，按回车添加自定义标签
- 勾"计划"开关后，展开一个日期选择器（today / this week / custom）
- 点 `[面试复盘]` → 弹出 `InterviewForm` 模态框
- 点 `[记录项目]` → 弹出 `ProjectForm` 模态框
- 点 `[发送]`：调 `addEntry({ content, category, tags, is_plan, due_type, due_at })`，成功后清空

### §5.2 InterviewForm（模态框）

```
┌─────────────────────────────┐
│ 面试复盘                     │
├─────────────────────────────┤
│ 公司名称: [________]        │
│ 岗位:     [________]        │
│ 轮次:     [技术一面 ▼]      │
│                             │
│ 问了什么 · 我怎么答的:       │
│ ┌─────────────────────────┐ │
│ │ Q: [_________________]  │ │
│ │ A: [_________________]  │ │
│ └─────────────────────────┘ │
│ [+ 加一题]                   │
│                             │
│ 自评:     ○好 ●一般 ○差     │
│ 结果:     ○通过 ○未通过 ●待定│
│ 复盘感受: [________]         │
│                             │
│         [保存]  [取消]       │
└─────────────────────────────┘
```

- 轮次下拉：`技术一面` / `技术二面` / `技术三面` / `HR 面` / `综合面` / `其他`
- 问答对默认 1 对，`[+ 加一题]` 追加，每对右侧有 `[×]` 删除
- 自评/结果用 radio 按钮
- 保存时：
  - `content` 自动拼：`"{公司} {轮次}"`
  - `category = 'interview'`
  - `structured_data` = 表单数据
  - `tags` = `['面试', 公司名]`
  - 调 `addEntry(...)`

### §5.3 ProjectForm（模态框）

```
┌─────────────────────────────┐
│ 记录项目                     │
├─────────────────────────────┤
│ 项目名称: [________]        │
│ 简介:     [________]        │
│ 技术栈:   [React, Node.js…] │
│ 项目链接: [________]         │
│ 状态:     ○计划中 ●进行中 ○已完成│
│                             │
│         [保存]  [取消]       │
└─────────────────────────────┘
```

- 技术栈用逗号分隔字符串，保存时 split 成数组
- 保存时：
  - `content` = 项目名称
  - `category = 'project'`
  - `structured_data` = 表单数据
  - `tags` = `['项目', ...技术栈]`

### §5.4 EntryCard — 按 category 渲染不同布局

```tsx
function EntryCard({ entry }: { entry: GrowthEntry }) {
  if (entry.category === 'interview') return <InterviewCardBody entry={entry} />
  if (entry.category === 'project') return <ProjectCardBody entry={entry} />
  return <LearningCardBody entry={entry} />  // 默认
}
```

**学习笔记卡片**（最简）：
```
┌──────────────────────────────────────┐
│ 搞懂了 TCP 三次握手的 SYN/ACK 过程   │
│ #学习 #网络         2 小时前          │
│                         [AI 建议]    │
└──────────────────────────────────────┘
```

**面试复盘卡片**（展开问答）：
```
┌──────────────────────────────────────┐
│ 字节跳动 · 技术二面    #面试 #字节    │
│                                      │
│ Q: Redis 持久化 → 只说了 RDB          │
│ Q: 反转链表 → 写出来了但复杂度卡了    │
│                                      │
│ 自评: 一般 · 结果: 待定                │
│ 感受: 基础还行但 Redis 那块真得补     │
│                                      │
│ 昨天              [AI 建议 ✓(3)]     │
├──────────────────────────────────────┤
│ AI 建议:                              │
│ 1. 复习 RDB/AOF 区别    [转为计划]   │
│ 2. LeetCode 206        [转为计划]   │
│ 3. 整理字节常考题      [转为计划]   │
└──────────────────────────────────────┘
```

**项目记录卡片**：
```
┌──────────────────────────────────────┐
│ 网络库 epoll 模块写完了    #项目 #C++ │
│                                      │
│ 📁 基于 epoll 的高并发网络库          │
│ 🏷 C++ · Linux · epoll · 多线程       │
│ 🔗 github.com/example/net-lib         │
│ ● 进行中                              │
│                                      │
│ 2 天前                  [AI 建议]    │
└──────────────────────────────────────┘
```

**所有卡片共同行为**：
- 右下角 `[AI 建议]` 按钮
  - 首次点击：调 `getMockAiSuggestions(entry)`（500ms 延迟），把结果写回 entry.ai_suggestions
  - 已有建议：按钮显示 `[AI 建议 ✓(3)]`，点击折叠/展开建议区
- 建议区里每条有 `[转为计划]` 按钮 → `addEntry({ content: s.text, is_plan: true, due_type: 'daily', ... })`

### §5.5 PlanRow（未完成计划）

```
┌──────────────────────────────────────┐
│ ☐ 本周完成简历第二版      周日截止   │
│ ☐ 复习 RDB 和 AOF 区别    今天      │
└──────────────────────────────────────┘
```

- checkbox 点击 → `updateEntry(id, { status: 'done', completed_at: new Date().toISOString() })`
  - 视觉上：checkbox 打勾 → 200ms 淡出 → 从计划区消失，出现在时间线"今天"组
- 右侧显示相对截止时间：`今天 / 明天 / 周日截止 / 3 天后`
- 长按（或右键）出现"放弃"选项 → `updateEntry(id, { status: 'dropped' })`

### §5.6 TagChips（标签选择器）

```
[#项目] [#面试] [#学习]  [+自定义]
```

- 预设 3 个，点击切换 `selected` 状态
- `[+自定义]` 点击后变成一个 input，输入后回车添加到 selected tags
- selected tags 显示时用主色（蓝），未选的灰色

---

## §6 样式规则

- **复用现有样式**：卡片边框、间距、颜色直接抄 `frontend/src/components/growth-log/RecordRow.tsx`
- **slate 基调** + 蓝色强调（和旧页保持一致）
- 面试/项目卡片不要特别设计颜色，和学习笔记视觉上一致，只是内容更丰富
- AI 建议区用浅蓝 bg（`bg-blue-50` 或 `rgba(37,99,235,0.04)`）区分
- 计划区的 checkbox 完成动画：checkmark 画出 → 0.2s → 整行淡出

---

## §7 测试清单

demo 完成后，访问 `/growth-log-v2`，确认：

1. ☐ 页面顶部 QuickInput 常驻
2. ☐ 写"今天搞懂了 CAP 理论"+ 选 `#学习` + 点发送 → 出现在"今天"组
3. ☐ 写"下周完成 Redis 八股"+ 勾"计划"+ 选本周 + 发送 → 出现在计划区
4. ☐ 点计划区的 checkbox → 消失，出现在时间线
5. ☐ 点"面试复盘"按钮 → 模态框打开，填完保存 → 出现面试卡片，展开显示问答
6. ☐ 点"记录项目"按钮 → 模态框打开，填完保存 → 出现项目卡片
7. ☐ 面试卡片点 `[AI 建议]` → 500ms 后显示 3 条建议
8. ☐ 点建议上的 `[转为计划]` → 出现在计划区
9. ☐ FilterChips 切换到 `#面试` → 只显示面试记录
10. ☐ 所有旧数据（`ProjectRecord` / `JobApplication`）**不读取**，纯 mock

---

## §8 不需要做的事

- ❌ 不碰任何后端代码
- ❌ 不改 `/api/growth-log/*` 任何接口
- ❌ 不改现有 `GrowthLogPage.tsx` 和 `components/growth-log/` 目录下的任何文件
- ❌ 不用做持久化 — 刷新页面后 mock 数据回到初始状态是 OK 的
- ❌ 不用做删除确认、撤销等精细交互 — 直接删即可

---

## §9 开工前的一句话

看完 spec 如果有不确定的地方，先写下问题问，不要猜。
特别注意：这是**前端 demo**，所有数据都是 mock，目标是**让用户点一遍看效果**，不是生产实现。

开工前回一句"文档读完，准备开工"。
