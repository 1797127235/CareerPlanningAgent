# 职业报告 PDF 导出 spec（交给 Kimi 执行）

## 目的

把当前网页版职业报告（`/report`，路由在 `frontend/src/pages/ReportPage.tsx`，4 章节由 `ChapterI/II/III/IV.tsx` 渲染）导出成**杂志级多栏 editorial 风格的 PDF**——效果对标：

> https://somnai-dreams.github.io/pretext-demos/the-editorial-engine.html

技术路线：

- **版面引擎**：`@chenglou/pretext` 负责文字测量 + 多栏流动 + 标题自适应字号 + 障碍物绕排
- **渲染目标**：真 DOM（绝对定位的 `<div>`），文字可选可复制
- **PDF 输出**：后端 Playwright headless Chromium 打开专用打印路由，`page.pdf()` 返回 PDF 流

最终成品：真文本 PDF（可搜索可复制）+ 杂志多栏排版 + 文件大小合理（不截图）。

## 顶层架构

```
用户点"导出 PDF"
  └─ frontend 调 POST /api/report/{id}/export (带 Authorization)
      └─ backend 起 Playwright
          ├─ new browser context
          ├─ addInitScript 注入 localStorage.token
          ├─ navigate to http://localhost:5173/report/print/{id}
          ├─ wait_for_selector('[data-print-ready="true"]')
          ├─ page.pdf({format:'A4', printBackground:true, preferCSSPageSize:true})
          └─ 返回 PDF 字节流
      └─ frontend 接 blob，触发下载
```

**注入 token 的原因**：前端用 JWT in `localStorage`（见 `frontend/src/api/client.ts`），headless 浏览器一开始没 token，`/report/print/{id}` 里的 `rawFetch` 会 401 跳 `/login`。Playwright 必须在 `navigate` 之前把 token 写进浏览器的 localStorage。

## 文件清单

### 新增
- `frontend/src/pages/ReportPrintPage.tsx` — 打印专用路由页面
- `frontend/src/components/report-print/` — pretext 排版组件目录
  - `utils/fitHeadline.ts` — 二分搜索字号让标题刚好 N 行
  - `utils/flowColumns.ts` — 文字流进多栏，支持障碍物
  - `utils/useFontsReady.ts` — 等字体加载完
  - `PrintChapterI.tsx` — 你是谁（单栏引用式）
  - `PrintChapterII.tsx` — 你能去哪（两栏流动 + 里程碑 pullquote）
  - `PrintChapterIII.tsx` — 现状评估（网格 + 技能徽章）
  - `PrintChapterIV.tsx` — 下一步（三栏行动卡）
  - `PrintHeader.tsx` — 封面/报头（目标岗位大字）
  - `PrintFooter.tsx` — 页脚（生成日期）
- `backend/services/report/pdf_export.py` — Playwright 渲染服务
- `backend/routers/report.py` 新增路由 `POST /report/{id}/export`
- `docs/report-export-install.md` — 环境安装说明（playwright + chromium + 字体）

### 修改
- `frontend/package.json` — 加 `@chenglou/pretext` 依赖
- `frontend/src/App.tsx` — 加 `/report/print/:id` 路由（不要带 Layout 包一层，全屏裸页面）
- `frontend/src/api/report.ts` — 加 `exportReportPdf(reportId): Promise<Blob>` 函数
- `frontend/src/pages/ReportPage.tsx` — 在现有"再生成 →"旁加"导出 PDF"按钮
- `backend/requirements.txt` 或 `pyproject.toml` — 加 `playwright>=1.40`

### 不要动
- `frontend/src/components/report/ChapterI.tsx` / `ChapterII.tsx` / `ChapterIII.tsx` / `ChapterIV.tsx`（网页版，保留）
- 后端的 `backend/services/report/pipeline.py` 等报告生成逻辑
- 认证系统

---

## Part 1：前端装 pretext + 打印路由骨架

### 1.1 安装

```bash
cd frontend
npm install @chenglou/pretext
```

### 1.2 新增路由

`frontend/src/App.tsx`，在现有 `<Route path="/report" ...>` 附近加：

```tsx
import ReportPrintPage from '@/pages/ReportPrintPage'
// ...
<Route path="/report/print/:id" element={<ReportPrintPage />} />
```

**注意**：这个路由**不能**被 `<Layout>` 或 `<Sidebar>` 包裹——必须是裸页面（整个 body 只有报告内容）。如果 App.tsx 里其它路由都套了 Layout，打印路由要单独写在 Layout 外面。

