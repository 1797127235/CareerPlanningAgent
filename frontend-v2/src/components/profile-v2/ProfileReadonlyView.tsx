import { useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  PenLine,
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
} from 'lucide-react'
import type { ProfileData, Skill, Internship } from '@/types/profile'

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

interface Props {
  data: ProfileData
  onEdit: () => void
  onReport?: () => void
}

export default function ProfileReadonlyView({ data, onEdit, onReport }: Props) {
  const profile = data.profile
  const gp = data.graph_position
  const primaryGoal = data.career_goals?.find((g) => g.is_primary)

  /* Derived data */
  const matchRate = useMemo(() => {
    if (gp?.gap_skills?.length) {
      return Math.max(30, 100 - gp.gap_skills.length * 9)
    }
    return 85
  }, [gp])

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
          <Kicker text="AI 职业能力画像" />
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
            <Sparkles className="w-4 h-4" style={{ color: ink(3) }} />
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
              <p className="text-[18px] font-semibold" style={{ ...serif, color: 'var(--chestnut)' }}>
                {matchRate}%
              </p>
            </div>
            <div className="rounded-lg p-3" style={{ background: 'var(--bg-paper)' }}>
              <p className="text-[11px] mb-1" style={{ ...sans, color: ink(3) }}>待补技能</p>
              <p className="text-[18px] font-semibold" style={{ ...serif, color: ink(1) }}>
                {gapCount} <span className="text-[13px] font-normal" style={{ color: ink(3) }}>项</span>
              </p>
            </div>
            <div className="rounded-lg p-3" style={{ background: 'var(--bg-paper)' }}>
              <p className="text-[11px] mb-1" style={{ ...sans, color: ink(3) }}>预计成长周期</p>
              <p className="text-[18px] font-semibold" style={{ ...serif, color: ink(1) }}>
                {weeks > 0 ? `${weeks}` : '—'}
                <span className="text-[13px] font-normal" style={{ color: ink(3) }}> 周 / {totalHours} 小时</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onReport}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-[13px] font-medium text-white transition-opacity hover:opacity-90 active:scale-[0.98]"
              style={{ background: '#6B3E2E', ...sans }}
            >
              查看成长路径
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onEdit}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-[13px] font-medium border transition-colors hover:bg-[var(--bg-card-hover)] active:scale-[0.98]"
              style={{ borderColor: 'var(--line)', color: ink(2), ...sans }}
            >
              <PenLine className="w-3.5 h-3.5" />
              编辑档案
            </button>
          </div>
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

      {/* ── Skills Gap + Soft Skills ── */}
      <motion.section custom={3} variants={fadeUp} initial="hidden" animate="visible" className="grid gap-6 md:grid-cols-2 mb-8">
        {/* Skills Table */}
        <Card className="p-0 overflow-hidden">
          <div className="p-5 border-b border-[var(--line)]">
            <h2 className="text-[15px] font-semibold" style={{ ...sans, color: ink(1) }}>技能结构 / 能力差距</h2>
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
        <Card>
          <h2 className="text-[15px] font-semibold mb-4" style={{ ...sans, color: ink(1) }}>软技能特质</h2>
          <div className="divide-y divide-[var(--line)]">
            {(() => {
              const ss = profile.soft_skills as Record<string, { score?: number; level?: string; advice?: string }> | undefined
              if (!ss) return null
              const items = Object.entries(ss)
                .filter(([k]) => !k.startsWith('_'))
                .map(([key, val]) => {
                  const labelMap: Record<string, string> = {
                    communication: '沟通表达',
                    learning: '学习能力',
                    collaboration: '协作意识',
                    innovation: '创新意识',
                    resilience: '抗压韧性',
                  }
                  return { key, label: labelMap[key] || key, advice: val.advice || '' }
                })
                .filter((i) => i.advice)
              return items.map((item, idx) => (
                <div key={item.key} className={idx === 0 ? 'pb-3' : 'py-3'}>
                  <p className="text-[12px] font-medium mb-1" style={{ ...sans, color: ink(3) }}>{item.label}</p>
                  <p className="text-[13px] leading-relaxed" style={{ ...serif, color: ink(2), fontStyle: 'italic' }}>
                    “{item.advice}”
                  </p>
                </div>
              ))
            })()}
          </div>
        </Card>
      </motion.section>

      {/* ── Experience Timeline ── */}
      <motion.section custom={4} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <h2 className="text-[16px] font-semibold mb-4" style={{ ...sans, color: ink(1) }}>经历与项目</h2>
        <div className="relative">
          {/* Horizontal connector line */}
          <div className="hidden md:block absolute top-6 left-0 right-0 h-px bg-[var(--line)]" />

          <div className="grid gap-4 md:grid-cols-4">
            {/* Education */}
            {profile.education?.school && (
              <div className="relative">
                <div className="hidden md:flex absolute -top-1.5 left-6 w-3 h-3 rounded-full border-2 border-[var(--chestnut)] bg-[var(--bg-paper)] z-10" />
                <Card className="h-full">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-7 h-7 rounded-full bg-[var(--bg-paper)] border border-[var(--line)] flex items-center justify-center">
                      <GraduationCap className="w-3.5 h-3.5" style={{ color: ink(3) }} />
                    </div>
                    <span className="text-[11px] font-medium" style={{ ...sans, color: ink(3) }}>教育经历</span>
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
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-7 h-7 rounded-full bg-[var(--bg-paper)] border border-[var(--line)] flex items-center justify-center">
                      <Briefcase className="w-3.5 h-3.5" style={{ color: ink(3) }} />
                    </div>
                    <span className="text-[11px] font-medium" style={{ ...sans, color: ink(3) }}>实习经历</span>
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
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-7 h-7 rounded-full bg-[var(--bg-paper)] border border-[var(--line)] flex items-center justify-center">
                        <FolderKanban className="w-3.5 h-3.5" style={{ color: ink(3) }} />
                      </div>
                      <span className="text-[11px] font-medium" style={{ ...sans, color: ink(3) }}>项目 {i + 1}</span>
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
          {onReport && (
            <button
              onClick={onReport}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-[13px] font-medium text-white transition-opacity hover:opacity-90 active:scale-[0.98] shrink-0 relative z-10"
              style={{ background: '#6B3E2E', ...sans }}
            >
              <FileText className="w-4 h-4" />
              生成成长报告
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </motion.section>

      {/* ── Footer ── */}
      <motion.footer custom={6} variants={fadeUp} initial="hidden" animate="visible">
        <p className="text-center text-[11px]" style={{ ...sans, color: ink(3) }}>
          档案仅用于系统分析，不会分享给任何第三方。
        </p>
      </motion.footer>
    </div>
  )
}
