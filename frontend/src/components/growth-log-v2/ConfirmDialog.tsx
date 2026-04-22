interface ConfirmDialogProps {
  open: boolean
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = '确认',
  cancelLabel = '取消',
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-slate-900/20"
        style={{ backdropFilter: 'blur(4px)' }}
        onClick={onCancel}
      />
      <div className="relative z-10 w-full max-w-[400px] glass-static p-5">
        <div className="g-inner">
        <h3 className="text-[15px] font-bold text-[var(--text-1)]">{title}</h3>
        {message && (
          <p className="mt-2 text-[13px] text-[var(--text-2)] leading-relaxed">{message}</p>
        )}
        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-[13px] font-medium text-[var(--text-2)] hover:text-[var(--text-1)] cursor-pointer"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={[
              'px-3 py-1.5 text-[13px] font-semibold text-white rounded-md transition-colors cursor-pointer',
              danger
                ? 'bg-red-500 hover:bg-red-600'
                : 'bg-[var(--text-1)] hover:bg-[var(--blue)]',
            ].join(' ')}
          >
            {confirmLabel}
          </button>
        </div>
        </div>
      </div>
    </div>
  )
}