### 1.3 `ReportPrintPage.tsx` 骨架

```tsx
import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { fetchReport } from '@/api/report'  // 按现有接口
import type { ReportV2Data } from '@/api/report'
import { useFontsReady } from '@/components/report-print/utils/useFontsReady'
import { PrintHeader } from '@/components/report-print/PrintHeader'
import { PrintChapterI } from '@/components/report-print/PrintChapterI'
import { PrintChapterII } from '@/components/report-print/PrintChapterII'
import { PrintChapterIII } from '@/components/report-print/PrintChapterIII'
import { PrintChapterIV } from '@/components/report-print/PrintChapterIV'
import { PrintFooter } from '@/components/report-print/PrintFooter'

export default function ReportPrintPage() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<ReportV2Data | null>(null)
  const [layoutDone, setLayoutDone] = useState(false)
  const fontsReady = useFontsReady()

  useEffect(() => {
    if (!id) return
    fetchReport(Number(id)).then(setData)
  }, [id])

  const ready = data && fontsReady && layoutDone

  return (
    <div
      className="report-print-root"
      data-print-ready={ready ? 'true' : 'false'}
    >
      {data && fontsReady && (
        <>
          <PrintHeader data={data} />
          <PrintChapterI data={data} onLayoutDone={() => {}} />
          <PrintChapterII data={data} onLayoutDone={() => {}} />
          <PrintChapterIII data={data} onLayoutDone={() => {}} />
          <PrintChapterIV
            data={data}
            onLayoutDone={() => setLayoutDone(true)}  // 最后一章布局完才 ready
          />
          <PrintFooter data={data} />
        </>
      )}
    </div>
  )
}
```

**`data-print-ready` 属性是 Playwright 的等待信号**——所有章节布局 + 字体都就位后才置为 `true`，Playwright 看到这个才开始 `page.pdf()`。

### 1.4 全局打印样式

在 `frontend/src/index.css`（或报告页专用 css）加：

```css
@page {
  size: A4;
  margin: 18mm 16mm;
}

.report-print-root {
  background: #fff;
  color: #0f172a;
  font-family: 'Source Han Serif SC', 'Noto Serif CJK SC', 'Songti SC', serif;
}

/* 让每章从新页开始（除第一章外） */
.print-chapter {
  break-before: page;
  break-inside: auto;
}
.print-chapter:first-of-type {
  break-before: auto;
}

/* 不可被拆分的单元 */
.print-avoid-break {
  break-inside: avoid;
}
```

字体家族选项 Kimi 按实际可用字体调整；中文衬线字体最接近 editorial 感。

---

## Part 2：pretext 工具函数

### 2.1 `frontend/src/components/report-print/utils/useFontsReady.ts`

```ts
import { useEffect, useState } from 'react'

export function useFontsReady() {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    if (!document.fonts) {
      setReady(true)
      return
    }
    document.fonts.ready.then(() => setReady(true))
  }, [])
  return ready
}
```

### 2.2 `frontend/src/components/report-print/utils/fitHeadline.ts`

参考 pretext editorial demo 的做法：用 `prepare` + `layout` 二分搜索字号。

```ts
import { prepare, layout } from '@chenglou/pretext'

/**
 * 二分搜索最大字号使标题刚好 N 行（默认 1 行）
 * @param text 标题文字
 * @param fontFamily 字体 family（例如 "Source Han Serif SC"）
 * @param fontWeight 字重（例如 700）
 * @param maxWidth 容器宽度 px
 * @param maxLines 允许的最大行数
 * @param minSize 最小字号（例如 24）
 * @param maxSize 最大字号（例如 96）
 */
export function fitHeadline(
  text: string,
  fontFamily: string,
  fontWeight: number,
  maxWidth: number,
  maxLines = 1,
  minSize = 24,
  maxSize = 96,
): number {
  let lo = minSize, hi = maxSize, best = minSize
  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2)
    const font = `${fontWeight} ${mid}px "${fontFamily}"`
    const prepared = prepare(text, font)
    const { lineCount } = layout(prepared, maxWidth, mid * 1.15)
    if (lineCount <= maxLines) {
      best = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  return best
}
```

### 2.3 `frontend/src/components/report-print/utils/flowColumns.ts`

把文字流进多列，支持"障碍物"（拉 quote、图片占位）。

