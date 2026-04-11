import { useState, useCallback } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { Skill, Internship } from '@/types/profile'

interface ManualProfileFormProps {
  onSave: (data: ManualProfilePayload) => void
  onCancel: () => void
  saving: boolean
  initialData?: ManualProfilePayload
}

export interface ManualProfilePayload {
  name: string
  /** 教育 — 全部字段可编辑 */
  education: {
    degree: string
    major: string
    school: string
  }
  experience_years: number
  job_target: string
  skills: Skill[]
  knowledge_areas: string[]
  projects: string[]
  internships: Internship[]
  certificates: string[]
  awards: string[]
}

const LEVEL_OPTIONS: { value: Skill['level']; label: string }[] = [
  { value: 'beginner', label: '入门' },
  { value: 'familiar', label: '熟悉' },
  { value: 'proficient', label: '熟练' },
  { value: 'expert', label: '精通' },
]

const EMPTY_INTERNSHIP: Internship = {
  company: '',
  role: '',
  duration: '',
  tech_stack: [],
  highlights: '',
}

export function ManualProfileForm({ onSave, onCancel, saving, initialData }: ManualProfileFormProps) {
  const [name, setName] = useState(initialData?.name ?? '')
  const [degree, setDegree] = useState(initialData?.education?.degree ?? '')
  const [major, setMajor] = useState(initialData?.education?.major ?? '')
  const [school, setSchool] = useState(initialData?.education?.school ?? '')
  const [experienceYears, setExperienceYears] = useState<string>(
    String(initialData?.experience_years ?? 0),
  )
  const [jobTarget, setJobTarget] = useState(initialData?.job_target ?? '')
  const [skills, setSkills] = useState<Skill[]>(
    initialData?.skills?.length ? initialData.skills : [{ name: '', level: 'familiar' }],
  )
  const [knowledgeText, setKnowledgeText] = useState(
    initialData?.knowledge_areas?.join('、') ?? '',
  )
  const [projects, setProjects] = useState<string[]>(
    initialData?.projects?.length ? initialData.projects : [],
  )
  const [internships, setInternships] = useState<Internship[]>(
    initialData?.internships ?? [],
  )
  const [certificates, setCertificates] = useState<string[]>(
    initialData?.certificates ?? [],
  )
  const [awards, setAwards] = useState<string[]>(
    initialData?.awards ?? [],
  )

  const [errors, setErrors] = useState<{ name?: string; skills?: string }>({})

  /* ── Skills ── */
  const addSkill = useCallback(() => {
    setSkills((prev) => [...prev, { name: '', level: 'familiar' }])
  }, [])
  const removeSkill = useCallback((idx: number) => {
    setSkills((prev) => prev.filter((_, i) => i !== idx))
  }, [])
  const updateSkill = useCallback((idx: number, field: 'name' | 'level', value: string) => {
    setSkills((prev) => prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)))
  }, [])

  /* ── Projects ── */
  const addProject = useCallback(() => setProjects((p) => [...p, '']), [])
  const removeProject = useCallback((idx: number) => {
    setProjects((p) => p.filter((_, i) => i !== idx))
  }, [])
  const updateProject = useCallback((idx: number, value: string) => {
    setProjects((p) => p.map((v, i) => (i === idx ? value : v)))
  }, [])

  /* ── Internships ── */
  const addInternship = useCallback(() => {
    setInternships((p) => [...p, { ...EMPTY_INTERNSHIP }])
  }, [])
  const removeInternship = useCallback((idx: number) => {
    setInternships((p) => p.filter((_, i) => i !== idx))
  }, [])
  const updateInternship = useCallback(
    <K extends keyof Internship>(idx: number, field: K, value: Internship[K]) => {
      setInternships((p) => p.map((v, i) => (i === idx ? { ...v, [field]: value } : v)))
    },
    [],
  )

  /* ── Certificates ── */
  const addCertificate = useCallback(() => setCertificates((p) => [...p, '']), [])
  const removeCertificate = useCallback((idx: number) => {
    setCertificates((p) => p.filter((_, i) => i !== idx))
  }, [])
  const updateCertificate = useCallback((idx: number, value: string) => {
    setCertificates((p) => p.map((v, i) => (i === idx ? value : v)))
  }, [])

  /* ── Awards ── */
  const addAward = useCallback(() => setAwards((p) => [...p, '']), [])
  const removeAward = useCallback((idx: number) => {
    setAwards((p) => p.filter((_, i) => i !== idx))
  }, [])
  const updateAward = useCallback((idx: number, value: string) => {
    setAwards((p) => p.map((v, i) => (i === idx ? value : v)))
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

    const cleanInternships = internships
      .filter((v) => v.company.trim() || v.role.trim())
      .map((v) => ({
        ...v,
        company: v.company.trim(),
        role: v.role.trim(),
        duration: v.duration?.trim() ?? '',
        highlights: v.highlights?.trim() ?? '',
        tech_stack: (v.tech_stack ?? []).map((t) => t.trim()).filter(Boolean),
      }))

    onSave({
      name: name.trim(),
      education: {
        degree: degree.trim(),
        major: major.trim(),
        school: school.trim(),
      },
      experience_years: Number.parseInt(experienceYears, 10) || 0,
      job_target: jobTarget.trim(),
      skills: validSkills,
      knowledge_areas: knowledgeAreas,
      projects: projects.map((p) => p.trim()).filter(Boolean),
      internships: cleanInternships,
      certificates: certificates.map((c) => c.trim()).filter(Boolean),
      awards: awards.map((a) => a.trim()).filter(Boolean),
    })
  }, [
    name, degree, major, school, experienceYears, jobTarget,
    skills, knowledgeText, projects, internships, certificates, awards,
    onSave,
  ])

  return (
    <div className="glass-static max-w-[680px] mx-auto px-9 py-8">
      <div className="g-inner">
      <h2 className="text-[18px] font-bold text-[var(--text-1)] mb-6">编辑画像</h2>

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

        {/* 教育 */}
        <div>
          <Label text="教育背景" />
          <div className="mt-1.5 grid grid-cols-3 gap-2">
            <input
              value={degree}
              onChange={(e) => setDegree(e.target.value)}
              placeholder="学位（本科/硕士）"
              className={inputCls()}
            />
            <input
              value={major}
              onChange={(e) => setMajor(e.target.value)}
              placeholder="专业"
              className={inputCls()}
            />
            <input
              value={school}
              onChange={(e) => setSchool(e.target.value)}
              placeholder="学校"
              className={inputCls()}
            />
          </div>
        </div>

        {/* 工作年限 + 求职意向 */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="工作年限">
            <input
              type="number"
              min="0"
              value={experienceYears}
              onChange={(e) => setExperienceYears(e.target.value)}
              placeholder="0"
              className={inputCls()}
            />
          </Field>
          <Field label="求职意向">
            <input
              value={jobTarget}
              onChange={(e) => setJobTarget(e.target.value)}
              placeholder="例如：数据分析师"
              className={inputCls()}
            />
          </Field>
        </div>

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

        {/* 实习经历 */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="实习经历" />
            <button
              type="button"
              onClick={addInternship}
              className="flex items-center gap-1 text-[12px] font-medium text-[var(--blue)] hover:opacity-80 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" /> 添加实习
            </button>
          </div>
          <div className="space-y-3">
            {internships.map((intern, i) => (
              <div
                key={i}
                className="rounded-xl p-3 bg-white/30 border border-white/40 space-y-2"
              >
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={intern.company}
                    onChange={(e) => updateInternship(i, 'company', e.target.value)}
                    placeholder="公司名称"
                    className={inputCls()}
                  />
                  <input
                    value={intern.role}
                    onChange={(e) => updateInternship(i, 'role', e.target.value)}
                    placeholder="实习岗位"
                    className={inputCls()}
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={intern.duration ?? ''}
                    onChange={(e) => updateInternship(i, 'duration', e.target.value)}
                    placeholder="时间范围 2024.10-2024.12"
                    className={inputCls()}
                  />
                  <input
                    value={(intern.tech_stack ?? []).join('、')}
                    onChange={(e) =>
                      updateInternship(
                        i,
                        'tech_stack',
                        e.target.value.split(/[,，、\s]+/).map((s) => s.trim()).filter(Boolean),
                      )
                    }
                    placeholder="技术栈（顿号分隔）"
                    className={inputCls()}
                  />
                </div>
                <textarea
                  value={intern.highlights ?? ''}
                  onChange={(e) => updateInternship(i, 'highlights', e.target.value)}
                  placeholder="核心成果一句话，如：优化推荐算法 CTR +10%"
                  rows={2}
                  className={`w-full resize-none ${inputCls()}`}
                />
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => removeInternship(i)}
                    className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-red-500 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> 删除这段实习
                  </button>
                </div>
              </div>
            ))}
            {internships.length === 0 && (
              <p className="text-[11px] text-slate-400 italic">点击"添加实习"开始填写</p>
            )}
          </div>
        </div>

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

        {/* 证书 */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="证书" />
            <button
              type="button"
              onClick={addCertificate}
              className="flex items-center gap-1 text-[12px] font-medium text-[var(--blue)] hover:opacity-80 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" /> 添加证书
            </button>
          </div>
          <div className="space-y-2">
            {certificates.map((cert, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  value={cert}
                  onChange={(e) => updateCertificate(i, e.target.value)}
                  placeholder="如：CET-6、软考中级、普通话二甲、机动车驾驶证C2"
                  className={`flex-1 ${inputCls()}`}
                />
                <button
                  type="button"
                  onClick={() => removeCertificate(i)}
                  className="p-1.5 text-[var(--text-3)] hover:text-red-500 cursor-pointer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {certificates.length === 0 && (
              <p className="text-[11px] text-slate-400 italic">点击"添加证书"开始填写</p>
            )}
          </div>
        </div>

        {/* 奖项 */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="奖项与荣誉" />
            <button
              type="button"
              onClick={addAward}
              className="flex items-center gap-1 text-[12px] font-medium text-[var(--blue)] hover:opacity-80 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" /> 添加奖项
            </button>
          </div>
          <div className="space-y-2">
            {awards.map((aw, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  value={aw}
                  onChange={(e) => updateAward(i, e.target.value)}
                  placeholder="如：蓝桥杯省一、校级奖学金、ACM 铜牌"
                  className={`flex-1 ${inputCls()}`}
                />
                <button
                  type="button"
                  onClick={() => removeAward(i)}
                  className="p-1.5 text-[var(--text-3)] hover:text-red-500 cursor-pointer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {awards.length === 0 && (
              <p className="text-[11px] text-slate-400 italic">点击"添加奖项"开始填写</p>
            )}
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
