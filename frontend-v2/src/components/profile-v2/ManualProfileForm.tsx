import { useState, useCallback } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { Skill, Internship } from '@/types/profile'

export interface ManualProfilePayload {
  name: string
  education: { degree: string; major: string; school: string }
  experience_years: number
  job_target: string
  skills: Skill[]
  knowledge_areas: string[]
  projects: Array<string | Record<string, unknown>>
  internships: Internship[]
  certificates: string[]
  awards: string[]
}

interface ManualProfileFormProps {
  onSave: (data: ManualProfilePayload) => void
  onCancel: () => void
  saving: boolean
  initialData?: ManualProfilePayload
}

const LEVEL_OPTIONS: { value: Skill['level']; label: string }[] = [
  { value: 'beginner', label: '入门' },
  { value: 'familiar', label: '熟悉' },
  { value: 'intermediate', label: '熟练' },
  { value: 'proficient', label: '熟练' },
  { value: 'advanced', label: '精通' },
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
  const [experienceYears, setExperienceYears] = useState<string>(String(initialData?.experience_years ?? 0))
  const [jobTarget, setJobTarget] = useState(initialData?.job_target ?? '')
  const [skills, setSkills] = useState<Skill[]>(
    initialData?.skills?.length ? initialData.skills : [{ name: '', level: 'familiar' }],
  )
  const [knowledgeText, setKnowledgeText] = useState(initialData?.knowledge_areas?.join('、') ?? '')
  const [projects, setProjects] = useState<string[]>(
    initialData?.projects?.length
      ? initialData.projects.map((p) => (typeof p === 'string' ? p : (p.description as string) || ''))
      : [],
  )
  const [internships, setInternships] = useState<Internship[]>(initialData?.internships ?? [])
  const [certificates, setCertificates] = useState<string[]>(initialData?.certificates ?? [])
  const [awards, setAwards] = useState<string[]>(initialData?.awards ?? [])

  const addSkill = useCallback(() => setSkills((prev) => [...prev, { name: '', level: 'familiar' }]), [])
  const removeSkill = useCallback((idx: number) => setSkills((prev) => prev.filter((_, i) => i !== idx)), [])
  const updateSkill = useCallback((idx: number, field: 'name' | 'level', value: string) => {
    setSkills((prev) => prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)))
  }, [])

  const addProject = useCallback(() => setProjects((p) => [...p, '']), [])
  const removeProject = useCallback((idx: number) => setProjects((p) => p.filter((_, i) => i !== idx)), [])
  const updateProject = useCallback((idx: number, value: string) => {
    setProjects((p) => p.map((v, i) => (i === idx ? value : v)))
  }, [])

  const addInternship = useCallback(() => setInternships((p) => [...p, { ...EMPTY_INTERNSHIP }]), [])
  const removeInternship = useCallback((idx: number) => setInternships((p) => p.filter((_, i) => i !== idx)), [])
  const updateInternship = useCallback(<K extends keyof Internship>(idx: number, field: K, value: Internship[K]) => {
    setInternships((p) => p.map((v, i) => (i === idx ? { ...v, [field]: value } : v)))
  }, [])

  const addCertificate = useCallback(() => setCertificates((p) => [...p, '']), [])
  const removeCertificate = useCallback((idx: number) => setCertificates((p) => p.filter((_, i) => i !== idx)), [])
  const updateCertificate = useCallback((idx: number, value: string) => {
    setCertificates((p) => p.map((v, i) => (i === idx ? value : v)))
  }, [])

  const addAward = useCallback(() => setAwards((p) => [...p, '']), [])
  const removeAward = useCallback((idx: number) => setAwards((p) => p.filter((_, i) => i !== idx)), [])
  const updateAward = useCallback((idx: number, value: string) => {
    setAwards((p) => p.map((v, i) => (i === idx ? value : v)))
  }, [])

  const handleSubmit = useCallback(() => {
    const validSkills = skills.filter((s) => s.name.trim())
    const knowledgeAreas = knowledgeText.split(/[,，、\s]+/).map((s) => s.trim()).filter(Boolean)
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
      education: { degree: degree.trim(), major: major.trim(), school: school.trim() },
      experience_years: Number.parseInt(experienceYears, 10) || 0,
      job_target: jobTarget.trim(),
      skills: validSkills,
      knowledge_areas: knowledgeAreas,
      projects: projects.map((p) => p.trim()).filter(Boolean),
      internships: cleanInternships,
      certificates: certificates.map((c) => c.trim()).filter(Boolean),
      awards: awards.map((a) => a.trim()).filter(Boolean),
    })
  }, [name, degree, major, school, experienceYears, jobTarget, skills, knowledgeText, projects, internships, certificates, awards, onSave])

  const inputCls = 'w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]'

  return (
    <div className="space-y-8">
      <div>
        <h2 className="font-display text-[length:var(--fs-display-sm)] text-[var(--ink-1)] mb-6">手动录入档案</h2>
      </div>

      <div className="space-y-6">
        <div>
          <Label text="姓名" />
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="你的名字" className={inputCls} />
        </div>

        <div>
          <Label text="教育背景" />
          <div className="mt-1.5 grid grid-cols-1 md:grid-cols-3 gap-3">
            <input value={school} onChange={(e) => setSchool(e.target.value)} placeholder="学校" className={inputCls} />
            <input value={major} onChange={(e) => setMajor(e.target.value)} placeholder="专业" className={inputCls} />
            <input value={degree} onChange={(e) => setDegree(e.target.value)} placeholder="学位" className={inputCls} />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <Label text="工作年限" />
            <input type="number" min="0" value={experienceYears} onChange={(e) => setExperienceYears(e.target.value)} placeholder="0" className={inputCls} />
          </div>
          <div>
            <Label text="求职意向" />
            <input value={jobTarget} onChange={(e) => setJobTarget(e.target.value)} placeholder="例如：数据分析师" className={inputCls} />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="技能" />
            <button type="button" onClick={addSkill} className="flex items-center gap-1 text-[12px] font-medium text-[var(--chestnut)] hover:opacity-80">
              <Plus className="w-3.5 h-3.5" /> 添加技能
            </button>
          </div>
          <div className="space-y-2">
            {skills.map((skill, i) => (
              <div key={i} className="flex items-center gap-2">
                <input value={skill.name} onChange={(e) => updateSkill(i, 'name', e.target.value)} placeholder="技能名称" className={`flex-1 ${inputCls}`} />
                <select value={skill.level} onChange={(e) => updateSkill(i, 'level', e.target.value)} className="w-[100px] px-2.5 py-2 text-[13px] rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50">
                  {LEVEL_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <button type="button" onClick={() => removeSkill(i)} disabled={skills.length <= 1} className="p-1.5 text-[var(--ink-3)] hover:text-red-500 disabled:opacity-30">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <Label text="知识领域" />
          <input value={knowledgeText} onChange={(e) => setKnowledgeText(e.target.value)} placeholder="用顿号分隔，例如：机器学习、Web开发、数据库" className={inputCls} />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="实习经历" />
            <button type="button" onClick={addInternship} className="flex items-center gap-1 text-[12px] font-medium text-[var(--chestnut)] hover:opacity-80">
              <Plus className="w-3.5 h-3.5" /> 添加实习
            </button>
          </div>
          <div className="space-y-3">
            {internships.map((intern, i) => (
              <div key={i} className="rounded-lg border border-[var(--line)] bg-[var(--bg-card)] p-3 space-y-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <input value={intern.company} onChange={(e) => updateInternship(i, 'company', e.target.value)} placeholder="公司名称" className={inputCls} />
                  <input value={intern.role} onChange={(e) => updateInternship(i, 'role', e.target.value)} placeholder="实习岗位" className={inputCls} />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <input value={intern.duration ?? ''} onChange={(e) => updateInternship(i, 'duration', e.target.value)} placeholder="时间范围" className={inputCls} />
                  <input value={(intern.tech_stack ?? []).join('、')} onChange={(e) => updateInternship(i, 'tech_stack', e.target.value.split(/[,，、\s]+/).map((s) => s.trim()).filter(Boolean))} placeholder="技术栈（顿号分隔）" className={inputCls} />
                </div>
                <textarea value={intern.highlights ?? ''} onChange={(e) => updateInternship(i, 'highlights', e.target.value)} placeholder="核心成果一句话" rows={2} className={`w-full resize-none ${inputCls}`} />
                <div className="flex justify-end">
                  <button type="button" onClick={() => removeInternship(i)} className="flex items-center gap-1 text-[11px] text-[var(--ink-3)] hover:text-red-500">
                    <Trash2 className="w-3.5 h-3.5" /> 删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="项目经历" />
            <button type="button" onClick={addProject} className="flex items-center gap-1 text-[12px] font-medium text-[var(--chestnut)] hover:opacity-80">
              <Plus className="w-3.5 h-3.5" /> 添加项目
            </button>
          </div>
          <div className="space-y-2">
            {projects.map((proj, i) => (
              <div key={i} className="flex items-start gap-2">
                <textarea value={proj} onChange={(e) => updateProject(i, e.target.value)} placeholder="简要描述项目内容、你的角色和使用的技术" rows={2} className={`flex-1 resize-none ${inputCls}`} />
                <button type="button" onClick={() => removeProject(i)} className="p-1.5 mt-1.5 text-[var(--ink-3)] hover:text-red-500">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="证书" />
            <button type="button" onClick={addCertificate} className="flex items-center gap-1 text-[12px] font-medium text-[var(--chestnut)] hover:opacity-80">
              <Plus className="w-3.5 h-3.5" /> 添加证书
            </button>
          </div>
          <div className="space-y-2">
            {certificates.map((cert, i) => (
              <div key={i} className="flex items-center gap-2">
                <input value={cert} onChange={(e) => updateCertificate(i, e.target.value)} placeholder="如：CET-6、软考中级" className={`flex-1 ${inputCls}`} />
                <button type="button" onClick={() => removeCertificate(i)} className="p-1.5 text-[var(--ink-3)] hover:text-red-500">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <Label text="奖项与荣誉" />
            <button type="button" onClick={addAward} className="flex items-center gap-1 text-[12px] font-medium text-[var(--chestnut)] hover:opacity-80">
              <Plus className="w-3.5 h-3.5" /> 添加奖项
            </button>
          </div>
          <div className="space-y-2">
            {awards.map((aw, i) => (
              <div key={i} className="flex items-center gap-2">
                <input value={aw} onChange={(e) => updateAward(i, e.target.value)} placeholder="如：蓝桥杯省一、校级奖学金" className={`flex-1 ${inputCls}`} />
                <button type="button" onClick={() => removeAward(i)} className="p-1.5 text-[var(--ink-3)] hover:text-red-500">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 pt-6 border-t border-[var(--line)]">
        <button type="button" onClick={handleSubmit} disabled={saving} className="px-6 py-2.5 rounded-full bg-[var(--chestnut)] text-white text-[13px] font-medium hover:opacity-90 disabled:opacity-50">
          {saving ? '保存中...' : '保存画像'}
        </button>
        <button type="button" onClick={onCancel} disabled={saving} className="px-5 py-2.5 rounded-full text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] disabled:opacity-50">
          取消
        </button>
      </div>
    </div>
  )
}

function Label({ text }: { text: string }) {
  return <span className="text-[13px] font-medium text-[var(--ink-2)]">{text}</span>
}
