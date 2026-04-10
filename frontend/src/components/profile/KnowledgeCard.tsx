/* eslint-disable @typescript-eslint/no-explicit-any */
import { motion } from 'framer-motion'
import { tagVariants } from './constants'

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
      className="flex flex-wrap gap-2 p-4"
    >
      {knowledgeAreas.map((area, i) => (
        <motion.span
          key={area}
          custom={i}
          variants={tagVariants}
          initial="hidden"
          animate="visible"
          className="chip text-[13px] font-medium text-[var(--text-1)] cursor-default"
        >
          {area}
        </motion.span>
      ))}
    </motion.div>
  )
}
