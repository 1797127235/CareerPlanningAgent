import { useEffect, useState } from 'react'

interface TOCItem {
  id: string
  numeral: string
  label: string
}

export function TableOfContents({
  items,
  placement = 'fixed',
  className = '',
}: {
  items: TOCItem[]
  placement?: 'fixed' | 'inline'
  className?: string
}) {
  const [active, setActive] = useState(items[0]?.id ?? '')

  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActive(entry.target.id)
        })
      },
      { rootMargin: '-40% 0px -50% 0px', threshold: 0 }
    )

    items.forEach((item) => {
      const el = document.getElementById(item.id)
      if (el) obs.observe(el)
    })

    return () => obs.disconnect()
  }, [items])

  return (
    <nav
      className={[
        placement === 'fixed' ? 'hidden lg:block fixed right-8 top-24 w-[220px] z-20' : 'w-full',
        className,
      ].filter(Boolean).join(' ')}
      aria-label="目录"
    >
      <p className="font-sans text-[13px] font-bold uppercase tracking-[0.2em] text-[var(--chestnut)] mb-5">
        目录
      </p>
      <ul className={[placement === 'fixed' ? 'space-y-4' : 'space-y-3', 'border-l border-[var(--line)] pl-4'].join(' ')}>
        {items.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              className={`block ${placement === 'fixed' ? 'text-[15px]' : 'text-[14px]'} leading-[1.5] transition-colors ${
                active === item.id ? 'text-[var(--ink-1)] font-medium' : 'text-[var(--ink-3)] hover:text-[var(--ink-2)]'
              }`}
            >
              <span className="font-serif italic mr-2.5" style={{ fontFamily: 'var(--font-serif)' }}>
                {item.numeral}
              </span>
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
