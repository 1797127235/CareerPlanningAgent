# Kimi 任务：模拟面试 Setup 空态页面重做 + Overdrive 动效

## 文件位置
`frontend/src/pages/InterviewPage.tsx` — 只改 `phase === 'setup'` 分支。

**所有业务逻辑保持不变。**

---

## Part 1：空态布局重做

### 当前问题
首次使用时（无历史记录），表单缩在 520px 窄容器里，80% 空白。

### 新布局

去掉卡片包裹，表单直接裸在页面上，用间距划分层次。内容垂直居中。

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│                                                      │
│  模拟面试                                            │
│  AI 面试官根据你的简历出题，逐题评分                  │
│                                                      │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  后端工程师|                                   │   │  ← 打字机 placeholder
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  [后端工程师] [前端开发] [产品经理] [算法工程师]      │  ← 热门岗位 chips
│                                                      │
│  > 附加 JD（可选）                                   │
│                                                      │
│                                                      │
│  [████████ 开始面试 · 5道题 · 约15分钟 ████████]    │  ← 宽 CTA
│                                                      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 具体改动

#### 1. 容器：统一宽度 + 无历史时垂直居中

找到：
```tsx
className={`px-6 py-8 ${hasHistory ? 'max-w-[960px] mx-auto' : 'max-w-[520px] mx-auto'}`}
```

改为：
```tsx
className={`px-6 ${hasHistory ? 'max-w-[960px] mx-auto py-8' : 'max-w-[640px] mx-auto min-h-full flex flex-col justify-center py-12'}`}
```

#### 2. 标题区：统一结构

把现有的 `{hasHistory ? ... : ...}` 标题条件渲染和单独的 `{!hasHistory && <p>...}` 引导语，替换为统一结构：

```tsx
{/* Title */}
<div className={hasHistory ? 'flex items-center justify-between mb-6' : 'mb-12'}>
  <div>
    <h1 className={`font-bold text-slate-900 tracking-tight ${hasHistory ? 'text-[28px]' : 'text-[36px]'}`}>
      模拟面试
    </h1>
    {hasHistory ? (
      <span className="text-[13px] text-slate-400 tabular-nums">
        共 {history!.length} 次 · 均分 {avgScore}
      </span>
    ) : (
      <p className="text-[15px] text-slate-400 mt-2">
        AI 面试官根据你的简历出题，逐题评分
      </p>
    )}
  </div>
</div>
```

无历史时标题更大（36px），下方间距更大（mb-12），给页面呼吸感。

#### 3. 输入区：无历史时去掉卡片包裹

把 `{/* Start interview block */}` 那个 `<div className="rounded-xl border ...">` 改为条件样式：

```tsx
<div className={hasHistory ? 'rounded-xl border border-slate-200/60 bg-white/50 p-6' : ''}>
```

无历史时没有边框、没有背景、没有 padding——表单直接裸露在页面上。

#### 4. 输入框加大

无历史时输入框更大更突出：

```tsx
<input
  type="text"
  value={targetRole}
  onChange={(e) => setTargetRole(e.target.value)}
  placeholder=""
  className={`w-full rounded-lg border border-slate-200/60 bg-white/50 text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300/60 transition-all ${
    hasHistory ? 'px-4 py-2.5 text-[14px]' : 'px-5 py-4 text-[16px]'
  }`}
/>
```

注意 `placeholder=""` — 空的，因为我们用打字机效果替代（见 Part 2）。

#### 5. 热门岗位 chips（仅无历史时）

在输入框下方，`{/* JD 折叠区 */}` 上方，加热门岗位：

```tsx
{!hasHistory && (
  <div className="flex flex-wrap gap-2 mt-4">
    {['后端工程师', '前端开发', '产品经理', '算法工程师', '数据分析', '测试开发'].map((role) => (
      <button
        key={role}
        onClick={() => setTargetRole(role)}
        className={`px-3 py-1.5 rounded-lg text-[13px] font-medium border transition-all duration-200 cursor-pointer ${
          targetRole === role
            ? 'border-blue-400 bg-blue-50 text-blue-700'
            : 'border-slate-200/60 bg-white/80 text-slate-500 hover:border-blue-300 hover:bg-blue-50/50 hover:text-slate-700'
        }`}
      >
        {role}
      </button>
    ))}
  </div>
)}
```

#### 6. CTA 按钮：无历史时全宽 + 包含预期信息

把 `<div className="flex justify-end mt-5">` 和按钮改为：

```tsx
<div className={`${hasHistory ? 'flex justify-end mt-5' : 'mt-10'}`}>
  <button
    onClick={() => startMutation.mutate({ target_role: targetRole, jd_text: jdText })}
    disabled={!targetRole.trim() || startMutation.isPending}
    className={`rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-none active:scale-[0.98] transition-all duration-200 disabled:opacity-30 disabled:hover:translate-y-0 disabled:hover:shadow-none disabled:cursor-not-allowed cursor-pointer ${
      hasHistory ? 'px-6 py-2.5 text-[14px]' : 'w-full py-4 text-[15px]'
    }`}
  >
    {startMutation.isPending ? '正在生成题目...' : hasHistory ? '开始面试' : '开始面试 · 5道题 · 约15分钟'}
  </button>
</div>
```

无历史时：按钮全宽、更高（py-4）、文字包含"5道题 · 约15分钟"。

---

## Part 2：打字机 Placeholder

### 效果
输入框 placeholder 循环展示不同岗位名，像打字机一样逐字出现、停留、擦除、换下一个。用户点击输入框或开始输入时停止动画。

### 实现

