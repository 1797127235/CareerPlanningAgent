import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { X, GitBranch, CheckCircle2, Target } from 'lucide-react'
import { createProject, updateProject, getGrowthDashboard } from '@/api/growthLog'
import type { ProjectRecord } from '@/api/growthLog'

const STATUS_OPTIONS = [
  { value: 'planning',    label: '计划中' },
  { value: 'in_progress', label: '进行中' },
  { value: 'completed',   label: '已完成' },
]

const SKILL_SUGGESTIONS = [
  'React', 'Vue.js', 'TypeScript', 'Node.js', 'Python', 'Java', 'Go', 'C++', 'Rust',
  'Docker', 'Kubernetes', 'MySQL', 'Redis', 'PostgreSQL', 'MongoDB',
  'Linux', '多线程', '网络编程', '机器学习', 'LangChain', 'FastAPI', 'Spring Boot',
]

interface Props {
  onSuccess: (project: ProjectRecord) => void
  onCancel: () => void
  initial?: ProjectRecord
}

export function ProjectForm({ onSuccess, onCancel, initial }: Props) {
  const isEdit = !!initial
  const [name, setName] = useState(initial?.name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [github, setGithub] = useState(initial?.github_url ?? '')
  const [status, setStatus] = useState<string>(initial?.status ?? 'in_progress')
  const [reflection, setReflection] = useState(initial?.reflection ?? '')
  const [skills, setSkills] = useState<string[]>(initial?.skills_used ?? [])
  const [gapLinks, setGapLinks] = useState<string[]>(initial?.gap_skill_links ?? [])
  const [skillInput, setSkillInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Load current gap skills from dashboard (core missing + important missing)
  const { data: dashboard } = useQuery({
    queryKey: ['growth-dashboard'],
    queryFn: getGrowthDashboard,
    staleTime: 60_000,
  })
  const availableGaps: string[] = (() => {
    if (!dashboard?.has_goal) return []
    const coreMissing = dashboard.skill_coverage?.core?.missing ?? []
    const impMissing = dashboard.skill_coverage?.important?.missing ?? []
    // Deduplicate, prioritize core
    const seen = new Set<string>()
    const result: string[] = []
    for (const s of [...coreMissing, ...impMissing]) {
      if (s && !seen.has(s)) { seen.add(s); result.push(s) }
    }
    return result
  })()

  function toggleGapLink(skill: string) {
    if (gapLinks.includes(skill)) {
      setGapLinks(gapLinks.filter(s => s !== skill))
    } else {
      setGapLinks([...gapLinks, skill])
    }
  }

  function addSkill(s: string) {
    const trimmed = s.trim()
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed])
    }
    setSkillInput('')
  }

  function removeSkill(s: string) {
    setSkills(skills.filter((x) => x !== s))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) { setError('项目名称不能为空'); return }
    setSaving(true)
    setError('')
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || undefined,
        skills_used: skills,
        gap_skill_links: gapLinks,
        github_url: github.trim() || undefined,
        status,
        reflection: reflection.trim() || undefined,
      }
      let result: ProjectRecord
      if (isEdit) {
        result = await updateProject(initial!.id, payload)
      } else {
        result = await createProject(payload)
      }
      onSuccess(result)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white/70 backdrop-blur-sm border border-slate-200/80 rounded-xl p-5 space-y-4">
      {/* Name */}
      <div>
        <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">项目名称 *</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="如：高性能网络服务器、React 电商平台..."
          className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
        />
      </div>

      {/* Status */}
      <div>
        <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">状态</label>
        <div className="flex gap-2">
          {STATUS_OPTIONS.map((opt) => (
            <button
              type="button"
              key={opt.value}
              onClick={() => setStatus(opt.value)}
              className={`flex-1 py-2 text-[12px] font-medium rounded-lg border transition-all ${
                status === opt.value
                  ? 'bg-blue-50 border-blue-400 text-blue-700'
                  : 'border-slate-200 text-slate-500 hover:border-slate-300'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Gap skill links — 这个项目补哪些缺口技能 */}
      {availableGaps.length > 0 && (
        <div>
          <label className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-600 mb-1.5">
            <Target className="w-3.5 h-3.5 text-blue-600" />
            这个项目补哪些缺口技能？
            <span className="text-[10px] font-normal text-slate-400">（基于你的目标方向）</span>
          </label>
          <div className="flex flex-wrap gap-1.5">
            {availableGaps.slice(0, 10).map(s => {
              const active = gapLinks.includes(s)
              return (
                <button
                  type="button"
                  key={s}
                  onClick={() => toggleGapLink(s)}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-lg border transition-all cursor-pointer ${
                    active
                      ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                      : 'bg-white border-slate-200 text-slate-500 hover:border-blue-300 hover:text-blue-600'
                  }`}
                >
                  {active && <CheckCircle2 className="w-3 h-3 inline mr-1" />}
                  {s}
                </button>
              )
            })}
          </div>
          {gapLinks.length > 0 && (
            <p className="text-[10px] text-blue-600 mt-1.5">
              已选 {gapLinks.length} 项缺口，项目完成后会反映到成长档案
            </p>
          )}
        </div>
      )}

      {/* Skills */}
      <div>
        <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">用到的技能</label>
        {skills.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {skills.map((s) => (
              <span key={s} className="flex items-center gap-1 px-2 py-1 bg-blue-50 border border-blue-200 rounded-lg text-[11px] text-blue-700 font-medium">
                {s}
                <button type="button" onClick={() => removeSkill(s)} className="hover:text-red-500 transition-colors">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
        <input
          value={skillInput}
          onChange={(e) => setSkillInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addSkill(skillInput) }
          }}
          placeholder="输入技能后按 Enter 添加..."
          className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 mb-2"
        />
        <div className="flex flex-wrap gap-1">
          {SKILL_SUGGESTIONS.filter((s) => !skills.includes(s)).slice(0, 8).map((s) => (
            <button
              type="button"
              key={s}
              onClick={() => addSkill(s)}
              className="px-2 py-0.5 text-[11px] border border-dashed border-slate-300 rounded text-slate-400 hover:border-blue-300 hover:text-blue-500 transition-all"
            >
              + {s}
            </button>
          ))}
        </div>
      </div>

      {/* Description */}
      <div>
        <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">项目描述（可选）</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          placeholder="简单描述项目做了什么..."
          className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 resize-none"
        />
      </div>

      {/* GitHub */}
      <div>
        <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">
          <GitBranch className="w-3 h-3 inline mr-1" />
          GitHub 链接（可选）
        </label>
        <input
          value={github}
          onChange={(e) => setGithub(e.target.value)}
          placeholder="https://github.com/..."
          className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
        />
      </div>

      {/* Reflection (only for completed) */}
      {status === 'completed' && (
        <div>
          <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">做完了有什么收获？（可选）</label>
          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            rows={2}
            placeholder="学到了什么？遇到了什么难点？"
            className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 resize-none"
          />
        </div>
      )}

      {error && <p className="text-[12px] text-red-500">{error}</p>}

      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={saving}
          className="flex-1 py-2 bg-[var(--blue)] text-white text-[13px] font-medium rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center justify-center gap-1.5"
        >
          {saving ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <CheckCircle2 className="w-4 h-4" />
          )}
          {saving ? '保存中...' : isEdit ? '保存修改' : '添加项目'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-[13px] text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
        >
          取消
        </button>
      </div>
    </form>
  )
}
