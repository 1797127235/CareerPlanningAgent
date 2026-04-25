import { useEffect, useState } from 'react'

export function Tooltip({
  content,
  storageKey,
  children,
}: {
  content: string
  storageKey: string
  children: React.ReactNode
}) {
  const [dismissedKeys, setDismissedKeys] = useState<Record<string, true>>({})

  const flashing =
    typeof window !== 'undefined' &&
    !dismissedKeys[storageKey] &&
    !window.localStorage.getItem(`tooltip-seen-${storageKey}`)

  useEffect(() => {
    if (!flashing) return

    const timer = window.setTimeout(() => {
      setDismissedKeys((prev) => ({ ...prev, [storageKey]: true }))
      window.localStorage.setItem(`tooltip-seen-${storageKey}`, '1')
    }, 1500)

    return () => window.clearTimeout(timer)
  }, [flashing, storageKey])

  return (
    <span className="relative inline-flex items-center gap-1 group/tooltip">
      {children}
      <span className="inline-flex items-center justify-center w-4 h-4 rounded-full border border-[var(--line)] text-[var(--text-2xs)] text-[var(--ink-3)] cursor-help select-none">
        ?
      </span>
      <span
        className={[
          'pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-[240px] px-3 py-2 rounded-[var(--radius-md)] bg-[var(--ink-1)] text-[var(--bg-paper)] text-[var(--text-xs)] shadow-[var(--shadow-float)] z-50 transition-opacity duration-200',
          'opacity-0 group-hover/tooltip:opacity-100',
          flashing ? 'opacity-100' : '',
        ].join(' ')}
      >
        {content}
        <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-[var(--ink-1)]" />
      </span>
    </span>
  )
}