```ts
import {
  prepareWithSegments,
  layoutNextLine,
  walkLineRanges,
} from '@chenglou/pretext'

export type Obstacle = {
  // 相对于容器的矩形 {x, y, w, h}
  x: number; y: number; w: number; h: number
}

export type Column = { x: number; y: number; width: number; height: number }

export type PlacedLine = {
  text: string
  x: number
  y: number
  width: number
}

/**
 * 把 text 按列（从第一列顺序到最后一列）流入 columns，遇到 obstacles 则跳过被挡的竖向区间。
 * @param text 段落原文
 * @param font canvas font shorthand
 * @param lineHeight 行高 px
 * @param columns 列布局
 * @param obstacles 障碍物
 * @returns 每行的绝对位置（相对容器）
 */
export function flowIntoColumns(
  text: string,
  font: string,
  lineHeight: number,
  columns: Column[],
  obstacles: Obstacle[],
): PlacedLine[] {
  const prepared = prepareWithSegments(text, font)
  const lines: PlacedLine[] = []
  let cursorIndex = 0

  for (const col of columns) {
    let y = col.y
    while (y + lineHeight <= col.y + col.height && cursorIndex < text.length) {
      // 计算当前行的有效宽度：列宽减去与障碍物相交部分
      const effectiveWidth = availableWidth(col, y, lineHeight, obstacles)
      if (effectiveWidth <= 0) {
        y += lineHeight
        continue
      }
      const result = layoutNextLine(prepared, cursorIndex, effectiveWidth)
      if (!result || result.length === 0) break
      const lineText = text.slice(cursorIndex, cursorIndex + result.length)
      lines.push({
        text: lineText,
        x: col.x + offsetForObstacles(col, y, lineHeight, obstacles),
        y,
        width: effectiveWidth,
      })
      cursorIndex += result.length
      y += lineHeight
    }
    if (cursorIndex >= text.length) break
  }
  return lines
}

function availableWidth(col: Column, y: number, h: number, obstacles: Obstacle[]): number {
  let w = col.width
  for (const ob of obstacles) {
    if (ob.y < y + h && ob.y + ob.h > y) {
      const overlap = Math.max(0, Math.min(col.x + col.width, ob.x + ob.w) - Math.max(col.x, ob.x))
      w -= overlap
    }
  }
  return Math.max(0, w)
}

function offsetForObstacles(col: Column, y: number, h: number, obstacles: Obstacle[]): number {
  let offset = 0
  for (const ob of obstacles) {
    if (ob.y < y + h && ob.y + ob.h > y && ob.x <= col.x && ob.x + ob.w > col.x) {
      offset = Math.max(offset, ob.x + ob.w - col.x)
    }
  }
  return offset
}
```

**说明**：`layoutNextLine` 的确切签名请 Kimi 查 `@chenglou/pretext` 的 d.ts（`node_modules/@chenglou/pretext/dist/*.d.ts`），上面是概念代码。如果 pretext 的 API 用 `{ length, width, ... }` 返回对象，按实际类型调整。核心思想不变：**按列从上到下走，每行用 pretext 问"这行塞多少字"**。

---

## Part 3：四章打印组件

每章都遵循模式：

1. 用 `useRef` 拿容器 DOM 尺寸（`offsetWidth`）
2. 在 `useEffect` 里用 pretext 算好所有行位置
3. 渲染成绝对定位的 div
4. 布局完成调 `onLayoutDone()`

### 3.1 `PrintHeader.tsx`

封面块：

- 顶端"职业生涯发展报告"小标（10pt，uppercase，tracking 宽）
- 目标岗位（`data.target_label`），用 `fitHeadline` 自适应，最大 96pt
- 生成日期（10pt，右对齐）

### 3.2 `PrintChapterI.tsx` — 你是谁（单栏引用式）

- 章节号 "I · 你是谁"（10pt 蓝色 uppercase）
- 大标题 "先把你自己看清楚。"（`fitHeadline`）
- 叙事正文分两段：
  - 第一段用 drop cap（首字放大 3 倍，浮左，文字绕排——用 pretext `flowIntoColumns` 带一个 drop-cap 障碍物）
  - 剩余段落正常流
- 引用块（如简历项目摘录），缩进 + 左 1pt 灰线（注意 print CSS 允许 1px 左边框，禁令只针对 >1px 的装饰性 side-stripe）

### 3.3 `PrintChapterII.tsx` — 你能去哪（两栏 + pullquote）

