import { X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const CHIP = {
  initial: { opacity: 0, scale: 0.85 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.85 },
  transition: { duration: 0.15, ease: [0.22, 1, 0.36, 1] as const },
}

export function KnowledgeChips({
  areas,
  onDelete,
}: {
  areas: string[]
  onDelete?: (area: string) => void
}) {
  if (areas.length === 0) {
    return <p className="text-[length:var(--fs-body)] text-[var(--ink-3)] italic">还没有知识领域记录。</p>
  }
  return (
    <div className="flex flex-wrap gap-2">
      <AnimatePresence>
        {areas.map((a) => (
          <motion.span
            key={a}
            layout
            {...CHIP}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[13px] font-medium bg-[var(--bg-paper)] text-[var(--ink-2)] border border-[var(--line)]"
          >
            {a}
            {onDelete && (
              <button
                onClick={() => onDelete(a)}
                className="p-0.5 hover:bg-[var(--line)] rounded-full transition-colors duration-150"
                aria-label="删除"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </motion.span>
        ))}
      </AnimatePresence>
    </div>
  )
}
