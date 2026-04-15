import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

export function PullQuote({ children, attribution }: { children: ReactNode; attribution?: string }) {
  const shouldReduceMotion = useReducedMotion()

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
      className="my-10 max-w-[58ch] mx-auto text-center"
    >
      <motion.div
        variants={lineVariants}
        className="h-px bg-[var(--line)] origin-left"
      />
      <motion.blockquote
        variants={contentVariants}
        className="py-6 font-serif italic text-[var(--fs-quote)] leading-[1.4] text-[var(--chestnut)]"
      >
        "{children}"
      </motion.blockquote>
      {attribution && (
        <motion.figcaption
          variants={contentVariants}
          className="pb-6 text-[var(--fs-caption)] uppercase tracking-[0.2em] text-[var(--ink-3)]"
        >
          — {attribution}
        </motion.figcaption>
      )}
      <motion.div
        variants={lineVariants}
        className="h-px bg-[var(--line)] origin-left"
      />
    </motion.figure>
  )
}
