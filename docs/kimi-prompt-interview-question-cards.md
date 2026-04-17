# Kimi 任务：InterviewPage 逐题评分卡片升级

## 文件位置
`frontend/src/pages/InterviewPage.tsx` — 只改 `QuestionEvalRow` 组件。

**所有业务逻辑保持不变。AnimatedScore、CountUp 等已有组件不动。**

---

## 当前问题

逐题评分是一堆用虚线分隔的平铺文字，每道题长一模一样，没有视觉层次。用户一眼扫过去分不清哪题好哪题差。

---

## 新设计

每道题变成一张独立卡片，左侧有**分数色条**（高分绿色长、低分红色短），让用户一眼看出强弱分布。

```
┌─────────────────────────────────────────────────────────────┐
│ ██████████████████████████░░░░░░  ← 分数色条（85% 填充）    │
│                                                             │
│  01  技术题 · 网络编程                                  85  │
│  你在基于 Reactor 模型的 C++ 高性能网络库项目中...          │
│                                                             │
│  ✓ 所有权用 shared_ptr 管理                                │
│  ✓ 线程安全靠 EventLoop 保证                               │
│  △ 可以进一步说明关键代码的具体实现                         │
│                                                             │
│  ▸ 参考回答                                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ██████████████████░░░░░░░░░░░░░  ← 分数色条（65% 填充）    │
│                                                             │
│  03  行为题 · 沟通协作                                  65  │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 具体实现

替换整个 `QuestionEvalRow` 组件：

```tsx
function QuestionEvalRow({
  eval: ev,
  question,
  index,
}: {
  eval: PerQuestionEval
  question: Question
  index: number
}) {
  const [showSuggested, setShowSuggested] = useState(false)
  const tc = typeColors[question.type] || { bg: 'bg-slate-50', text: 'text-slate-600' }

  // 分数色条颜色
  const barColor = ev.score >= 80
    ? 'bg-emerald-400'
    : ev.score >= 60
    ? 'bg-blue-400'
    : ev.score >= 40
    ? 'bg-amber-400'
    : 'bg-red-400'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6 + index * 0.15, duration: 0.45, ease }}
      className="rounded-xl border border-slate-200/60 bg-white/50 overflow-hidden"
    >
      {/* 顶部分数色条 */}
      <div className="h-1 bg-slate-100">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${ev.score}%` }}
          transition={{ delay: 0.8 + index * 0.15, duration: 0.6, ease }}
          className={`h-full ${barColor}`}
        />
      </div>

      <div className="p-5">
        {/* Header line */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[12px] font-bold text-slate-300 tabular-nums">
                {String(index + 1).padStart(2, '0')}
              </span>
              <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${tc.bg} ${tc.text}`}>
                {typeLabel(question.type)}
              </span>
              <span className="text-[11px] text-slate-400">
                {question.focus_area}
              </span>
            </div>
            <p className="text-[13px] text-slate-600 leading-relaxed line-clamp-2">
              {question.question}
            </p>
          </div>
          <span className={`text-[28px] font-black tabular-nums shrink-0 leading-none ${scoreColor(ev.score)}`}>
            <CountUp value={ev.score} delay={700 + index * 150} />
          </span>
        </div>

        {/* Strengths & Improvements */}
        {(ev.strengths.length > 0 || ev.improvements.length > 0) && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            {ev.strengths.length > 0 && (
              <div className="space-y-1.5 mb-2">
                {ev.strengths.map((s, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-emerald-500 text-[12px] mt-0.5 shrink-0">✓</span>
                    <p className="text-[13px] text-slate-600 leading-relaxed">{s}</p>
                  </div>
                ))}
              </div>
            )}
            {ev.improvements.length > 0 && (
              <div className="space-y-1.5">
                {ev.improvements.map((s, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-amber-500 text-[12px] mt-0.5 shrink-0">△</span>
                    <p className="text-[13px] text-slate-600 leading-relaxed">{s}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Suggested answer toggle */}
        <button
          onClick={() => setShowSuggested((v) => !v)}
          className="mt-4 flex items-center gap-1 text-[12px] font-semibold text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
        >
          <ChevronRight className={`w-3 h-3 transition-transform ${showSuggested ? 'rotate-90' : ''}`} />
          参考回答
        </button>
        <AnimatePresence>
          {showSuggested && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-2 p-4 rounded-lg bg-slate-50/80 text-[13px] text-slate-600 leading-[1.8]">
                {ev.suggested_answer}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
```

---

## 配套改动

### 卡片容器间距

在 Results 阶段中，逐题评分的容器从无间距改为 `space-y-3`：

找到这段：
```tsx
<div>
  {(evaluation.per_question || []).map((pq, idx) => (
```

把外层 `<div>` 改为 `<div className="space-y-3">`。

原来用 `border-b border-dashed` 做分隔，现在每张是独立卡片，不需要分隔线了。

### "逐题评分" 标题微调

把：
```tsx
<h3 className="text-[13px] font-bold text-slate-400 uppercase tracking-wider mb-4">
  逐题评分
</h3>
```

改为：
```tsx
<h3 className="text-[14px] font-semibold text-slate-700 mb-4">
  逐题评分
</h3>
```

不需要 uppercase tracking-wider，跟上面总分区域的风格保持一致。

---

## 视觉效果

1. **分数色条**：卡片顶部 1px 高的进度条，从左到右动画填充到 `score%`，颜色跟分数挂钩
   - ≥80: emerald（绿）
   - ≥60: blue（蓝）
   - ≥40: amber（橙）
   - <40: red（红）
2. **题型标签**：从纯文字变成带背景色的 pill（复用已有的 `typeColors`）
3. **分数字号加大**：从 22px 增大到 28px，更有冲击力
4. **strengths/improvements**：用 flex + gap 对齐 icon 和文字，不再是纯文本
5. **参考回答**：用 `ChevronRight` 图标替代文字 `▸`，展开时旋转 90°

---

## 动画时间线

```
0.6s + index*0.15  ── 卡片 fade + slide 入场
0.8s + index*0.15  ── 色条从 0 填充到 score%（600ms）
0.7s + index*0.15  ── 分数数字从 0 计数到 score（600ms）
```

三个动画几乎同时进行，视觉上：卡片飘入 → 色条开始填充 + 数字开始跳动。

---

## 技术约束

- framer-motion（已安装）
- lucide-react `ChevronRight`（已 import）
- `typeColors`、`typeLabel`、`scoreColor`、`CountUp` — 全部已存在，直接复用
- 不引入新依赖
- 不改其他阶段的代码

## 禁止

- 不要 bounce/elastic 缓动
- 不要给卡片加 shadow（用 border 就够了）
- 不要改 AnimatedScore 组件
- 不要改业务逻辑
