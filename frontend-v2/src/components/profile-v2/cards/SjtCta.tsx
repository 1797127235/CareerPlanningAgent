import { Brain } from 'lucide-react'

export function SjtCta({ onStart }: { onStart: () => void }) {
  return (
    <div className="rounded-[var(--radius-md)] p-5 md:p-6 bg-[var(--bg-card)] border border-[var(--line)] shadow-[var(--shadow-block)]">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-[var(--bg-paper)] flex items-center justify-center shrink-0">
          <Brain className="w-5 h-5 text-[var(--chestnut)]" />
        </div>
        <div>
          <h3 className="text-[var(--text-base)] font-medium text-[var(--ink-1)]">
            一个 3 分钟的情境小测
          </h3>
          <p className="mt-1 text-[var(--text-sm)] text-[var(--ink-2)] max-w-[40ch]">
            帮系统理解你做事的偏好。没有标准答案，选最真实的就好。
          </p>
          <button
            onClick={onStart}
            className="mt-3 inline-flex items-center px-4 py-2 rounded-full bg-[var(--chestnut)] text-white text-[var(--text-xs)] font-medium hover:opacity-90 transition-opacity duration-200 active:scale-[0.98]"
          >
            开始测试
          </button>
        </div>
      </div>
    </div>
  )
}
