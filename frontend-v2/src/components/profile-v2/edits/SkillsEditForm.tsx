import { useState, useRef, useCallback } from 'react'
import { EditModal, FormField, FormInput } from '../EditModal'
import { X, Plus } from 'lucide-react'
import type { Skill } from '@/types/profile'

const LEVEL_OPTIONS = [
  { value: 'expert', label: '精通' },
  { value: 'proficient', label: '熟练' },
  { value: 'advanced', label: '进阶' },
  { value: 'intermediate', label: '中级' },
  { value: 'familiar', label: '熟悉' },
  { value: 'beginner', label: '入门' },
]

interface SkillsEditFormProps {
  open: boolean
  onClose: () => void
  data: Skill[]
  onSave: (data: Skill[]) => Promise<void>
}

export function SkillsEditForm({ open, onClose, data, onSave }: SkillsEditFormProps) {
  const [skills, setSkills] = useState<Skill[]>(data)
  const [newSkill, setNewSkill] = useState('')
  const [saving, setSaving] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const addSkill = useCallback(() => {
    const name = newSkill.trim()
    if (!name) return
    if (skills.some((s) => s.name === name)) return
    setSkills([...skills, { name, level: 'familiar' }])
    setNewSkill('')
    inputRef.current?.focus()
  }, [newSkill, skills])

  const removeSkill = useCallback((name: string) => {
    setSkills(skills.filter((s) => s.name !== name))
  }, [skills])

  const updateLevel = useCallback((name: string, level: Skill['level']) => {
    setSkills(skills.map((s) => (s.name === name ? { ...s, level } : s)))
  }, [skills])

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(skills)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <EditModal
      open={open}
      onClose={onClose}
      title="编辑技能"
      onSave={handleSave}
      saving={saving}
      width={560}
    >
      <FormField label="添加技能">
        <div className="flex gap-2">
          <div className="flex-1">
            <FormInput
              value={newSkill}
              onChange={setNewSkill}
              placeholder="输入技能名称，回车添加"
            />
          </div>
          <button
            onClick={addSkill}
            disabled={!newSkill.trim()}
            className="px-3 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium text-white transition-all cursor-pointer disabled:opacity-40 flex items-center gap-1"
            style={{ background: 'var(--chestnut)' }}
          >
            <Plus className="w-3.5 h-3.5" />
            添加
          </button>
        </div>
      </FormField>

      <div className="mt-4 space-y-2">
        {skills.length === 0 && (
          <p className="text-[13px] text-[var(--ink-3)] italic py-4 text-center">
            还没有技能，添加一些吧
          </p>
        )}
        {skills.map((skill) => (
          <div
            key={skill.name}
            className="flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg-paper)]"
          >
            <span className="flex-1 text-[13px] font-medium text-[var(--ink-1)]">
              {skill.name}
            </span>
            <select
              value={skill.level}
              onChange={(e) => updateLevel(skill.name, e.target.value as Skill['level'])}
              className="px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg-card)] text-[12px] text-[var(--ink-2)] cursor-pointer focus:outline-none focus:border-[var(--chestnut)]"
              style={{
                appearance: 'none',
                backgroundImage: `url("data:image/svg+xml,%3Csvg width='10' height='10' viewBox='0 0 12 12' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M3 4.5L6 7.5L9 4.5' stroke='%239A9590' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 8px center',
                paddingRight: '28px',
              }}
            >
              {LEVEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <button
              onClick={() => removeSkill(skill.name)}
              className="w-7 h-7 rounded flex items-center justify-center text-[var(--ink-3)] hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </EditModal>
  )
}
