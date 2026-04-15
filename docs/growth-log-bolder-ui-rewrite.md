# GrowthLogPage UI 重写 · Editorial Morning Light

交付人：Kimi
审查 / 文档：Claude
日期：2026-04-15
触发：owner /impeccable:bolder + 选择"重写视觉语言"

---

## 一、背景与目标

### 当前状态（owner 截图证据）
GrowthLogPage 实际渲染：
- 80% 屏幕高度空白
- 顶部 GoalBar 一行 + 4 个 filter chips 挤在一排
- 中间 EmptyState 极简卡片"还没有任何记录" + 两个按钮
- **GrowthDashboard 组件存在但未被渲染**（page.tsx 漏掉了）

owner 反馈："感觉有问题，UI 和其它方面"。诊断：荒芜空屏 + 已写未连 + 视觉无温度。

### 目标
按 `.impeccable.md` 定义的 **晨光编辑体（Editorial Morning Light）** 方向重写 GrowthLogPage 的 UI 层。

**完成标准**：
1. 页面不再荒芜（首屏填充率 ≥ 70%）
2. 视觉风格摆脱 liquid glass + AI slop 默认
3. 章节式叙事结构（不是仪表盘 grid）
4. 触动用户的"温暖陪伴 · 学长视角"

### 非目标（不做）
- ❌ 不改 backend API
- ❌ 不改数据 schema
- ❌ 不改 React Query key（缓存继续 work）
- ❌ 不动 supervisor / agent / skill 系统
- ❌ 暂不做深色模式

---

## 二、Design Context（必读）

**所有设计决策必须从 `.impeccable.md` 取根**。本文档不重复其内容，但以下三条强调：

1. 用户：CS/IT 大三/大四迷茫学生，常在情绪不稳定时打开
2. 品牌人格：**温暖 · 同行 · 不评判** — 像懂你的学长，不是导师/AI 工具
3. 视觉方向：**晨光编辑体** — 纸感底 + 章节分节 + 温润色板 + 衬线/sans 混排

**Absolute bans（impeccable 协议）**：
- ❌ glassmorphism（替换掉所有 `.glass` / `.glass-static` 用法）
- ❌ border-left/right > 1px 色条
- ❌ gradient text（`background-clip: text` + gradient）
- ❌ AI cyan/purple gradient
- ❌ Plus Jakarta Sans / Inter / DM Sans 等禁用字体（当前用了 Plus Jakarta Sans，要换）

---

## 三、改造范围（文件级清单）

### 3.1 Token / 全局样式
| 文件 | 动作 |
|---|---|
| `frontend/src/index.css` | 改 `:root` 色变量 → OKLCH 暖色板；改 `--font-sans` → Bricolage + Geist + Noto Sans SC；新增 `--font-display`（Bricolage variable）+ `--font-serif`（Source Serif 4） |
| `frontend/index.html` | `<link>` 加载 Google Fonts: Bricolage Grotesque + Source Serif 4 + Noto Serif SC（Noto Sans SC 已有） |

### 3.2 新建组件
| 文件 | 职责 |
|---|---|
| `frontend/src/components/growth-log/Chapter.tsx` | 章节包裹 — 渲染 `CHAPTER N · 标签` + serif 大标题 + 引言段落 + children |
| `frontend/src/components/growth-log/PaperCard.tsx` | 替代 glass 的纸感卡片（米色填充 + 1px 细 line border + 温暖 shadow） |
| `frontend/src/components/growth-log/SectionDivider.tsx` | 章节分隔（细水平线 + 居中罗马数字） |

### 3.3 重写组件
| 文件 | 重写要点 |
|---|---|
| `frontend/src/pages/GrowthLogPage.tsx` | 章节布局；删本地 `EmptyState`（被 Chapter I 的叙事替代）；空数据时也要好看 |
| `frontend/src/components/growth-log/GrowthDashboard.tsx` | 保留逻辑/数据查询，重做视觉（嵌入 Chapter I，去掉 glass-static） |
| `frontend/src/components/growth-log/GoalBar.tsx` | 合并到 Chapter I 的 hero 段，**不再独立顶部条** |
| `frontend/src/components/growth-log/RecordRow.tsx` | PaperCard 风格，去 glass |
| `frontend/src/components/growth-log/FilterChips.tsx` | 数据为空时**隐藏**；字体用 serif/grotesk 重做 |

### 3.4 不动
- 所有 `frontend/src/api/*.ts`
- 所有 React Query queryKey
- DB models / backend routes

