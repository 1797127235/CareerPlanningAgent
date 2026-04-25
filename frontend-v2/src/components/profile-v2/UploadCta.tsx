import { Upload } from 'lucide-react'
import { motion } from 'framer-motion'

const uploadSteps = ['选择文件', '解析简历', '合并画像']

function CircularProgress({ progress, size = 64 }: { progress: number; size?: number }) {
  const stroke = 4
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (progress / 100) * circumference
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        stroke="var(--line)"
        strokeWidth={stroke}
        fill="transparent"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        stroke="var(--chestnut)"
        strokeWidth={stroke}
        fill="transparent"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-500"
      />
    </svg>
  )
}

export function UploadCta({
  step,
  totalSteps = 3,
  label,
  subLabel,
  onClick,
}: {
  step: number
  totalSteps?: number
  label: string
  subLabel?: string
  onClick: () => void
}) {
  const isUploading = step > 0 && step <= totalSteps
  const progress = isUploading ? ((step) / totalSteps) * 100 : 0
  const stepLabel = isUploading ? uploadSteps[step - 1] || '处理中' : ''

  return (
    <button
      onClick={onClick}
      disabled={isUploading}
      className="group relative flex items-center gap-5 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] px-6 py-5 text-left hover:shadow-[var(--shadow-paper)] transition-shadow disabled:opacity-80"
    >
      <div className="relative shrink-0">
        {isUploading ? (
          <CircularProgress progress={progress} size={56} />
        ) : (
          <div className="w-14 h-14 rounded-full bg-[var(--bg-paper)] flex items-center justify-center">
            <Upload className="w-5 h-5 text-[var(--chestnut)]" />
          </div>
        )}
        {!isUploading && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-[var(--chestnut)]"
          />
        )}
      </div>
      <div>
        <p className="font-sans text-[length:var(--fs-body-lg)] font-medium text-[var(--ink-1)]">
          {isUploading ? stepLabel : label}
        </p>
        {subLabel && !isUploading && (
          <p className="text-[length:var(--fs-body)] text-[var(--ink-2)]">{subLabel}</p>
        )}
        {isUploading && (
          <p className="text-[13px] text-[var(--ink-3)]">请稍等，正在处理简历…</p>
        )}
      </div>
    </button>
  )
}
