import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { Skill } from '@/types/profile'

const LEVEL_OPTIONS = [
  { value: 'expert', label: '熟练掌握' },
  { value: 'advanced', label: '熟练掌握' },
  { value: 'proficient', label: '比较熟练' },
  { value: 'intermediate', label: '比较熟练' },
  { value: 'familiar', label: '了解' },
  { value: 'beginner', label: '刚接触' },
] as const

export function SkillEdit({
  onAdd,
  onCancel,
  saving,
}: {
  onAdd: (skill: Skill) => void
  onCancel: () => void
  saving?: boolean
}) {
  const [name, setName] = useState('')
  const [level, setLevel] = useState<Skill['level']>('familiar')

  const handleAdd = () => {
    const trimmed = name.trim()
    if (!trimmed) return
    onAdd({ name: trimmed, level })
    setName('')
    setLevel('familiar')
  }

  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--bg-card)] p-4 md:p-5">
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="技能名称"
          className="flex-1 px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
        />
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value as Skill['level'])}
          className="px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
        >
          {LEVEL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <button
          onClick={handleAdd}
          disabled={saving || !name.trim()}
          className="inline-flex items-center justify-center gap-1 px-4 py-2 rounded-full bg-[var(--chestnut)] text-white text-[13px] font-medium hover:opacity-90 disabled:opacity-50"
        >
          <Plus className="w-4 h-4" /> 添加
        </button>
        <button
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 rounded-full text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] disabled:opacity-50"
        >
          取消
        </button>
      </div>
    </div>
  )
}
