# Kimi 任务：InterviewPage Results 阶段 — 分数揭晓动画

## 文件位置
`frontend/src/pages/InterviewPage.tsx` — 只改 `phase === 'results'` 分支的 JSX 和样式。

**所有业务逻辑、类型定义、API 调用、状态管理保持不变。**

---

## 设计目标

让用户看到面试结果时有**成绩揭晓的仪式感**——总分从 0 数到实际分数，环形进度条动画填充，逐题得分依次飘入。第一眼就有冲击力。

---

## 改动 1：总分区域 — 环形进度条 + 计数动画

### 当前
```
78              一句话评语...
综合得分
████████░░ (扁平进度条)
```

### 改为
```
    ┌─────────┐
    │  ╭───╮  │
    │  │78 │  │     候选人在技术问题上表现良好...
    │  ╰───╯  │
    │ 综合得分 │
    └─────────┘
```

环形进度条（SVG circle）替代扁平条，数字在环中央从 0 计数到实际分数。

### 具体实现

**新增一个 `AnimatedScore` 组件**，放在 InterviewPage 文件内（不新建文件）：

```tsx
function AnimatedScore({ score, color }: { score: number; color: string }) {
  const [displayed, setDisplayed] = useState(0)
  const radius = 54
  const circumference = 2 * Math.PI * radius
  const progress = (displayed / 100) * circumference

  useEffect(() => {
    let frame: number
    const duration = 1200 // ms
    const start = performance.now()
    const animate = (now: number) => {
      const elapsed = now - start
      const t = Math.min(elapsed / duration, 1)
      // ease-out-quart
      const eased = 1 - Math.pow(1 - t, 4)
      setDisplayed(Math.round(eased * score))
      if (t < 1) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [score])

  return (
    <div className="relative w-[140px] h-[140px] shrink-0">
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        {/* Background circle */}
        <circle
          cx="60" cy="60" r={radius}
          fill="none"
          stroke="currentColor"
          className="text-slate-100"
          strokeWidth="8"
        />
        {/* Progress circle */}
        <motion.circle
          cx="60" cy="60" r={radius}
          fill="none"
          stroke="currentColor"
          className={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 0.05, ease: 'linear' }}
        />
      </svg>
      {/* Score number in center */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-[42px] font-black tabular-nums leading-none ${color}`}>
          {displayed}
        </span>
        <span className="text-[11px] text-slate-400 mt-1">综合得分</span>
      </div>
    </div>
  )
}
```

**颜色逻辑**（复用已有的 `scoreColor` 但改为返回完整类名）：

在 `AnimatedScore` 的父级调用时传入颜色：
```tsx
const ringColor = evaluation.overall_score >= 80
  ? 'text-emerald-500'
  : evaluation.overall_score >= 60
  ? 'text-blue-500'
  : evaluation.overall_score >= 40
  ? 'text-amber-500'
  : 'text-red-500'
```

### Results 顶部区域的新 JSX

替换整个 `{/* Overall score */}` 的 `motion.div`：

```tsx
<motion.div
  initial={{ opacity: 0, scale: 0.95 }}
  animate={{ opacity: 1, scale: 1 }}
  transition={{ duration: 0.5, ease }}
  className="flex items-center gap-8 mb-10"
>
  <AnimatedScore score={evaluation.overall_score} color={ringColor} />
  <div className="flex-1 min-w-0">
    <p className="text-[15px] text-slate-600 leading-relaxed max-w-[420px]">
      {evaluation.overall_comment}
    </p>
  </div>
</motion.div>
```

**删掉**原来的扁平进度条（`w-32 h-1.5 bg-slate-100 rounded-full` 那一坨）。

---

## 改动 2：逐题评分 — stagger 飘入动画

### 当前
所有题目同时出现，没有节奏感。

### 改为
每道题依次飘入，间隔 150ms，从下方 fade + slide 进入。

### 具体改动

在 `QuestionEvalRow` 组件中，改 `motion.div` 的 `transition`：

```tsx
// 原来的
transition={{ delay: 0.05 + index * 0.04, duration: 0.35, ease }}

// 改为（更大的 delay 间隔 + 更远的起始位置）
transition={{ delay: 0.6 + index * 0.15, duration: 0.45, ease }}
```

同时改 `initial`：
```tsx
// 原来的
initial={{ opacity: 0, y: 8 }}

