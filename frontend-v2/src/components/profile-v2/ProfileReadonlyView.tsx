import { useMemo, useState, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  PenLine,
  Plus,
  Sparkles,
  GraduationCap,
  Briefcase,
  FolderKanban,
  Target,
  ArrowRight,
  TrendingUp,
  Award,
  CheckCircle2,
  AlertTriangle,
  Rocket,
  ChevronRight,
  MapPin,
  Clock,
  FileText,
  ShieldCheck,
  Zap,
  RefreshCw,
  Leaf,
  MessageCircle,
  BookOpen,
  Users,
  MoreHorizontal,
} from 'lucide-react'
import type { ProfileData, Skill, Internship, Education } from '@/types/profile'
import { EducationEditForm } from './edits/EducationEditForm'
import { SkillsEditForm } from './edits/SkillsEditForm'
import { InternshipsEditForm } from './edits/InternshipsEditForm'
import { ProjectsEditForm } from './edits/ProjectsEditForm'
import { getSjtProgress } from '@/api/profiles'

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

function statusBadge(status: '达标' | '需提升' | '重点补齐') {
  const styles = {
    达标: { bg: '#EEF5F0', color: '#5A8F6E', dot: '#5A8F6E' },
    需提升: { bg: '#FDF5E8', color: '#C4853F', dot: '#C4853F' },
    重点补齐: { bg: '#FDF0EA', color: '#B85C38', dot: '#B85C38' },
  }
  const s = styles[status]
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-medium"
      style={{ background: s.bg, color: s.color }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.dot }} />
      {status}
    </span>
  )
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

/* ── Main View ── */

interface RecommendationItem {
  role_id: string
  label: string
  reason: string
  zone?: string
  replacement_pressure?: number
}

interface Props {
  data: ProfileData
  onReport?: () => void
  onSetGoal?: () => void
  onChangeGoal?: () => void
  onDelete?: () => Promise<void>
  onStartAssessment?: () => void
  recommendations?: RecommendationItem[]
  onSaveEducation?: (data: Education) => Promise<void>
  onSaveSkills?: (data: Skill[]) => Promise<void>
  onSaveInternships?: (data: Internship[]) => Promise<void>
  onSaveProjects?: (data: Array<string | Record<string, unknown>>) => Promise<void>
}