---

## 四、信息架构（GrowthLogPage 章节布局）

```
┌────────────────────────────────────────────────────────────┐
│ CHAPTER I · 你在哪                                          │  hero 区（替代 GoalBar + GrowthDashboard）
│                                                            │
│ 「你的目标是 [后端开发]，                                    │  serif Display 大字
│   从开始到现在 14 天。」                                     │  
│                                                            │
│ 系统看见你做了 3 件具体的事，                                 │  body 段落 65ch
│ 还差关键的 2 步。                                           │
│                                                            │
│ ┌────────────────────────────────────────────────┐         │
│ │  技能覆盖（按市场重要性分层）                     │         │  PaperCard 内容
│ │  [Tier bar 横铺]                                │         │
│ ├────────────────────────────────────────────────┤         │
│ │  [Readiness 曲线]                              │         │
│ └────────────────────────────────────────────────┘         │
│                                                            │
├──────────────  · II ·  ──────────────────────────────────┤  SectionDivider
│                                                            │
│ CHAPTER II · 这两周你做了什么                                │  
│                                                            │
│ [今天]                                                     │  
│   · ProjectRecord PaperCard                                │
│ [本周]                                                     │
│   · JobApplication PaperCard                               │
│                                                            │
├──────────────  · III ·  ─────────────────────────────────┤
│                                                            │
│ CHAPTER III · 接下来想试试什么                                │  
│                                                            │
│ [Refine / ActionProgress 区]                               │
└────────────────────────────────────────────────────────────┘
```

### 空状态（无 goal / 无 records）
不显示空 grid。直接进 Chapter I 的 **PROLOGUE** 文案（参考现有 GrowthDashboard.EmptyDashboard 的 editorial 文案，但用新色板/字体重绘）。

---

## 五、技术规范

### 5.1 Token（写到 `index.css`）

**完全替换 `:root` 内的色变量**：

```css
:root {
  /* ── Editorial Morning Light · 晨光编辑体 ── */
  --bg-paper:    oklch(0.97 0.012 75);
  --bg-card:     oklch(0.99 0.006 75);
  --ink-1:       oklch(0.20 0.018 60);
  --ink-2:       oklch(0.42 0.012 60);
  --ink-3:       oklch(0.62 0.008 60);
  --moss:        oklch(0.55 0.090 145);
  --ember:       oklch(0.66 0.13 50);
  --chestnut:    oklch(0.32 0.05 30);
  --line:        oklch(0.88 0.012 75);

  /* shadcn 兼容映射 */
  --background: var(--bg-paper);
  --foreground: var(--ink-1);
  --card: var(--bg-card);
  --card-foreground: var(--ink-1);
  --primary: var(--moss);
  --primary-foreground: oklch(0.99 0.006 75);
  --muted: oklch(0.94 0.010 75);
  --muted-foreground: var(--ink-3);
  --accent: var(--ember);
  --accent-foreground: oklch(0.99 0.006 75);
  --destructive: oklch(0.55 0.18 30);
  --border: var(--line);
  --input: var(--line);
  --ring: var(--moss);
  --radius: 0.375rem;  /* 6px — 不要 12px+ 大圆角 */
}
```

**完全替换 `@theme` 内的字体**：

```css
@theme {
  --font-sans: 'Geist Variable', 'Noto Sans SC', system-ui, sans-serif;
  --font-display: 'Bricolage Grotesque', 'Noto Sans SC', sans-serif;
  --font-serif: 'Source Serif 4', 'Noto Serif SC', Georgia, serif;
  --ease-quart: cubic-bezier(0.25, 1, 0.5, 1);
}
```

**删除/弃用**：`.glass-nav` / `.glass` / `.glass-static` utility — 保留定义但 GrowthLogPage 相关组件**禁止使用**。

### 5.2 字体加载（`frontend/index.html`）

在 `<head>` 加：
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,500;0,8..60,600;1,8..60,400&family=Noto+Serif+SC:wght@500;600;700&display=swap" rel="stylesheet" />
```

（Noto Sans SC + Geist 已在原 css 加载，保留）

### 5.3 间距系统

不用具体 px，**用 Tailwind 既有 spacing scale**（Tailwind 4 已配 4pt 基础）。规则：
- Page padding：`px-6 md:px-16 lg:px-24`（移动 24 / 桌面 64-96）
- 章节间垂直留白：`py-16 md:py-24`（不要 py-8 这种局促）
- 段落 max-width：`max-w-[68ch]`（中文友好）

### 5.4 Chapter 组件 API

```tsx
// frontend/src/components/growth-log/Chapter.tsx

