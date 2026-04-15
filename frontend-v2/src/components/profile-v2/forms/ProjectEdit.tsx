import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'

export type ProjectItem = string | { name?: string; description?: string; tech_stack?: string[] }

export function ProjectEdit({
  projects,
  onSave,
  onCancel,
  saving,
}: {
  projects: ProjectItem[]
  onSave: (data: ProjectItem[]) => void
  onCancel: () => void
  saving?: boolean
}) {
  const normalize = (p: ProjectItem) =>
    typeof p === 'string' ? { name: '', description: p, tech_stack: [] } : { name: p.name || '', description: p.description || '', tech_stack: p.tech_stack || [] }

  const [items, setItems] = useState(() => projects.length ? projects.map(normalize) : [{ name: '', description: '', tech_stack: [] }])

  const update = (idx: number, field: string, value: unknown) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, [field]: value } : it)))
  }

  const add = () => setItems((prev) => [...prev, { name: '', description: '', tech_stack: [] }])
  const remove = (idx: number) => setItems((prev) => prev.filter((_, i) => i !== idx))

  const handleSave = () => {
    const cleaned: ProjectItem[] = items
      .filter((it) => it.name.trim() || it.description.trim())
      .map((it) => ({
        name: it.name.trim(),
        description: it.description.trim(),
        tech_stack: (it.tech_stack || []).map((t: string) => t.trim()).filter(Boolean),
      }))
    onSave(cleaned)
  }

  return (
    <div className="space-y-3">
      {items.map((it, idx) => (
        <div key={idx} className="rounded-lg border border-[var(--line)] bg-[var(--bg-card)] p-4 md:p-5 space-y-3">
          <input
            value={it.name}
            onChange={(e) => update(idx, 'name', e.target.value)}
            placeholder="项目名（可选）"
            className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
          />
          <textarea
            value={it.description}
            onChange={(e) => update(idx, 'description', e.target.value)}
            placeholder="项目描述"
            rows={3}
            className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px] resize-none"
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
        <Plus className="w-4 h-4" /> 再加一个项目
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
