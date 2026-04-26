# 上传仪式感 UX 增强规范

> 将上传简历的体验从静态双卡片改为"杂志排版室"仪式流程，混搭"档案投递"元素。
> 最后更新：2026-04-26（v1.1 — Kimi 审核修订）

---

## 一、设计方向

**主线：杂志排版室**（Direction 3）—— 把上传看作一叠稿件交给排版师，看着他排出一本杂志。
**点缀：档案投递仪式**（Direction 1）—— 打字机效果处理中提示 + 火漆印章完成反馈。

### 为什么选这个方向

| 维度 | 匹配度 |
|---|---|
| 项目现有 editorial 组件体系 | ChapterOpener、DropCap、PullQuote、TOC 已是排版概念 |
| 项目语言基调 | "档案""画像""卷宗" = 出版/归档语境 |
| 品牌色 #B85C38（chestnut） | 可充当校对红线 + 火漆印章色 |
| 现有双卡布局 | 天然就是"两张并排版式稿纸"的起点 |
| 实现复杂度 | CSS + framer-motion，不引入新依赖 |

---

## 二、四阶段流程总览

```
阶段1 稿纸就绪 ──→ 阶段2 稿件落下 ──→ 阶段3 排字进行中 ──→ 阶段4 装订成册
  (idle state)     (file selected)     (uploading)         (complete → profile)
```

| 阶段 | 触发条件 | 持续 | 视觉焦点 |
|---|---|---|---|
| 1 稿纸就绪 | 页面挂载 | 一直，直到文件选择 | 裁切标记 + 网格底纹 + 脉冲呼吸光晕 |
| 2 稿件落下 | `onFileSelected` 调用 | 1 秒 | 文件名飘落 + 校对红线出现 |
| 3 排字进行中 | `uploadStep` 1→3 | 取决于上传耗时 | 打字机步骤文字 + 圆形进度环 + 网格脉搏 |
| 4 装订成册 | `uploadStep` 归零 + `justUploaded=true` | 1.5 秒 | 稿纸合并装订 + 火漆印章 → 动画播完后硬切到画像页 |

---

## 三、需修改/新建的文件清单

```
新增:
  src/components/profile-v2/CeremonyUpload.tsx     # 新仪式感上传组件
  src/components/profile-v2/SealStamp.tsx           # 火漆印章完成动效

修改:
  src/components/profile-v2/UploadCta.tsx           # （无需改动）打字机效果+网格底纹在CeremonyUpload层实现
  src/hooks/useResumeUpload.ts                     # 新增 selectedFileName state
  src/pages/ProfilePage.tsx                         # 替换双卡布局 + onCeremonyComplete回调
  src/index.css                                     # 添加裁切标记、网格底纹、校对红线等全局 CSS
  src/components/profile-v2/index.ts               # 补充新组件导出

删除:
  src/components/profile-v2/CeremonyUpload.css      # 不新建独立CSS文件，全局样式归入index.css
```

---

## 四、详细实现规范

### 4.1 阶段 1 —— 稿纸就绪（Idle State）

**目标**：两张卡片从"灰色矩形"变成有排版稿纸的质感。

#### 4.1.1 CSS：裁切标记（Corner Crops）

在 `index.css` 末尾添加。使用 `::before` + `::after` 伪元素 + `linear-gradient` 绘制四角 L 形裁切线，零额外 DOM 节点：

