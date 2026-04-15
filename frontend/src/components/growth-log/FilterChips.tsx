import { FolderGit2, Briefcase, Sparkles } from 'lucide-react'
import type { ComponentType } from 'react'

export type FilterKey = 'all' | 'project' | 'pursuit' | 'refine'

export const FILTERS: { key: FilterKey; label: string; icon?: ComponentType<{ className?: string }> }[] = [
  { key: 'all',      label: '全部' },
  { key: 'project',  label: '项目',  icon: FolderGit2 },
  { key: 'pursuit',  label: '实战',  icon: Briefcase },
  { key: 'refine',   label: '精修', icon: Sparkles },
]

export function FilterChips({ value, onChange }: { value: FilterKey; onChange: (v: FilterKey) => void }) {
  return (
    <div className="inline-flex gap-1 bg-[var(--bg-card)] p-1 rounded-md border border-[var(--line)] shadow-[0_1px_2px_rgba(60,40,20,0.03)]">
      {FILTERS.map(f => (
        <button
          key={f.key}
          onClick={() => onChange(f.key)}
          className={`flex items-center gap-1 px-3 py-1.5 rounded text-[12px] font-medium transition-all cursor-pointer ${
            value === f.key
              ? 'bg-[var(--chestnut)] text-white shadow-sm'
              : 'text-[var(--ink-2)] hover:text-[var(--ink-1)] hover:bg-[var(--bg-paper)]'
          }`}
        >
          {f.icon && <f.icon className="w-3.5 h-3.5" />}
          {f.label}
        </button>
      ))}
    </div>
  )
}
