import { useState } from 'react'
import { EditModal, FormField, FormInput, FormRow } from '../EditModal'
import { Plus, Trash2, X } from 'lucide-react'

interface Project {
  name: string
  description: string
  tech_stack: string[]
}

interface ProjectsEditFormProps {
  open: boolean
  onClose: () => void
  data: Array<string | Record<string, unknown>>
  onSave: (data: Project[]) => Promise<void>
}

function normalizeProject(raw: string | Record<string, unknown>): Project {
  if (typeof raw === 'string') {
    return { name: raw, description: '', tech_stack: [] }
  }
  return {
    name: (raw.name as string) || '',
    description: (raw.description as string) || '',
    tech_stack: Array.isArray(raw.tech_stack) ? raw.tech_stack.map(String) : [],
  }
}

const EMPTY_PROJECT: Project = { name: '', description: '', tech_stack: [] }

export function ProjectsEditForm({ open, onClose, data, onSave }: ProjectsEditFormProps) {
  const [items, setItems] = useState<Project[]>(
    data.length > 0 ? data.map(normalizeProject) : [{ ...EMPTY_PROJECT }]
  )
  const [saving, setSaving] = useState(false)
  const [techInput, setTechInput] = useState<Record<number, string>>({})

  const update = (index: number, field: keyof Project, value: string | string[]) => {
    setItems(items.map((item, i) => i === index ? { ...item, [field]: value } : item))
  }

  const addTech = (index: number) => {
    const val = (techInput[index] || '').trim()
    if (!val) return
    const techs = [...items[index].tech_stack]
    if (!techs.includes(val)) {
      techs.push(val)
      update(index, 'tech_stack', techs)
    }
    setTechInput({ ...techInput, [index]: '' })
  }

  const removeTech = (index: number, techIdx: number) => {
    const techs = items[index].tech_stack.filter((_, i) => i !== techIdx)
    update(index, 'tech_stack', techs)
  }

  const add = () => setItems([...items, { ...EMPTY_PROJECT }])

  const remove = (index: number) => {
    const next = items.filter((_, i) => i !== index)
    setItems(next.length > 0 ? next : [{ ...EMPTY_PROJECT }])
  }

  const handleSave = async () => {
    const valid = items.filter((item) => item.name.trim())
    setSaving(true)
    try {
      await onSave(valid)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <EditModal
      open={open}
      onClose={onClose}
      title="编辑项目经历"
      onSave={handleSave}
      saving={saving}
      width={580}
    >
      <div className="space-y-6">
        {items.map((item, idx) => (
          <div key={idx} className="relative">
            {items.length > 1 && (
              <div className="flex items-center justify-between mb-3">
                <span className="text-[12px] font-semibold text-[var(--ink-3)] uppercase tracking-wider">
                  项目 {idx + 1}
                </span>
                <button
                  onClick={() => remove(idx)}
                  className="flex items-center gap-1 text-[12px] text-[var(--ink-3)] hover:text-red-500 transition-colors cursor-pointer"
                >
                  <Trash2 className="w-3 h-3" />
                  删除
                </button>
              </div>
            )}
            <FormField label="项目名称">
              <FormInput
                value={item.name}
                onChange={(v) => update(idx, 'name', v)}
                placeholder="如：高并发内存池"
              />
            </FormField>
            <FormField label="项目描述">
              <textarea
                value={item.description}
                onChange={(e) => update(idx, 'description', e.target.value)}
                placeholder="简要描述项目内容、技术亮点和成果"
                rows={3}
                className="w-full px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg-card)] text-[14px] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] transition-colors hover:border-[var(--chestnut-light)] focus:outline-none focus:border-[var(--chestnut)] resize-none"
              />
            </FormField>
            <FormField label="技术栈" hint="输入后按回车添加">
              <div className="flex flex-wrap gap-1.5 mb-2">
                {item.tech_stack.map((t, ti) => (
                  <span
                    key={ti}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] border bg-[var(--bg-paper)]"
                    style={{ borderColor: 'var(--line)', color: 'var(--ink-2)' }}
                  >
                    {t}
                    <button onClick={() => removeTech(idx, ti)} className="hover:text-red-500 cursor-pointer">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  value={techInput[idx] || ''}
                  onChange={(e) => setTechInput({ ...techInput, [idx]: e.target.value })}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTech(idx) } }}
                  placeholder="如：C++、epoll"
                  className="flex-1 px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg-card)] text-[13px] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] transition-colors hover:border-[var(--chestnut-light)] focus:outline-none focus:border-[var(--chestnut)]"
                />
                <button
                  onClick={() => addTech(idx)}
                  className="px-3 py-2 rounded-[var(--radius-sm)] text-[12px] font-medium border border-[var(--line)] hover:bg-[var(--bg-paper)] transition-colors cursor-pointer"
                  style={{ color: 'var(--ink-2)' }}
                >
                  添加
                </button>
              </div>
            </FormField>
            {idx < items.length - 1 && (
              <div className="mt-4 border-b border-[var(--line)]" />
            )}
          </div>
        ))}
      </div>
      <button
        onClick={add}
        className="mt-4 flex items-center gap-1.5 text-[13px] font-medium text-[var(--chestnut)] hover:text-[var(--chestnut-light)] transition-colors cursor-pointer"
      >
        <Plus className="w-4 h-4" />
        添加项目
      </button>
    </EditModal>
  )
}
