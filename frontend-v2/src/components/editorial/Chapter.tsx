import { motion, useReducedMotion } from 'framer-motion'
import { Children } from 'react'
import type { ReactNode } from 'react'
import { Kicker } from './Kicker'

export interface ChapterProps {
  numeral: string
  label: string
  title?: ReactNode
  intro?: ReactNode
  children?: ReactNode
  compact?: boolean
  className?: string
  bodyClassName?: string
  kickerClassName?: string
  titleClassName?: string
  introClassName?: string
}

export function Chapter({
  numeral,
  label,
  title,
  intro,
  children,
  compact = false,
  className = '',
  bodyClassName = '',
  kickerClassName = '',
  titleClassName = '',
  introClassName = '',
}: ChapterProps) {
  const shouldReduceMotion = useReducedMotion()

  const containerVariants = {
    hidden: { opacity: shouldReduceMotion ? 1 : 0, y: shouldReduceMotion ? 0 : 12 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        ease: [0.22, 1, 0.36, 1],
        staggerChildren: shouldReduceMotion ? 0 : 0.08,
      },
    },
  }

  const childVariants = {
    hidden: { opacity: shouldReduceMotion ? 1 : 0, y: shouldReduceMotion ? 0 : 12 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
    },
  }

  return (
    <motion.section
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
      variants={containerVariants}
      className={['relative', compact ? 'py-8 md:py-10' : 'py-16 md:py-24', className].filter(Boolean).join(' ')}
    >
      <motion.div variants={childVariants}>
        <Kicker className={[compact ? 'mb-2' : '', kickerClassName].filter(Boolean).join(' ')}>
          Chapter {numeral} · {label}
        </Kicker>
      </motion.div>
      {title && (
        <motion.h2
          variants={childVariants}
          className={[
            'font-display font-medium text-[length:var(--fs-display-lg)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight max-w-[22ch]',
            titleClassName,
          ].filter(Boolean).join(' ')}
        >
          {title}
        </motion.h2>
      )}
      {intro && (
        <motion.div
          variants={childVariants}
          className={[
            'mt-6 font-sans text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[68ch]',
            introClassName,
          ].filter(Boolean).join(' ')}
        >
          {intro}
        </motion.div>
      )}
      <div className={[compact ? 'mt-6 md:mt-8' : 'mt-12', bodyClassName].filter(Boolean).join(' ')}>
        {Children.map(children, (child, i) => (
          <motion.div key={i} variants={childVariants}>
            {child}
          </motion.div>
        ))}
      </div>
    </motion.section>
  )
}
