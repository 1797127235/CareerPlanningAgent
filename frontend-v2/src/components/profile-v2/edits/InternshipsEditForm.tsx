import { useState, useEffect, useRef } from 'react'
import { EditModal, FormField, FormInput, FormRow } from '../EditModal'
import { Plus, Trash2 } from 'lucide-react'
import type { Internship } from '@/types/profile'

interface InternshipsEditFormProps {
  open: boolean
  onClose: () => void
  data: Internship[]
  onSave: (data: Internship[]) => Promise<void>
}

const EMPTY_INTERNSHIP: Internship = {
  company: '',
  role: '',
  duration: '',
  tech_stack: [],
  highlights: '',
}

export function InternshipsEditForm({ open, onClose, data, onSave }: InternshipsEditFormProps) {
  const [items, setItems] = useState<Internship[]>(
    data.length > 0 ? data : [{ ...EMPTY_INTERNSHIP }]
  )
  const [saving, setSaving] = useState(false)

  const prevOpenRef = useRef(false)
  useEffect(() => {
    if (open && !prevOpenRef.current) {
      setItems(data.length > 0 ? data : [{ ...EMPTY_INTERNSHIP }])
    }
    prevOpenRef.current = open
  }, [open, data])

  const update = (index: number, field: keyof Internship, value: string) => {
    setItems(items.map((item, i) => i === index ? { ...item, [field]: value } : item))
  }

  const add = () => setItems([...items, { ...EMPTY_INTERNSHIP }])

  const remove = (index: number) => {
    const next = items.filter((_, i) => i !== index)
    setItems(next.length > 0 ? next : [{ ...EMPTY_INTERNSHIP }])
  }

  const handleSave = async () => {
    const valid = items.filter((item) => item.company.trim() || item.role.trim())
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
      title="编辑实习经历"
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
                  实习 {idx + 1}
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
            <FormRow>
              <FormField label="公司">
                <FormInput
                  value={item.company}
                  onChange={(v) => update(idx, 'company', v)}
                  placeholder="如：字节跳动"
                />
              </FormField>
              <FormField label="职位">
                <FormInput
                  value={item.role}
                  onChange={(v) => update(idx, 'role', v)}
                  placeholder="如：前端开发实习生"
                />
              </FormField>
            </FormRow>
            <FormField label="时长" hint="如：3个月">
              <FormInput
                value={item.duration ?? ''}
                onChange={(v) => update(idx, 'duration', v)}
                placeholder="如：2024.06 - 2024.09"
              />
            </FormField>
            <FormField label="工作内容">
              <textarea
                value={item.highlights ?? ''}
                onChange={(e) => update(idx, 'highlights', e.target.value)}
                placeholder="简要描述工作内容和成果"
                rows={3}
                className="w-full px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg-card)] text-[14px] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] transition-colors hover:border-[var(--chestnut-light)] focus:outline-none focus:border-[var(--chestnut)] resize-none"
              />
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
        添加实习经历
      </button>
    </EditModal>
  )
}
