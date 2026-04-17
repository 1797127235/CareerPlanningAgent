# Kimi 任务：模拟面试 Setup 空态页面优化

## 文件位置
`frontend/src/pages/InterviewPage.tsx` — 只改 `phase === 'setup'` 且 `!hasHistory` 时的渲染。

**所有业务逻辑保持不变。有历史记录时的渲染不动。**

---

## 当前问题

首次使用时页面 80% 空白：一个 520px 窄容器里放了标题 + 引导语 + 一个输入框 + JD 折叠 + 按钮。用户不知道接下来会发生什么，没有预期，没有动力。

---

## 新设计：左右分栏（和有历史时一致的宽度）

首次使用时也用 `max-w-[960px]`，左侧放输入区，右侧放**面试流程预览 + 热门岗位**。

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  模拟面试                                                    │
│  AI 面试官根据你的简历出题，逐题评分                          │
│                                                              │
│  ┌─ 输入区 ──────────────┐   ┌─ 面试预览 ───────────────┐  │
│  │                        │   │                           │  │
│  │  目标岗位 *            │   │  面试包含                  │  │
│  │  ___________________   │   │                           │  │
│  │                        │   │  5 道题                    │  │
│  │  > 附加 JD（可选）     │   │  2 技术 + 2 行为 + 1 场景  │  │
│  │                        │   │  约 15-20 分钟             │  │
│  │        [开始面试]      │   │                           │  │
│  └────────────────────────┘   │  ─────────────────────── │  │
│                                │                           │  │
│                                │  热门岗位                  │  │
│                                │                           │  │
│                                │  [后端工程师] [前端开发]   │  │
│                                │  [产品经理] [算法工程师]   │  │
│                                │  [数据分析] [测试开发]     │  │
│                                │                           │  │
│                                └───────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 具体改动

### 1. 容器宽度：首次使用也用宽布局

找到这行：
```tsx
className={`px-6 py-8 ${hasHistory ? 'max-w-[960px] mx-auto' : 'max-w-[520px] mx-auto'}`}
```

改为：
```tsx
className="px-6 py-8 max-w-[960px] mx-auto"
```

### 2. 首次使用的标题和引导语

把现有的：
```tsx
{!hasHistory && (
  <>
    <h1 className="text-[28px] font-bold text-slate-900 tracking-tight mb-2">
      模拟面试
    </h1>
    <p className="text-[14px] text-slate-400 mb-6">
      选一个目标岗位，开始你的第一场模拟面试
    </p>
  </>
)}
```

改为（注意这个标题区域在 hasHistory 和 !hasHistory 两种情况下都要有，所以把整个 title 条件渲染重构）：

```tsx
{/* Title — always shown */}
<div className="mb-6">
  <h1 className="text-[28px] font-bold text-slate-900 tracking-tight">模拟面试</h1>
  {hasHistory ? (
    <span className="text-[13px] text-slate-400 tabular-nums">
      共 {history!.length} 次 · 均分 {avgScore}
    </span>
  ) : (
    <p className="text-[14px] text-slate-400 mt-1">
      AI 面试官根据你的简历出题，逐题评分
    </p>
  )}
</div>
```

这样标题行变成统一的，有历史时显示统计，无历史时显示引导语。原来的 `{hasHistory ? ... : ...}` 那段 title 条件渲染整个替换掉。

### 3. 首次使用时：输入区 + 右侧预览 左右分栏

把 `{/* Start interview block */}` 那整个 `<div className="rounded-xl border ...">` 包在一个 flex 容器里：

**当 `!hasHistory` 时**，在输入区块后面加右侧面板：

```tsx
{/* Start interview block — with side panel for first-time users */}
<div className={`${!hasHistory ? 'flex flex-col md:flex-row gap-6' : ''}`}>
  {/* Left: input area */}
  <div className={`rounded-xl border border-slate-200/60 bg-white/50 p-6 ${!hasHistory ? 'flex-1' : ''}`}>
    {/* ... 原有的输入区内容不变 ... */}
  </div>

  {/* Right: interview preview — only for first-time users */}
  {!hasHistory && (
    <div className="w-full md:w-[320px] shrink-0 space-y-6">
      {/* Interview format preview */}
      <div className="rounded-xl border border-slate-200/60 bg-white/50 p-5">
        <h3 className="text-[13px] font-semibold text-slate-700 mb-4">面试包含</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[13px] text-slate-600">题目数量</span>
            <span className="text-[13px] font-semibold text-slate-800">5 道</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[13px] text-slate-600">题目类型</span>
            <span className="text-[13px] font-semibold text-slate-800">技术 + 行为 + 场景</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[13px] text-slate-600">预计时间</span>
            <span className="text-[13px] font-semibold text-slate-800">15-20 分钟</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[13px] text-slate-600">评估方式</span>
            <span className="text-[13px] font-semibold text-slate-800">逐题 AI 评分</span>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100">
          <p className="text-[12px] text-slate-400 leading-relaxed">
            题目基于你的简历画像生成，覆盖岗位核心能力
          </p>
        </div>
      </div>

      {/* Popular roles */}
      <div className="rounded-xl border border-slate-200/60 bg-white/50 p-5">
        <h3 className="text-[13px] font-semibold text-slate-700 mb-3">热门岗位</h3>
        <div className="flex flex-wrap gap-2">
          {['后端工程师', '前端开发', '产品经理', '算法工程师', '数据分析', '测试开发'].map((role) => (
            <button
              key={role}
              onClick={() => setTargetRole(role)}
              className={`px-3 py-1.5 rounded-lg text-[13px] font-medium border transition-all duration-200 cursor-pointer ${
                targetRole === role
                  ? 'border-blue-400 bg-blue-50 text-blue-700'
                  : 'border-slate-200/60 bg-white text-slate-600 hover:border-blue-300 hover:bg-blue-50/50 hover:scale-[1.03] active:scale-[0.97]'
              }`}
            >
              {role}
            </button>
          ))}
        </div>
      </div>
    </div>
  )}
</div>
```

### 4. 原有的 `{!hasHistory && ...}` 引导语删除

因为引导语已经合并到标题行了，把原来单独的引导语删掉：
```tsx
// 删除这段
{!hasHistory && (
  <p className="text-[14px] text-slate-400 mb-6">
    选一个目标岗位，开始你的第一场模拟面试
  </p>
)}
```

---

## 热门岗位标签交互

点击热门岗位标签后：
- `setTargetRole(role)` — 填入输入框
- 标签变为选中态（蓝色边框 + 蓝色背景）
- 输入框同步显示选中的岗位名（双向绑定，已有逻辑）
- 用户可以在输入框里修改，修改后标签取消选中

---

## 入场动画

右侧面板用 framer-motion 延迟入场：

```tsx
{!hasHistory && (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: 0.15, duration: 0.35, ease }}
    className="w-full md:w-[320px] shrink-0 space-y-6"
  >
    {/* ... 内容 ... */}
  </motion.div>
)}
```

---

## 技术约束

- framer-motion（已安装）
- Tailwind v4
- 不引入新依赖
- 热门岗位列表硬编码（不需要从后端拉取）

## 不改的部分

- 有历史记录时的渲染 — 不动
- Interviewing / Evaluating / Results 阶段 — 不动
- 所有业务逻辑 — 不动
- 输入区块内部的表单元素 — 不动（只是外面包了一层 flex）

## 禁止

- 不要大图标/插画（不是营销页）
- 不要 gradient text
- 不要 glassmorphism 堆叠
- 不要 bounce/elastic 动画
