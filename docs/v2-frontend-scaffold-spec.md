# v2 Frontend Scaffold · 晨光编辑体落地脚手架

> 创建：2026-04-15
> 状态：待 Kimi 实施
> 依赖：`.impeccable.md` v2.0（已落地）
> 策略：P2 子项目 — `frontend-v2/` 完全隔离，不污染 v1

---

## I. 背景与决策

### 为什么 P2 不是 P1

- v2 走 P2 方案：独立子项目 `frontend-v2/`，不在 v1 项目里加 `/v2/*` 路径
- 原因：彻底隔离 Tailwind config / dependencies / build 流程，避免 v1 的 cyan/purple 色污染 v2 的晨光编辑体
- v1 **冻结** — 留作对比参考，不再改动（bug 除外）

### GrowthLog 在 v2 的处置

- GrowthLog v1（晨光编辑体基础版）已在 `frontend/src/` 落地 + commit（`a824356`）
- 在 v2 项目里按 `.impeccable.md` **v2.0** 重做一版（Hero 更大 / 纸感纹理落地 / 装饰组件齐全）
- **不是直接拷贝 v1** — 是基于 v1 升级到 v2.0

---

## II. 项目结构

```
frontend-v2/
├── index.html                          # 字体 preconnect + viewport
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts                  # 复制 v1 + OKLCH v2.0 变量
├── package.json
├── public/
│   └── noise.svg                       # 全局纸感纹理（.impeccable.md 指定）
└── src/
    ├── main.tsx                        # React 挂载
    ├── App.tsx                         # Router
    ├── index.css                       # 全局 CSS（OKLCH v2.0 + 字体 + noise overlay）
    ├── api/                            # 从 frontend/ 拷贝（不 symlink）
    │   ├── client.ts
    │   ├── profiles.ts
    │   ├── report.ts
    │   ├── growthLog.ts
    │   ├── recommendations.ts
    │   ├── applications.ts
    │   └── graph.ts
    ├── types/                          # 从 frontend/ 拷贝
    │   ├── application.ts
    │   ├── profile.ts
    │   ├── dashboard.ts
    │   ├── graph.ts
    │   └── jd.ts
    ├── components/
    │   ├── editorial/                  # ⭐ v2 原子组件库（核心）
    │   │   ├── Chapter.tsx
    │   │   ├── ChapterOpener.tsx
    │   │   ├── SectionDivider.tsx
    │   │   ├── PaperCard.tsx
    │   │   ├── DropCap.tsx
    │   │   ├── PullQuote.tsx
    │   │   ├── Kicker.tsx
    │   │   └── index.ts                # barrel export
    │   ├── ui/                         # shadcn primitives（按需添加）
    │   └── shared/                     # 跨页公共组件（nav / footer）
    ├── hooks/
    │   └── useAuth.ts                  # 从 v1 拷贝
    └── pages/
        ├── HomePage.tsx                # v2
        ├── ProfilePage.tsx             # v2
        ├── ReportPage.tsx              # v2（优先级 1）
        ├── CoachResultPage.tsx         # v2
        ├── GrowthLogPage.tsx           # v2（基于 v1 升级，非拷贝）
        ├── RoleDetailPage.tsx          # v2
        ├── ProjectGraphPage.tsx        # v2
        └── PursuitDetailPage.tsx       # v2
```

**关键原则**：
- `api/` 和 `types/` 从 v1 **物理拷贝**，不 symlink（P2 完全隔离的体现）
- 如果 v1 的 client.ts 有 bug 修复，手动同步到 v2（后续 v1 废弃后不再同步）
- `components/editorial/` 是 v2 的**灵魂** — 所有页面都基于这 7 个原子组件搭建

---

## III. 技术栈与依赖

### package.json（核心）

```json
{
  "name": "frontend-v2",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "@tanstack/react-query": "^5.0.0",
    "framer-motion": "^11.0.0",
    "lucide-react": "^0.400.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

**NOT 引入**：
- ❌ shadcn 作为 npm 包（shadcn 是 CLI 生成到 src/，不是运行时依赖）
- ❌ 新字体包（全走 Google Fonts CDN）
- ❌ UI 库（headlessui / radix UI 只按需 cherry-pick）

### vite.config.ts

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5174,  // v1 用 5173，v2 用 5174，避免冲突
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

---

## IV. 路由方案

```tsx
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'

<BrowserRouter>
  <Routes>
    <Route path="/" element={<HomePage />} />
    <Route path="/profile" element={<ProfilePage />} />
    <Route path="/report" element={<ReportPage />} />
    <Route path="/coach" element={<CoachResultPage />} />
    <Route path="/growth-log" element={<GrowthLogPage />} />
    <Route path="/graph" element={<ProjectGraphPage />} />
    <Route path="/roles/:id" element={<RoleDetailPage />} />
    <Route path="/pursuits/:id" element={<PursuitDetailPage />} />
    <Route path="*" element={<NotFoundPage />} />
  </Routes>