- 章节号 + 标题同上
- 正文两栏流动（`columns` 参数传两列）
- 里程碑 / 市场信号做成一个**居中的 pullquote 障碍物**（大字号引述），正文绕它流
- 底部三个 "achievable" / "stretch" / "dream" 节点缩成一行卡片

### 3.4 `PrintChapterIII.tsx` — 现状评估（网格）

- 章节号 + 标题
- 顶部匹配分数大字（独占一行，`fitHeadline`）
- 技能掌握 / 缺失 / 待验证 三栏并列
- 每栏内用 tag 形式罗列（小 chip，不分栏流动，用 flex wrap）

### 3.5 `PrintChapterIV.tsx` — 下一步（三栏行动卡）

- 章节号 + 标题
- 每个 stage 独占一段，stage 标题大字
- stage 内 items 按三栏卡片布局：
  - 每张卡 = type 标签 + tag 大标题 + observation（用 pretext flow） + action（粗体一句）
  - `break-inside: avoid`（每张卡不被页切断）
- 最后一条卡渲染完调 `onLayoutDone()`（触发 `data-print-ready`）

### 3.6 章节 DOM 骨架示例

```tsx
function PrintChapterII({ data, onLayoutDone }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [lines, setLines] = useState<PlacedLine[]>([])

  useEffect(() => {
    if (!containerRef.current) return
    const w = containerRef.current.offsetWidth
    const colWidth = (w - 32) / 2  // 两栏中间 32px gutter
    const columns: Column[] = [
      { x: 0, y: 0, width: colWidth, height: 600 },
      { x: colWidth + 32, y: 0, width: colWidth, height: 600 },
    ]
    const obstacles: Obstacle[] = [
      // 居中 pullquote：宽 280，高 120，位置 (w/2 - 140, 200)
      { x: w / 2 - 140, y: 200, w: 280, h: 120 },
    ]
    const font = '14px "Source Han Serif SC"'
    const placed = flowIntoColumns(data.narrative.body, font, 22, columns, obstacles)
    setLines(placed)
    onLayoutDone()
  }, [data])

  return (
    <section className="print-chapter" ref={containerRef}>
      {/* 章节号 + 标题 */}
      <div className="mb-8">
        <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600">
          II · 你能去哪
        </span>
        <h2 className="text-[36px] font-bold mt-2">
          在 {data.target_label} 方向上，你还能走多远。
        </h2>
      </div>

      {/* 流动正文（绝对定位 div） */}
      <div className="relative" style={{ height: 600 }}>
        {lines.map((ln, i) => (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: ln.x,
              top: ln.y,
              width: ln.width,
              fontSize: 14,
              lineHeight: '22px',
              fontFamily: '"Source Han Serif SC"',
            }}
          >
            {ln.text}
          </div>
        ))}

        {/* Pullquote 障碍物（视觉元素，带白色背景遮盖正文） */}
        <blockquote
          style={{
            position: 'absolute',
            left: '50%',
            top: 200,
            transform: 'translateX(-50%)',
            width: 280,
            height: 120,
            background: '#fff',
            padding: 16,
          }}
          className="text-[18px] italic font-bold text-slate-900 print-avoid-break"
        >
          {data.market_pullquote ?? '岗位处于 ...'}
        </blockquote>
      </div>
    </section>
  )
}
```

**实现要点**：

- 正文文字用绝对定位 div 贴位置，不用浏览器自动 wrap
- 障碍物（pullquote）必须 `background: #fff`，否则会和底下的文字行叠加
- 高度 600 是占位，实际项目可以让 pretext 根据内容决定；Kimi 可以让 `flowIntoColumns` 返回总高度，然后 setState 回去
- 每章独立判断字段来源：narrative、market、alignments、skill_gap、action_plan——按 `ReportV2Data` 的类型定义（在 `frontend/src/api/report.ts`）取字段

---

## Part 4：后端 Playwright 渲染

### 4.1 依赖

`backend/requirements.txt` 加：

```
playwright>=1.40
```

部署环境执行一次：

```bash
pip install playwright
playwright install chromium
```

Windows 用户如遇到缺 DLL 报错，装 VC++ redist。

### 4.2 `backend/services/report/pdf_export.py`

