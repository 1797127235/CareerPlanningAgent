# Kimi 任务：重写 InterviewPage Setup 阶段 + 添加语音输入

## 文件位置
`frontend/src/pages/InterviewPage.tsx` — 只改 Setup 阶段（`phase === 'setup'` 分支）的 JSX 和样式 + Interviewing 阶段添加语音输入按钮。

**所有业务逻辑（状态机、API 调用、useMutation、handleNext/handlePrev/handleSubmit/handleRestart/handleLoadHistory）保持不变。**

---

## 设计方向：训练日志

这是一个**日常刷题练手**的工具。用户反复回到这个页面，像打开训练日志一样查看练习记录和进步，然后进入下一场面试。

核心体验：**仪式感** — 每次开始面试不是随便点个按钮，而是像进入考场前的安静切换。

---

## Part 1: Setup 阶段重设计

### 当前问题
1. 无历史时是 520px 窄居中表单，空旷
2. 有历史时左右分栏但右侧只是简单列表，信息量少
3. 没有训练统计（总次数、均分），用户看不到进步
4. 每次都要手动输入岗位名，重复练习同一岗位很烦
5. JD textarea 默认展开占空间，但日常练习很少用

### 新布局

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  模拟面试                                  共 23 次 · 均分 71    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                                                         │    │
│  │  最近练过                                               │    │
│  │  [后端工程师] [产品经理] [算法工程师]                     │    │
│  │                                                         │    │
│  │  ────────────────── 或 ──────────────────               │    │
│  │                                                         │    │
│  │  输入新岗位  ________________________________           │    │
│  │                                                         │    │
│  │  ▸ 附加 JD（可选，让题目更有针对性）                     │    │
│  │                                                         │    │
│  │                                    [ 开始面试 ]         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ─────────────────────────────────────────────────────────────── │
│                                                                  │
│  练习记录                                                        │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ 后端工程师    │ │ 后端工程师    │ │ 产品经理      │            │
│  │ 03/15        │ │ 03/12        │ │ 03/10        │            │
│  │              │ │              │ │              │            │
│  │     82       │ │     74       │ │     65       │            │
│  │ 表现不错...  │ │ 基础扎实...  │ │ 需要加强...  │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
│                                                                  │
│  [查看更多]                                                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 具体实现

#### 页面标题行

```
模拟面试                                  共 23 次 · 均分 71
```

- 左侧：`text-[28px] font-bold text-slate-900 tracking-tight`（不要 36px 那么大）
- 右侧：统计文字 `text-[13px] text-slate-400 tabular-nums`
- 统计数据从 `history` 数组计算：总次数 = `history.length`，均分 = 已完成的平均 score
- `flex items-center justify-between`
- 无历史时不显示右侧统计

#### 开始面试区块

整体包在一个区块里：`rounded-xl border border-slate-200/60 bg-white/50 p-6`

**快速启动标签（最近练过）：**
- 从 `history` 中提取不重复的 `target_role`，取最近 5 个
- 每个渲染为可点击标签：
  ```
  px-3 py-1.5 rounded-lg text-[13px] font-medium
  bg-white border border-slate-200/60 text-slate-700
  hover:border-blue-300 hover:bg-blue-50/50 transition-all cursor-pointer
  ```
- 点击标签：`setTargetRole(role)`，标签变为选中态（`border-blue-400 bg-blue-50 text-blue-700`）
- 有快速标签时，标签下方显示分隔线 + "或" 文字：
  ```html
  <div class="flex items-center gap-3 my-4">
    <div class="flex-1 h-px bg-slate-200/60"></div>
    <span class="text-[12px] text-slate-400">或</span>
    <div class="flex-1 h-px bg-slate-200/60"></div>
  </div>
  ```
- 无历史时不显示快速标签区域和分隔线

**岗位输入框：**
- `w-full px-4 py-2.5 rounded-lg border border-slate-200/60 bg-white/50 text-[14px]`
- placeholder: `"输入目标岗位，如 后端工程师"`
- 和现有逻辑一样绑定 `targetRole` / `setTargetRole`
- 如果用户点了快速标签，这个输入框显示选中的岗位名（双向绑定）

**JD 折叠区：**
- 默认折叠，只显示一行：
  ```html
  <button class="text-[13px] text-slate-400 hover:text-slate-600 transition-colors">
    ▸ 附加 JD（可选，让题目更有针对性）
  </button>
  ```
- 点击展开 textarea（用 `useState` 控制 `showJd`）
- 展开后 textarea：`w-full mt-3 px-4 py-3 rounded-lg border border-slate-200/60 bg-white/50 text-[14px] resize-none`，`rows={3}`
- 绑定现有的 `jdText` / `setJdText`

**开始按钮：**
- 放在区块右下角：`flex justify-end mt-5`
- 按钮样式：`px-6 py-2.5 rounded-lg bg-blue-600 text-white text-[14px] font-bold hover:bg-blue-700 active:scale-[0.98] transition-all cursor-pointer`
- disabled 条件不变：`!targetRole.trim() || startMutation.isPending`
- loading 文字不变：`"正在生成题目..."`

**错误提示：** 保留现有 `startMutation.isError` 的错误文字。

#### 练习记录区域

标题行：
```
练习记录                                      
```
- `text-[15px] font-semibold text-slate-700 mb-4`
- 在开始面试区块下方，间距 `mt-8`

**历史卡片网格：**
- `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3`
- 默认显示最近 9 条，超过 9 条显示"查看更多"按钮
- "查看更多"展开剩余所有（`useState` 控制 `showAllHistory`）

