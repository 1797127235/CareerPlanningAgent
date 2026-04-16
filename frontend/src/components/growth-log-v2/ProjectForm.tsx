import { useState } from 'react'
import type { ProjectData, GrowthEntry } from './mockData'

interface ProjectFormProps {
  onClose: () => void
  onSaved?: () => void
  onAddEntry: (data: Partial<GrowthEntry>) => Promise<unknown> | unknown
  /** 编辑模式 */
  initialEntry?: GrowthEntry | null
  onUpdate?: (id: number, data: Partial<GrowthEntry>) => Promise<unknown>
}

export function ProjectForm({
  onClose,
  onSaved,
  onAddEntry,
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

  return (
    <div className="bg-white rounded-xl shadow-xl p-5">
      <h3 className="text-[16px] font-bold text-slate-900 mb-4">
        {isEdit ? '编辑项目记录' : '记录项目'}
      </h3>
      <div className="space-y-4">
        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-1">项目名称</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 text-[13px] border border-slate-300 rounded-lg outline-none focus:border-blue-500"
            placeholder="例如：高并发网络库"
          />
        </div>
        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-1">简介</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 text-[13px] border border-slate-300 rounded-lg outline-none focus:border-blue-500 resize-none"
            placeholder="一句话描述项目目标..."
          />
        </div>
        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-1">技术栈</label>
          <input
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            className="w-full px-3 py-2 text-[13px] border border-slate-300 rounded-lg outline-none focus:border-blue-500"
            placeholder="React, Node.js, PostgreSQL（逗号分隔）"
          />
        </div>
        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-1">项目链接</label>
          <input
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
            className="w-full px-3 py-2 text-[13px] border border-slate-300 rounded-lg outline-none focus:border-blue-500"
            placeholder="https://github.com/..."
          />
        </div>
        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-1">状态</label>
          <div className="flex items-center gap-4">
            {[
              { key: 'planning', label: '计划中' },
              { key: 'in_progress', label: '进行中' },
              { key: 'completed', label: '已完成' },
            ].map((o) => (
              <label key={o.key} className="flex items-center gap-1.5 text-[13px] text-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="project_status"
                  checked={status === o.key}
                  onChange={() => setStatus(o.key as any)}
                  className="cursor-pointer"
                />
                {o.label}
              </label>
            ))}
          </div>
        </div>
      </div>

      {err && (
        <div className="mt-4 px-3 py-2 text-[12px] text-red-700 bg-red-50 border border-red-200 rounded-md">
          {err}
        </div>
      )}
      <div className="mt-6 flex items-center justify-end gap-3">
        <button
          onClick={onClose}
          disabled={saving}
          className="px-4 py-2 text-[13px] font-medium text-slate-500 hover:text-slate-800 disabled:opacity-40 cursor-pointer"
        >
          取消
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 text-[13px] font-semibold text-white bg-slate-900 hover:bg-blue-700 disabled:opacity-40 rounded-lg transition-colors cursor-pointer"
        >
          {saving ? '保存中…' : '保存'}
        </button>
      </div>
    </div>
  )
}