```python
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def render_report_pdf(
    report_id: int,
    token: str,
    user_json: dict,
    frontend_base: str | None = None,
) -> bytes:
    """
    用 Playwright headless 打开报告打印页，渲染成 PDF 字节。

    Args:
        report_id: 报告 ID
        token: 用户的 JWT（从请求 Authorization header 拿）
        user_json: localStorage 里存的 user 对象（从数据库查或从请求拿）
        frontend_base: 前端地址，默认读 env FRONTEND_URL 或 http://localhost:5173
    Raises:
        TimeoutError: 渲染超时（默认 30s）
        RuntimeError: 渲染异常
    """
    from playwright.async_api import async_playwright

    base = frontend_base or os.getenv("FRONTEND_URL", "http://localhost:5173")
    url = f"{base}/report/print/{report_id}"
    user_str = json.dumps(user_json).replace("'", "\\'")
    # addInitScript 注入 localStorage，确保应用加载前就有 token
    init_script = f"""
      localStorage.setItem('token', '{token}');
      localStorage.setItem('user', '{user_str}');
    """

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                viewport={"width": 1240, "height": 1754},  # A4 @ 150dpi
            )
            await context.add_init_script(init_script)
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # 等打印就绪信号（由 ReportPrintPage 设置）
            await page.wait_for_selector(
                '[data-print-ready="true"]',
                timeout=30000,
            )

            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            return pdf_bytes
        finally:
            await browser.close()
```

**注意**：
- `token` 和 `user_json` 从路由里的请求状态拿（见 4.3）
- `prefer_css_page_size=True` 让 `@page { size: A4 }` 生效
- margin 设 0 是因为 `@page` 里已经写了 margin；两边都留会变双倍
- 超时 30s 可以根据实际情况调
- 浏览器 launch 每次新起（简单）；以后可优化为单例池

### 4.3 路由

`backend/routers/report.py` 增加：

```python
from fastapi import Response
from fastapi.responses import StreamingResponse

@router.post("/{report_id}/export")
async def export_report_pdf(
    report_id: int,
    request: Request,  # 拿 Authorization header
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. 权限校验：报告属于当前用户
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if report.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")

    # 2. 拿 token（从请求头）
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = auth[len("Bearer "):]

    # 3. 拿 user_json（前端 localStorage.user 的格式）
    user_json = {
        "id": current_user.id,
        "email": current_user.email,
        # ... 按 frontend/src/hooks/useAuth.ts 里 localStorage.user 的实际结构来
    }

    # 4. 渲染
    from backend.services.report.pdf_export import render_report_pdf
    try:
        pdf_bytes = await render_report_pdf(report_id, token, user_json)
    except Exception as e:
        logger.exception("PDF export failed")
        raise HTTPException(500, f"PDF 生成失败：{e}")

    # 5. 构造文件名
    target = report.data.get("target_label", "报告") if isinstance(report.data, dict) else "报告"
    date_str = report.created_at.strftime("%Y-%m-%d") if report.created_at else "unknown"
    filename = f"{target}_职业报告_{date_str}.pdf"
    # RFC 5987 encode
    from urllib.parse import quote
    encoded = quote(filename)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
        },
    )
```

**`user_json` 的字段**：Kimi 自己看 `frontend/src/hooks/useAuth.ts` 里 `localStorage.setItem('user', ...)` 的那行，照抄字段。

### 4.4 FRONTEND_URL 环境变量

`.env` 加：

```
FRONTEND_URL=http://localhost:5173
```

生产环境如果前后端同源，可以填 `http://localhost:8000`（后端端口）——但前提是后端已经 serve 静态前端。按实际部署调。

---

## Part 5：前端导出按钮

### 5.1 `frontend/src/api/report.ts` 增加：

```ts
export async function exportReportPdf(reportId: number): Promise<Blob> {
  const token = localStorage.getItem('token') ?? ''
  const res = await fetch(`${API_BASE}/report/${reportId}/export`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `导出失败 (${res.status})`)
  }
  return res.blob()
}
```

### 5.2 `frontend/src/pages/ReportPage.tsx` 加按钮

找到现有"再生成 →"按钮所在位置，旁边加一个"导出 PDF"。按钮三态：

```tsx
const [exporting, setExporting] = useState(false)
const [exportError, setExportError] = useState<string | null>(null)

const handleExport = async () => {
  if (exporting || !reportData?.id) return
  setExporting(true)
  setExportError(null)
  try {
    const blob = await exportReportPdf(reportData.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const target = reportData.target_label || '报告'
    const date = new Date().toISOString().slice(0, 10)
    a.download = `${target}_职业报告_${date}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    setExportError(e instanceof Error ? e.message : String(e))
  } finally {
    setExporting(false)
  }
}
```

按钮 UI：

```tsx
<button
  onClick={handleExport}
  disabled={exporting}
  className="text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 disabled:opacity-60 cursor-pointer transition-colors"
