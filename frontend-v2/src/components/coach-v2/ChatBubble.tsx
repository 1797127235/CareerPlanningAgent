import { motion } from 'framer-motion'
import { EditorialMarkdown } from './EditorialMarkdown'

export function ChatBubble({
  role,
  text,
  streaming,
}: {
  role: 'user' | 'assistant'
  text: string
  streaming?: boolean
}) {
  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-[var(--bg-paper-2)] rounded-2xl px-5 py-3">
          <p className="font-sans text-[length:var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
            {text}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[60ch]">
        <EditorialMarkdown source={text} />
        {streaming && (
          <motion.span
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 0.8, repeat: Infinity, ease: 'easeInOut' }}
            className="font-mono text-[length:var(--fs-body)] text-[var(--ink-1)]"
          >
            ▍
          </motion.span>
        )}
      </div>
    </div>
  )
}
