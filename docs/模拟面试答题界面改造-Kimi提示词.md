# 模拟面试答题界面改造 — Kimi 执行提示词

## 你的任务

改造文件 `frontend/src/pages/InterviewPage.tsx` 中答题阶段的 UI，将原来的「大空白输入框」布局改造为**沉浸式对话气泡布局**。

**原则：只改 UI，不改任何逻辑、state、mutation、hook。**

---

## 第一步：修改 lucide-react import

找到文件顶部的 import 行：

```tsx
import {
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  Loader2,
  CheckCircle2,
  Circle,
  RotateCcw,
  Mic,
  Trash2,
  Cpu,
  Monitor,
  Server,
  Calculator,
  BarChart3,
  ShieldCheck,
} from 'lucide-react'
```

在末尾加一个 `Bot`：

```tsx
import {
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  Loader2,
  CheckCircle2,
  Circle,
  RotateCcw,
  Mic,
  Trash2,
  Cpu,
  Monitor,
  Server,
  Calculator,
  BarChart3,
  ShieldCheck,
  Bot,
} from 'lucide-react'
```

---

## 第二步：替换答题阶段 return block

找到文件中的注释行：

```
/* ── Phase: Interviewing ── */
```

将从这行开始、到下一个 `/* ── Phase:` 注释之前的整个 `if` block（约第 1129-1347 行）**全部替换**为以下代码：

