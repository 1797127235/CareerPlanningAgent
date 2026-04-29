import { useMemo, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  PenLine,
  Plus,
  Sparkles,
  GraduationCap,
  Briefcase,
  FolderKanban,
  Award,
  CheckCircle2,
  AlertTriangle,
  MapPin,
  Clock,
  Zap,
  Tag,
  Heart,
  Shield,
} from 'lucide-react'
import type { V2ProfileData } from '@/types/profile-v2'
import type { Education, Skill, Internship } from '@/types/profile'
import { EducationEditForm } from './edits/EducationEditForm'
import { SkillsEditForm } from './edits/SkillsEditForm'
import { InternshipsEditForm } from './edits/InternshipsEditForm'
import { ProjectsEditForm } from './edits/ProjectsEditForm'

/* ── Design Tokens ── */
const serif = { fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }
const ink = (n: 1 | 2 | 3) =>
  n === 1 ? 'var(--ink-1)' : n === 2 ? 'var(--ink-2)' : 'var(--ink-3)'

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.45, ease: [0.22, 1, 0.36, 1] },
  }),
}

/* ── Helpers ── */
function formatDate(d?: string | null) {
  if (!d) return ''
  return d.slice(0, 10)
}

function levelLabel(l?: string) {
  const map: Record<string, string> = {
    expert: '精通', proficient: '熟练', advanced: '进阶',
    intermediate: '中级', familiar: '熟悉', beginner: '入门',
  }
  return map[l ?? ''] ?? l ?? ''
}

function scoreColor(score: number) {
  if (score >= 80) return '#5A8F6E'
  if (score >= 60) return '#C4853F'
  return '#B85C38'
}

/* ── Sub-components ── */