</BrowserRouter>
```

**对外访问**：
- v1：`http://localhost:5173/*`
- v2：`http://localhost:5174/*`
- 用户并行对比时两个窗口开着看

---

## V. 全局 CSS 系统（`src/index.css`）

### 字体加载（index.html）

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@400;500;600;700&family=Source+Serif+4:ital,wght@0,400;0,500;1,400;1,500&family=Geist:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### index.css（关键片段）

```css
@import "tailwindcss";

:root {
  /* v2.0 色板（从 .impeccable.md 取全量）*/
  --bg-paper:       oklch(0.97 0.012 75);
  --bg-paper-2:     oklch(0.955 0.014 75);
  --bg-card:        oklch(0.99 0.006 75);
  --bg-card-hover:  oklch(0.985 0.008 75);
  --ink-1:          oklch(0.20 0.018 60);
  --ink-2:          oklch(0.42 0.012 60);
  --ink-3:          oklch(0.62 0.008 60);
  --moss:           oklch(0.55 0.090 145);
  --ember:          oklch(0.66 0.13 50);
  --chestnut:       oklch(0.32 0.05 30);
  --line:           oklch(0.88 0.012 75);
  --highlight:      oklch(0.93 0.045 85);
  --warm-shadow-1:  oklch(0.65 0.025 55 / 0.08);
  --warm-shadow-2:  oklch(0.50 0.035 50 / 0.12);

  /* Typography scale */
  --fs-display-xl: clamp(42px, 6vw, 96px);
  --fs-display-lg: clamp(36px, 5vw, 72px);
  --fs-display-md: clamp(28px, 3.6vw, 52px);
  --fs-body-lg:    17px;
  --fs-body:       15px;
  --fs-body-sm:    13px;
  --fs-caption:    11px;
  --fs-quote:      clamp(20px, 2.4vw, 32px);

  --lh-display:    1.12;
  --lh-body:       1.75;
  --lh-body-zh:    1.85;
  --lh-ui:         1.4;

  /* Warm shadow */
  --shadow-paper:   0 1px 2px var(--warm-shadow-1), 0 4px 12px var(--warm-shadow-2);
  --shadow-chapter: 0 2px 4px var(--warm-shadow-1), 0 12px 40px var(--warm-shadow-2);

  /* Font families */
  --font-display: "Bricolage Grotesque", "Noto Serif SC", serif;
  --font-serif:   "Source Serif 4", "Noto Serif SC", serif;
  --font-sans:    "Geist", "Noto Sans SC", sans-serif;
  --font-mono:    "JetBrains Mono", monospace;
}

html, body {
  background: var(--bg-paper);
  color: var(--ink-1);
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body-zh);
  -webkit-font-smoothing: antialiased;
}

/* 全局 noise overlay（.impeccable.md v2.0 必达）*/
body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1;
  background-image: url("/noise.svg");
  opacity: 0.025;
  mix-blend-mode: multiply;
}

/* 确保所有内容在 noise 之上 */
#root > * { position: relative; z-index: 2; }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### `public/noise.svg`

```svg
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <filter id="n">
    <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch"/>
    <feColorMatrix values="0 0 0 0 0.15
                           0 0 0 0 0.12
                           0 0 0 0 0.08
                           0 0 0 0.6 0"/>
  </filter>
  <rect width="100%" height="100%" filter="url(#n)"/>