```css
/* ── 裁切标记（排版稿纸四角，伪元素实现，零 DOM 开销） ── */
.corner-crops::before,
.corner-crops::after {
  content: '';
  position: absolute;
  inset: 8px;
  pointer-events: none;
  z-index: 1;
  /* 分上下两部分绘制，每个伪元素画两个对角的 L */
}
.corner-crops::before {
  background:
    /* 左上角 */ linear-gradient(to right, var(--line) 1px, transparent 12px),
                 linear-gradient(to bottom, var(--line) 1px, transparent 12px),
    /* 右下角 */ linear-gradient(to left, var(--line) 1px, transparent 12px),
                 linear-gradient(to top, var(--line) 1px, transparent 12px);
  background-position: top left, top left, bottom right, bottom right;
  background-size: 12px 1px, 1px 12px, 12px 1px, 1px 12px;
  background-repeat: no-repeat;
}
.corner-crops::after {
  background:
    /* 右上角 */ linear-gradient(to left, var(--line) 1px, transparent 12px),
                 linear-gradient(to bottom, var(--line) 1px, transparent 12px),
    /* 左下角 */ linear-gradient(to right, var(--line) 1px, transparent 12px),
                 linear-gradient(to top, var(--line) 1px, transparent 12px);
  background-position: top right, top right, bottom left, bottom left;
  background-size: 12px 1px, 1px 12px, 12px 1px, 1px 12px;
  background-repeat: no-repeat;
}
```

使用方式：只需给容器加 `corner-crops` 类，无需添加任何子 div。

#### 4.1.2 CSS：网格底纹 + 呼吸光晕

在 `index.css` 末尾添加：

```css
/* ── 稿纸网格底纹（静态层） ── */
.baseline-grid {
  background-image:
    linear-gradient(var(--line) 0.5px, transparent 0.5px);
  background-size: 100% 28px;  /* 行高 28px，匹配排版网格 */
  background-position: 0 14px;
}

/* ── 呼吸光晕（opacity 脉动层，叠加在静态网格之上） ── */
@keyframes grid-glow {
  0%, 100% { opacity: 0; }
  50%      { opacity: 1; }
}
.baseline-grid-glow {
  background-color: var(--chestnut-soft);  /* oklch(0.92 0.04 30) */
  animation: grid-glow 3s ease-in-out infinite;
}
/* 注意：使用 opacity 动画而非 background-image 动画，GPU 合成层，避免 repaint */

/* ── 校对红线 ── */
@keyframes proof-line-grow {
  from { transform: scaleX(0); }
  to   { transform: scaleX(1); }
}
.proof-line {
  height: 1px;
  background: var(--chestnut);
  transform-origin: left center;
  box-shadow: 0 0 4px oklch(0.32 0.05 30 / 0.3);
}
.proof-line-appear {
  animation: proof-line-grow 0.8s cubic-bezier(0.22, 1, 0.36, 1) both;
}

/* ── 打字机光标闪烁 ── */
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
.typewriter-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: var(--chestnut);
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 1s step-end infinite;
}
```

#### 4.1.3 CeremonyUpload 组件骨架

新建 `src/components/profile-v2/CeremonyUpload.tsx`：

```tsx
import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, PenLine, FileText } from 'lucide-react'
import { UploadCta } from './UploadCta'
import { SealStamp } from './SealStamp'

interface CeremonyUploadProps {
  uploadStep: number
  uploadError: string | null
  justUploaded: boolean
  fileName: string                     // 从 useResumeUpload.selectedFileName 传入
  onUpload: () => void
  onManual: () => void
  onCeremonyComplete?: () => void       // 阶段 4 动画播完后回调，通知父组件可以切到画像页
}

// 四个阶段的枚举
type Phase = 'papers-ready' | 'paper-drop' | 'typesetting' | 'bound'

export function CeremonyUpload({
  uploadStep,
  uploadError,
  justUploaded,
  fileName,
  onUpload,
  onManual,
  onCeremonyComplete,
}: CeremonyUploadProps) {
  const [phase, setPhase] = useState<Phase>('papers-ready')
  const prevStep = useRef(0)

  // 监听 uploadStep 变化，驱动阶段切换
  // 步骤见 4.1.4

  return (
    // 见 4.1.5
    null
  )
}
```

#### 4.1.3.1 useResumeUpload 改动

在 `src/hooks/useResumeUpload.ts` 中新增 `selectedFileName` 状态：

