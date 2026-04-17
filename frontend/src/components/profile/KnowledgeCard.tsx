/* eslint-disable @typescript-eslint/no-explicit-any */
import { motion } from 'framer-motion'

const AREA_COLORS = [
  'bg-blue-50 text-blue-700 border-blue-200/60',
  'bg-indigo-50 text-indigo-700 border-indigo-200/60',
  'bg-violet-50 text-violet-700 border-violet-200/60',
  'bg-sky-50 text-sky-700 border-sky-200/60',
  'bg-teal-50 text-teal-700 border-teal-200/60',
  'bg-cyan-50 text-cyan-700 border-cyan-200/60',
  'bg-emerald-50 text-emerald-700 border-emerald-200/60',
  'bg-amber-50 text-amber-700 border-amber-200/60',
]

const tagVariants: any = {
  hidden: { opacity: 0, scale: 0.8, y: 8 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1], delay: 0.1 + i * 0.05 },
  }),
}

interface KnowledgeCardProps {
  knowledgeAreas: string[]
  stagger: number
  cardVariants: any
}

export function KnowledgeCard({ knowledgeAreas, stagger, cardVariants }: KnowledgeCardProps) {
  if (knowledgeAreas.length === 0) {
    return (
      <motion.div custom={2 * stagger} variants={cardVariants} initial="hidden" animate="visible">
        <span className="text-sm text-slate-400">暂无知识领域数据</span>
      </motion.div>
    )
  }

  return (
    <motion.div
      custom={2 * stagger}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      className="flex flex-wrap gap-2.5 p-4"
    >
      {knowledgeAreas.map((area, i) => (
        <motion.span
          key={area}
          custom={i}
          variants={tagVariants}
          initial="hidden"
          animate="visible"
          whileHover={{ scale: 1.05, y: -2 }}
          transition={{ type: 'tween', duration: 0.15 }}
          className={`
            px-3.5 py-1.5 rounded-lg text-[13px] font-medium
            border cursor-default select-none
            ${AREA_COLORS[i % AREA_COLORS.length]}
          `}
        >
          {area}
        </motion.span>
      ))}
    </motion.div>
  )
}
