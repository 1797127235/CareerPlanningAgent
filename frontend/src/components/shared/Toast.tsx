import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastAction {
  label: string
  onClick: () => void
}

export interface ToastState {
  message: string
  type?: ToastType
  action?: ToastAction
  durationMs?: number
}

interface ToastProps extends ToastState {
  onClose: () => void
}

const TYPE_COLOR: Record<ToastType, string> = {
  success: 'text-green-600',
  error: 'text-red-600',
  info: 'text-slate-700',
}

export function Toast({ message, type = 'success', action, durationMs = 3000, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, durationMs)
    return () => clearTimeout(timer)
  }, [onClose, durationMs])

  const colorClass = TYPE_COLOR[type]

  const handleAction = () => {
    action?.onClick()
    onClose()
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      style={{ position: 'fixed', top: '16px', right: '16px', zIndex: 9999 }}
      className={`flex items-center gap-3 rounded-xl px-4 py-3 text-[14px] font-medium
        bg-white/90 backdrop-blur-md border border-white/60
        shadow-[0_4px_20px_rgba(0,0,0,0.10)] ${colorClass}`}
    >
      <span>{message}</span>
      {action && (
        <button
          onClick={handleAction}
          className="shrink-0 text-[13px] font-semibold text-blue-600 hover:text-blue-800 underline underline-offset-4 decoration-blue-300 transition-colors cursor-pointer"
        >
          {action.label}
        </button>
      )}
      <button onClick={onClose} className="shrink-0 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer" aria-label="关闭通知">
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  )
}

interface ToastContainerProps {
  toast: ToastState | null
  onClose: () => void
}

export function ToastContainer({ toast, onClose }: ToastContainerProps) {
  return (
    <AnimatePresence>
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          action={toast.action}
          durationMs={toast.durationMs}
          onClose={onClose}
        />
      )}
    </AnimatePresence>
  )
}