// 改为
initial={{ opacity: 0, y: 20 }}
```

这样效果是：总分环形动画播完（约 1.2s），然后逐题从 delay 0.6s 开始、每题间隔 0.15s 依次飘入。

---

## 改动 3：逐题得分数字也加计数动画

在 `QuestionEvalRow` 组件中，把分数从静态数字改为小型计数动画。

**新增一个简单的 `CountUp` 组件**：

```tsx
function CountUp({ value, delay = 0 }: { value: number; delay?: number }) {
  const [displayed, setDisplayed] = useState(0)

  useEffect(() => {
    const timeout = setTimeout(() => {
      let frame: number
      const duration = 600
      const start = performance.now()
      const animate = (now: number) => {
        const elapsed = now - start
        const t = Math.min(elapsed / duration, 1)
        const eased = 1 - Math.pow(1 - t, 4)
        setDisplayed(Math.round(eased * value))
        if (t < 1) frame = requestAnimationFrame(animate)
      }
      frame = requestAnimationFrame(animate)
      return () => cancelAnimationFrame(frame)
    }, delay)
    return () => clearTimeout(timeout)
  }, [value, delay])

  return <>{displayed}</>
}
```

在 `QuestionEvalRow` 中替换分数显示：

```tsx
// 原来的
<span className={`text-[22px] font-black tabular-nums shrink-0 ${scoreColor(ev.score)}`}>
  {ev.score}
</span>

// 改为
<span className={`text-[22px] font-black tabular-nums shrink-0 ${scoreColor(ev.score)}`}>
  <CountUp value={ev.score} delay={700 + index * 150} />
</span>
```

`delay` 和 stagger 动画同步：卡片 delay 0.6s 飘入 + 0.1s 后数字开始计数。

---

## 改动 4：技能缺口和改进建议区域 — 延迟入场

给技能缺口 + 改进建议的 `motion.div` 加更大的延迟，让它在逐题评分全部显示后再出现：

```tsx
// 原来的
transition={{ delay: 0.25, duration: 0.4, ease }}

// 改为（5 题 × 0.15 间隔 = 0.75s + 基础 0.6s = 约 1.35s 后全部显示，再等 0.3s）
transition={{ delay: 1.6, duration: 0.45, ease }}
```

---

## 改动 5：底部操作按钮 — 最后出现

```tsx
// 原来的
transition={{ delay: 0.4, duration: 0.35 }}

// 改为
transition={{ delay: 2.0, duration: 0.4, ease }}
```

---

## 动画时间线总览

```
0.0s  ───  总分环形 + 数字计数开始（scale 0.95→1 + opacity 0→1）
1.2s  ───  总分计数完成
0.6s  ───  第1题卡片飘入
0.75s ───  第2题卡片飘入
0.90s ───  第3题卡片飘入
1.05s ───  第4题卡片飘入
1.20s ───  第5题卡片飘入
0.7s  ───  第1题分数开始计数（600ms duration）
0.85s ───  第2题分数开始计数
...
1.6s  ───  技能缺口 + 改进建议 fade in
2.0s  ───  底部按钮 fade in
~2.4s ───  全部动画结束
```

总时长约 2.4 秒，不会让用户觉得等太久。

---

## 技术约束

- framer-motion（已安装）用于 motion.div 和 motion.circle
- SVG circle 做环形进度条，不引入任何图表库
- `requestAnimationFrame` 做数字计数，不引入新依赖
- ease 曲线：环形进度用 framer-motion 内置，计数用 ease-out-quart `1 - Math.pow(1 - t, 4)`
- `scoreColor` 函数已存在，复用
- **不改任何业务逻辑**

## 不改的部分

- Setup 阶段 — 不动
- Interviewing 阶段 — 不动
- Evaluating 阶段 — 不动
- 所有类型定义、API 调用、handler 函数 — 不动
- `QuestionEvalRow` 的内容结构（strengths/improvements/suggested_answer）— 不动，只改动画参数

## 禁止

- 不要 bounce/elastic 缓动
- 不要 confetti/粒子效果（不适合这个产品调性）
- 不要改变布局结构（环形进度条替换扁平条，其余布局不变）
- 不要引入新 npm 依赖
- 不要用 CSS @keyframes，全部用 framer-motion + requestAnimationFrame
