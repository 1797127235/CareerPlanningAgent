import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion'
import type { ReactNode, RefObject } from 'react'
import { useRef } from 'react'

export function ChapterOpener({ numeral, title }: { numeral: string; title: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const shouldReduceMotion = useReducedMotion()

  const { scrollYProgress } = useScroll({
    target: ref as RefObject<HTMLElement>,
    offset: ['start end', 'end start'],
  })

  const rawOpacity = useTransform(scrollYProgress, [0, 0.5], [0.3, 0.6])
  const rawScale = useTransform(scrollYProgress, [0, 0.5], [0.95, 1])

  const opacity = shouldReduceMotion ? 0.6 : rawOpacity
  const scale = shouldReduceMotion ? 1 : rawScale

  return (
    <div ref={ref} className="relative py-24 md:py-32 mb-8">
      <motion.span
        aria-hidden
        className="absolute left-0 top-1/2 -translate-y-1/2 font-serif font-light text-[160px] md:text-[220px] leading-none tracking-tighter select-none pointer-events-none"
        style={{ opacity, scale, color: 'var(--line)', zIndex: 0 }}
      >
        {numeral}
      </motion.span>
      <div className="relative z-10 max-w-[26ch]">
        <h1 className="font-display font-medium text-[var(--fs-display-xl)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight">
          {title}
        </h1>
      </div>
    </div>
  )
}
