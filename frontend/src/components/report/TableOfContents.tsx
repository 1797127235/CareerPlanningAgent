import { useEffect, useState } from 'react'

interface TOCItem {
  id: string
  numeral: string
  label: string
}

/**
 * Sticky-in-layout chapter nav. Lives inside its grid cell (no `fixed`
 * positioning), so the parent page decides when to show/hide it via
 * container queries. This avoids collisions with any globally-positioned
 * right-side UI (e.g. the persistent chat panel).
 *
 * Scroll-spy via IntersectionObserver: the chapter closest to ~40% viewport
 * is marked active.
 */
export function TableOfContents({ items }: { items: TOCItem[] }) {
  const [activeId, setActiveId] = useState<string | null>(items[0]?.id ?? null)

  useEffect(() => {
    const observers: IntersectionObserver[] = []
    items.forEach((item) => {
      const el = document.getElementById(item.id)
      if (!el) return
      const obs = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) setActiveId(item.id)
          })
        },
        { rootMargin: '-30% 0px -60% 0px' },
      )
      obs.observe(el)
      observers.push(obs)
    })
    return () => observers.forEach((o) => o.disconnect())
  }, [items])

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault()
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <nav aria-label="章节导航" className="sticky top-24 w-full">
      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-400 mb-4">
        目录
      </p>
      <ul className="space-y-3">
        {items.map((item) => {
          const active = activeId === item.id
          return (
            <li key={item.id}>
              <a
                href={`#${item.id}`}
                onClick={(e) => handleClick(e, item.id)}
                className={[
                  'flex items-baseline gap-2 text-[12px] transition-colors',
                  active
                    ? 'text-slate-900 font-semibold'
                    : 'text-slate-400 hover:text-slate-700',
                ].join(' ')}
              >
                <span className="tabular-nums w-5 shrink-0 text-right">{item.numeral}</span>
                <span
                  className={[
                    'transition-[border-color] duration-200 pb-0.5',
                    active ? 'border-b-2 border-slate-900' : 'border-b-2 border-transparent',
                  ].join(' ')}
                >
                  {item.label}
                </span>
              </a>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
