import { FolderGit2, Briefcase, BookOpen } from 'lucide-react'
import type { ComponentType } from 'react'

export type FilterKey = 'all' | 'project' | 'pursuit' | 'learning'

export const FILTERS: { key: FilterKey; label: string; icon?: ComponentType<{ className?: string }> }[] = [
  { key: 'all',      label: '全部' },
  { key: 'project',  label: '项目',  icon: FolderGit2 },
  { key: 'pursuit',  label: '实战',  icon: Briefcase },
  { key: 'learning', label: '学习',  icon: BookOpen },
]

export function FilterChips({ value, onChange }: { value: FilterKey; onChange: (v: FilterKey) => void }) {
  return (
    <div className="flex gap-1 bg-white/40 p-1 rounded-xl backdrop-blur-md border border-white/60 shadow-sm">
      {FILTERS.map(f => (
        <button
          key={f.key}
          onClick={() => onChange(f.key)}
          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-all cursor-pointer ${
            value === f.key
              ? 'bg-slate-800 text-white shadow-sm'
              : 'text-slate-500 hover:text-slate-800 hover:bg-white/50'
          }`}
        >
          {f.icon && <f.icon className="w-3.5 h-3.5" />}
          {f.label}
        </button>
      ))}
    </div>
  )
}
