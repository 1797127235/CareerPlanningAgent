import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion'
import type { ReactNode, RefObject } from 'react'
import { useRef } from 'react'

type ChapterOpenerVariant = 'display' | 'chapter'
type ChapterOpenerTone = 'default' | 'book'

interface ChapterOpenerProps {
  numeral: string
  title: ReactNode
  variant?: ChapterOpenerVariant
  tone?: ChapterOpenerTone
  className?: string
  titleClassName?: string
}

export function ChapterOpener({
  numeral,
  title,
  variant = 'display',
  tone = 'default',
  className = '',
  titleClassName = '',
}: ChapterOpenerProps) {
  const ref = useRef<HTMLDivElement>(null)
  const shouldReduceMotion = useReducedMotion()
  const isDisplay = variant === 'display'
  const isBook = tone === 'book'

  const { scrollYProgress } = useScroll({
    target: ref as RefObject<HTMLElement>,
    offset: ['start end', 'end start'],
  })

  const rawOpacity = useTransform(scrollYProgress, [0, 0.5], isDisplay ? [0.08, 0.16] : [0.05, 0.1])
  const rawScale = useTransform(scrollYProgress, [0, 0.5], [0.98, 1])

  const opacity = shouldReduceMotion ? (isDisplay ? 0.12 : 0.08) : rawOpacity
  const scale = shouldReduceMotion ? 1 : rawScale

  return (
    <div
      ref={ref}
      className={[
        'relative',
        isDisplay ? 'py-8 md:py-10 mb-2 md:mb-3' : 'pt-6 md:pt-8 pb-2 md:pb-3 mb-0',
        className,
      ].filter(Boolean).join(' ')}
    >
      <motion.span
        aria-hidden
        className={[
          'absolute font-light leading-none tracking-tighter select-none pointer-events-none',
          isDisplay
            ? 'left-[-0.04em] top-[48%] -translate-y-1/2 text-[108px] md:text-[150px]'
            : 'left-[-0.02em] top-0 text-[64px] md:text-[84px]',
        ].join(' ')}
        style={{ opacity, scale, color: 'var(--line)', zIndex: 0, fontFamily: 'var(--font-serif)' }}
      >
        {numeral}
      </motion.span>
      <div className={['relative z-10', isDisplay ? 'pl-0 md:pl-2' : 'pl-6 md:pl-8'].join(' ')}>
        <h1
          className={[
            'font-medium text-[var(--ink-1)]',
            isDisplay
              ? isBook
                ? 'text-[clamp(40px,5vw,70px)] leading-[1.14] tracking-[0.01em] max-w-[10.5ch] md:max-w-[11.5ch]'
                : 'text-[clamp(42px,6.4vw,84px)] leading-[1.06] tracking-[-0.035em] max-w-[8.5ch] md:max-w-[9.5ch]'
              : isBook
                ? 'text-[clamp(28px,3vw,40px)] leading-[1.28] tracking-[0.01em] max-w-[15ch]'
                : 'text-[clamp(32px,4vw,52px)] leading-[1.12] tracking-tight max-w-[14ch]',
            titleClassName,
          ].filter(Boolean).join(' ')}
          style={{ fontFamily: isBook ? 'var(--font-serif)' : 'var(--font-display)' }}
        >
          {title}
        </h1>
      </div>
    </div>
  )
}
