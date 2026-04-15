import { motion, useReducedMotion } from 'framer-motion'

export function DropCap({ children }: { children: string }) {
  const [first, ...rest] = children
  const isChinese = /[\u4e00-\u9fff]/.test(first)
  const shouldReduceMotion = useReducedMotion()

  return (
    <p className="text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
      <motion.span
        initial={{ color: shouldReduceMotion ? 'var(--chestnut)' : 'var(--ink-2)' }}
        whileInView={{ color: 'var(--chestnut)' }}
        viewport={{ once: true, amount: 0.5 }}
        transition={{ duration: shouldReduceMotion ? 0 : 0.6 }}
        className={
          isChinese
            ? 'float-left font-serif text-[64px] leading-[0.85] mr-2 mt-1'
            : 'float-left font-serif text-[56px] leading-[0.85] mr-1 mt-1'
        }
        style={{ fontFamily: 'var(--font-serif)' }}
      >
        {first}
      </motion.span>
      {rest.join('')}
    </p>
  )
}
