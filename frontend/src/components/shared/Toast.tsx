import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

interface ToastProps {
  message: string
  type: 'success' | 'error'
  onClose: () => void
}

export function Toast({ message, type, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000)
    return () => clearTimeout(timer)
  }, [onClose])

  const colorClass = type === 'error' ? 'text-red-600' : 'text-green-600'

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
      <button onClick={onClose} className="shrink-0 hover:opacity-70 cursor-pointer" aria-label="关闭通知">
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  )
}

/* Convenience wrapper for page-level toast state */
interface ToastContainerProps {
  toast: { message: string; type: 'success' | 'error' } | null
  onClose: () => void
}

export function ToastContainer({ toast, onClose }: ToastContainerProps) {
  return (
    <AnimatePresence>
      {toast && <Toast message={toast.message} type={toast.type} onClose={onClose} />}
    </AnimatePresence>
  )
}
