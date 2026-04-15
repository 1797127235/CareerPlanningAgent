import { Brain } from 'lucide-react'
import { motion } from 'framer-motion'

export function SjtCta({ onStart }: { onStart: () => void }) {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
      className="rounded-xl p-6 md:p-8 bg-[var(--bg-card)] border border-[var(--line)] shadow-[var(--shadow-paper)] text-center"
    >
      <div className="w-12 h-12 rounded-full bg-[var(--bg-paper)] flex items-center justify-center mx-auto mb-4">
        <Brain className="w-6 h-6 text-[var(--chestnut)]" />
      </div>
      <h3 className="font-display text-[length:var(--fs-display-sm)] text-[var(--ink-1)] mb-2">
        一个 3 分钟的情境小测
      </h3>
      <p className="text-[length:var(--fs-body)] text-[var(--ink-2)] mb-6 max-w-[40ch] mx-auto">
        帮系统理解你做事的偏好。没有标准答案，选最真实的就好。
      </p>
      <button
        onClick={onStart}
        className="inline-flex items-center px-5 py-2.5 rounded-full bg-[var(--chestnut)] text-white text-[13px] font-medium hover:opacity-90 transition-opacity"
      >
        开始测试
      </button>
    </motion.div>
  )
}
