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
    <nav className="hidden lg:block fixed right-8 top-24 w-[220px] z-20">
      <p className="font-sans text-[13px] font-bold uppercase tracking-[0.2em] text-[var(--chestnut)] mb-5">
        目录
      </p>
      <ul className="space-y-4 border-l border-[var(--line)] pl-4">
        {items.map(i => (
          <li key={i.id}>
            <a
              href={`#${i.id}`}
              className={`block text-[15px] leading-[1.5] transition-colors ${
                active === i.id ? 'text-[var(--ink-1)] font-medium' : 'text-[var(--ink-3)] hover:text-[var(--ink-2)]'
              }`}
            >
              <span className="font-serif italic mr-2.5">{i.numeral}</span>
              {i.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
