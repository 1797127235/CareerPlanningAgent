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

  const inputCls =
    'w-full px-3.5 py-2.5 text-[13px] rounded-xl outline-none transition-all bg-[var(--bg-paper)] border placeholder:text-[var(--ink-3)] focus:border-[var(--chestnut)] focus:ring-2 focus:ring-[var(--chestnut)]/10'

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-[12px] font-semibold mb-1.5" style={{ color: 'var(--ink-2)' }}>
          项目名 *
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="如 Muduo 网络库"
          className={inputCls}
          style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
        />
      </div>

      <div>
        <label className="block text-[12px] font-semibold mb-1.5" style={{ color: 'var(--ink-2)' }}>
          简介
        </label>
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="一句话描述这个项目"
          className={inputCls}
          style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
        />
      </div>

      <div>
        <label className="block text-[12px] font-semibold mb-1.5" style={{ color: 'var(--ink-2)' }}>
          技术栈
        </label>
        <input
          value={skills}
          onChange={(e) => setSkills(e.target.value)}
          placeholder="C++, 多线程, CMake（逗号分隔）"
          className={inputCls}
          style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
        />
      </div>

      <div>
        <label className="block text-[12px] font-semibold mb-1.5" style={{ color: 'var(--ink-2)' }}>
          项目链接
        </label>
        <input
          value={githubUrl}
          onChange={(e) => setGithubUrl(e.target.value)}
          placeholder="https://github.com/..."
          className={inputCls}
          style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
        />
      </div>

      <div>
        <label className="block text-[12px] font-semibold mb-2" style={{ color: 'var(--ink-2)' }}>
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
                className="flex-1 py-2 rounded-xl text-[13px] font-medium border transition-all cursor-pointer"
                style={{
                  color: active ? '#fff' : 'var(--ink-2)',
                  background: active ? 'var(--chestnut)' : 'var(--bg-paper)',
                  borderColor: active ? 'var(--chestnut)' : 'var(--line)',
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
          className="px-3 py-2 text-[12px] rounded-lg border"
          style={{ color: '#B85C38', background: 'rgba(184,92,56,0.06)', borderColor: 'rgba(184,92,56,0.15)' }}
        >
          {err}
        </div>
      )}

      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          onClick={onClose}
          disabled={saving}
          className="px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all cursor-pointer disabled:opacity-40"
          style={{ color: 'var(--ink-2)' }}
        >
          取消
        </button>
        <button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          className="px-5 py-2.5 rounded-xl text-[13px] font-semibold text-white transition-all cursor-pointer disabled:opacity-40"
          style={{ background: 'var(--chestnut)' }}
        >
          {saving ? '保存中…' : '保存'}
        </button>
      </div>
    </div>
  )
}
