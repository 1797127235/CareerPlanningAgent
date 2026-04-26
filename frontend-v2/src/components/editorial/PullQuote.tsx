import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

type PullQuoteVariant = 'editorial' | 'book'

export function PullQuote({
  children,
  attribution,
  variant = 'editorial',
  className = '',
}: {
  children: ReactNode
  attribution?: string
  variant?: PullQuoteVariant
  className?: string
}) {
  const shouldReduceMotion = useReducedMotion()
  const isBook = variant === 'book'

  const lineVariants = {
    hidden: { scaleX: shouldReduceMotion ? 1 : 0 },
    visible: {
      scaleX: 1,
      transition: { duration: 0.4, ease: 'easeOut' },
    },
  }

  const contentVariants = {
    hidden: { opacity: shouldReduceMotion ? 1 : 0 },
    visible: {
      opacity: 1,
      transition: { duration: 0.4, ease: 'easeOut' },
    },
  }

  return (
    <motion.figure
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.3 }}
      className={[
        isBook ? 'my-8 md:my-10 max-w-[44rem] mx-auto text-center' : 'my-10 max-w-[58ch] mx-auto text-center',
        className,
      ].filter(Boolean).join(' ')}
    >
      <motion.div variants={lineVariants} className="h-px bg-[var(--line)] origin-left" />
      <motion.blockquote
        variants={contentVariants}
        className={[
          isBook
            ? 'py-5 md:py-6 font-serif italic text-[clamp(26px,3vw,38px)] leading-[1.55] text-[var(--chestnut)]'
            : 'py-6 font-serif italic text-[length:var(--fs-quote)] leading-[1.4] text-[var(--chestnut)]',
        ].join(' ')}
        style={{ fontFamily: 'var(--font-serif)' }}
      >
        “{children}”
      </motion.blockquote>
      {attribution && (
        <motion.figcaption
          variants={contentVariants}
          className={[
            isBook
              ? 'pb-5 text-[10px] uppercase tracking-[0.18em] text-[var(--ink-3)]'
              : 'pb-6 text-[length:var(--fs-caption)] uppercase tracking-[0.2em] text-[var(--ink-3)]',
          ].join(' ')}
        >
          — {attribution}
        </motion.figcaption>
      )}
      <motion.div variants={lineVariants} className="h-px bg-[var(--line)] origin-left" />
    </motion.figure>
  )
}