interface ChapterProps {
  numeral: 'I' | 'II' | 'III' | 'IV'
  label: string             // e.g. "你在哪"
  title: ReactNode          // serif Display 大字，可含 <br/>
  intro?: ReactNode         // body 引言段落（可选）
  children: ReactNode       // 章节内容
}

export function Chapter({ numeral, label, title, intro, children }: ChapterProps) {
  return (
    <section className="relative py-16 md:py-24">
      {/* CHAPTER N · 标签 */}
      <div className="flex items-center gap-3 mb-6">
        <span className="font-serif text-[11px] tracking-[0.2em] uppercase text-[var(--chestnut)]">
          Chapter {numeral} · {label}
        </span>
        <div className="flex-1 h-px bg-[var(--line)]" />
      </div>

      {/* Hero title */}
      <h2 className="font-display text-[clamp(28px,4vw,44px)] font-medium leading-[1.25] text-[var(--ink-1)] tracking-tight max-w-[20ch]">
        {title}
      </h2>

      {/* Intro */}
      {intro && (
        <p className="mt-4 font-sans text-[15px] leading-[1.7] text-[var(--ink-2)] max-w-[68ch]">
          {intro}
        </p>
      )}

      {/* Body */}
      <div className="mt-10">{children}</div>
    </section>
  )
}
```

### 5.5 PaperCard 组件 API

```tsx
// frontend/src/components/growth-log/PaperCard.tsx

interface PaperCardProps {
  children: ReactNode
  className?: string
  padded?: boolean   // default true
}

