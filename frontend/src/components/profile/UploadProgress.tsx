import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { uploadSteps, uploadTips } from './constants'

export function UploadProgress({ step }: { step: number }) {
  const [tipIdx, setTipIdx] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setTipIdx((i) => (i + 1) % uploadTips.length)
    }, 2500)
    return () => clearInterval(timer)
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6 glass-static px-6 py-5"
    >
      <div className="g-inner">
        {/* Step indicators */}
        <div className="flex items-center gap-2 mb-5">
          {uploadSteps.map((s, i) => {
            const isCompleted = i < step;
            const isActive = i === step;
            const isPending = i > step;

            return (
              <div key={s.label} className="flex items-center gap-2 flex-1 last:flex-none">
                <div className={`
                  w-6 h-6 rounded-full flex items-center justify-center text-[11px] shrink-0 transition-all duration-300 font-bold
                  ${isCompleted ? 'bg-[var(--blue)] text-white' : ''}
                  ${isActive ? 'bg-white/50 border-2 border-[var(--blue)] text-[var(--blue)]' : ''}
                  ${isPending ? 'bg-white/30 text-[var(--text-3)] border border-white/40' : ''}
                `}>
                  {isCompleted ? '✓' : isActive ? <div className="w-1.5 h-1.5 rounded-full bg-[var(--blue)]" /> : i + 1}
                </div>
                <span className={`text-[12px] font-medium ${isCompleted || isActive ? 'text-[var(--text-1)]' : 'text-[var(--text-3)]'}`}>
                  {s.label}
                </span>
                {i < uploadSteps.length - 1 && (
                  <div className={`flex-1 h-[2px] mx-2 rounded-full ${isCompleted ? 'bg-[var(--blue)]' : 'bg-white/30'}`} />
                )}
              </div>
            )
          })}
        </div>

        {/* Progress bar */}
        <div className="progress-track mb-4">
          <div className="progress-fill transition-all duration-500" style={{ width: `${((step + 1) / uploadSteps.length) * 100}%` }} />
        </div>

        {/* Animated tip */}
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/25 border border-white/30">
          <div className="w-3.5 h-3.5 border-2 border-[var(--blue)] border-t-transparent rounded-full animate-spin shrink-0" />
          <AnimatePresence mode="wait">
            <motion.span
              key={tipIdx}
              initial={{ opacity: 0, x: 4 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -4 }}
              transition={{ duration: 0.2 }}
              className="text-[13px] text-[var(--text-2)] font-medium"
            >
              {uploadTips[tipIdx]}
            </motion.span>
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  )
}
