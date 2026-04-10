import { useState, useCallback } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { Skill } from '@/types/profile'

interface ManualProfileFormProps {
  onSave: (data: ManualProfilePayload) => void
  onCancel: () => void
  saving: boolean
  initialData?: ManualProfilePayload
}

export interface ManualProfilePayload {
  name: string
  major: string
  skills: Skill[]
  knowledge_areas: string[]
  projects: string[]
}

const LEVEL_OPTIONS: { value: Skill['level']; label: string }[] = [
  { value: 'beginner', label: '入门' },
  { value: 'familiar', label: '熟悉' },
  { value: 'proficient', label: '熟练' },
  { value: 'expert', label: '精通' },
]

export function ManualProfileForm({ onSave, onCancel, saving, initialData }: ManualProfileFormProps) {
  const [name, setName] = useState(initialData?.name ?? '')
  const [major, setMajor] = useState(initialData?.major ?? '')
  const [skills, setSkills] = useState<Skill[]>(
    initialData?.skills?.length ? initialData.skills : [{ name: '', level: 'familiar' }],
  )
  const [knowledgeText, setKnowledgeText] = useState(
    initialData?.knowledge_areas?.join('、') ?? '',
  )
  const [projects, setProjects] = useState<string[]>(
    initialData?.projects?.length ? initialData.projects : [],
  )

  const [errors, setErrors] = useState<{ name?: string; skills?: string }>({})

  const addSkill = useCallback(() => {
    setSkills((prev) => [...prev, { name: '', level: 'familiar' }])
  }, [])

  const removeSkill = useCallback((idx: number) => {
    setSkills((prev) => prev.filter((_, i) => i !== idx))
  }, [])

  const updateSkill = useCallback((idx: number, field: 'name' | 'level', value: string) => {
    setSkills((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)),
    )
  }, [])

  const addProject = useCallback(() => {
    setProjects((prev) => [...prev, ''])
  }, [])

  const removeProject = useCallback((idx: number) => {
    setProjects((prev) => prev.filter((_, i) => i !== idx))
  }, [])

  const updateProject = useCallback((idx: number, value: string) => {
    setProjects((prev) => prev.map((p, i) => (i === idx ? value : p)))
  }, [])

  const handleSubmit = useCallback(() => {
    const newErrors: typeof errors = {}
    if (name.trim().length < 2) newErrors.name = '姓名至少 2 个字符'
    const validSkills = skills.filter((s) => s.name.trim())
    if (validSkills.length === 0) newErrors.skills = '至少添加 1 项技能'
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }
    setErrors({})

    const knowledgeAreas = knowledgeText
      .split(/[,，、\s]+/)
      .map((s) => s.trim())
      .filter(Boolean)

    onSave({
      name: name.trim(),
      major: major.trim(),
      skills: validSkills,
      knowledge_areas: knowledgeAreas,
      projects: projects.filter((p) => p.trim()),
    })
  }, [name, major, skills, knowledgeText, projects, onSave])

  return (
    <div className="glass-static max-w-[680px] mx-auto px-9 py-8">
      <div className="g-inner">
      <h2 className="text-[18px] font-bold text-[var(--text-1)] mb-6">手动建立画像</h2>

      <div className="space-y-6">
        {/* 姓名 */}
        <Field label="姓名" required error={errors.name}>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="你的名字"
            className={inputCls(errors.name)}
          />
        </Field>

        {/* 专业 */}
        <Field label="专业">
          <input
            value={major}
            onChange={(e) => setMajor(e.target.value)}
            placeholder="例如：计算机科学与技术"
            className={inputCls()}
          />
        </Field>

        {/* 技能列表 */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="技能" required />
            <button
              type="button"
              onClick={addSkill}
              className="flex items-center gap-1 text-[12px] font-medium text-[var(--blue)] hover:opacity-80 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" /> 添加技能
            </button>
          </div>
          {errors.skills && <p className="text-[12px] text-red-500 mb-2">{errors.skills}</p>}
          <div className="space-y-2">
            {skills.map((skill, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  value={skill.name}
                  onChange={(e) => updateSkill(i, 'name', e.target.value)}
                  placeholder="技能名称"
                  className={`flex-1 ${inputCls()}`}
                />
                <select
                  value={skill.level}
                  onChange={(e) => updateSkill(i, 'level', e.target.value)}
                  className="w-[90px] px-2.5 py-2 text-[13px] border border-white/40 rounded-lg bg-white/40 backdrop-blur-sm text-[var(--text-2)] focus:outline-none focus:border-[var(--blue)]/50"
                >
                  {LEVEL_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => removeSkill(i)}
                  disabled={skills.length <= 1}
                  className="p-1.5 text-[var(--text-3)] hover:text-red-500 disabled:opacity-30 disabled:cursor-default cursor-pointer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* 知识领域 */}
        <Field label="知识领域">
          <input
            value={knowledgeText}
            onChange={(e) => setKnowledgeText(e.target.value)}
            placeholder="用顿号分隔，例如：机器学习、Web开发、数据库"
            className={inputCls()}
          />
        </Field>

        {/* 项目经历 */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="项目经历" />
            <button
              type="button"
              onClick={addProject}
              className="flex items-center gap-1 text-[12px] font-medium text-[var(--blue)] hover:opacity-80 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" /> 添加项目
            </button>
          </div>
          <div className="space-y-2">
            {projects.map((proj, i) => (
              <div key={i} className="flex items-start gap-2">
                <textarea
                  value={proj}
                  onChange={(e) => updateProject(i, e.target.value)}
                  placeholder="简要描述项目内容、你的角色和使用的技术"
                  rows={2}
                  className={`flex-1 resize-none ${inputCls()}`}
                />
                <button
                  type="button"
                  onClick={() => removeProject(i)}
                  className="p-1.5 mt-1.5 text-[var(--text-3)] hover:text-red-500 cursor-pointer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 mt-8 pt-6 border-t border-white/30">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={saving}
          className="btn-cta px-6 py-2.5 text-[13px] font-medium cursor-pointer disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存画像'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="btn-glass px-5 py-2.5 text-[13px] font-medium text-[var(--text-2)] cursor-pointer disabled:opacity-50"
        >
          取消
        </button>
      </div>
      </div>
    </div>
  )
}

/* ── Helpers ── */

function Label({ text, required }: { text: string; required?: boolean }) {
  return (
    <span className="text-[13px] font-medium text-[var(--text-2)]">
      {text}
      {required && <span className="text-red-500 ml-0.5">*</span>}
    </span>
  )
}

function Field({
  label,
  required,
  error,
  children,
}: {
  label: string
  required?: boolean
  error?: string
  children: React.ReactNode
}) {
  return (
    <div>
      <Label text={label} required={required} />
      <div className="mt-1.5">{children}</div>
      {error && <p className="text-[12px] text-red-500 mt-1">{error}</p>}
    </div>
  )
}

function inputCls(error?: string) {
  return `w-full px-3 py-2 text-[13px] rounded-lg bg-white/40 backdrop-blur-sm text-[var(--text-1)] placeholder:text-[var(--text-3)] focus:outline-none transition-colors border ${
    error ? 'border-red-300 focus:border-red-400' : 'border-white/40 focus:border-[var(--blue)]/50'
  }`
}
