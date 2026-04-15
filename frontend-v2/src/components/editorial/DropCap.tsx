export function DropCap({ children }: { children: string }) {
  const [first, ...rest] = children
  const isChinese = /[\u4e00-\u9fff]/.test(first)
  return (
    <p className="text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
      <span
        className={isChinese
          ? "float-left font-serif text-[64px] leading-[0.85] mr-2 mt-1 text-[var(--chestnut)]"
          : "float-left font-serif text-[56px] leading-[0.85] mr-1 mt-1 text-[var(--chestnut)]"
        }
        style={{ fontFamily: 'var(--font-serif)' }}
      >
        {first}
      </span>
      {rest.join('')}
    </p>
  )
}