export default function ProfileReadonlyView({ data, onReport, onSetGoal, onChangeGoal, onDelete, onStartAssessment, recommendations = [], onSaveEducation, onSaveSkills, onSaveInternships, onSaveProjects }: Props) {
  const navigate = useNavigate()
  const profile = data.profile
  const gp = data.graph_position
  const primaryGoal = data.career_goals?.find((g) => g.is_primary)
  const hasGoal = !!primaryGoal && !!primaryGoal.target_node_id

  /* ── Edit modal state ── */
  const [editEdu, setEditEdu] = useState(false)
  const [editSkills, setEditSkills] = useState(false)
  const [editInterns, setEditInterns] = useState(false)
  const [editProjects, setEditProjects] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleSaveEdu = useCallback(async (edu: Education) => {
    if (onSaveEducation) await onSaveEducation(edu)
  }, [onSaveEducation])

  const handleSaveProjects = useCallback(async (projects: Array<string | Record<string, unknown>>) => {
    if (onSaveProjects) await onSaveProjects(projects)
  }, [onSaveProjects])

  const handleSaveSkills = useCallback(async (skills: Skill[]) => {
    if (onSaveSkills) await onSaveSkills(skills)
  }, [onSaveSkills])

  const handleSaveInterns = useCallback(async (interns: Internship[]) => {
    if (onSaveInternships) await onSaveInternships(interns)
  }, [onSaveInternships])

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

  /* SJT progress check */
  const [hasSjtProgress, setHasSjtProgress] = useState(false)
  useEffect(() => {
    getSjtProgress().then((p) => setHasSjtProgress(!!p)).catch(() => {})
  }, [])

  /* Derived data */
  const matchRate = useMemo(() => {
    if (!hasGoal) return null
    if (gp?.gap_skills?.length) {
      return Math.max(30, 100 - gp.gap_skills.length * 9)
    }
    return 95
  }, [gp, hasGoal])

  const gapCount = gp?.gap_skills?.length ?? 0
  const totalHours = gp?.total_hours ?? 0
  const weeks = totalHours > 0 ? Math.round(totalHours / 25) : 0

  const skillRows = useMemo(() => {
    const rows: Array<{ name: string; current: string; target: string; status: '达标' | '需提升' | '重点补齐' }> = []
    const skillMap = new Map((profile.skills ?? []).map((s) => [s.name, s.level]))
    const targets = new Map<string, string>()
    ;(gp?.gap_skills ?? []).forEach((g) => {
      targets.set(g, '熟练')
    })
    // Known skills
    ;(profile.skills ?? []).forEach((s) => {
      const t = targets.get(s.name) ?? s.level
      const status: '达标' | '需提升' | '重点补齐' = t === s.level ? '达标' : '需提升'
      rows.push({ name: s.name, current: levelLabel(s.level), target: levelLabel(t) || levelLabel(s.level), status })
    })
    // Missing skills from gap
    ;(gp?.gap_skills ?? []).forEach((g) => {
      if (!skillMap.has(g)) {
        rows.push({ name: g, current: '缺失', target: '熟悉', status: '重点补齐' })
      }
    })
    // Knowledge areas as base level
    ;(profile.knowledge_areas ?? []).forEach((k) => {
      if (!rows.find((r) => r.name === k)) {
        rows.push({ name: k, current: '基础', target: '熟练', status: '需提升' })
      }
    })
    return rows.slice(0, 8)
  }, [profile.skills, profile.knowledge_areas, gp])

  const softSkills = useMemo(() => {
    const ss = profile.soft_skills as Record<string, unknown> | undefined
    if (!ss) return []
    return Object.entries(ss)
      .filter(([k]) => !k.startsWith('_'))
      .map(([key, val]) => {
        const score = typeof val === 'number' ? val : (val as { score?: number })?.score ?? 0
        const labelMap: Record<string, string> = {
          communication: '沟通表达',
          learning: '学习能力',
          collaboration: '协作意识',
          innovation: '创新意识',
          resilience: '抗压韧性',
        }
        return { key, label: labelMap[key] || key, score: Math.round((score / 100) * 10 * 10) / 10 }
      })
      .sort((a, b) => b.score - a.score)
  }, [profile.soft_skills])

  const aiSummary = useMemo(() => {
    const from = gp?.from_node_label || '当前岗位'
    const to = gp?.target_label || '目标岗位'
    const gaps = gp?.gap_skills ?? []
    if (gaps.length > 0) {
      return `适合从${from}转向${to}，已具备编程与工程基础，建议重点补齐${gaps.slice(0, 2).join('与')}能力。`
    }
    return `${data.name || '你'} 的档案显示具备扎实的专业基础，建议继续深耕现有方向。`
  }, [gp, data.name])

  const strengths = useMemo(() => {
    const list: string[] = []
    const skills = profile.skills ?? []
    if (skills.some((s) => s.name.toLowerCase().includes('python'))) list.push('Python 开发基础扎实')
    if ((profile.internships?.length ?? 0) > 0) list.push('后端开发经验')
    if ((profile.projects?.length ?? 0) > 0) list.push('Web 项目落地能力')
    if ((profile.skills?.length ?? 0) >= 3) list.push('学习能力强')
    if (list.length === 0) list.push('具备基础编程能力')
    return list.slice(0, 4)
  }, [profile])

  const gaps = useMemo(() => {
    const list: string[] = []
    const gs = gp?.gap_skills ?? []
    if (gs.some((g) => g.includes('学习') || g.includes('深度'))) list.push('机器学习项目经验不足')
    if (gs.some((g) => g.includes('LangChain') || g.includes('RAG'))) list.push('LangChain 仅入门')
    if (gs.some((g) => g.includes('部署'))) list.push('缺少模型部署经验')
    gs.slice(0, 3).forEach((g) => {
      if (!list.some((l) => l.includes(g))) list.push(`${g} 经验不足`)
    })
    return list.slice(0, 3)
  }, [gp])

  const nextSteps = useMemo(() => {
    const list: string[] = []
    const gs = gp?.gap_skills ?? []
    if (gs.some((g) => g.includes('RAG'))) list.push('完成一个 RAG 项目')
    if (gs.some((g) => g.includes('向量') || g.includes('Agent'))) list.push('学习向量数据库与 Agent')
    if (gs.some((g) => g.includes('部署'))) list.push('补充模型部署实践')
    if (list.length === 0) list.push('深入学习目标岗位核心技能')
    return list.slice(0, 3)
  }, [gp])

  return (
    <div className="max-w-[1100px] mx-auto px-5 md:px-10 pt-[80px] pb-20">
      {/* ── Header + Match Summary ── */}
      <motion.header custom={0} variants={fadeUp} initial="hidden" animate="visible" className="grid gap-6 md:grid-cols-2 mb-10 items-start">
        {/* Left — Identity + AI Summary */}
        <div>
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

          {/* Delete confirmation — inline */}
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
            {data.name || '你的职业档案'}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5" style={{ ...sans, fontSize: '13px', color: ink(3) }}>
            {profile.education?.school && (
              <span className="inline-flex items-center gap-1">
                <GraduationCap className="w-3.5 h-3.5" />
                {profile.education.school}
                {profile.education.major && ` · ${profile.education.major}`}
              </span>
            )}
            <span className="inline-flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" />
              {data.source === 'resume' ? '基于简历解析' : '手动创建'}
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              更新于 {formatDate(data.updated_at)}
            </span>
          </div>

          {/* AI Summary — inside left column */}
          <div className="mt-5 rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-4 flex items-start gap-3">
            <Sparkles className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--chestnut)' }} />
            <p style={{ ...sans, fontSize: '13px', lineHeight: 1.7, color: ink(2) }}>
              {aiSummary}
            </p>
          </div>
        </div>

        {/* Right — Match Summary Card */}
        <Card className="relative overflow-hidden h-full">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[14px] font-semibold flex items-center gap-2" style={{ ...sans, color: ink(1) }}>
              <Target className="w-4 h-4" style={{ color: 'var(--chestnut)' }} />
              岗位匹配摘要
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-5">
            <div className="rounded-lg p-3" style={{ background: 'var(--bg-paper)' }}>
              <p className="text-[11px] mb-1" style={{ ...sans, color: ink(3) }}>目标岗位</p>
              <p className="text-[18px] font-semibold" style={{ ...serif, color: ink(1) }}>
                {primaryGoal?.target_label || '—'}
              </p>
            </div>
            <div className="rounded-lg p-3" style={{ background: 'var(--bg-paper)' }}>
              <p className="text-[11px] mb-1" style={{ ...sans, color: ink(3) }}>岗位匹配度</p>
              <p className="text-[18px] font-semibold" style={{ ...serif, color: hasGoal ? 'var(--chestnut)' : ink(3) }}>
                {matchRate != null ? `${matchRate}%` : '—'}
              </p>
            </div>
            <div className="rounded-lg p-3" style={{ background: 'var(--bg-paper)' }}>
              <p className="text-[11px] mb-1" style={{ ...sans, color: ink(3) }}>待补技能</p>
              <p className="text-[18px] font-semibold" style={{ ...serif, color: ink(1) }}>
                {hasGoal ? gapCount : '—'} <span className="text-[13px] font-normal" style={{ color: ink(3) }}>项</span>
              </p>
            </div>
            <div className="rounded-lg p-3" style={{ background: 'var(--bg-paper)' }}>
              <p className="text-[11px] mb-1" style={{ ...sans, color: ink(3) }}>预计成长周期</p>
              <p className="text-[18px] font-semibold" style={{ ...serif, color: ink(1) }}>
                {hasGoal && weeks > 0 ? `${weeks}` : '—'}
                <span className="text-[13px] font-normal" style={{ color: ink(3) }}> 周 / {hasGoal ? totalHours : '—'} 小时</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {hasGoal ? (
              <>
                <button
                  onClick={onReport}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-[13px] font-medium text-white transition-opacity hover:opacity-90 active:scale-[0.98]"
                  style={{ background: '#6B3E2E', ...sans }}
                >
                  查看成长路径
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={onSetGoal}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-[13px] font-medium text-white transition-opacity hover:opacity-90 active:scale-[0.98]"
                  style={{ background: '#6B3E2E', ...sans }}
                >
                  设定目标岗位
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
          {hasGoal && onChangeGoal && (
            <button
              onClick={onChangeGoal}
              className="mt-3 w-full flex items-center justify-center gap-1.5 py-2 text-[11px] transition-colors hover:text-[var(--ink-1)] active:scale-[0.98]"
              style={{ color: ink(3), ...sans }}
            >
              <RefreshCw className="w-3 h-3" /> 更换目标方向
            </button>
          )}
        </Card>
      </motion.header>

      {/* ── Core Analysis ── */}
      <motion.section custom={2} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <h2 className="text-[16px] font-semibold mb-4" style={{ ...sans, color: ink(1) }}>核心分析</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {/* Strengths */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <ShieldCheck className="w-4 h-4" style={{ color: '#5A8F6E' }} />
              <span className="text-[13px] font-semibold" style={{ ...sans, color: ink(1) }}>优势能力</span>
            </div>
            <ul className="space-y-2">
              {strengths.map((s) => (
                <li key={s} className="flex items-start gap-2 text-[13px]" style={{ ...sans, color: ink(2) }}>
                  <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: '#5A8F6E' }} />
                  {s}
                </li>
              ))}
            </ul>
          </Card>

          {/* Gaps */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4" style={{ color: '#C4853F' }} />
              <span className="text-[13px] font-semibold" style={{ ...sans, color: ink(1) }}>主要差距</span>
            </div>
            <ul className="space-y-2">
              {gaps.map((g) => (
                <li key={g} className="flex items-start gap-2 text-[13px]" style={{ ...sans, color: ink(2) }}>
                  <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: '#C4853F' }} />
                  {g}
                </li>
              ))}
            </ul>
          </Card>

          {/* Next Steps */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <Rocket className="w-4 h-4" style={{ color: '#5A7A9A' }} />
              <span className="text-[13px] font-semibold" style={{ ...sans, color: ink(1) }}>推荐下一步</span>
            </div>
            <ul className="space-y-2">
              {nextSteps.map((s) => (
                <li key={s} className="flex items-start gap-2 text-[13px]" style={{ ...sans, color: ink(2) }}>
                  <ChevronRight className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: '#5A7A9A' }} />
                  {s}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </motion.section>

      {/* ── Direction / Recommendations ── */}
      <div id="recs-section">
        <motion.section custom={3} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
          {hasGoal ? (
            <Card>
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-bold uppercase tracking-[0.15em] mb-1.5" style={{ ...sans, color: ink(3) }}>目标方向</p>
                  <h3 className="text-[20px] font-semibold" style={{ ...serif, color: ink(1) }}>{primaryGoal?.target_label}</h3>
                  <p className="text-[13px] mt-1" style={{ ...sans, color: ink(2) }}>
                    {primaryGoal?.gap_skills && primaryGoal.gap_skills.length > 0
                      ? `差距技能 ${primaryGoal.gap_skills.length} 项待补 · 通过实战项目逐项跨过`
                      : '技能已全部覆盖，继续深化经验'}
                  </p>
                  {primaryGoal?.gap_skills && primaryGoal.gap_skills.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {primaryGoal.gap_skills.slice(0, 8).map((s) => (
                        <span
                          key={s}
                          className="text-[11px] px-2 py-0.5 rounded-md font-medium border"
                          style={{ background: '#FDF0EA', color: '#B85C38', borderColor: '#EBDDD0' }}
                        >
                          {s}
                        </span>
                      ))}
                      {primaryGoal.gap_skills.length > 8 && (
                        <span className="text-[11px]" style={{ color: ink(3) }}>+{primaryGoal.gap_skills.length - 8} 项</span>
                      )}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => navigate('/growth-log')}
                  className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-[12px] font-medium text-white transition-opacity hover:opacity-90 active:scale-[0.98]"
                  style={{ background: '#6B3E2E', ...sans }}
                >
                  去成长档案追踪 <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </Card>
          ) : recommendations.length > 0 ? (
            <>
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-4 h-4" style={{ color: ink(3) }} />
                <h2 className="text-[16px] font-semibold" style={{ ...sans, color: ink(1) }}>推荐方向</h2>
              </div>
              <p className="text-[13px] mb-4" style={{ ...sans, color: ink(2) }}>
                基于你的技能背景，以下方向与你的经历最为契合。点击了解详情，不急着做决定。
              </p>
              <div className="grid gap-4 sm:grid-cols-2">
                {recommendations.slice(0, 4).map((rec) => {
                  const rp = rec.replacement_pressure ?? 50
                  const rpLabel = rp < 30 ? 'AI安全' : rp < 55 ? 'AI中等' : 'AI风险'
                  const rpColor = rp < 30 ? '#5A8F6E' : rp < 55 ? '#C4853F' : '#B85C38'
                  const zoneMap: Record<string, string> = { safe: '安全区', leverage: '杠杆区', transition: '过渡区', danger: '危险区' }
                  return (
                    <div
                      key={rec.role_id}
                      onClick={() => navigate(`/roles/${rec.role_id}`)}
                      className="rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-5 cursor-pointer hover:shadow-[var(--shadow-paper)] transition-all duration-200 active:scale-[0.98]"
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <h3 className="text-[14px] font-semibold truncate" style={{ ...sans, color: ink(1) }}>{rec.label}</h3>
                      </div>
                      <div className="flex items-center gap-2 mb-2">
                        {rec.zone && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: '#FDF5E8', color: '#C4853F' }}>
                            {zoneMap[rec.zone] || rec.zone}
                          </span>
                        )}
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full text-white" style={{ background: rpColor }}>
                          {rpLabel}
                        </span>
                      </div>
                      <p className="text-[12px] line-clamp-2" style={{ ...sans, color: ink(3) }}>{rec.reason}</p>
                    </div>
                  )
                })}
              </div>
            </>
          ) : (
            <Card>
              <div className="flex flex-col items-center gap-4 py-8">
                {/* Animated compass icon */}
                <div className="relative w-14 h-14">
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-dashed"
                    style={{ borderColor: 'var(--chestnut, #B85C38)', opacity: 0.3 }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
                  />
                  <motion.div
                    className="absolute inset-2 rounded-full flex items-center justify-center"
                    style={{ background: 'linear-gradient(135deg, #FDF5E8, #F5E6D0)' }}
                    animate={{ scale: [1, 1.05, 1] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    <Sparkles className="w-5 h-5" style={{ color: '#B85C38' }} />
                  </motion.div>
                </div>

                {/* Progress text */}
                <div className="text-center">
                  <p className="text-[14px] font-medium" style={{ ...serif, color: ink(1) }}>
                    AI 正在分析你的技术方向
                  </p>
                  <motion.p
                    className="text-[12px] mt-1.5"
                    style={{ ...sans, color: ink(3) }}
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    匹配技能图谱 · 计算契合度 · 生成推荐
                  </motion.p>
                </div>

                {/* Progress bar */}
                <div className="w-48 h-1 rounded-full overflow-hidden" style={{ background: 'var(--line)' }}>
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: 'linear-gradient(90deg, #B85C38, #C4853F)' }}
                    initial={{ width: '0%' }}
                    animate={{ width: '90%' }}
                    transition={{ duration: 20, ease: 'easeOut' }}
                  />
                </div>

                {/* Skip link */}
                <button
                  onClick={() => navigate('/graph')}
                  className="text-[12px] transition-colors hover:opacity-70"
                  style={{ ...sans, color: ink(3) }}
                >
                  先去图谱探索 →
                </button>
              </div>
            </Card>
          )}
        </motion.section>
      </div>

      {/* ── Skills Gap + Soft Skills ── */}
      <motion.section custom={4} variants={fadeUp} initial="hidden" animate="visible" className="grid gap-6 md:grid-cols-2 mb-8">
        {/* Skills Table */}
        <Card className="p-0 overflow-hidden">
          <div className="p-5 border-b border-[var(--line)] flex items-center justify-between">
            <h2 className="text-[15px] font-semibold" style={{ ...sans, color: ink(1) }}>技能结构 / 能力差距</h2>
            {onSaveSkills && (
              <button
                onClick={() => setEditSkills(true)}
                className="flex items-center gap-1.5 text-[12px] font-medium text-[var(--ink-3)] hover:text-[var(--chestnut)] transition-colors cursor-pointer"
                title="编辑技能"
              >
                <PenLine className="w-3 h-3" />
                编辑
              </button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]" style={sans}>
              <thead>
                <tr style={{ color: ink(3) }}>
                  <th className="text-left font-medium px-5 py-3">能力项</th>
                  <th className="text-left font-medium px-3 py-3">当前水平</th>
                  <th className="text-left font-medium px-3 py-3">目标要求</th>
                  <th className="text-left font-medium px-5 py-3">状态</th>
                </tr>
              </thead>
              <tbody>
                {skillRows.map((row) => (
                  <tr key={row.name} className="border-t border-[var(--line)]">
                    <td className="px-5 py-2.5 font-medium" style={{ color: ink(1) }}>{row.name}</td>
                    <td className="px-3 py-2.5" style={{ color: ink(2) }}>{row.current}</td>
                    <td className="px-3 py-2.5" style={{ color: ink(2) }}>{row.target}</td>
                    <td className="px-5 py-2.5">{statusBadge(row.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Soft Skills — Qualitative */}
        <Card className="!p-0 overflow-hidden h-full">
          {(() => {
            const ss = profile.soft_skills as Record<string, { score?: number; level?: string; advice?: string }> | undefined
            const sjtDims = ['communication', 'learning', 'collaboration', 'innovation', 'resilience'] as const
            const isV2 = ss?._version === 2
            const hasData = isV2 && sjtDims.some((d) => ss?.[d] != null)

            if (!hasData) {
              return (
                <div className="relative overflow-hidden rounded-xl h-full" style={{ background: 'linear-gradient(135deg, #FDF8F3 0%, #F5EDE4 100%)' }}>
                  {/* Background decorative circles */}
                  <div className="absolute top-[-40px] right-[-20px] w-[160px] h-[160px] rounded-full opacity-25" style={{ background: 'linear-gradient(135deg, #E8C4A0 0%, #D4A574 100%)' }} />
                  <div className="absolute bottom-[-30px] left-[35%] w-[100px] h-[100px] rounded-full opacity-15" style={{ background: 'linear-gradient(135deg, #E8C4A0 0%, #D4A574 100%)' }} />
                  <div className="absolute top-[25%] right-[12%] w-[60px] h-[60px] rounded-full opacity-10" style={{ background: '#E8C4A0' }} />

                  <div className="relative z-10 p-6">
                    {/* Header */}
                    <div className="flex items-center gap-2 mb-5">
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'rgba(196, 113, 90, 0.12)' }}>
                        <Leaf className="w-4 h-4" style={{ color: '#C4715A' }} />
                      </div>
                      <span className="text-[14px] font-semibold" style={{ ...sans, color: '#5C4033' }}>软技能特质</span>
                    </div>

                    <div className="flex items-end justify-between gap-4">
                      {/* Left content */}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-[22px] font-bold leading-tight mb-2" style={{ ...serif, color: '#3D2B1F' }}>
                          了解你的软技能画像
                        </h3>
                        {/* Decorative line */}
                        <div className="flex items-center gap-1.5 mb-4">
                          <div className="w-6 h-[3px] rounded-full" style={{ background: '#C4715A' }} />
                          <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#C4715A' }} />
                        </div>

                        <p className="text-[13px] leading-relaxed mb-4 max-w-[320px]" style={{ ...sans, color: '#8B6F5C' }}>
                          通过几个职场情境题，快速了解你的沟通、学习、协作等能力倾向。没有标准答案，完成后即可生成专属评估。
                        </p>

                        {/* Tags */}
                        <div className="flex items-center gap-2 mb-5 flex-wrap">
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-medium border" style={{ background: 'rgba(196, 113, 90, 0.06)', borderColor: 'rgba(196, 113, 90, 0.15)', color: '#9B6B5A' }}>
                            <MessageCircle className="w-3.5 h-3.5" />
                            沟通表达
                          </span>
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-medium border" style={{ background: 'rgba(196, 113, 90, 0.06)', borderColor: 'rgba(196, 113, 90, 0.15)', color: '#9B6B5A' }}>
                            <BookOpen className="w-3.5 h-3.5" />
                            学习能力
                          </span>
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-medium border" style={{ background: 'rgba(196, 113, 90, 0.06)', borderColor: 'rgba(196, 113, 90, 0.15)', color: '#9B6B5A' }}>
                            <Users className="w-3.5 h-3.5" />
                            团队协作
                          </span>
                          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full border" style={{ background: 'rgba(196, 113, 90, 0.06)', borderColor: 'rgba(196, 113, 90, 0.15)', color: '#9B6B5A' }}>
                            <MoreHorizontal className="w-3.5 h-3.5" />
                          </span>
                        </div>

                        {onStartAssessment && (
                          <motion.button
                            onClick={onStartAssessment}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-[14px] font-semibold text-white transition-opacity hover:opacity-90 cursor-pointer"
                            style={{ background: 'linear-gradient(135deg, #C4715A 0%, #A85D48 100%)', boxShadow: '0 4px 14px rgba(196, 113, 90, 0.35)', ...sans }}
                          >
                            {hasSjtProgress ? '继续评估' : '开始评估'}
                            <ChevronRight className="w-4 h-4" />
                          </motion.button>
                        )}
                      </div>

                      {/* Right decoration */}
                      <div className="hidden sm:block relative w-[160px] h-[140px] shrink-0">
                        {/* Plant */}
                        <svg className="absolute bottom-0 right-6 w-16 h-24" viewBox="0 0 80 110" fill="none">
                          <path d="M40 110 Q40 70 55 50" stroke="#D4A574" strokeWidth="2" fill="none" />
                          <ellipse cx="55" cy="45" rx="12" ry="20" fill="#E8B895" transform="rotate(-20 55 45)" />
                          <ellipse cx="48" cy="55" rx="10" ry="16" fill="#D4A574" transform="rotate(10 48 55)" />
                          <ellipse cx="60" cy="35" rx="9" ry="14" fill="#F0C4A0" transform="rotate(-30 60 35)" />
                          <circle cx="58" cy="30" r="3" fill="#E8D5A3" />
                        </svg>
                        {/* Geometric shapes */}
                        <div className="absolute bottom-0 right-0 w-8 h-14 rounded-t-lg" style={{ background: 'linear-gradient(180deg, #E8B895 0%, #D4A574 100%)' }} />
                        <div className="absolute bottom-0 right-10 w-12 h-8 rounded-t-full" style={{ background: 'linear-gradient(180deg, #F0C4A0 0%, #E8B895 100%)' }} />
                        <div className="absolute bottom-8 right-1 w-5 h-5 rounded-full" style={{ background: 'linear-gradient(135deg, #E8B895 0%, #D4A574 100%)' }} />
                        {/* Sparkle */}
                        <svg className="absolute top-2 right-12 w-4 h-4" viewBox="0 0 16 16" fill="none">
                          <path d="M8 0 L9 7 L16 8 L9 9 L8 16 L7 9 L0 8 L7 7 Z" fill="#E8D5A3" />
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>
              )
            }

            const DIM_LABEL: Record<string, string> = {
              communication: '沟通表达',
              learning: '学习能力',
              collaboration: '协作意识',
              innovation: '创新意识',
              resilience: '抗压韧性',
            }
            const LEVEL_STYLE: Record<string, { bg: string; text: string; bar: string }> = {
              '待发展': { bg: '#F8F7F6', text: '#8B7355', bar: '#D4C4B0' },
              '基础': { bg: '#F5F0EB', text: '#A67C52', bar: '#C4A882' },
              '良好': { bg: '#FDF5E8', text: '#B85C38', bar: '#D4A574' },
              '优秀': { bg: '#FDF0EA', text: '#9B4D3A', bar: '#C4715A' },
              'high': { bg: '#FDF0EA', text: '#9B4D3A', bar: '#C4715A' },
              'medium': { bg: '#FDF5E8', text: '#B85C38', bar: '#D4A574' },
              'low': { bg: '#F8F7F6', text: '#8B7355', bar: '#D4C4B0' },
            }

            // Compute overall score
            const dimEntries = sjtDims
              .map((key) => ({ key, dim: ss?.[key] as { score?: number; level?: string; advice?: string } | undefined }))
              .filter((d) => d.dim != null)
            const avgScore = dimEntries.length
              ? Math.round(dimEntries.reduce((sum, d) => sum + (d.dim?.score ?? 0), 0) / dimEntries.length)
              : 0
            const overallLevel = avgScore >= 80 ? '优秀' : avgScore >= 60 ? '良好' : avgScore >= 40 ? '基础' : '待发展'

            return (
              <div className="px-5 py-5 space-y-5">
                {/* Overall — centered, large level */}
                <div className="text-center py-3">
                  <p className="text-[12px] tracking-wide" style={{ ...sans, color: ink(3) }}>
                    你的软技能综合表现为
                  </p>
                  <p
                    className="font-bold mt-1 leading-tight"
                    style={{
                      ...serif,
                      fontSize: 'clamp(36px, 5vw, 44px)',
                      color: '#3D2B1F',
                    }}
                  >
                    {overallLevel}
                  </p>
                  <p className="text-[11px] mt-2 tabular-nums" style={{ ...sans, color: ink(3) }}>
                    综合得分 {avgScore} / 100
                  </p>
                </div>

                {/* Dimension list */}
                <div className="space-y-0">
                  {dimEntries.map(({ key, dim }) => {
                    const style = LEVEL_STYLE[dim?.level || ''] || LEVEL_STYLE['待发展']
                    const score = dim?.score ?? 0
                    return (
                      <div
                        key={key}
                        className="py-4 border-b border-[var(--line)] last:border-b-0"
                      >
                        <div className="flex items-baseline justify-between">
                          <span
                            className="text-[14px] font-medium"
                            style={{ ...sans, color: ink(1) }}
                          >
                            {DIM_LABEL[key]}
                          </span>
                          <div className="flex items-center gap-2">
                            <span
                              className="text-[14px] font-semibold tabular-nums"
                              style={{ color: style.text }}
                            >
                              {score}
                            </span>
                            <span
                              className="text-[12px]"
                              style={{ ...sans, color: ink(3) }}
                            >
                              {dim?.level || '待发展'}
                            </span>
                          </div>
                        </div>
                        {/* Thin progress bar */}
                        <div className="h-[2px] rounded-full overflow-hidden mt-2 mb-2.5" style={{ background: '#F0EBE5' }}>
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${score}%`, background: style.bar }}
                          />
                        </div>
                        {dim?.advice && (
                          <p className="text-[12px] leading-relaxed" style={{ ...sans, color: ink(3) }}>
                            {dim.advice}
                          </p>
                        )}
                      </div>
                    )
                  })}
                </div>

                {onStartAssessment && (
                  <div className="flex justify-center pt-1">
                    <button
                      onClick={onStartAssessment}
                      className="text-[12px] transition-colors cursor-pointer hover:opacity-60"
                      style={{ color: ink(3), ...sans }}
                    >
                      重新评估
                    </button>
                  </div>
                )}
              </div>
            )
          })()}
        </Card>
      </motion.section>

      {/* ── Experience Timeline ── */}
      <motion.section custom={6} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[16px] font-semibold" style={{ ...sans, color: ink(1) }}>经历与项目</h2>
          {onSaveProjects && (
            <button
              onClick={() => setEditProjects(true)}
              className="flex items-center gap-1.5 text-[12px] font-medium text-[var(--ink-3)] hover:text-[var(--chestnut)] transition-colors cursor-pointer"
              title="添加或编辑项目"
            >
              <Plus className="w-3.5 h-3.5" />
              {(profile.projects?.length ?? 0) > 0 ? '编辑' : '添加项目'}
            </button>
          )}
        </div>
        <div className="relative">
          {/* Horizontal connector line */}
          <div className="hidden md:block absolute top-6 left-0 right-0 h-px bg-[var(--line)]" />

          <div className="grid gap-4 md:grid-cols-4">
            {/* Education */}
            {profile.education?.school && (
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
                    {profile.education.school}
                  </p>
                  <p className="text-[12px] mt-1" style={{ ...sans, color: ink(2) }}>
                    {profile.education.degree} · {profile.education.major}
                  </p>
                </Card>
              </div>
            )}

            {/* Internships */}
            {profile.internships?.map((intern, i) => (
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
                  {intern.tech_stack && intern.tech_stack.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-3">
                      {intern.tech_stack.map((t) => (
                        <span key={t} className="px-2 py-0.5 rounded text-[10px] border bg-[var(--bg-paper)]" style={{ borderColor: 'var(--line)', color: ink(3) }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="mt-3 inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium" style={{ background: '#EEF5F0', color: '#5A8F6E' }}>
                    职业相关性：高
                  </div>
                </Card>
              </div>
            ))}

            {/* Projects */}
            {profile.projects?.map((proj, i) => {
              const title = typeof proj === 'string' ? proj : (proj as { name?: string }).name || ''
              const desc = typeof proj === 'string' ? '' : (proj as { description?: string }).description || ''
              const techs = typeof proj === 'string' ? [] : (proj as { tech_stack?: string[] }).tech_stack ?? []
              return (
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
                    <p className="text-[14px] font-semibold" style={{ ...sans, color: ink(1) }}>{title}</p>
                    {desc && (
                      <p className="text-[11px] mt-1.5 leading-relaxed line-clamp-3" style={{ ...sans, color: ink(3) }}>{desc}</p>
                    )}
                    {techs.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {techs.map((t) => (
                          <span key={t} className="px-2 py-0.5 rounded text-[10px] border bg-[var(--bg-paper)]" style={{ borderColor: 'var(--line)', color: ink(3) }}>
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="mt-3 inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium" style={{ background: '#FDF5E8', color: '#C4853F' }}>
                      相关性：{i === 0 ? '中' : '中低'}
                    </div>
                  </Card>
                </div>
              )
            })}
          </div>
        </div>
      </motion.section>

      {/* ── Recommendation Banner ── */}
      <motion.section custom={5} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <div className="relative rounded-xl border overflow-hidden p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-5" style={{ borderColor: '#EBDDD0', background: '#FAF0E6' }}>
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-full flex items-center justify-center shrink-0" style={{ background: '#FDF0EA', border: '1px solid #EBDDD0' }}>
              <Target className="w-6 h-6" style={{ color: '#B85C38' }} />
            </div>
            <div>
              <p className="text-[11px] font-medium mb-1" style={{ ...sans, color: ink(3) }}>当前推荐方向</p>
              <p className="text-[22px] font-semibold" style={{ ...serif, color: ink(1) }}>
                {primaryGoal?.target_label || '—'}
              </p>
              <p className="text-[13px] mt-1 max-w-[420px]" style={{ ...sans, color: ink(2) }}>
                从{gp?.from_node_label || '当前岗位'}出发，优先补齐{gp?.gap_skills?.slice(0, 2).join('、') || '核心'}能力。
              </p>
              <div className="flex flex-wrap items-center gap-4 mt-3 text-[12px]" style={{ ...sans, color: ink(3) }}>
                <span className="inline-flex items-center gap-1">
                  <Zap className="w-3.5 h-3.5" />
                  待补 {gapCount} 项技能
                </span>
                <span className="inline-flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  预计 {totalHours} 小时
                </span>
              </div>
            </div>
          </div>
          {hasGoal ? (
            onReport && (
              <button
                onClick={onReport}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-[13px] font-medium text-white transition-opacity hover:opacity-90 active:scale-[0.98] shrink-0 relative z-10"
                style={{ background: '#6B3E2E', ...sans }}
              >
                <FileText className="w-4 h-4" />
                生成成长报告
                <ArrowRight className="w-4 h-4" />
              </button>
            )
          ) : (
            onSetGoal && (
              <button
                onClick={onSetGoal}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-[13px] font-medium border transition-colors hover:bg-[var(--line)]/10 active:scale-[0.98] shrink-0 relative z-10"
                style={{ borderColor: 'var(--line)', color: ink(1), ...sans }}
              >
                <Target className="w-4 h-4" />
                去图谱探索
                <ArrowRight className="w-4 h-4" />
              </button>
            )
          )}
        </div>
      </motion.section>

      {/* ── Footer ── */}
      <motion.footer custom={7} variants={fadeUp} initial="hidden" animate="visible">
        <p className="text-center text-[11px]" style={{ ...sans, color: ink(3) }}>
          档案仅用于系统分析，不会分享给任何第三方。
        </p>
      </motion.footer>

      {/* ── Edit Modals ── */}
      {onSaveEducation && profile.education && (
        <EducationEditForm
          open={editEdu}
          onClose={() => setEditEdu(false)}
          data={profile.education}
          onSave={handleSaveEdu}
        />
      )}
      {onSaveSkills && (
        <SkillsEditForm
          open={editSkills}
          onClose={() => setEditSkills(false)}
          data={profile.skills ?? []}
          onSave={handleSaveSkills}
        />
      )}
      {onSaveInternships && (
        <InternshipsEditForm
          open={editInterns}
          onClose={() => setEditInterns(false)}
          data={profile.internships ?? []}
          onSave={handleSaveInterns}
        />
      )}
      {onSaveProjects && (
        <ProjectsEditForm
          open={editProjects}
          onClose={() => setEditProjects(false)}
          data={profile.projects ?? []}
          onSave={handleSaveProjects}
        />
      )}
    </div>
  )
}