```ts
// 修改前：
let _uploading = false
let _step = 0
let _error: string | null = null
let _justUploaded = false

// 修改后：新增
let _fileName = ''

function _set(uploading: boolean, step: number, error: string | null, justUploaded?: boolean) {
  // ... 保持不变
}

// Hook 返回值新增：
export function useResumeUpload(onSuccess: () => Promise<void>) {
  // ... 原有代码 ...

  // 同步 _fileName 的 listener 逻辑与已有 _uploading / _step 一致
  const [selectedFileName, setSelectedFileName] = useState(_fileName)

  useEffect(() => {
    const sync = () => {
      // ... 原有 setter ...
      setSelectedFileName(_fileName)
    }
    sync()
    _listeners.add(sync)
    return () => { _listeners.delete(sync) }
  }, [])

  // 在 onFileSelected 中写入文件名：
  const onFileSelected = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    _fileName = file.name                    // 记录文件名，传给 CeremonyUpload
    _listeners.forEach((fn) => fn())
    _set(true, 1, null)
    // ... 其余逻辑不变
  }, [onSuccess])

  return {
    // ... 原有字段 ...
    selectedFileName,   // 新增
    // ... 原有字段 ...
  }
}

#### 4.1.4 阶段切换逻辑

在 `CeremonyUpload` 内部实现 `useEffect` 驱动阶段机：

```
uploadStep 变化规则：
  0 (idle) ──→ 1 (选择文件) ──→ 2 (解析简历) ──→ 3 (合并画像) ──→ 0 (完成)

阶段切换规则：
  papers-ready   →   page-load + uploadStep === 0 + !justUploaded
  paper-drop     →   uploadStep === 1（仅持续一次）
  typesetting    →   uploadStep >= 2  || (uploadStep === 1 && 持续 > 1s)
  bound          →   justUploaded === true
```

**关键时序**：
- `paper-drop` 阶段持续 `800ms` 后自动进入 `typesetting`（用 `setTimeout`）
- `bound` 阶段检测到 `justUploaded === true` 后播放 1.5s 动画，然后通过回调通知父组件完成

具体代码：

```tsx
useEffect(() => {
  // 步骤 1 触发 → 稿件落下
  if (uploadStep === 1 && prevStep.current === 0 && phase === 'papers-ready') {
    setPhase('paper-drop')
    const timer = setTimeout(() => setPhase('typesetting'), 800)
    return () => clearTimeout(timer)
  }

  // 步骤 2-3 → 排字进行中
  if (uploadStep >= 2 && (phase === 'papers-ready' || phase === 'paper-drop')) {
    setPhase('typesetting')
  }

  // 上传完成 → 装订成册（1.5s 动画，播完后回调父组件）
  if (justUploaded && uploadStep === 0 && phase !== 'bound') {
    setPhase('bound')
    const timer = setTimeout(() => {
      onCeremonyComplete?.()
    }, 1500)
    return () => clearTimeout(timer)
  }

  // 重置
  if (uploadStep === 0 && !justUploaded && phase !== 'papers-ready') {
    setPhase('papers-ready')
  }

  prevStep.current = uploadStep
}, [uploadStep, justUploaded, phase, onCeremonyComplete])
```

#### 4.1.5 阶段 1 JSX：稿纸就绪

```tsx
{/* ── 阶段 1：两张稿纸并排 ── */}
<AnimatePresence mode="wait">
  {phase === 'papers-ready' && (
    <motion.div
      key="papers"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="flex flex-col md:flex-row gap-6"
    >
      {/* 稿纸 1：上传简历 */}
      <div className="corner-crops relative flex-1 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6 hover:shadow-[var(--shadow-paper)] transition-shadow duration-300">
        {/* 网格底纹：静态层 + 呼吸光晕层（opacity 脉动，GPU 合成） */}
        <div className="baseline-grid absolute inset-0 rounded-xl opacity-[0.03] pointer-events-none" />
        <div className="baseline-grid-glow absolute inset-0 rounded-xl opacity-[0.04] pointer-events-none" />

        <button
          onClick={onUpload}
          className="relative z-10 w-full text-left"
        >
          <UploadCta
            step={0}
            label="上传一份简历"
            subLabel="PDF / Word / TXT，10MB 以内"
            onClick={onUpload}
          />
        </button>
      </div>

      {/* 稿纸 2：手动填写 */}
      <div className="corner-crops relative flex-1 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6">
        <div className="baseline-grid absolute inset-0 rounded-xl opacity-[0.03] pointer-events-none" />
        <div className="baseline-grid-glow absolute inset-0 rounded-xl opacity-[0.04] pointer-events-none" />

        <button onClick={onManual} className="relative z-10 w-full text-left">
          <div className="flex items-center gap-5">
            <div className="w-14 h-14 rounded-full bg-[var(--bg-paper)] flex items-center justify-center">
              <PenLine className="w-5 h-5 text-[var(--chestnut)]" />
            </div>
            <div>
              <p className="font-sans text-[length:var(--fs-body-lg)] font-medium text-[var(--ink-1)]">
                手动讲给我听
              </p>
              <p className="text-[length:var(--fs-body)] text-[var(--ink-2)]">
                几个字就够了，不用一次填完
              </p>
            </div>
          </div>
        </button>
      </div>
    </motion.div>
  )}
