import { motion } from 'framer-motion'
import { Trash2 } from 'lucide-react'

interface ConfirmDialogProps {
  message: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  message,
  confirmText = '删除',
  cancelText = '取消',
  danger = true,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
      {/* Backdrop */}
      <motion.div
        className="absolute inset-0"
        style={{ background: 'rgba(31,31,31,0.25)', backdropFilter: 'blur(6px)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onCancel}
      />

      {/* Dialog */}
      <motion.div
        initial={{ opacity: 0, scale: 0.92, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.92, y: 12 }}
        transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }}
        className="relative w-full max-w-[300px] z-10"
        style={{
          background: 'rgba(252,250,247,0.96)',
          backdropFilter: 'blur(32px) saturate(160%)',
          WebkitBackdropFilter: 'blur(32px) saturate(160%)',
          borderRadius: 20,
          border: '1px solid var(--line)',
          boxShadow: '0 24px 48px rgba(0,0,0,0.14), 0 8px 16px rgba(0,0,0,0.08)',
        }}
      >
        <div className="px-6 pt-6 pb-5 text-center">
          {/* Icon */}
          <div className="w-11 h-11 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: danger ? 'rgba(184,92,56,0.10)' : 'rgba(37,99,235,0.10)' }}>
            <Trash2 className="w-5 h-5" style={{ color: danger ? 'var(--chestnut)' : '#2563EB' }} />
          </div>

          <p className="text-[14px] font-semibold leading-relaxed" style={{ color: 'var(--ink-1)' }}>{message}</p>
        </div>

        {/* Buttons */}
        <div className="flex gap-2.5 px-4 pb-4">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 rounded-xl text-[13px] font-semibold transition-colors cursor-pointer"
            style={{
              color: 'var(--ink-2)',
              background: 'rgba(0,0,0,0.05)',
              border: '1px solid rgba(0,0,0,0.06)',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.08)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.05)')}
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-2.5 rounded-xl text-[13px] font-semibold text-white transition-colors cursor-pointer"
            style={{
              background: danger ? 'var(--chestnut)' : '#2563EB',
              boxShadow: danger ? '0 4px 12px rgba(184,92,56,0.30)' : '0 4px 12px rgba(37,99,235,0.30)',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.88')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            {confirmText}
          </button>
        </div>
      </motion.div>
    </div>
  )
}