</svg>
```

---

## VI. 原子组件库（`src/components/editorial/`）

### 组件清单（7 个必须）

| 组件 | 用途 | 关键 props |
|---|---|---|
| **Chapter** | 章节容器（替代 v1 version） | `numeral / label / title / intro / children` |
| **ChapterOpener** | 章节开篇大号罗马数字装饰 | `numeral / title` |
| **SectionDivider** | 章节之间的分隔（细线 + 斜体罗马数字） | `numeral` |
| **PaperCard** | 纸感卡片基础容器 | `children / className` |
| **DropCap** | 段落首字母放大 | `children`（第一个字符会被 extract） |
| **PullQuote** | 引文/金句 | `children / attribution?` |
| **Kicker** | 章节上方小导语 | `children` |

### 设计要点

**DropCap 中英文处理**：

```tsx
// 中文首字下沉 3 行 + Noto Serif SC
// 英文首字母 float + Source Serif 4
export function DropCap({ children }: { children: string }) {
  const [first, ...rest] = children
  const isChinese = /[\u4e00-\u9fff]/.test(first)
  return (
    <p className="text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
      <span
        className={isChinese
          ? "float-left font-serif text-[64px] leading-[0.85] mr-2 mt-1 text-[var(--chestnut)]"
          : "float-left font-serif text-[56px] leading-[0.85] mr-1 mt-1 text-[var(--chestnut)]"
        }
        style={{ fontFamily: isChinese ? 'var(--font-serif)' : 'var(--font-serif)' }}
      >
        {first}
      </span>
      {rest.join('')}
    </p>
  )
}
```

**PullQuote**（禁 border-left，用上下线）：

```tsx
export function PullQuote({ children, attribution }: { children: ReactNode; attribution?: string }) {
  return (
    <figure className="my-10 py-6 border-y border-[var(--line)] max-w-[58ch] mx-auto text-center">
      <blockquote className="font-serif italic text-[var(--fs-quote)] leading-[1.4] text-[var(--chestnut)]">
        "{children}"
      </blockquote>
      {attribution && (
        <figcaption className="mt-3 text-[var(--fs-caption)] uppercase tracking-[0.2em] text-[var(--ink-3)]">
          — {attribution}
        </figcaption>
      )}
    </figure>
  )
}
```

**Kicker**：

```tsx
export function Kicker({ children }: { children: ReactNode }) {
  return (
    <p className="font-sans text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--chestnut)] mb-3">
      {children}
    </p>
  )
}
```

**ChapterOpener**（装饰大号罗马数字背景）：

```tsx
export function ChapterOpener({ numeral, title }: { numeral: string; title: ReactNode }) {
  return (
    <div className="relative py-24 md:py-32 mb-8">
      <span
        aria-hidden
        className="absolute left-0 top-1/2 -translate-y-1/2 font-serif font-light text-[160px] md:text-[220px] leading-none tracking-tighter select-none pointer-events-none"
        style={{ color: 'var(--line)', zIndex: 0 }}
      >
        {numeral}
      </span>
      <div className="relative z-10 max-w-[18ch]">
        <h1 className="font-display font-medium text-[var(--fs-display-xl)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight">
          {title}
        </h1>
      </div>
    </div>
  )
}
```

**Chapter**（升级 v1 版本，fs scale 用 v2.0）：

```tsx
export function Chapter({ numeral, label, title, intro, children }: ChapterProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="relative py-24 md:py-32"
    >
      <Kicker>Chapter {numeral} · {label}</Kicker>
      <h2 className="font-display font-medium text-[var(--fs-display-lg)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight max-w-[22ch]">
        {title}
      </h2>
      {intro && (
        <p className="mt-6 font-sans text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[68ch]">
          {intro}
        </p>
      )}
      <div className="mt-12">{children}</div>
    </motion.section>
  )
}
```

---

## VII. 开发流程

### 启动

```bash
# Terminal 1 - backend
python -m uvicorn backend.app:app --reload

# Terminal 2 - v1 frontend (保留对照)
cd frontend && npm run dev           # :5173

# Terminal 3 - v2 frontend
cd frontend-v2 && npm run dev        # :5174
```

`start.bat` 更新增加 v2 启动入口（option 4）。

### Build

```bash
cd frontend-v2 && npm run build
```

输出到 `frontend-v2/dist/`，独立于 v1 的 dist。

---

## VIII. 验收标准

1. **项目能跑**：`cd frontend-v2 && npm install && npm run dev` → `http://localhost:5174` 出现空白 Home 骨架
2. **字体正确**：浏览器 DevTools Network 看到 Bricolage Grotesque / Source Serif 4 加载成功
3. **Noise overlay 可见**：肉眼在空白背景看到极细颗粒纹理（不是纯色）
4. **OKLCH 变量生效**：DevTools Inspector 看 `body` 的 color 是 `oklch(0.20 0.018 60)`，background 是 `oklch(0.97 0.012 75)`
5. **7 个 editorial 组件 Storybook 页**：`/__demo` 路由展示 Chapter / ChapterOpener / DropCap / PullQuote / Kicker / SectionDivider / PaperCard 各一个实例
6. **Build 无错误**：`npm run build` EXIT 0
7. **tsc 无错误**：`npm run build` 内嵌的 tsc --noEmit 通过

---

## IX. 不做的事

- ❌ 不做任何业务页（Home / Profile / Report / Coach 等）— 留给后续 spec
- ❌ 不引入 shadcn CLI（按需手动 copy radix primitive 再说）
- ❌ 不做 dark mode
- ❌ 不动 backend（API 完全复用）
- ❌ 不动 v1（v1 冻结）

---

## X. 给 Kimi 的执行顺序

1. `cd /c/Users/liu/Desktop/CareerPlanningAgent && mkdir frontend-v2`
2. `cd frontend-v2 && npm create vite@latest . -- --template react-ts`（Vite 脚手架）
3. 安装 deps（§III 清单）
4. 覆盖 `vite.config.ts` / `tsconfig.json`
5. 拷贝 `frontend/src/api/` → `frontend-v2/src/api/`
6. 拷贝 `frontend/src/types/` → `frontend-v2/src/types/`
7. 新建 `src/index.css`（§V）
8. 新建 `public/noise.svg`（§V）
9. 实现 7 个 editorial 组件（§VI）
10. 实现 `/__demo` 路由 + 各组件 showcase
11. 跑验收（§VIII 7 项）
12. commit：`feat(frontend-v2): scaffold + editorial component library`
13. 回我："P2 脚手架完成 + 访问地址"

---

**完成判定**：owner 打开 `http://localhost:5174/__demo` 看到 7 个组件按 `.impeccable.md` v2.0 描述的样子呈现，且感受到「温暖的纸上杂志」而非「SaaS 工具」。