新增一个 hook `useTypingPlaceholder`，放在文件内：

```tsx
function useTypingPlaceholder(
  items: string[],
  { typeSpeed = 100, eraseSpeed = 50, pauseMs = 2000 } = {}
) {
  const [text, setText] = useState('')
  const [isActive, setIsActive] = useState(true)

  useEffect(() => {
    if (!isActive || items.length === 0) return

    let itemIndex = 0
    let charIndex = 0
    let isErasing = false
    let timer: ReturnType<typeof setTimeout>

    const tick = () => {
      const current = items[itemIndex]

      if (!isErasing) {
        charIndex++
        setText(current.slice(0, charIndex))
        if (charIndex >= current.length) {
          isErasing = true
          timer = setTimeout(tick, pauseMs)
          return
        }
        timer = setTimeout(tick, typeSpeed)
      } else {
        charIndex--
        setText(current.slice(0, charIndex))
        if (charIndex <= 0) {
          isErasing = false
          itemIndex = (itemIndex + 1) % items.length
          timer = setTimeout(tick, typeSpeed * 2)
          return
        }
        timer = setTimeout(tick, eraseSpeed)
      }
    }

    timer = setTimeout(tick, 500)
    return () => clearTimeout(timer)
  }, [isActive, items, typeSpeed, eraseSpeed, pauseMs])

  return { text, stop: () => setIsActive(false), restart: () => setIsActive(true) }
}
```

### 在输入框中使用

在 Setup 阶段的组件内：

```tsx
const typingPlaceholder = useTypingPlaceholder(
  ['后端工程师', '前端开发工程师', '产品经理', '算法工程师', 'Java 开发', '数据分析师'],
  { typeSpeed: 80, eraseSpeed: 40, pauseMs: 1500 }
)
```

输入框改为相对定位容器 + 假 placeholder overlay：

```tsx
<div className="relative">
  <input
    type="text"
    value={targetRole}
    onChange={(e) => setTargetRole(e.target.value)}
    onFocus={() => typingPlaceholder.stop()}
    onBlur={() => { if (!targetRole) typingPlaceholder.restart() }}
    className={`w-full rounded-lg border border-slate-200/60 bg-white/50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300/60 transition-all ${
      hasHistory ? 'px-4 py-2.5 text-[14px]' : 'px-5 py-4 text-[16px]'
    }`}
  />
  {/* Typing placeholder overlay */}
  {!targetRole && !hasHistory && (
    <div className="absolute inset-0 flex items-center pointer-events-none">
      <span className={`text-slate-300 ${hasHistory ? 'px-4 text-[14px]' : 'px-5 text-[16px]'}`}>
        {typingPlaceholder.text}
        <span className="inline-block w-px h-[1.1em] bg-slate-300 ml-0.5 animate-pulse align-middle" />
      </span>
    </div>
  )}
</div>
```

关键细节：
- `pointer-events-none` 让 overlay 不阻碍点击
- 光标用一个 `animate-pulse` 的竖线模拟
- 用户输入后（`targetRole` 不为空）overlay 消失
- 用户清空输入框且失焦后 `restart()` 恢复动画
- 有历史记录时不显示打字机（有 recentRoles chips）

---

## Part 3：CTA 按钮变形动画

### 效果
点击"开始面试"后，按钮不是简单变灰——而是文字过渡为"正在生成题目..."，按钮出现内部进度条动画。

### 实现

这个效果通过 `startMutation.isPending` 状态切换实现，不需要额外 state。

把 CTA 按钮改为：

```tsx
<button
  onClick={() => startMutation.mutate({ target_role: targetRole, jd_text: jdText })}
  disabled={!targetRole.trim() || startMutation.isPending}
  className={`relative overflow-hidden rounded-lg text-white font-bold transition-all duration-300 cursor-pointer ${
    startMutation.isPending
      ? 'bg-blue-700 cursor-wait'
      : 'bg-blue-600 hover:bg-blue-700 hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-none active:scale-[0.98]'
  } disabled:opacity-30 disabled:hover:translate-y-0 disabled:hover:shadow-none disabled:cursor-not-allowed ${
    hasHistory ? 'px-6 py-2.5 text-[14px]' : 'w-full py-4 text-[15px]'
  }`}
>
  {/* Progress bar inside button */}
  {startMutation.isPending && (
    <motion.div
      initial={{ width: '0%' }}
      animate={{ width: '100%' }}
      transition={{ duration: 15, ease: 'linear' }}
      className="absolute inset-y-0 left-0 bg-blue-500/30"
    />
  )}
  <span className="relative z-10">
    {startMutation.isPending
      ? '正在生成题目...'
      : hasHistory
      ? '开始面试'
      : '开始面试 · 5道题 · 约15分钟'}
  </span>
</button>
```

效果：按钮背景内有一个半透明进度条从左到右慢慢填充（15 秒线性），给用户"在处理中"的反馈。如果 API 在 15 秒前返回，按钮直接消失进入 interviewing。

---

## 技术约束

- framer-motion（已安装）
- 不引入新依赖
- 打字机效果用原生 setTimeout，不用第三方库
- 所有动效用 transform + opacity（GPU 加速）
- `prefers-reduced-motion` 时打字机静态显示第一个岗位名

## 不改的部分

- 有历史记录时的渲染（recentRoles chips、历史卡片网格）— 不动
- Interviewing / Evaluating / Results 阶段 — 不动
- 所有业务逻辑 — 不动

## 禁止

- 不要大图标/插画
- 不要 gradient text
- 不要 bounce/elastic 动画
- 不要引入新 npm 依赖
