import { useState } from 'react'
import type { ProjectData, GrowthEntry } from './mockData'

interface ProjectFormProps {
  onClose: () => void
  onSaved?: () => void
  onAddEntry: (data: Partial<GrowthEntry>) => Promise<unknown> | unknown
  onCreateProject?: (data: {
    name: string
    description?: string
    skills_used?: string[]
    github_url?: string
    status?: string
  }) => Promise<unknown> | unknown
  initialEntry?: GrowthEntry | null
  onUpdate?: (id: number, data: Partial<GrowthEntry>) => Promise<unknown>
}

export function ProjectForm({
  onClose,
  onSaved,
  onAddEntry,
  onCreateProject,
  initialEntry,
  onUpdate,
}: ProjectFormProps) {
  const initData = (initialEntry?.structured_data as ProjectData | null) || null
  const isEdit = !!initialEntry
  const [name, setName] = useState(initData?.name ?? '')
  const [description, setDescription] = useState(initData?.description ?? '')
  const [skills, setSkills] = useState((initData?.skills_used ?? []).join(', '))
  const [githubUrl, setGithubUrl] = useState(initData?.github_url ?? '')
  const [status, setStatus] = useState<'planning' | 'in_progress' | 'completed'>(
    initData?.status ?? 'in_progress'
  )
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const handleSave = async () => {
    if (saving) return
    if (!name.trim()) {
      setErr('请填项目名称')
      return
    }
    const skillsArr = skills
      .split(/[,，]/)
      .map((s) => s.trim())
      .filter(Boolean)
    const structured: ProjectData = {
      name: name.trim(),
      description,
      skills_used: skillsArr,
      github_url: githubUrl,
      status,
    }
    setSaving(true)
    setErr(null)
    try {
      if (isEdit && onUpdate && initialEntry) {
        await onUpdate(initialEntry.id, {
          content: structured.name,
          tags: ['项目', ...skillsArr.slice(0, 3)],
          structured_data: structured as any,
        })
      } else if (onCreateProject) {
        await onCreateProject({
          name: structured.name,
          description: structured.description,
          skills_used: skillsArr,
          github_url: structured.github_url,
          status: structured.status,
        })
      } else {
        await onAddEntry({
          content: structured.name,
          category: 'project',
          tags: ['项目', ...skillsArr.slice(0, 3)],
          structured_data: structured as any,
          is_plan: false,
          status: 'done',
          due_type: null,
          due_at: null,
          completed_at: null,
          ai_suggestions: null,
        })
      }
      onSaved?.()
      onClose()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    background: '#EDE8DE',
    border: '1px solid rgba(107,62,46,0.08)',
    color: '#3A3028',
    borderRadius: 16,
    boxShadow: 'inset 0 1px 3px rgba(60,50,40,0.06)',
  }

  return (
    <div className="space-y-7">
      <div className="space-y-2.5">
        <label className="block text-[13px] font-medium" style={{ color: '#5A4D3F' }}>
          项目名 <span style={{ color: '#B85C38' }}>*</span>
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="如 Muduo 网络库"
          className="w-full px-5 py-3.5 text-[14px] outline-none transition-all placeholder:text-[#C4B8A8] focus:border-[#B85C38]/40"
          style={inputStyle}
        />
      </div>

      <div className="space-y-2.5">
        <label className="block text-[13px] font-medium" style={{ color: '#5A4D3F' }}>
          简介
        </label>
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="一句话描述这个项目"
          className="w-full px-5 py-3.5 text-[14px] outline-none transition-all placeholder:text-[#C4B8A8] focus:border-[#B85C38]/40"
          style={inputStyle}
        />
      </div>

      <div className="space-y-2.5">
        <label className="block text-[13px] font-medium" style={{ color: '#5A4D3F' }}>
          技术栈
        </label>
        <input
          value={skills}
          onChange={(e) => setSkills(e.target.value)}
          placeholder="C++, 多线程, CMake（逗号分隔）"
          className="w-full px-5 py-3.5 text-[14px] outline-none transition-all placeholder:text-[#C4B8A8] focus:border-[#B85C38]/40"
          style={inputStyle}
        />
      </div>

      <div className="space-y-2.5">
        <label className="block text-[13px] font-medium" style={{ color: '#5A4D3F' }}>
          项目链接
        </label>
        <input
          value={githubUrl}
          onChange={(e) => setGithubUrl(e.target.value)}
          placeholder="https://github.com/..."
          className="w-full px-5 py-3.5 text-[14px] outline-none transition-all placeholder:text-[#C4B8A8] focus:border-[#B85C38]/40"
          style={inputStyle}
        />
      </div>

      <div className="space-y-3">
        <label className="block text-[13px] font-medium" style={{ color: '#5A4D3F' }}>
          状态
        </label>
        <div className="flex gap-2">
          {[
            { key: 'planning' as const, label: '规划中' },
            { key: 'in_progress' as const, label: '进行中' },
            { key: 'completed' as const, label: '已完成' },
          ].map((o) => {
            const active = status === o.key
            return (
              <button
                key={o.key}
                type="button"
                onClick={() => setStatus(o.key)}
                className="flex-1 py-2.5 rounded-2xl text-[13px] font-medium border transition-all cursor-pointer"
                style={{
                  color: active ? '#fff' : '#5A4D3F',
                  background: active ? '#B85C38' : '#FDFBF7',
                  borderColor: active ? '#B85C38' : 'rgba(107,62,46,0.12)',
                  boxShadow: active ? '0 2px 8px rgba(184,92,56,0.25)' : 'inset 0 1px 2px rgba(60,50,40,0.04)',
                }}
              >
                {o.label}
              </button>
            )
          })}
        </div>
      </div>

      {err && (
        <div
          className="px-4 py-2.5 text-[13px] rounded-xl"
          style={{
            color: '#B85C38',
            background: 'rgba(184,92,56,0.06)',
            border: '1px solid rgba(184,92,56,0.12)',
          }}
        >
          {err}
        </div>
      )}

      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          onClick={onClose}
          disabled={saving}
          className="px-6 py-2.5 rounded-2xl text-[14px] font-medium transition-all cursor-pointer disabled:opacity-40"
          style={{ color: '#9A8B7A' }}
        >
          取消
        </button>
        <button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          className="px-7 py-2.5 rounded-2xl text-[14px] font-semibold text-white transition-all cursor-pointer disabled:opacity-40"
          style={{ background: '#B85C38', boxShadow: '0 2px 8px rgba(184,92,56,0.25)' }}
        >
          {saving ? '保存中…' : '保存'}
        </button>
      </div>
    </div>
  )
}
