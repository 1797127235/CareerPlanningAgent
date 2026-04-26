import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { Upload, PenLine, FileText, Check } from 'lucide-react'
import { SealStamp } from './SealStamp'

interface CeremonyUploadProps {
  uploadStep: number
  uploadError: string | null
  justUploaded: boolean
  fileName: string
  onUpload: () => void
  onManual: () => void
  onCeremonyComplete?: () => void
}

type Phase = 'papers-ready' | 'paper-drop' | 'typesetting' | 'bound'

/* ── 圆形进度环 ── */
function CircularProgress({ progress, size = 64 }: { progress: number; size?: number }) {
  const stroke = 4
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (progress / 100) * circumference
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={radius} stroke="var(--line)" strokeWidth={stroke} fill="transparent" />
      <circle
        cx={size / 2} cy={size / 2} r={radius}
        stroke="var(--chestnut)" strokeWidth={stroke} fill="transparent"
        strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
        className="transition-all duration-500"
      />
    </svg>
  )
}

/* ── 打字机步骤子组件 ── */
function TypewriterStep({ text, completed }: { text: string; completed: boolean }) {
  const [displayLen, setDisplayLen] = useState(completed ? text.length : 0)

  useEffect(() => {
    if (completed) {
      setDisplayLen(text.length)
      return
    }
    setDisplayLen(0)
    let i = 0
    const interval = setInterval(() => {
      i++
      if (i > text.length) {
        clearInterval(interval)
      } else {
        setDisplayLen(i)
      }
    }, 80)
    return () => clearInterval(interval)
  }, [text, completed])

  return (
    <div className="flex items-center gap-2.5">
      <div className="w-5 flex items-center justify-center shrink-0">
        {completed ? (
          <Check className="w-4 h-4 text-green-600" strokeWidth={2.5} />
        ) : (
          <div className="w-1.5 h-1.5 rounded-full bg-[var(--line)]" />
        )}
      </div>
      <span className="text-[14px] font-sans text-[var(--ink-1)]">
        {text.slice(0, displayLen)}
        {!completed && <span className="typewriter-cursor" />}
      </span>
    </div>
  )
}

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
  const prefersReduced = useReducedMotion()

  // 阶段切换逻辑
  useEffect(() => {
    if (uploadStep === 1 && prevStep.current === 0 && phase === 'papers-ready') {
      setPhase('paper-drop')
      const timer = setTimeout(() => setPhase('typesetting'), 800)
      prevStep.current = uploadStep
      return () => clearTimeout(timer)
    }

    if (uploadStep >= 2 && (phase === 'papers-ready' || phase === 'paper-drop')) {
      setPhase('typesetting')
    }

    if (justUploaded && uploadStep === 0 && phase !== 'bound') {
      setPhase('bound')
      const timer = setTimeout(() => {
        onCeremonyComplete?.()
      }, 1500)
      prevStep.current = uploadStep
      return () => clearTimeout(timer)
    }

    if (uploadStep === 0 && !justUploaded && phase !== 'papers-ready') {
      setPhase('papers-ready')
    }

    prevStep.current = uploadStep
  }, [uploadStep, justUploaded, phase, onCeremonyComplete])

  return (
    <div
      role="region"
      aria-label="简历上传区域"
      aria-live="polite"
      className="w-full"
    >
      <AnimatePresence mode="wait">
        {/* ── 阶段 1：两张稿纸并排 ── */}
        {phase === 'papers-ready' && (
          <motion.div
            key="papers"
            initial={prefersReduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={prefersReduced ? undefined : { opacity: 0, scale: 0.95 }}
            className="flex flex-col md:flex-row gap-6"
          >
            {/* 稿纸 1：上传简历 */}
            <div className="corner-crops relative flex-1 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6 hover:shadow-[var(--shadow-paper)] transition-shadow duration-300">
              <div className="baseline-grid absolute inset-0 rounded-xl opacity-[0.02] pointer-events-none" />
              {!prefersReduced && <div className="baseline-grid-glow absolute inset-0 rounded-xl pointer-events-none" />}

              <button onClick={onUpload} className="relative z-10 w-full text-left">
                <div className="flex items-center gap-4">
                  <div className="relative shrink-0">
                    <div className="w-12 h-12 rounded-full bg-[var(--bg-paper)] flex items-center justify-center">
                      <Upload className="w-5 h-5 text-[var(--chestnut)]" />
                    </div>
                    <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[var(--chestnut)]" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-sans text-[15px] font-medium text-[var(--ink-1)] whitespace-nowrap">
                      上传一份简历
                    </p>
                    <p className="text-[13px] text-[var(--ink-2)] whitespace-nowrap">
                      PDF / Word / TXT，10MB 以内
                    </p>
                  </div>
                </div>
              </button>
            </div>

            {/* 稿纸 2：手动填写 */}
            <div className="corner-crops relative flex-1 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6">
              <div className="baseline-grid absolute inset-0 rounded-xl opacity-[0.02] pointer-events-none" />
              {!prefersReduced && <div className="baseline-grid-glow absolute inset-0 rounded-xl pointer-events-none" />}

              <button onClick={onManual} className="relative z-10 w-full text-left">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-[var(--bg-paper)] flex items-center justify-center">
                    <PenLine className="w-5 h-5 text-[var(--chestnut)]" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-sans text-[15px] font-medium text-[var(--ink-1)] whitespace-nowrap">
                      手动讲给我听
                    </p>
                    <p className="text-[13px] text-[var(--ink-2)] whitespace-nowrap">
                      几个字就够了，不用一次填完
                    </p>
                  </div>
                </div>
              </button>
            </div>
          </motion.div>
        )}

        {/* ── 阶段 2：稿件落下 ── */}
        {phase === 'paper-drop' && (
          <motion.div
            key="paper-drop"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-4"
            role="status"
            aria-label="文件已选择，正在准备处理"
          >
            {/* 文件名飘落动画 */}
            <motion.div
              initial={prefersReduced ? false : { y: -30, opacity: 0, rotateX: 15 }}
              animate={{ y: 0, opacity: 1, rotateX: 0 }}
              transition={prefersReduced ? { duration: 0 } : { type: 'spring', stiffness: 200, damping: 18 }}
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
              initial={prefersReduced ? false : { scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={prefersReduced ? { duration: 0 } : { delay: 0.2, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            />

            {/* 两张稿纸（下沉版本） */}
            <div className="flex flex-col md:flex-row gap-6 w-full">
              <motion.div
                initial={prefersReduced ? false : { y: 0 }}
                animate={{ y: 4 }}
                transition={prefersReduced ? { duration: 0 } : { type: 'spring', stiffness: 300, damping: 20 }}
                className="corner-crops relative flex-1 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6 opacity-60"
              >
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="flex items-center gap-3 text-[var(--ink-3)]">
                    <Upload className="w-5 h-5" />
                    <span className="text-[13px]">选择文件</span>
                  </div>
                </div>
              </motion.div>

              <motion.div
                initial={prefersReduced ? false : { y: 0 }}
                animate={{ y: 4 }}
                transition={prefersReduced ? { duration: 0 } : { type: 'spring', stiffness: 300, damping: 20 }}
                className="corner-crops relative flex-1 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6 opacity-60"
              >
                <div className="absolute inset-0 flex items-center justify-center text-[var(--ink-3)] text-[13px]">
                  手动填写暂停中...
                </div>
              </motion.div>
            </div>
          </motion.div>
        )}

        {/* ── 阶段 3：排字进行中 ── */}
        {phase === 'typesetting' && (
          <motion.div
            key="typesetting"
            initial={prefersReduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={prefersReduced ? undefined : { opacity: 0 }}
            className="flex flex-col items-center"
            role="status"
            aria-label={`正在处理简历，当前步骤：${
              uploadStep === 2 ? '解析简历' : uploadStep === 3 ? '合并画像' : '处理中'
            }`}
          >
            {/* 中央稿纸：排版台 */}
            <div className="corner-crops relative w-full max-w-[420px] rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6">
              <div
                className="baseline-grid absolute inset-0 rounded-xl pointer-events-none"
                style={{ opacity: 0.05 }}
              />
              {!prefersReduced && (
                <div
                  className="baseline-grid-glow absolute inset-0 rounded-xl pointer-events-none"
                  style={{ opacity: 0.6, animationDuration: '1.5s' }}
                />
              )}

              {/* 水平并排：进度环 + 步骤 */}
              <div className="relative z-10 flex items-center justify-center gap-8">
                {/* 左侧进度环 */}
                <div className="shrink-0">
                  <CircularProgress progress={((uploadStep) / 3) * 100} size={68} />
                </div>

                {/* 右侧步骤 */}
                <div className="space-y-2 min-w-[120px]">
                  <TypewriterStep text="选择文件" completed={uploadStep >= 2} />
                  <TypewriterStep text="解析简历" completed={uploadStep >= 3} />
                  <TypewriterStep text="合并画像" completed={uploadStep === 0 && justUploaded} />
                </div>
              </div>

              {/* 错误提示 */}
              {uploadError && (
                <div className="relative z-10 mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
                  {uploadError}
                </div>
              )}
            </div>

            {/* 底部提示 */}
            <p className="mt-4 text-[13px] text-[var(--ink-3)]">
              正在将你的经历排版为档案...
            </p>
          </motion.div>
        )}

        {/* ── 阶段 4：装订成册 ── */}
        {phase === 'bound' && (
          <motion.div
            key="bound"
            initial={prefersReduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center gap-6 p-8"
            role="status"
            aria-label="档案已归档，正在生成画像"
          >
            <div className="flex items-center gap-0">
              {/* 左页 */}
              <motion.div
                initial={prefersReduced ? false : { x: 0 }}
                animate={{ x: 8 }}
                transition={prefersReduced ? { duration: 0 } : { duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
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
                  initial={prefersReduced ? false : { scaleY: 0, opacity: 0 }}
                  animate={{ scaleY: 1, opacity: 1 }}
                  transition={prefersReduced ? { duration: 0 } : { delay: 0.2, duration: 0.5 }}
                  className="w-0 h-64 border-l-2 border-dashed border-[var(--chestnut)]/40"
                />
                {/* 印章 */}
                <div className="absolute top-1/2 -translate-y-1/2">
                  <SealStamp text="归档" />
                </div>
              </div>

              {/* 右页 */}
              <motion.div
                initial={prefersReduced ? false : { x: 0 }}
                animate={{ x: -8 }}
                transition={prefersReduced ? { duration: 0 } : { duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                className="corner-crops relative w-56 h-72 rounded-r-lg border border-[var(--line)] bg-[var(--bg-card)]"
              >
                <div className="absolute inset-0 flex items-center justify-center text-[var(--ink-3)] text-[13px]">
                  档案 B
                </div>
              </motion.div>
            </div>

            {/* 翻页过渡文字 */}
            <motion.p
              initial={prefersReduced ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={prefersReduced ? { duration: 0 } : { delay: 1.2 }}
              className="text-[length:var(--fs-body)] text-[var(--ink-2)]"
            >
              档案已归档，正在生成画像...
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
