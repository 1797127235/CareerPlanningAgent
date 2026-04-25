import { X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { Skill } from '@/types/profile'

const LEVEL_ORDER: Record<string, number> = {
  expert: 3,
  advanced: 3,
  proficient: 2,
  intermediate: 2,
  familiar: 1,
  beginner: 0,
}

const LEVEL_LABEL: Record<string, string> = {
  expert: '熟练掌握',
  advanced: '熟练掌握',
  proficient: '比较熟练',
  intermediate: '比较熟练',
  familiar: '了解',
  beginner: '刚接触',
}

const LEVEL_COLOR: Record<string, string> = {
  expert: 'bg-[var(--chestnut)] text-white border-[var(--chestnut)]',
  advanced: 'bg-[var(--chestnut)] text-white border-[var(--chestnut)]',
  proficient: 'bg-emerald-700 text-white border-emerald-700',
  intermediate: 'bg-emerald-700 text-white border-emerald-700',
  familiar: 'bg-[var(--ink-2)] text-white border-[var(--ink-2)]',
  beginner: 'bg-[var(--ink-3)] text-white border-[var(--ink-3)]',
}

const CHIP = {
  initial: { opacity: 0, scale: 0.85 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.85 },
  transition: { duration: 0.15, ease: [0.22, 1, 0.36, 1] as const },
}

export function SkillChips({
  skills,
  onEdit,
  onDelete,
}: {
  skills: Skill[]
  onEdit?: (skill: Skill) => void
  onDelete?: (skill: Skill) => void
}) {
  const grouped = skills.reduce<Record<string, Skill[]>>((acc, s) => {
    const lvl = s.level || 'beginner'
    acc[lvl] = acc[lvl] || []
    acc[lvl].push(s)
    return acc
  }, {})

  const ordered = Object.keys(grouped).sort((a, b) => LEVEL_ORDER[b] - LEVEL_ORDER[a])

  if (skills.length === 0) {
    return <p className="text-[length:var(--fs-body)] text-[var(--ink-3)] italic">还没有技能记录 —— 加一个是一个。</p>
  }

  return (
    <div className="space-y-5">
      {ordered.map((lvl) => {
        const list = grouped[lvl]
        if (!list?.length) return null
        return (
          <div key={lvl}>
            <p className="text-[12px] font-medium text-[var(--ink-3)] mb-2">
              {LEVEL_LABEL[lvl]}（{list.length}）
            </p>
            <div className="flex flex-wrap gap-2">
              <AnimatePresence>
                {list.map((s) => (
                  <motion.button
                    key={s.name}
                    layout
                    {...CHIP}
                    onClick={() => onEdit?.(s)}
                    className={[
                      'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[13px] font-medium border active:scale-95 transition-transform',
                      LEVEL_COLOR[lvl],
                    ].join(' ')}
                  >
                    {s.name}
                    {onDelete && (
                      <span
                        onClick={(e) => {
                          e.stopPropagation()
                          onDelete(s)
                        }}
                        className="ml-0.5 p-0.5 hover:bg-white/20 rounded-full transition-colors duration-150"
                      >
                        <X className="w-3 h-3" />
                      </span>
                    )}
                  </motion.button>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )
      })}
    </div>
  )
}