export function PaperCard({ children, className = '', padded = true }: PaperCardProps) {
  return (
    <div
      className={[
        'rounded-md border',
        'bg-[var(--bg-card)] border-[var(--line)]',
        // 暖 shadow（不是 cool blue）
        'shadow-[0_1px_2px_rgba(60,40,20,0.04),0_4px_12px_rgba(60,40,20,0.05)]',
        padded ? 'p-6 md:p-8' : '',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}
```

**禁止**：`.glass` / `.glass-static` / `backdrop-filter` / 大圆角（rounded-2xl 改为 rounded-md = 6px）。

### 5.6 SectionDivider 组件

```tsx
// frontend/src/components/growth-log/SectionDivider.tsx

export function SectionDivider({ numeral }: { numeral: 'II' | 'III' | 'IV' }) {
  return (
    <div className="flex items-center gap-4 my-8 md:my-12">
      <div className="flex-1 h-px bg-[var(--line)]" />
      <span className="font-serif italic text-[12px] text-[var(--ink-3)] tracking-wider">
        · {numeral} ·
      </span>
      <div className="flex-1 h-px bg-[var(--line)]" />
    </div>
  )
}
```

### 5.7 GrowthLogPage 重写要点

- 删除 `EmptyState` 本地函数（line 94-113）
- 删除 `<GoalBar />`（line 172）
- 引入 `<Chapter>` × 3 + `<SectionDivider>` × 2 + `<PaperCard>` 包裹细节
- 数据为空时 Chapter I 显示 **PROLOGUE 文案**（参考 `GrowthDashboard.EmptyDashboard`，复用文案，重新视觉化）
- FilterChips：`if (!allRecords.length) return null` — 空数据时不渲染

### 5.8 文案改写（按 Design Principle 3 · 零评判用语）

对照表（必改）：
| 旧文案 | 新文案 |
|---|---|
| "还没有任何记录" | "还没有可以记下来的事 — 我们从一件最小的开始" |
| "没有符合条件的记录" | "这个分类下还是空的" |
| "+ 新记录" | "记一笔" |
| "选方向" | "去看看可能的方向" |
| "已坚持 14 天" | "陪你 14 天了" |
| "请上传简历" | "想看你的画像 — 上传一份简历就好" |

---

## 六、Kimi 任务拆解（T1 → T6）

### T1 · Token + 字体加载
- 改 `frontend/src/index.css` 的 `:root` + `@theme`
- 改 `frontend/index.html` 加字体 `<link>`
- 删 css 里和 GrowthLog 相关的 glass utility 引用（保留 utility 定义供其他页面用）

**T1 验证**：
```bash
cd frontend && npm run build 2>&1 | tail -10
# 期望：build 通过；no font 404
```

### T2 · 新建 3 个组件
- `Chapter.tsx`、`PaperCard.tsx`、`SectionDivider.tsx`

**T2 验证**：tsc + 组件可独立 import

### T3 · 重写 GrowthDashboard
- 保留所有 react-query / data shape / TierBar / ReadinessCurve 内部组件逻辑
- 视觉层完全重做：去 `glass-static` + 改字体 class + 改色变量
- 头部用 serif label 而不是 emoji 图标
- EmptyDashboard 复用文案，视觉重做

**T3 验证**：tsc + 截图比对

### T4 · 重写 RecordRow + GoalBar 拆并
- RecordRow 用 PaperCard 替代 glass
- GoalBar 内容并入 Chapter I 的 intro 段（删除独立组件 OR 标记 deprecated）

### T5 · 重写 GrowthLogPage 主结构
- 章节布局 + Chapter × 3 + Divider × 2
- 文案表全替换
- FilterChips 空数据隐藏
- 删本地 EmptyState

**T5 验证**：tsc 通过 + 启动 dev server 视觉验收

### T6 · 整体回归
- `npm run build` 通过
- `npm run lint`（如有）通过
- owner 启动 dev 看实际效果
- 边缘场景（无 goal / 有 goal 无 records / 有 records）每种都好看

---

## 七、红线（Kimi 严守）

1. **不引入新依赖** — 字体走 Google Fonts CDN，不装新 npm 包
2. **不改 backend** — 任何 backend/* 文件都不动
3. **不改数据接口** — `frontend/src/api/*.ts` 不动；queryKey 不变；prop 类型不变
4. **不破坏其他页面** — 改 index.css 时确认其他页面（Profile / Graph / Report）色彩可读，不要让全站翻车
5. **glass utility 定义保留** —— 只在 GrowthLog 相关组件停止使用；其他页面继续 work
6. **impeccable absolute bans 全程遵守**：
   - ❌ glassmorphism on GrowthLog
   - ❌ border-left/right > 1px 色条
   - ❌ gradient text
   - ❌ Plus Jakarta Sans / Inter / DM Sans
   - ❌ AI cyan/purple gradient
7. **每个 T 完成后**必跑 `npm run build` 贴输出；不绿不进下一个 T

---

## 八、验证策略

由于无 visual regression test，验收靠：

1. **TypeScript build**：`npm run build` 通过
2. **owner 启动 dev**：`cd frontend && npm run dev` → 打开 `/growth-log` 用三个状态验收：
   - **No goal + no records**：Chapter I 显示 PROLOGUE，单页有温度，不空荡
   - **Has goal, no records**：Chapter I 显示 dashboard，Chapter II 显示"还没记下任何事"温文案
   - **Has goal + records**：完整三章节
3. **截图对比**：owner 可以截图发回，确认是否达到"晨光编辑体"目标

---

## 九、交付 Checklist（Kimi 自查）

- [ ] T1 token / 字体已落地，build 通过
- [ ] T2 3 个新组件就位
- [ ] T3 GrowthDashboard 视觉重做（数据逻辑零改动）
- [ ] T4 RecordRow 用 PaperCard；GoalBar 并入或删
- [ ] T5 GrowthLogPage 章节式重构 + 文案替换
- [ ] T6 build 全绿；其他页面（Profile/Graph/Report）人眼快查不崩
- [ ] 字体 404 检查（Bricolage / Source Serif 4 / Noto Serif SC 都加载到）
- [ ] 无新增 npm 依赖
- [ ] 无 glassmorphism 残留在 GrowthLog 相关文件
- [ ] 文案对照表全部替换

---

## 十、验收时的视觉锚点（owner 看效果）

成功的画面应该像：
- 翻开一本米白色封面、印着深栗色章节标题的小书
- 比起 SaaS 仪表盘，更像 **The Atlantic / 端传媒 / 单读** 的长 form 页面
- 用户读到第一行就感觉"哦，这不是又一个工具"

失败的迹象：
- ❌ 看起来还是个 dashboard
- ❌ 渐变背景 / glassmorphism 残留
- ❌ Plus Jakarta Sans 没换掉
- ❌ 文案还在用"建议你应该..."

---

## 附录 · 参考资料

- 设计上下文：[`.impeccable.md`](../.impeccable.md)
- 前序拆分文档：[`backend-slimdown-phase1-profile-service.md`](./backend-slimdown-phase1-profile-service.md)
- impeccable 协议：`~/.claude/plugins/cache/impeccable/impeccable/2.1.1/.claude/skills/impeccable/SKILL.md`
