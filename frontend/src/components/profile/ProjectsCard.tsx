/* eslint-disable @typescript-eslint/no-explicit-any */
import { motion } from 'framer-motion'
import { FolderGit2 } from 'lucide-react'
import { tagVariants } from './constants'

interface ProjectsCardProps {
  projects: string[]
  stagger: number
  cardVariants: any
}

export function ProjectsCard({ projects, stagger, cardVariants }: ProjectsCardProps) {
  if (projects.length === 0) return null

  return (
    <motion.div
      custom={5 * stagger}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
    >
      <div className="flex items-center justify-between mb-4 px-1">
        <h3 className="text-[15px] font-bold text-slate-900 tracking-tight">项目经历</h3>
        <span className="text-[12px] font-medium text-slate-500">{projects.length} 个项目</span>
      </div>
      <div className="glass overflow-hidden">
        <div className="g-inner divide-y divide-white/20">
          {projects.map((project, i) => (
            <motion.div
              key={i}
              custom={i}
              variants={tagVariants}
              initial="hidden"
              animate="visible"
              className="flex items-center gap-3 px-5 py-3.5 hover:bg-white/20 transition-colors"
            >
              <FolderGit2 className="w-4 h-4 text-slate-400 shrink-0" />
              <span className="text-[13px] font-medium text-[var(--text-1)]">{project}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