</AnimatePresence>
```

### 4.2 阶段 2 —— 稿件落下（File Selected）

#### 4.2.1 视觉效果

**触发条件**：`uploadStep === 1`（用户选择了文件，`onFileSelected` 开始执行）

**动画序列**（总时长 ~800ms）：
1. **文件名飘落**（0-600ms）：一个带 `FileText` 图标的文件名 chip 从上方 20px 处 `spring` 动画落到两张稿纸之间的缝隙上方
2. **校对红线出现**（200-800ms）：一道 chestnut 色的水平细线从缝隙中心向两端生长，带 `drop-shadow`
3. **稿纸微沉**（0-400ms）：两张稿纸的 `y` 从 0 下沉 4px（像一叠纸落下的物理反馈）

#### 4.2.2 实现代码

```tsx
{/* ── 阶段 2：稿件落下 ── */}
{phase === 'paper-drop' && (
  <motion.div
    key="paper-drop"
    initial={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="flex flex-col items-center gap-4"
  >
    {/* 文件名飘落动画 */}
    <motion.div
      initial={{ y: -30, opacity: 0, rotateX: 15 }}
      animate={{ y: 0, opacity: 1, rotateX: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 18 }}
      className="inline-flex items-center gap-2 rounded-full border border-[var(--chestnut)]/30 bg-[var(--bg-card)] px-4 py-2 shadow-sm"
    >
      <FileText className="w-4 h-4 text-[var(--chestnut)]" />
      <span className="text-[13px] font-medium text-[var(--ink-1)]">
        {fileName || '简历文件'}
      </span>
    </motion.div>

    {/* 校对红线 */}
    <motion.div
      className="proof-line w-full max-w-md proof-line-appear"
      initial={{ scaleX: 0 }}
      animate={{ scaleX: 1 }}
      transition={{ delay: 0.2, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    />

    {/* 两张稿纸（下沉版本） */}
    <div className="flex flex-col md:flex-row gap-6 w-full">
      <motion.div
        initial={{ y: 0 }}
        animate={{ y: 4 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        className="corner-crops relative flex-1 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6 opacity-60"
      >
        <div className="absolute inset-0 flex items-center justify-center">
          <UploadCta step={1} label="选择文件" onClick={() => {}} />
        </div>
      </motion.div>

      <motion.div
        initial={{ y: 0 }}
        animate={{ y: 4 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        className="corner-crops relative flex-1 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6 opacity-60"
      >
        <div className="absolute inset-0 flex items-center justify-center text-[var(--ink-3)] text-[13px]">
          手动填写暂停中...
        </div>
      </motion.div>
    </div>
  </motion.div>
)}
```

### 4.3 阶段 3 —— 排字进行中（Uploading）

#### 4.3.1 视觉效果

**触发条件**：`uploadStep >= 2`（`parseResume` 或 `updateProfile` 进行中）

**动画**：
1. **打字机步骤文字**：当前步骤的文字（"解析简历" / "合并画像"）逐字出现，末尾有闪烁光标
2. **圆形进度环**：UploadCta 自带的 `CircularProgress`，三阶段对应 33% / 66% / 100%
3. **网格脉搏增强**：底纹 `opacity` 从 0.03 提升到 0.06，`animation-duration` 从 3s 加快到 1.5s
4. **已完成的步骤打勾**：步骤 1 完成后在左侧出现一个小对勾

#### 4.3.2 打字机组件（TypewriterStep）

```tsx
function TypewriterStep({ text, completed }: { text: string; completed: boolean }) {
  const [displayLen, setDisplayLen] = useState(completed ? text.length : 0)

  useEffect(() => {
    if (completed) {
      setDisplayLen(text.length)        // 完成后直接全显
      return
    }
    // 逐字显示
    setDisplayLen(0)
    let i = 0
    const interval = setInterval(() => {
      i++
      if (i > text.length) {
        clearInterval(interval)
      } else {
        setDisplayLen(i)
      }
    }, 80) // 每字 80ms
    return () => clearInterval(interval)
  }, [text, completed])

  return (
    <div className="flex items-center gap-2">
      {completed && <Check className="w-4 h-4 text-green-500" />}
      <span className="text-[length:var(--fs-body)] text-[var(--ink-1)]">
        {text.slice(0, displayLen)}
        {!completed && <span className="typewriter-cursor" />}
      </span>
    </div>
  )
}
```

#### 4.3.3 阶段 3 JSX

```tsx
{/* ── 阶段 3：排字进行中 ── */}
{phase === 'typesetting' && (
  <motion.div
    key="typesetting"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="flex flex-col items-center gap-6 p-8"
  >
    {/* 中央稿纸：排版中 */}
    <div className="corner-crops relative w-full max-w-lg rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-8">
      {/* 增强版网格脉搏（静态层 + 呼吸光晕层，opacity 和 animation-duration 加强） */}
      <div
        className="baseline-grid absolute inset-0 rounded-xl pointer-events-none"
        style={{ opacity: 0.06 }}
      />
      <div
        className="baseline-grid-glow absolute inset-0 rounded-xl pointer-events-none"
        style={{ opacity: 0.75, animationDuration: '1.5s' }}
      />

      <div className="relative z-10 space-y-6">
        {/* 进度环 */}
        <div className="flex justify-center">
          <UploadCta
            step={uploadStep}
            label=""
            onClick={() => {}}
          />
        </div>

        {/* 打字机步骤列表 */}
        <div className="space-y-3">
          <TypewriterStep
            text="选择文件"
            completed={uploadStep >= 2}
          />
          <TypewriterStep
            text="解析简历"
            completed={uploadStep >= 3}
          />
          <TypewriterStep
            text="合并画像"
            completed={uploadStep === 0 && justUploaded}
          />
        </div>

        {/* 错误提示 */}
        {uploadError && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
            {uploadError}
          </div>
        )}
      </div>
    </div>

    {/* 提示文字 */}
    <p className="text-[13px] text-[var(--ink-3)]">
      正在将你的经历排版为档案...
    </p>
  </motion.div>
)}
```

### 4.4 阶段 4 —— 装订成册（Complete → Profile）

#### 4.4.1 视觉效果与时序说明

**触发条件**：`justUploaded === true && uploadStep === 0`

**时序风险**：`justUploaded` 触发后 `loadProfile()` 会立即拉数据，`hasProfile` 变为 `true`，父组件可能提前卸载 CeremonyUpload。**采用方案 B**：

1. CeremonyUpload 内部锁 1.5s，完整播放 bound 动画
2. ProfilePage 用本地 `ceremonyAnimating` state 延迟 `hasProfile` 判定
3. 动画播完后 `onCeremonyComplete()` 回调 ProfilePage，state 翻转，硬切到画像页
4. 不做翻页过渡动画（免去 3D `rotateY` 的复杂度和不可靠性）

**动画序列**（总时长 ~1500ms）：
1. **稿纸合拢**（0-800ms）：两张稿纸向中间 slide，彼此靠拢
2. **书脊缝线**（300-800ms）：稿纸之间的缝隙出现竖向虚线（缝线图案），模拟装订
3. **火漆印章弹出**（600-1100ms）：在书脊正中央弹出一个 chestnut 色圆形印章，印有"归档"二字，`scale(0)` → `scale(1.15)` → `scale(1)`
4. **完成文字出现**（1100-1500ms）：底部浮现"档案已归档，正在生成画像..."，然后整体 fade out

#### 4.4.2 SealStamp 组件

新建 `src/components/profile-v2/SealStamp.tsx`：

```tsx
import { motion } from 'framer-motion'

interface SealStampProps {
  text?: string
  size?: number
  color?: string
}

export function SealStamp({
  text = '归档',
  size = 72,
  color = 'var(--chestnut)',
}: SealStampProps) {
  return (
    <motion.div
      initial={{ scale: 0, rotate: -15, opacity: 0 }}
      animate={{ scale: 1, rotate: 0, opacity: 1 }}
      transition={{
        type: 'spring',
        stiffness: 400,
        damping: 12,
        delay: 0.3,
      }}
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {/* 外圆 */}
      <svg width={size} height={size} className="absolute">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - 4}
          fill="transparent"
          stroke={color}
          strokeWidth="2"
          strokeDasharray="6 3"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - 8}
          fill="transparent"
          stroke={color}
          strokeWidth="1"
        />
      </svg>
      {/* 文字 */}
      <span
        className="font-sans text-[11px] font-bold tracking-[0.3em] uppercase"
        style={{ color }}
      >
        {text}
      </span>
      {/* 微妙阴影 */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          boxShadow: `0 2px 12px ${color}33, inset 0 1px 3px ${color}1a`,
        }}
      />
    </motion.div>
  )
}
```

#### 4.4.3 阶段 4 JSX

```tsx
{/* ── 阶段 4：装订成册 ── */}
{phase === 'bound' && (
  <motion.div
    key="bound"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="flex flex-col items-center gap-6 p-8"
  >
    <div className="flex items-center gap-0">
      {/* 左页 */}
      <motion.div
        initial={{ x: 0 }}
        animate={{ x: 8 }}  // 向右靠拢
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="corner-crops relative w-56 h-72 rounded-l-lg border border-[var(--line)] bg-[var(--bg-card)]"
      >
        <div className="absolute inset-0 flex items-center justify-center text-[var(--ink-3)] text-[13px]">
          档案 A
        </div>
      </motion.div>

      {/* 书脊 + 火漆印章 */}
      <div className="relative flex flex-col items-center">
        {/* 竖向缝线（书脊装订线） */}
        <motion.div
          initial={{ scaleY: 0, opacity: 0 }}
          animate={{ scaleY: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="w-0 h-64 border-l-2 border-dashed border-[var(--chestnut)]/40"
        />
        {/* 印章 */}
        <div className="absolute top-1/2 -translate-y-1/2">
          <SealStamp text="归档" />
        </div>
      </div>

      {/* 右页 */}
      <motion.div
        initial={{ x: 0 }}
        animate={{ x: -8 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="corner-crops relative w-56 h-72 rounded-r-lg border border-[var(--line)] bg-[var(--bg-card)]"
      >
        <div className="absolute inset-0 flex items-center justify-center text-[var(--ink-3)] text-[13px]">
          档案 B
        </div>
      </motion.div>
    </div>

    {/* 翻页过渡文字 */}
    <motion.p
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 1.2 }}
      className="text-[length:var(--fs-body)] text-[var(--ink-2)]"
    >
      档案已归档，正在生成画像...
    </motion.p>
  </motion.div>
)}
```

### 4.5 ProfilePage 集成

修改 `ProfilePage.tsx` 中"无画像"状态的渲染：

```tsx
// ── ProfilePage 新增状态 ──
const { uploadStep, uploadError, justUploaded, selectedFileName,
  fileInputRef, triggerFileDialog, onFileSelected }
  = useResumeUpload(loadProfile)

// 装订动画锁：防止 hasProfile 变为 true 后立即卸载 CeremonyUpload
const [ceremonyAnimating, setCeremonyAnimating] = useState(false)
useEffect(() => {
  if (justUploaded) setCeremonyAnimating(true)
}, [justUploaded])

// ── 渲染：替换原来的双卡区域（约 Line 340-445）──
// 条件：无画像 或 装订动画播放中
{(!hasProfile || ceremonyAnimating) && !showManual && (
  <CeremonyUpload
    uploadStep={uploadStep}
    uploadError={uploadError}
    justUploaded={justUploaded}
    fileName={selectedFileName}
    onUpload={triggerFileDialog}
    onManual={() => setShowManual(true)}
    onCeremonyComplete={() => setCeremonyAnimating(false)}
  />
)}
{/* 手动填写Modal保持原有逻辑 */}
{showManual && (
  <ManualProfileForm ... />
)}
{/* hidden <input> 和 upload error display 保留 */}
{uploadError && !showManual && !ceremonyAnimating && (
  <div className="...">{uploadError}</div>
)}
```

### 4.6 profile-v2/index.ts 更新

```tsx
export { CeremonyUpload } from './CeremonyUpload'
export { SealStamp } from './SealStamp'
```

---

## 五、与现有组件的共存策略

**渐进增强，不破坏现有功能**：

1. `CeremonyUpload` 是**纯粹的表现层**——它接收和 UploadCta 完全相同的 props 接口
2. `UploadCta` 本身**不做任何修改**——打字机效果和网格底纹在 CeremonyUpload 层级实现
3. 原有的 `useResumeUpload` hook **不修改**——阶段机通过监听 `uploadStep` 和 `justUploaded` 驱动
4. 手动填写入口 (`setShowManual`) 的触发逻辑不变，只是在阶段 2 期间暂时 inline 显示"暂停中"
5. `hidden <input>` 文件选择器保留在 ProfilePage 中，`CeremonyUpload` 通过 `onUpload` 回调触发

---

## 六、无障碍 & 性能考量

### 6.1 无障碍

```tsx
// CeremonyUpload 顶层容器
<div role="region" aria-label="简历上传区域" aria-live="polite">
```

```tsx
// 阶段切换时更新 aria-label
<motion.div
  key="typesetting"
  role="status"
  aria-label={`正在处理简历，当前步骤：${
    uploadStep === 2 ? '解析简历' : uploadStep === 3 ? '合并画像' : '处理中'
  }`}
>
```

### 6.2 reduced-motion 适配

```css
/* 已有全局 reduced-motion 规则 (index.css:83-90)，会自动禁用所有动画 */
/* 额外检查：framer-motion 用 useReducedMotion() */
```

在 `CeremonyUpload` 中添加：

```tsx
import { useReducedMotion } from 'framer-motion'

const prefersReduced = useReducedMotion()

// 将 prefersReduced 传给子组件，跳过非必要动画
// reduced-motion 下：静态网格 + 隐藏光晕层，所有 framer-motion 用初始值即最终值
<div className="baseline-grid" />  {/* 静态网格，无光晕 */}
{!prefersReduced && <div className="baseline-grid-glow" />}
```

### 6.3 性能

- 裁切标记用 `::before`/`::after` 伪元素 + `linear-gradient`，零额外 DOM 节点
- 网格底纹分两层：静态 `baseline-grid`（`background-image`）+ `baseline-grid-glow`（`opacity` 动画），后者只改变合成层 opacity，避免 background-image 动画的 repaint
- framer-motion 动画仅影响 `transform` 和 `opacity`（GPU 加速属性）
- `typewriter-cursor` 用 CSS `animation`，不占用 JS 线程
- 阶段切换使用 `AnimatePresence mode="wait"`，确保旧阶段 DOM 完全卸载

---

## 七、实施步骤（按顺序）

### Step 1：基础 CSS
- [ ] 在 `index.css` 末尾添加：裁切标记 `.corner-crop*`、网格底纹 `.baseline-grid*`、校对红线 `.proof-line*`、打字机光标 `.typewriter-cursor`、印章弹出 `@keyframes seal-pop`

### Step 2：SealStamp 组件
- [ ] 创建 `src/components/profile-v2/SealStamp.tsx`
- [ ] 更新 `src/components/profile-v2/index.ts` 导出

### Step 3：CeremonyUpload 组件
- [ ] 创建 `src/components/profile-v2/CeremonyUpload.tsx`
  - 打骨架（props 接口 + 四个阶段的 AnimatePresence 容器）
  - 实现阶段机 `useEffect`
  - 实现阶段 1 JSX（双稿纸 + 裁切角 + 网格底纹）
  - 实现阶段 2 JSX（文件名飘落 + 校对红线 + 稿纸下沉）
  - 实现阶段 3 JSX（TypewriterStep + 进度环 + 增强脉搏）
  - 实现阶段 4 JSX（稿纸合拢 + 书脊缝线 + SealStamp + 翻页文字）
- [ ] 添加 `useReducedMotion` 检测
- [ ] 添加 `aria-label` 和 `role` 属性

### Step 4：ProfilePage 集成
- [ ] 在 `ProfilePage.tsx` 中导入 `CeremonyUpload`
- [ ] 替换原有双卡布局（无画像状态）为 `<CeremonyUpload>`
- [ ] 保留 `hidden <input>` 和错误提示
- [ ] 确保手动填写 Modal 触发正常

### Step 5：验证
- [ ] `npx tsc --noEmit` 类型检查
- [ ] `npm run build` 构建通过
- [ ] 手动测试：无画像状态 → 上传 → 处理 → 完成全流程
- [ ] 手动测试：手动填写入口仍然可用
- [ ] 验证 `prefers-reduced-motion` 媒体查询不播放动画
- [ ] 验证移动端布局（单列堆叠）

---

## 八、验收标准

| # | 标准 |
|---|---|
| 1 | 无画像时，两个卡片显示裁切标记四角 + 网格底纹 + 呼吸光晕 |
| 2 | 点击上传后，文件名以 spring 动画飘落到两卡之间 |
| 3 | 校对红线从卡片缝隙横向生长，有 chestnut 色和发光效果 |
| 4 | 处理中时，步骤文字以打字机效果逐字出现，带闪烁光标 |
| 5 | 处理中时，圆形进度环随步骤推进 |
| 6 | 上传完成后，两页稿纸向中间合拢，书脊出现虚线和火漆"归档"印章 |
| 7 | 印章以 scale(0) → scale(1.15) → scale(1) 弹出，带旋转 |
| 8 | 全过程无 JS 报错，无 TypeScript 类型错误 |
| 9 | `prefers-reduced-motion` 时动画禁用，直接显示最终状态 |
| 10 | 手动填写入口（"手动讲给我听"按钮）在所有阶段可正常点击 |
