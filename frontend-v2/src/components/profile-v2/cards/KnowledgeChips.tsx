import { X } from 'lucide-react'

export function KnowledgeChips({
  areas,
  onDelete,
}: {
  areas: string[]
  onDelete?: (area: string) => void
}) {
  if (areas.length === 0) {
    return <p className="text-[length:var(--fs-body)] text-[var(--ink-3)] italic">还没有知识领域记录。</p>
  }
  return (
    <div className="flex flex-wrap gap-2">
      {areas.map((a) => (
        <span
          key={a}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[13px] font-medium bg-[var(--bg-paper)] text-[var(--ink-2)] border border-[var(--line)]"
        >
          {a}
          {onDelete && (
            <button
              onClick={() => onDelete(a)}
              className="p-0.5 hover:bg-[var(--line)] rounded-full"
              aria-label="删除"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </span>
      ))}
    </div>
  )
}
