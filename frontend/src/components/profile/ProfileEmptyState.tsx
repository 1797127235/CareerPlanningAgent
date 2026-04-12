import { motion } from 'framer-motion'
import { FileText, PencilLine } from 'lucide-react'
import { cardVariants } from './constants'

interface ProfileEmptyStateProps {
  onUpload: () => void
  onManualEntry: () => void
  hint?: string
}

const cards = [
  { icon: FileText, title: '上传简历', action: 'upload' as const },
  { icon: PencilLine, title: '手动填写', action: 'manual' as const },
]

export function ProfileEmptyState({ onUpload, onManualEntry, hint }: ProfileEmptyStateProps) {
  return (
    <motion.div
      key="empty"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.25 }}
      className="flex flex-col items-center justify-center"
      style={{ minHeight: 'calc(100vh - 56px - 48px)' }}
    >
      {hint && (
        <div className="mb-5 px-4 py-3 rounded-xl bg-blue-50 border border-blue-200 text-[13px] text-blue-700 max-w-[340px] text-center">
          {hint}
        </div>
      )}
      <p className="text-[15px] text-[var(--text-2)] mb-6">选择一种方式开始建立你的能力画像</p>
      <div className="flex gap-5">
        {cards.map((card, i) => {
          const Icon = card.icon
          return (
            <motion.div
              key={card.title}
              custom={i}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              onClick={card.action === 'upload' ? onUpload : onManualEntry}
              className="glass w-[200px] px-7 py-10 text-center cursor-pointer"
            >
              <div className="g-inner">
                <div className="w-12 h-12 rounded-xl mx-auto mb-4 flex items-center justify-center bg-white/30 border border-white/40 text-[var(--blue)]">
                  <Icon className="w-5 h-5" strokeWidth={2} />
                </div>
                <h3 className="text-base font-bold text-[var(--text-1)]">{card.title}</h3>
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}