**单张历史卡片：**
```
┌──────────────────────┐
│ 后端工程师            │
│ 03/15                │
│                      │
│          82          │
│                      │
│ 总体表现不错...       │
└──────────────────────┘
```

- 容器：`rounded-lg border border-slate-200/60 bg-white/50 p-4 hover:bg-white/70 hover:border-slate-300/60 transition-all cursor-pointer`
- 点击调用现有的 `handleLoadHistory(item.id)`
- 岗位名：`text-[14px] font-semibold text-slate-700 truncate`
- 日期：`text-[12px] text-slate-400 mt-0.5`
- 分数：居中大号 `text-[28px] font-black tabular-nums mt-3 mb-2` + `scoreColor(item.score)`
- 未完成的不显示分数，显示标签：`text-[12px] text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full font-medium`
- 评语摘要：**当前 API 不返回评语摘要，此行暂时不显示**。如果后端 `/interview/history` 以后加了 `summary` 字段再补上。暂时卡片就是：岗位名 + 日期 + 分数。

#### 首次使用（无历史记录）

- 不显示统计行
- 不显示快速启动标签和"或"分隔线
- 不显示练习记录区域
- 开始面试区块居中，`max-w-[520px] mx-auto`
- 区块上方加一句引导语：`text-[14px] text-slate-400 mb-6` — "选一个目标岗位，开始你的第一场模拟面试"

#### 整体容器

- `max-w-[960px] mx-auto px-6 py-8`
- 不要 `items-center`（不居中，左对齐）
- 入场动画：整体 fade in `opacity 0→1, y 8→0, duration 0.3s`，只一次，不要 stagger

---

## Part 2: Interviewing 阶段添加语音输入

### 功能

在答题 textarea 旁边加一个麦克风按钮，用户可以语音输入答案，语音转文字后追加到 textarea。

### 实现

使用浏览器原生 `webkitSpeechRecognition`（Chrome）或 `SpeechRecognition` API。

**新增一个 hook `useSpeechRecognition`：**

```typescript
function useSpeechRecognition(onResult: (text: string) => void) {
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  
  const isSupported = typeof window !== 'undefined' && 
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  const start = useCallback(() => {
    if (!isSupported) return
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SR()
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = false
    
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map(r => r[0].transcript)
        .join('')
      onResult(transcript)
    }
    
    recognition.onend = () => setIsListening(false)
    recognition.onerror = () => setIsListening(false)
    
    recognitionRef.current = recognition
    recognition.start()
    setIsListening(true)
  }, [isSupported, onResult])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    setIsListening(false)
  }, [])

  return { isListening, isSupported, start, stop }
}
```

**注意**：需要在文件顶部加 `useRef, useCallback` 的 import。

**TypeScript 类型声明**：在 hook 上方加：

```typescript
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}
```

**在 Interviewing 阶段使用：**

在 textarea 下方加一个麦克风按钮：

```tsx
const { isListening, isSupported, start, stop } = useSpeechRecognition(
  useCallback((text: string) => {
    setCurrentAnswer(prev => prev + text)
  }, [])
)
```

在 textarea 和字数统计之间，加按钮：

```tsx
<div className="flex items-center justify-between mt-3">
  {isSupported && (
    <button
      onClick={isListening ? stop : start}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium transition-all cursor-pointer ${
        isListening
          ? 'bg-red-50 text-red-600 border border-red-200'
          : 'bg-slate-50 text-slate-500 border border-slate-200/60 hover:bg-slate-100'
      }`}
    >
      <Mic className={`w-3.5 h-3.5 ${isListening ? 'animate-pulse' : ''}`} />
      {isListening ? '停止录音' : '语音输入'}
    </button>
  )}
  <p className="text-[12px] text-slate-400">
    {currentAnswer.length} 字
  </p>
</div>
```

需要在文件顶部 import 里加 `Mic`：
```diff
  import {
    ArrowLeft,
    ChevronRight,
    ChevronLeft,
    Loader2,
    CheckCircle2,
    Circle,
    RotateCcw,
+   Mic,
  } from 'lucide-react'
```

还需要加 `useRef, useCallback`：
```diff
- import { useState, useEffect } from 'react'
+ import { useState, useEffect, useRef, useCallback } from 'react'
```

### 语音输入 UI 细节

- 不支持语音时（Firefox 等）：整个按钮不渲染（`isSupported` 为 false）
- 录音中：按钮红色背景 + Mic 图标 pulse 动画 + "停止录音"
- 未录音：按钮灰色背景 + "语音输入"
- 录音结果追加到 textarea 现有内容后面（不覆盖）
- `continuous: true` 让用户可以持续说话

---

## 技术约束

- framer-motion（已安装），ease `[0.23, 1, 0.32, 1]`
- lucide-react 图标（已安装）
- rawFetch from '@/api/client'
- @tanstack/react-query
- Tailwind v4，glass 类可用
- **所有业务逻辑保持不变**：状态机 4 阶段、API 调用、所有 handler 函数原封不动
- 不引入新依赖
- 语音识别用浏览器原生 API，不引入第三方库

## 不改的部分

- Interviewing 阶段的题目展示、导航按钮、进度条 — 不动（除了加语音输入按钮）
- Evaluating 阶段 — 不动
- Results 阶段 — 不动
- 所有 TypeScript 类型定义 — 不动
- 所有 useMutation / useQuery — 不动

## 禁止

- 不要居中大图标 + 标题 + 副标题的 AI slop 布局
- 不要 gradient 背景的圆角图标
- 不要 glassmorphism 堆叠
- 不要 gradient text
- 不要 bounce/elastic 动画
- 不要引入新 npm 依赖
