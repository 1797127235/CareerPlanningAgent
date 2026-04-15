export function DataRow({
  label,
  value,
  hint,
}: {
  label: React.ReactNode
  value: React.ReactNode
  hint?: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="font-serif italic text-[var(--text-sm)] text-[var(--ink-3)]">{label}</span>
      <div className="text-right">
        <span className="text-[var(--text-base)] text-[var(--ink-1)]">{value}</span>
        {hint && <p className="text-[var(--text-xs)] text-[var(--ink-3)] mt-0.5">{hint}</p>}
      </div>
    </div>
  )
}
