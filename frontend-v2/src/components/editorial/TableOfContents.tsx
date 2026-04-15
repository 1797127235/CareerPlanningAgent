import { useEffect, useState } from 'react'

interface TOCItem { id: string; numeral: string; label: string }

export function TableOfContents({ items }: { items: TOCItem[] }) {
  const [active, setActive] = useState(items[0]?.id)

  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach(e => {
          if (e.isIntersecting) setActive(e.target.id)
        })
      },
      { rootMargin: '-40% 0px -50% 0px', threshold: 0 }
    )
    items.forEach(i => {
      const el = document.getElementById(i.id)
      if (el) obs.observe(el)
    })
    return () => obs.disconnect()
  }, [items])

  return (
    <nav className="hidden lg:block sticky top-24 w-[180px] shrink-0">
      <p className="font-sans text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--chestnut)] mb-4">
        目录
      </p>
      <ul className="space-y-3 border-l border-[var(--line)] pl-4">
        {items.map(i => (
          <li key={i.id}>
            <a
              href={`#${i.id}`}
              className={`block text-[13px] leading-[1.5] transition-colors ${
                active === i.id ? 'text-[var(--ink-1)] font-medium' : 'text-[var(--ink-3)] hover:text-[var(--ink-2)]'
              }`}
            >
              <span className="font-serif italic mr-2">{i.numeral}</span>
              {i.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
