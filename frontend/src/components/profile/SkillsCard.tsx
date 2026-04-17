/* eslint-disable @typescript-eslint/no-explicit-any */
import { motion } from 'framer-motion'
import type { Skill } from '@/types/profile'
import { levelConfig, levelOrder, tagVariants } from './constants'

interface SkillsCardProps {
  skills: Skill[]
  stagger: number
  cardVariants: any
}

/* Badge: matches HTML .sb-exp / .sb-pro / .sb-fam */
const badgeStyle: Record<string, string> = {
  expert:       'bg-[var(--blue)] text-white',
  advanced:     'bg-[var(--blue)] text-white',
  proficient:   'bg-[var(--blue)]/10 text-[var(--blue)] border border-[var(--blue)]/20',
  intermediate: 'bg-white/30 text-[var(--text-2)] border border-white/40',
  familiar:     'bg-white/30 text-[var(--text-3)]',
  beginner:     'bg-white/30 text-[var(--text-3)]',
  entry:        'bg-white/30 text-[var(--text-3)]',
}

function SkillRow({ skill, index }: { skill: Skill; index: number }) {
  const cfg = levelConfig[skill.level] ?? levelConfig.beginner
  const badge = badgeStyle[skill.level] ?? badgeStyle.beginner
  return (
    <motion.div
      custom={index}
      variants={tagVariants}
      initial="hidden"
      animate="visible"
      className="flex items-center justify-between px-4 py-2.5 last:border-b-0 hover:bg-white/20 hover:scale-[1.01] hover:shadow-sm transition-all duration-150 cursor-default"
    >
      <span className="text-[13px] font-medium text-[var(--text-1)]">{skill.name}</span>
      <span className={`text-[10px] font-bold w-[26px] h-5 flex items-center justify-center flex-shrink-0 rounded-sm ${badge}`}>
        {cfg.label.charAt(0)}
      </span>
    </motion.div>
  )
}

export function SkillsCard({ skills, stagger, cardVariants }: SkillsCardProps) {
  if (skills.length === 0) {
    return (
      <motion.div custom={4 * stagger} variants={cardVariants} initial="hidden" animate="visible">
        <span className="text-sm text-slate-400">暂无技能数据，请上传简历或手动添加</span>
      </motion.div>
    )
  }

  // Sort by level, then split evenly — ensures both columns always have content
  const sorted = [...skills].sort(
    (a, b) => levelOrder.indexOf(a.level) - levelOrder.indexOf(b.level),
  )
  const mid = Math.ceil(sorted.length / 2)
  const leftCol = sorted.slice(0, mid)
  const rightCol = sorted.slice(mid)

  return (
    <motion.div
      custom={4 * stagger}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      className="glass overflow-hidden"
    >
      <div className="g-inner">
        {/* Column headers */}
        <div className="grid grid-cols-2 border-b border-white/30">
          <div className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-[var(--text-2)] border-r border-white/30">
            精通 · 熟悉
          </div>
          <div className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-[var(--text-2)]">
            熟悉 · 入门
          </div>
        </div>
        {/* Two columns — always balanced */}
        <div className="grid grid-cols-2">
          <div className="border-r border-white/30 divide-y divide-white/20">
            {leftCol.map((skill, i) => (
              <SkillRow key={skill.name} skill={skill} index={i} />
            ))}
          </div>
          <div className="divide-y divide-white/20">
            {rightCol.map((skill, i) => (
              <SkillRow key={skill.name} skill={skill} index={mid + i} />
            ))}
            {rightCol.length === 0 && (
              <div className="px-4 py-3 text-[12px] text-[var(--text-3)]">—</div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
