import { motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { Kicker } from './Kicker'

export interface ChapterProps {
  numeral: string
  label: string
  title: ReactNode
  intro?: string
  children?: ReactNode
}

export function Chapter({ numeral, label, title, intro, children }: ChapterProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="relative py-24 md:py-32"
    >
      <Kicker>Chapter {numeral} · {label}</Kicker>
      <h2 className="font-display font-medium text-[var(--fs-display-lg)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight max-w-[22ch]">
        {title}
      </h2>
      {intro && (
        <p className="mt-6 font-sans text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[68ch]">
          {intro}
        </p>
      )}
      <div className="mt-12">{children}</div>
    </motion.section>
  )
}