```tsx
/* ── Phase: Interviewing ── */
if (phase === 'interviewing' && questions.length > 0) {
  const q = questions[currentIndex]
  const tc = typeColors[q.type] || { bg: 'bg-slate-50', text: 'text-slate-600' }
  const pct = ((currentIndex + 1) / questions.length) * 100
  const isLast = currentIndex === questions.length - 1

  return (
    <div className="flex flex-col h-full w-full bg-slate-50/50">

      {/* ── 顶部栏 ── */}
      <div className="shrink-0 bg-white/80 backdrop-blur-md border-b border-slate-100/60 z-10">
        {/* 进度条 */}
        <div className="w-full h-[2px] bg-slate-100">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.4, ease }}
            className="h-full bg-gradient-to-r from-blue-400 to-blue-600"
          />
        </div>
        {/* 导航行 */}
        <div className="px-5 h-12 flex items-center justify-between">
          <button
            onClick={handleRestart}
            className="flex items-center gap-1 text-[13px] text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
            返回
          </button>

          {/* 点状进度指示器 */}
          <div className="flex items-center gap-1.5">
            {questions.map((_, i) => (
              <div
                key={i}
                className={`rounded-full transition-all duration-300 ${
                  i < currentIndex
                    ? 'w-1.5 h-1.5 bg-blue-400'
                    : i === currentIndex
                    ? 'w-2 h-2 bg-blue-600 ring-2 ring-blue-200'
                    : 'w-1.5 h-1.5 bg-slate-200'
                }`}
              />
            ))}
          </div>

          <span className={`text-[11px] font-medium px-2.5 py-1 rounded-full ${tc.bg} ${tc.text}`}>
            {typeLabel(q.type)}
          </span>
        </div>
      </div>

      {/* ── 对话流区域 ── */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[680px] mx-auto px-4 py-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.25, ease }}
              className="flex flex-col gap-5"
            >
              {/* 面试官气泡：主题目 */}
              <InterviewerBubble>
                <p className="text-[15px] font-medium text-slate-800 leading-[1.8]">
                  {q.question}
                </p>
                <div className="mt-2.5 flex items-center gap-2 flex-wrap">
                  <span className="text-[11px] text-slate-400">考察</span>
                  <span className="text-[12px] text-slate-600">{q.focus_area}</span>
                  <span className="text-[11px] text-slate-300">·</span>
                  <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                    q.difficulty === 'easy'
                      ? 'bg-emerald-50 text-emerald-600'
                      : q.difficulty === 'medium'
                      ? 'bg-amber-50 text-amber-600'
                      : 'bg-red-50 text-red-500'
                  }`}>
                    {q.difficulty === 'easy' ? '基础' : q.difficulty === 'medium' ? '进阶' : '专家'}
                  </span>
                </div>
              </InterviewerBubble>

              {/* 用户主回答气泡 */}
              <UserAnswerBubble
                value={currentAnswer}
                onChange={setCurrentAnswer}
                onBlur={handleMainAnswerBlur}
                placeholder="在这里写下你的回答..."
                minHint={30}
              />

              {/* 追问对话流 */}
              {currentFollowUps.map((turn, idx) => (
                <motion.div
                  key={`followup-${idx}`}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, ease }}
                  className="flex flex-col gap-5"
                >
                  {/* 面试官追问气泡 */}
                  <InterviewerBubble isFollowUp>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                        追问 {idx + 1}
                      </span>
                    </div>
                    <p className="text-[14px] font-medium text-slate-800 leading-[1.8]">
                      {turn.question}
                    </p>
                  </InterviewerBubble>

                  {/* 用户追问回答气泡 */}
                  <UserAnswerBubble
                    value={turn.answer}
                    onChange={(val) => {
                      const next = currentFollowUps.map((item, turnIndex) =>
                        turnIndex === idx ? { ...item, answer: val } : item
                      )
                      setCurrentFollowUps(next)
                    }}
                    onBlur={() => {
                      if (idx === currentFollowUps.length - 1 && turn.answer.trim().length >= 10) {
                        handleMainAnswerBlur()
                      }
                    }}
                    placeholder="补充这轮追问的回答..."
                    isFollowUp
                    minHint={10}
                  />
                </motion.div>
              ))}

              {/* AI 思考中气泡 */}
              {followUpMutation.isPending && <ThinkingBubble />}

              {/* 追问完毕提示 */}
              {followUpInfo && !followUpMutation.isPending && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex justify-center"
                >
                  <span className="text-[12px] text-slate-400 bg-white px-3 py-1.5 rounded-full border border-slate-100">
                    {followUpInfo}
                  </span>
                </motion.div>
              )}

              {/* 追问错误提示 */}
              {followUpError && (
                <p className="text-[12px] text-red-500 text-center">{followUpError}</p>
              )}

            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* ── 底部操作栏 ── */}
      <div className="shrink-0 bg-white/80 backdrop-blur-md border-t border-slate-100/60 px-5 h-16 flex items-center justify-between gap-4 z-10">
        {/* 语音输入 */}
        {isSupported && (
          <button
            onClick={isListening ? stop : start}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-[13px] font-medium transition-all cursor-pointer ${
              isListening
                ? 'bg-red-50 text-red-600 border border-red-200'
                : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100/60 border border-transparent'
            }`}
          >
            <Mic className={`w-4 h-4 ${isListening ? 'animate-pulse' : ''}`} />
            {isListening ? '停止录音' : '语音输入'}
          </button>
        )}
        {!isSupported && <div />}

        {/* 导航按钮 */}
        <div className="flex items-center gap-3">
          <button
            onClick={handlePrev}
            disabled={currentIndex === 0}
            className="flex items-center gap-1 px-3 py-2 text-[13px] font-medium text-slate-400 hover:text-slate-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
            上一题
          </button>

          {isLast ? (
            <button
              onClick={handleSubmit}
              disabled={submitMutation.isPending}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-white text-[13px] font-semibold hover:from-emerald-600 hover:to-emerald-700 active:scale-[0.98] transition-all cursor-pointer shadow-sm shadow-emerald-500/25 disabled:opacity-60 disabled:cursor-wait"
            >
              提交全部答案
              <CheckCircle2 className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-blue-600 text-white text-[13px] font-semibold hover:bg-blue-700 active:scale-[0.98] transition-all cursor-pointer shadow-sm shadow-blue-500/20"
            >
              下一题
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* 提交错误提示 */}
      {submitError && (
        <div className="shrink-0 px-5 pb-3 text-center">
          <p className="text-[12px] text-red-500">{submitError}</p>
        </div>
      )}
    </div>
  )
}
```

---

## 第三步：在文件末尾追加三个子组件

在文件最末尾（`QuestionEvalRow` 函数结束的 `}` 之后）追加以下三个组件：

### 组件一：InterviewerBubble

```tsx
/* ── Sub-component: InterviewerBubble ── */

function InterviewerBubble({
  children,
  isFollowUp = false,
}: {
  children: React.ReactNode
  isFollowUp?: boolean
}) {
  return (
    <div className="flex items-start gap-3">
      <div className={`shrink-0 w-9 h-9 rounded-full flex items-center justify-center shadow-sm ${
        isFollowUp ? 'bg-amber-700' : 'bg-slate-800'
      }`}>
        <Bot className="w-[18px] h-[18px] text-white" />
      </div>
      <div className={`flex-1 rounded-2xl rounded-tl-sm px-4 py-3.5 shadow-sm border ${
        isFollowUp
          ? 'bg-amber-50 border-amber-100/80'
          : 'bg-white border-slate-100'
      }`}>
        {children}
      </div>
    </div>
  )
}
```

### 组件二：UserAnswerBubble

```tsx
/* ── Sub-component: UserAnswerBubble ── */

function UserAnswerBubble({
  value,
  onChange,
  onBlur,
  placeholder,
  isFollowUp = false,
  minHint = 30,
}: {
  value: string
  onChange: (val: string) => void
  onBlur?: () => void
  placeholder: string
  isFollowUp?: boolean
  minHint?: number
}) {
  const len = value.length
  const lenColor =
    len === 0 ? 'text-slate-300'
    : len < minHint ? 'text-amber-500'
    : len <= 300 ? 'text-emerald-500'
    : 'text-slate-400'

  const taRef = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${ta.scrollHeight}px`
  }, [value])

  return (
    <div className="flex items-start gap-3 flex-row-reverse">
      <div className={`shrink-0 w-9 h-9 rounded-full flex items-center justify-center shadow-sm text-white text-[12px] font-bold ${
        isFollowUp ? 'bg-purple-500' : 'bg-blue-600'
      }`}>
        你
      </div>
      <div className={`flex-1 rounded-2xl rounded-tr-sm shadow-sm border overflow-hidden ${
        isFollowUp
          ? 'bg-purple-50 border-purple-100/80'
          : 'bg-blue-50 border-blue-100/80'
      }`}>
        <textarea
          ref={taRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          placeholder={placeholder}
          rows={isFollowUp ? 2 : 4}
          className="w-full px-4 py-3.5 bg-transparent text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none resize-none leading-[1.8]"
          style={{ minHeight: isFollowUp ? '72px' : '120px', maxHeight: '320px' }}
        />
        <div className="px-4 pb-2.5 flex justify-end">
          <span className={`text-[11px] tabular-nums transition-colors ${lenColor}`}>
            {len} 字{len < minHint && len > 0 ? `（建议至少 ${minHint} 字）` : ''}
          </span>
        </div>
      </div>
    </div>
  )
}
```

### 组件三：ThinkingBubble

```tsx
/* ── Sub-component: ThinkingBubble ── */

function ThinkingBubble() {
  return (
    <div className="flex items-start gap-3">
      <div className="shrink-0 w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center shadow-sm">
        <Bot className="w-[18px] h-[18px] text-white" />
      </div>
      <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full bg-slate-300"
              animate={{ y: [0, -5, 0] }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                delay: i * 0.15,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
```

---

## 执行检查清单

完成后逐项确认：

- [ ] `Bot` 已加入顶部 lucide-react import
- [ ] 原来的 `phase === 'interviewing'` return block 已被完整替换
- [ ] 文件末尾新增了 `InterviewerBubble`、`UserAnswerBubble`、`ThinkingBubble` 三个组件
- [ ] 所有原有的 state、handler、hook 名称未被改动
- [ ] TypeScript 无报错（`useRef<HTMLTextAreaElement>`、`React.ReactNode` 类型正确）
- [ ] 页面能正常启动，答题界面显示为对话气泡形式
