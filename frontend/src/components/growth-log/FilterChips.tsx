import type { ComponentType } from 'react'

export type FilterKey = 'all' | 'project' | 'pursuit'

export const FILTERS: { key: FilterKey; label: string; icon?: ComponentType<{ className?: string }> }[] = [
  { key: 'all',      label: '全部' },
  { key: 'project',  label: '项目' },
  { key: 'pursuit',  label: '实战' },
]

export function FilterChips({ value, onChange }: { value: FilterKey; onChange: (v: FilterKey) => void }) {
  return (
    <div className="flex items-center gap-6">
      {FILTERS.map(f => {
        const active = value === f.key
        return (
          <button
            key={f.key}
            onClick={() => onChange(f.key)}
            className={[
              'relative text-[13px] font-medium transition-colors cursor-pointer pb-1',
              active ? 'text-slate-900' : 'text-slate-500 hover:text-slate-900',
            ].join(' ')}
          >
            {f.label}
            <span
              className={[
                'absolute left-0 right-0 -bottom-0 h-[2px] bg-slate-900 transition-opacity',
                active ? 'opacity-100' : 'opacity-0',
              ].join(' ')}
            />
          </button>
        )
      })}
    </div>
  )
}
