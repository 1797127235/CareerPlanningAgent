import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { Internship } from '@/types/profile'

export function InternshipEdit({
  internships,
  onSave,
  onCancel,
  saving,
}: {
  internships: Internship[]
  onSave: (data: Internship[]) => void
  onCancel: () => void
  saving?: boolean
}) {
  const [items, setItems] = useState<Internship[]>(
    internships.length ? internships : [{ company: '', role: '', duration: '', tech_stack: [], highlights: '' }],
  )

  const update = (idx: number, field: keyof Internship, value: unknown) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, [field]: value } : it)))
  }

  const add = () => {
    setItems((prev) => [...prev, { company: '', role: '', duration: '', tech_stack: [], highlights: '' }])
  }

  const remove = (idx: number) => {
    setItems((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleSave = () => {
    const cleaned = items
      .filter((it) => it.company.trim() || it.role.trim())
      .map((it) => ({
        ...it,
        company: it.company.trim(),
        role: it.role.trim(),
        duration: it.duration?.trim() ?? '',
        highlights: it.highlights?.trim() ?? '',
        tech_stack: (it.tech_stack ?? []).map((t) => t.trim()).filter(Boolean),
      }))
    onSave(cleaned)
  }

  return (
    <div className="space-y-3">
      {items.map((it, idx) => (
        <div key={idx} className="rounded-lg border border-[var(--line)] bg-[var(--bg-card)] p-4 md:p-5 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              value={it.company}
              onChange={(e) => update(idx, 'company', e.target.value)}
              placeholder="公司"
              className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
            />
            <input
              value={it.role}
              onChange={(e) => update(idx, 'role', e.target.value)}
              placeholder="岗位"
              className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
            />
            <input
              value={it.duration || ''}
              onChange={(e) => update(idx, 'duration', e.target.value)}
              placeholder="时间范围"
              className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
            />
            <input
              value={(it.tech_stack || []).join('、')}
              onChange={(e) =>
                update(
                  idx,
                  'tech_stack',
                  e.target.value.split(/[,，、\s]+/).map((s) => s.trim()).filter(Boolean),
                )
              }
              placeholder="技术栈（顿号分隔）"
              className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
            />
          </div>
          <textarea
            value={it.highlights || ''}
            onChange={(e) => update(idx, 'highlights', e.target.value)}
            placeholder="核心成果一句话"
            rows={2}
            className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px] resize-none"
          />
          <div className="flex justify-end">
            <button onClick={() => remove(idx)} className="inline-flex items-center gap-1 text-[12px] text-[var(--ink-3)] hover:text-red-500">
              <Trash2 className="w-3.5 h-3.5" /> 删除
            </button>
          </div>
        </div>
      ))}
      <button
        onClick={add}
        className="inline-flex items-center gap-1 text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]"
      >
        <Plus className="w-4 h-4" /> 再加一段实习
      </button>
      <div className="flex items-center gap-3 pt-2">
        <button
          disabled={saving}
          onClick={handleSave}
          className="px-4 py-2 rounded-full bg-[var(--chestnut)] text-white text-[13px] font-medium hover:opacity-90 disabled:opacity-50"
        >
          {saving ? '保存中…' : '保存'}
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