function Kicker({ text }: { text: string }) {
  return (
    <div className="inline-flex items-center gap-2 mb-4 px-3 py-1.5 rounded-full border" style={{ background: 'var(--bg-card)', borderColor: 'var(--line)' }}>
      <Sparkles className="w-3 h-3" style={{ color: '#9A9590' }} />
      <p className="text-[11px] font-medium tracking-[0.12em]" style={{ ...sans, color: '#9A9590' }}>
        {text}
      </p>
    </div>
  )
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-5 ${className}`}>
      {children}
    </div>
  )
}

function SectionTitle({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-[16px] font-semibold" style={{ ...sans, color: ink(1) }}>{children}</h2>
      {action}
    </div>
  )
}

/* ── Props ── */

interface Props {
  profile: V2ProfileData
  source?: string
  updatedAt?: string
  onDelete?: () => Promise<void>
  onSaveEducation?: (data: Education) => Promise<void>
  onSaveSkills?: (data: Skill[]) => Promise<void>
  onSaveInternships?: (data: Internship[]) => Promise<void>
  onSaveProjects?: (data: Array<string | Record<string, unknown>>) => Promise<void>
  onOpenEdit?: () => void
}

export default function ProfileReadonlyView({
  profile,
  source = 'resume',
  updatedAt,
  onDelete,
  onSaveEducation,
  onSaveSkills,
  onSaveInternships,
  onSaveProjects,
  onOpenEdit,
}: Props) {
  /* ── Edit modal state ── */
  const [editEdu, setEditEdu] = useState(false)
  const [editSkills, setEditSkills] = useState(false)
  const [editInterns, setEditInterns] = useState(false)
  const [editProjects, setEditProjects] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleDelete = useCallback(async () => {
    if (!onDelete) return
    setDeleting(true)
    try {
      await onDelete()
      setDeleteConfirm(false)
    } finally {
      setDeleting(false)
    }
  }, [onDelete])

  /* ── Adapt v2 → v1 for edit forms ── */
  const v1Education: Education = useMemo(() => {
    const e = profile.education[0]
    return e ? { school: e.school, major: e.major, degree: e.degree } : {}
  }, [profile.education])

  const v1Skills: Skill[] = useMemo(() => {
    const levelMap: Record<string, Skill['level']> = {
      beginner: 'beginner',
      familiar: 'familiar',
      intermediate: 'intermediate',
      advanced: 'expert',
    }
    return profile.skills.map((s) => ({
      name: s.name,
      level: levelMap[s.level] ?? 'familiar',
    }))
  }, [profile.skills])

  const v1Internships: Internship[] = useMemo(() =>
    profile.internships.map((i) => ({
      company: i.company,
      role: i.role,
      duration: i.duration,
      tech_stack: i.tech_stack,
      highlights: i.highlights,
    })),
  [profile.internships])

  const v1Projects = useMemo(() =>
    profile.projects.map((p) => ({
      name: p.name,
      description: p.description,
      tech_stack: p.tech_stack,
    })),
  [profile.projects])

  const handleSaveEdu = useCallback(async (edu: Education) => {
    if (onSaveEducation) await onSaveEducation(edu)
  }, [onSaveEducation])

  const handleSaveSkills = useCallback(async (skills: Skill[]) => {
    if (onSaveSkills) await onSaveSkills(skills)
  }, [onSaveSkills])

  const handleSaveInterns = useCallback(async (interns: Internship[]) => {
    if (onSaveInternships) await onSaveInternships(interns)
  }, [onSaveInternships])

  const handleSaveProjects = useCallback(async (projects: Array<string | Record<string, unknown>>) => {
    if (onSaveProjects) await onSaveProjects(projects)
  }, [onSaveProjects])

  /* ── Derived data ── */
  const firstEdu = profile.education[0]
  const hasDimensions = (profile.dimension_scores?.length ?? 0) > 0
  const hasTags = (profile.tags?.length ?? 0) > 0
  const hasStrengths = (profile.strengths?.length ?? 0) > 0
  const hasWeaknesses = (profile.weaknesses?.length ?? 0) > 0
  const hasConstraints = (profile.constraints?.length ?? 0) > 0
  const hasPreferences = (profile.preferences?.length ?? 0) > 0

  return (
    <div className="max-w-[1100px] mx-auto px-5 md:px-10 pt-[80px] pb-20">
      {/* ── Header ── */}
      <motion.header custom={0} variants={fadeUp} initial="hidden" animate="visible" className="mb-10">
        <div className="flex items-start justify-between">
          <Kicker text="AI 职业能力画像" />
          {onDelete && (
            <button
              onClick={() => setDeleteConfirm(true)}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--ink-3)] hover:text-red-500 hover:bg-red-50 border border-[var(--line)] transition-colors cursor-pointer"
              title="重置画像"
            >
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>
            </button>
          )}
        </div>

        {/* Delete confirmation */}
        {deleteConfirm && (
          <div className="mt-3 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: '#FDF0EA', border: '1px solid #EBDDD0' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#B85C38" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>
              </div>
              <div>
                <p className="text-[14px] font-semibold" style={{ ...sans, color: ink(1) }}>确认重置画像？</p>
                <p className="text-[12px] mt-0.5" style={{ ...sans, color: ink(3) }}>将清空全部技能、项目和背景数据</p>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => setDeleteConfirm(false)}
                className="flex-1 py-2.5 rounded-lg text-[13px] font-medium border border-[var(--line)] transition-colors hover:bg-[var(--bg-paper)] active:scale-[0.98] cursor-pointer"
                style={{ ...sans, color: ink(2) }}
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 py-2.5 rounded-lg text-[13px] font-semibold text-white transition-all cursor-pointer disabled:opacity-50 hover:opacity-90 active:scale-[0.98]"
                style={{ background: '#B85C38', ...sans }}
              >
                {deleting ? '重置中...' : '确认重置'}
              </button>
            </div>
          </div>
        )}

        <h1
          style={{
            ...serif,
            fontSize: 'clamp(32px, 3.8vw, 48px)',
            lineHeight: 1.1,
            letterSpacing: '0.01em',
            color: ink(1),
          }}
        >
          {profile.name || '你的职业档案'}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5" style={{ ...sans, fontSize: '13px', color: ink(3) }}>
          {firstEdu?.school && (
            <span className="inline-flex items-center gap-1">
              <GraduationCap className="w-3.5 h-3.5" />
              {firstEdu.school}
              {firstEdu.major && ` · ${firstEdu.major}`}
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5" />
            {source === 'resume' ? '基于简历解析' : '手动创建'}
          </span>
          {updatedAt && (
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              更新于 {formatDate(updatedAt)}
            </span>
          )}
        </div>
      </motion.header>

      {/* ── Dimension Scores ── */}
      {hasDimensions && (
        <motion.section custom={1} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
          <SectionTitle>能力维度</SectionTitle>
          <Card>
            <div className="space-y-4">
              {profile.dimension_scores!.map((dim) => (
                <div key={dim.name}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[13px] font-medium" style={{ ...sans, color: ink(1) }}>{dim.name}</span>
                    <span className="text-[13px] font-semibold tabular-nums" style={{ color: scoreColor(dim.score) }}>
                      {dim.score}
                    </span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: '#F0EBE5' }}>
                    <motion.div
                      className="h-full rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${dim.score}%` }}
                      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                      style={{ background: scoreColor(dim.score) }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </motion.section>
      )}

      {/* ── Tags ── */}
      {hasTags && (
        <motion.section custom={2} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
          <SectionTitle>
            <span className="inline-flex items-center gap-2">
              <Tag className="w-4 h-4" style={{ color: ink(3) }} />
              标签
            </span>
          </SectionTitle>
          <div className="flex flex-wrap gap-2">
            {profile.tags!.map((tag) => (
              <span
                key={tag}
                className="px-3 py-1.5 rounded-full text-[12px] font-medium border"
                style={{ background: 'var(--bg-card)', borderColor: 'var(--line)', color: ink(2) }}
              >
                {tag}
              </span>
            ))}
          </div>
        </motion.section>
      )}

      {/* ── Strengths / Weaknesses ── */}
      {(hasStrengths || hasWeaknesses) && (
        <motion.section custom={3} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
          <SectionTitle>优势与短板</SectionTitle>
          <div className="grid gap-4 sm:grid-cols-2">
            {hasStrengths && (
              <Card>
                <div className="flex items-center gap-2 mb-3">
                  <ShieldCheck className="w-4 h-4" style={{ color: '#5A8F6E' }} />
                  <span className="text-[13px] font-semibold" style={{ ...sans, color: ink(1) }}>优势</span>
                </div>
                <ul className="space-y-2">
                  {profile.strengths!.map((s) => (
                    <li key={s} className="flex items-start gap-2 text-[13px]" style={{ ...sans, color: ink(2) }}>
                      <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: '#5A8F6E' }} />
                      {s}
                    </li>
                  ))}
                </ul>
              </Card>
            )}
            {hasWeaknesses && (
              <Card>
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4" style={{ color: '#C4853F' }} />
                  <span className="text-[13px] font-semibold" style={{ ...sans, color: ink(1) }}>短板</span>
                </div>
                <ul className="space-y-2">
                  {profile.weaknesses!.map((w) => (
                    <li key={w} className="flex items-start gap-2 text-[13px]" style={{ ...sans, color: ink(2) }}>
                      <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: '#C4853F' }} />
                      {w}
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </div>
        </motion.section>
      )}

      {/* ── Skills ── */}
      <motion.section custom={4} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <SectionTitle
          action={onSaveSkills && (
            <button
              onClick={() => setEditSkills(true)}
              className="flex items-center gap-1.5 text-[12px] font-medium text-[var(--ink-3)] hover:text-[var(--chestnut)] transition-colors cursor-pointer"
            >
              <PenLine className="w-3 h-3" />
              编辑
            </button>
          )}
        >
          技能
        </SectionTitle>
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]" style={sans}>
              <thead>
                <tr style={{ color: ink(3) }}>
                  <th className="text-left font-medium px-5 py-3">技能</th>
                  <th className="text-left font-medium px-5 py-3">水平</th>
                </tr>
              </thead>
              <tbody>
                {profile.skills.length > 0 ? profile.skills.map((s) => (
                  <tr key={s.name} className="border-t border-[var(--line)]">
                    <td className="px-5 py-2.5 font-medium" style={{ color: ink(1) }}>{s.name}</td>
                    <td className="px-5 py-2.5" style={{ color: ink(2) }}>{levelLabel(s.level)}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={2} className="px-5 py-6 text-center text-[13px]" style={{ color: ink(3) }}>
                      暂无技能数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.section>

      {/* ── Experience Timeline ── */}
      <motion.section custom={5} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[16px] font-semibold" style={{ ...sans, color: ink(1) }}>经历与项目</h2>
          {onSaveProjects && (
            <button
              onClick={() => setEditProjects(true)}
              className="flex items-center gap-1.5 text-[12px] font-medium text-[var(--ink-3)] hover:text-[var(--chestnut)] transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              {(profile.projects?.length ?? 0) > 0 ? '编辑' : '添加项目'}
            </button>
          )}
        </div>
        <div className="relative">
          <div className="hidden md:block absolute top-6 left-0 right-0 h-px bg-[var(--line)]" />
          <div className="grid gap-4 md:grid-cols-4">
            {/* Education */}
            {firstEdu && (
              <div className="relative">
                <div className="hidden md:flex absolute -top-1.5 left-6 w-3 h-3 rounded-full border-2 border-[var(--chestnut)] bg-[var(--bg-paper)] z-10" />
                <Card className="h-full">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-[var(--bg-paper)] border border-[var(--line)] flex items-center justify-center">
                        <GraduationCap className="w-3.5 h-3.5" style={{ color: ink(3) }} />
                      </div>
                      <span className="text-[11px] font-medium" style={{ ...sans, color: ink(3) }}>教育经历</span>
                    </div>
                    {onSaveEducation && (
                      <button
                        onClick={() => setEditEdu(true)}
                        className="w-6 h-6 rounded flex items-center justify-center text-[var(--ink-3)] hover:text-[var(--chestnut)] hover:bg-[var(--bg-paper)] transition-colors cursor-pointer"
                        title="编辑"
                      >
                        <PenLine className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  <p className="text-[14px] font-semibold" style={{ ...sans, color: ink(1) }}>
                    {firstEdu.school}
                  </p>
                  <p className="text-[12px] mt-1" style={{ ...sans, color: ink(2) }}>
                    {firstEdu.degree} · {firstEdu.major}
                  </p>
                  {firstEdu.duration && (
                    <p className="text-[11px] mt-1" style={{ ...sans, color: ink(3) }}>{firstEdu.duration}</p>
                  )}
                </Card>
              </div>
            )}

            {/* Internships */}
            {profile.internships.map((intern, i) => (
              <div key={`intern-${i}`} className="relative">
                <div className="hidden md:flex absolute -top-1.5 left-6 w-3 h-3 rounded-full border-2 border-[var(--chestnut)] bg-[var(--bg-paper)] z-10" />
                <Card className="h-full">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-[var(--bg-paper)] border border-[var(--line)] flex items-center justify-center">
                        <Briefcase className="w-3.5 h-3.5" style={{ color: ink(3) }} />
                      </div>
                      <span className="text-[11px] font-medium" style={{ ...sans, color: ink(3) }}>实习经历</span>
                    </div>
                    {i === 0 && onSaveInternships && (
                      <button
                        onClick={() => setEditInterns(true)}
                        className="w-6 h-6 rounded flex items-center justify-center text-[var(--ink-3)] hover:text-[var(--chestnut)] hover:bg-[var(--bg-paper)] transition-colors cursor-pointer"
                        title="编辑实习经历"
                      >
                        <PenLine className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  <p className="text-[11px] mb-1" style={{ ...sans, color: ink(3) }}>{intern.duration}</p>
                  <p className="text-[14px] font-semibold" style={{ ...sans, color: ink(1) }}>{intern.role}</p>
                  <p className="text-[12px] mt-0.5" style={{ ...sans, color: ink(2) }}>{intern.company}</p>
                  {intern.highlights && (
                    <p className="text-[11px] mt-2 leading-relaxed" style={{ ...sans, color: ink(3) }}>{intern.highlights}</p>
                  )}
                  {intern.tech_stack.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-3">
                      {intern.tech_stack.map((t) => (
                        <span key={t} className="px-2 py-0.5 rounded text-[10px] border bg-[var(--bg-paper)]" style={{ borderColor: 'var(--line)', color: ink(3) }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            ))}

            {/* Projects */}
            {profile.projects.map((proj, i) => (
              <div key={`proj-${i}`} className="relative">
                <div className="hidden md:flex absolute -top-1.5 left-6 w-3 h-3 rounded-full border-2 border-[var(--line)] bg-[var(--bg-paper)] z-10" />
                <Card className="h-full">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-[var(--bg-paper)] border border-[var(--line)] flex items-center justify-center">
                        <FolderKanban className="w-3.5 h-3.5" style={{ color: ink(3) }} />
                      </div>
                      <span className="text-[11px] font-medium" style={{ ...sans, color: ink(3) }}>项目 {i + 1}</span>
                    </div>
                    {onSaveProjects && (
                      <button
                        onClick={() => setEditProjects(true)}
                        className="w-6 h-6 rounded flex items-center justify-center text-[var(--ink-3)] hover:text-[var(--chestnut)] hover:bg-[var(--bg-paper)] transition-colors cursor-pointer"
                        title="编辑项目"
                      >
                        <PenLine className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  <p className="text-[14px] font-semibold" style={{ ...sans, color: ink(1) }}>{proj.name}</p>
                  {proj.description && (
                    <p className="text-[11px] mt-1.5 leading-relaxed line-clamp-3" style={{ ...sans, color: ink(3) }}>{proj.description}</p>
                  )}
                  {proj.tech_stack.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-3">
                      {proj.tech_stack.map((t) => (
                        <span key={t} className="px-2 py-0.5 rounded text-[10px] border bg-[var(--bg-paper)]" style={{ borderColor: 'var(--line)', color: ink(3) }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            ))}
          </div>
        </div>
      </motion.section>

      {/* ── Awards & Certificates ── */}
      {((profile.awards?.length ?? 0) > 0 || (profile.certificates?.length ?? 0) > 0) && (
        <motion.section custom={6} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
          <SectionTitle>
            <span className="inline-flex items-center gap-2">
              <Award className="w-4 h-4" style={{ color: ink(3) }} />
              荣誉与证书
            </span>
          </SectionTitle>
          <div className="grid gap-4 sm:grid-cols-2">
            {(profile.awards?.length ?? 0) > 0 && (
              <Card>
                <p className="text-[11px] font-medium tracking-wider text-[var(--ink-3)] uppercase mb-2">获奖</p>
                <ul className="space-y-1.5">
                  {profile.awards!.map((a) => (
                    <li key={a} className="text-[13px]" style={{ ...sans, color: ink(2) }}>{a}</li>
                  ))}
                </ul>
              </Card>
            )}
            {(profile.certificates?.length ?? 0) > 0 && (
              <Card>
                <p className="text-[11px] font-medium tracking-wider text-[var(--ink-3)] uppercase mb-2">证书</p>
                <ul className="space-y-1.5">
                  {profile.certificates!.map((c) => (
                    <li key={c} className="text-[13px]" style={{ ...sans, color: ink(2) }}>{c}</li>
                  ))}
                </ul>
              </Card>
            )}
          </div>
        </motion.section>
      )}

      {/* ── Preferences & Constraints ── */}
      {(hasPreferences || hasConstraints) && (
        <motion.section custom={7} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
          <SectionTitle>
            <span className="inline-flex items-center gap-2">
              <Heart className="w-4 h-4" style={{ color: ink(3) }} />
              偏好与约束
            </span>
          </SectionTitle>
          <div className="grid gap-4 sm:grid-cols-2">
            {hasPreferences && (
              <Card>
                <p className="text-[11px] font-medium tracking-wider text-[var(--ink-3)] uppercase mb-3">职业偏好</p>
                <div className="flex flex-wrap gap-2">
                  {profile.preferences!.map((p) => (
                    <span
                      key={`${p.type}-${p.value}`}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-medium border"
                      style={{ background: '#FDF5E8', borderColor: '#EBDDD0', color: '#B85C38' }}
                    >
                      <Zap className="w-3 h-3" />
                      {p.label}
                    </span>
                  ))}
                </div>
              </Card>
            )}
            {hasConstraints && (
              <Card>
                <p className="text-[11px] font-medium tracking-wider text-[var(--ink-3)] uppercase mb-3">硬性约束</p>
                <div className="flex flex-wrap gap-2">
                  {profile.constraints!.map((c) => (
                    <span
                      key={`${c.type}-${c.value}`}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-medium border"
                      style={{ background: '#EEF5F0', borderColor: '#D4E5D8', color: '#5A8F6E' }}
                    >
                      {c.type === 'location' && <MapPin className="w-3 h-3" />}
                      {c.type === 'salary_min' && <Shield className="w-3 h-3" />}
                      {c.label}
                    </span>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </motion.section>
      )}

      {/* ── Bottom Action Bar ── */}
      <motion.section custom={8} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <div className="flex items-center justify-between rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-5">
          <div>
            <p className="text-[14px] font-semibold" style={{ ...sans, color: ink(1) }}>补充画像信息</p>
            <p className="text-[12px] mt-0.5" style={{ ...sans, color: ink(3) }}>
              添加标签、能力维度、优势短板、偏好与约束，让画像更完整
            </p>
          </div>
          {onOpenEdit && (
            <button
              onClick={onOpenEdit}
              className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg text-[13px] font-medium text-white transition-opacity hover:opacity-90 active:scale-[0.98] shrink-0"
              style={{ background: '#6B3E2E', ...sans }}
            >
              <PenLine className="w-3.5 h-3.5" />
              补充信息
            </button>
          )}
        </div>
      </motion.section>

      {/* ── Footer ── */}
      <motion.footer custom={9} variants={fadeUp} initial="hidden" animate="visible">
        <p className="text-center text-[11px]" style={{ ...sans, color: ink(3) }}>
          档案仅用于系统分析，不会分享给任何第三方。
        </p>
      </motion.footer>

      {/* ── Edit Modals ── */}
      {onSaveEducation && (
        <EducationEditForm
          open={editEdu}
          onClose={() => setEditEdu(false)}
          data={v1Education}
          onSave={handleSaveEdu}
        />
      )}
      {onSaveSkills && (
        <SkillsEditForm
          open={editSkills}
          onClose={() => setEditSkills(false)}
          data={v1Skills}
          onSave={handleSaveSkills}
        />
      )}
      {onSaveInternships && (
        <InternshipsEditForm
          open={editInterns}
          onClose={() => setEditInterns(false)}
          data={v1Internships}
          onSave={handleSaveInterns}
        />
      )}
      {onSaveProjects && (
        <ProjectsEditForm
          open={editProjects}
          onClose={() => setEditProjects(false)}
          data={v1Projects}
          onSave={handleSaveProjects}
        />
      )}
    </div>
  )
}
