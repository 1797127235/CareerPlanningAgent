import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  description: string
  ctaText: string
  ctaHref: string
}

export function EmptyState({ icon, title, description, ctaText, ctaHref }: EmptyStateProps) {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
      className="max-w-md mx-auto mt-20 text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-[rgba(37,99,235,0.08)] mx-auto mb-4 flex items-center justify-center text-3xl text-[var(--blue)]">
        {icon}
      </div>
      <h2 className="text-[18px] font-semibold text-[var(--text-1)] mb-2">{title}</h2>
      <p className="text-[15px] text-[var(--text-3)] mb-6">{description}</p>
      <button
        onClick={() => navigate(ctaHref)}
        className="btn-cta px-5 py-2.5 text-[14px] font-semibold cursor-pointer"
      >
        {ctaText}
      </button>
    </motion.div>
  )
}
