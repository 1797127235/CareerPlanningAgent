import { useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

const EASE_OUT = [0.22, 1, 0.36, 1] as const

interface EditModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  onSave?: () => void
  saving?: boolean
  saveLabel?: string
  width?: number
}

export function EditModal({
  open,
  onClose,
  title,
  children,
  onSave,
  saving = false,
  saveLabel = '保存',
  width = 520,
}: EditModalProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [open, handleKeyDown])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[900] flex items-center justify-center p-6"
          style={{ background: 'rgba(26, 22, 20, 0.25)', backdropFilter: 'blur(4px)' }}
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.25, ease: EASE_OUT }}
            className="bg-[var(--bg-card)] rounded-[var(--radius-lg)] border border-[var(--line)] overflow-hidden"
            style={{
              width: '100%',
              maxWidth: width,
              maxHeight: '80vh',
              boxShadow: '0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div
              className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 border-b border-[var(--line)]"
              style={{ background: 'var(--bg-card)' }}
            >
              <h3
                className="text-[16px] font-semibold text-[var(--ink-1)]"
                style={{ fontFamily: 'var(--font-serif)' }}
              >
                {title}
              </h3>
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-[var(--radius-sm)] flex items-center justify-center text-[var(--ink-3)] hover:text-[var(--ink-1)] hover:bg-[var(--bg-paper)] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Body */}
            <div className="overflow-y-auto px-6 py-5" style={{ maxHeight: 'calc(80vh - 120px)' }}>
              {children}
            </div>

            {/* Footer */}
            {onSave && (
              <div
                className="sticky bottom-0 flex items-center justify-end gap-3 px-6 py-4 border-t border-[var(--line)]"
                style={{ background: 'var(--bg-card)' }}
              >
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] hover:bg-[var(--bg-paper)] border border-[var(--line)] transition-colors cursor-pointer"
                >
                  取消
                </button>
                <button
                  onClick={onSave}
                  disabled={saving}
                  className="px-5 py-2 rounded-[var(--radius-sm)] text-[13px] font-semibold text-white transition-all cursor-pointer disabled:opacity-50"
                  style={{ background: 'var(--chestnut)' }}
                >
                  {saving ? '保存中...' : saveLabel}
                </button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

/* ── Form primitives ── */

export function FormField({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="mb-4">
      <label className="block text-[13px] font-medium text-[var(--ink-1)] mb-1.5">
        {label}
        {hint && <span className="ml-1 text-[12px] text-[var(--ink-3)] font-normal">{hint}</span>}
      </label>
      {children}
    </div>
  )
}

export function FormInput({
  value,
  onChange,
  placeholder,
  type = 'text',
  disabled = false,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
  disabled?: boolean
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className="w-full px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg-card)] text-[14px] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] transition-colors hover:border-[var(--chestnut-light)] focus:outline-none focus:border-[var(--chestnut)] disabled:opacity-50"
      style={{ boxShadow: 'none' }}
    />
  )
}

export function FormSelect({
  value,
  onChange,
  options,
}: {
  value: string
  onChange: (v: string) => void
  options: Array<{ value: string; label: string }>
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg-card)] text-[14px] text-[var(--ink-1)] transition-colors hover:border-[var(--chestnut-light)] focus:outline-none focus:border-[var(--chestnut)] cursor-pointer"
      style={{
        appearance: 'none',
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 12 12' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M3 4.5L6 7.5L9 4.5' stroke='%239A9590' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 12px center',
        paddingRight: '36px',
      }}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  )
}

export function FormRow({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-4">{children}</div>
}