>
  {exporting ? '正在生成 PDF…' : '导出 PDF'}
</button>
{exportError && (
  <p className="mt-1 text-[12px] text-red-700">{exportError}</p>
)}
```

---

## Part 6：环境安装说明

新建 `docs/report-export-install.md`，内容：

```
# 报告 PDF 导出 —— 环境安装

## 后端依赖

1. 安装 Playwright Python SDK：
   ```
   pip install playwright>=1.40
   ```

2. 下载 Chromium（一次性，约 150MB）：
   ```
   playwright install chromium
   ```

3. Windows 如遇缺 DLL，装 Visual C++ Redistributable。

## 字体

打印使用中文衬线字体（按系统不同）：
- Windows: Source Han Serif SC / Noto Serif CJK SC（若无需自行下载）
- macOS: Songti SC / PingFang 内置
- Linux: fonts-noto-cjk

字体未安装时会回退，效果会差。建议部署机器安装 Source Han Serif SC。

## 前端依赖

   ```
   cd frontend
   npm install @chenglou/pretext
   ```

## 环境变量

`.env`：
   ```
   FRONTEND_URL=http://localhost:5173
   ```

生产环境按实际前端部署地址填。

## 启动

前端：
   ```
   cd frontend && npm run dev
   ```

后端：
   ```
   python -m uvicorn backend.app:app --reload
   ```

然后前端打开 /report 页面，点"导出 PDF"。
```

---

## 验收清单

逐项验证：

1. **依赖安装**：后端 `pip show playwright` 能看到版本；前端 `package.json` 有 `@chenglou/pretext`
2. **打印路由可渲染**：浏览器直接打开 `http://localhost:5173/report/print/1`（替换实际 ID）
   - 能看到四章排版（即使字体回退也应有结构）
   - 没有侧边栏、没有编辑/再生成按钮
   - F12 Elements 能看到 `<div class="report-print-root" data-print-ready="true">`（等 1-2 秒后变 true）
   - 选中任意段落文字能复制
3. **后端接口可用**：`curl -X POST http://localhost:8000/api/report/1/export -H "Authorization: Bearer <token>" -o test.pdf` 得到有效 PDF
4. **前端按钮**：报告页点"导出 PDF" → 按钮变"正在生成 PDF…" → 2-10 秒后浏览器弹出下载 → PDF 文件名是 `{目标岗位}_职业报告_{日期}.pdf`
5. **PDF 质量**：
   - 打开 PDF，文字可选可复制可搜
   - 每章在新页开始
   - 多栏排版正常，文字不串栏
   - 中文字体渲染正确（非方框、非乱码）
   - pullquote 障碍物不被正文压住
6. **错误路径**：
   - 前端故意不登录调 `/export` → 401
   - token 乱填 → 前端收到 401（Playwright 访问 print page 会被重定向到 login，wait_for_selector 超时，后端返回 500；这是已知边界）
7. **不影响现有流程**：
   - `/report` 网页版不变
   - 报告生成（POST /report/generate）不变
   - 成长档案、画像等不受影响

---

## 不要做

- 不要改 `ChapterI.tsx` / `ChapterII.tsx` / `ChapterIII.tsx` / `ChapterIV.tsx`（网页版原件）
- 不要引入除 `@chenglou/pretext` 和 `playwright` 以外的第三方库（**禁止**引入 jsPDF / html2canvas / react-pdf / puppeteer）
- 不要在打印路由里引任何侧边栏、Header、Layout 组件
- 不要在打印页面加交互元素（hover、button、input 都不要——打印不需要）
- 不要用 fixed / sticky 定位（print 媒介会拆分页面，fixed 会重复）
- 不要在 pretext 组件里用 `window.print()`——我们走后端 Playwright

---

## 实现顺序建议（Kimi 自行把控）

1. 先把前端路由骨架 + 后端 Playwright 接口打通（用一个最简陋的 `<div>Hello</div>` 充当打印页，能拿到 PDF 就行）
2. 再写 `fitHeadline` + `flowIntoColumns` 两个 util，单独写个测试页跑通
3. 再一章一章实现 PrintChapterI/II/III/IV
4. 最后对齐按钮 UI + 错误处理

每一步都可以单独验收，别一次写完最后全部调试。
