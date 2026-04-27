import { motion, useScroll, useSpring } from 'framer-motion'

export function ReadingProgressBar() {
  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001,
  })

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 h-[2px] origin-left z-50"
      style={{
        scaleX,
        background: 'var(--chestnut)',
        boxShadow: '0 0 6px oklch(0.42 0.10 30 / 0.35)',
      }}
    />
  )
}
