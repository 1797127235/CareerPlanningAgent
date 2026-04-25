import { useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  PenLine,
  FileText,
  GraduationCap,
  Briefcase,
  FolderKanban,
  Target,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Award,
} from 'lucide-react'
import type { ProfileData } from '@/types/profile'

/* ── Design Tokens ── */
const serif = { fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }
const ink = (n: 1 | 2 | 3) =>
  n === 1 ? 'var(--ink-1)' : n === 2 ? 'var(--ink-2)' : 'var(--ink-3)'

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.5, ease: [0.22, 1, 0.36, 1] },
  }),
}

/* ── Helpers ── */
function formatDate(d?: string | null) {
  if (!d) return ''
  return d.slice(0, 10)
}

function levelLabel(l?: string) {
  const map: Record<string, string> = {
    expert: '精通',
    proficient: '熟练',
    advanced: '进阶',
    intermediate: '中级',
    familiar: '熟悉',
    beginner: '入门',
  }
  return map[l ?? ''] ?? l ?? ''
}

function scoreColor(score: number) {
  if (score >= 80) return 'var(--moss)'
  if (score >= 60) return 'var(--ember)'
  return 'var(--ink-3)'
}

/* ── Sub-components ── */

function Kicker({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <span className="inline-block h-px w-6" style={{ background: '#9A9590' }} />
      <p
        className="text-[10px] font-medium uppercase tracking-[0.28em]"
        style={{ ...sans, color: '#9A9590' }}
      >
        {text}
      </p>
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="mb-8"
      style={{
        ...serif,
        fontSize: 'clamp(20px, 2.2vw, 28px)',
        lineHeight: 1.2,
        letterSpacing: '0.01em',
        color: ink(1),
      }}
    >
      {children}
    </h2>
  )
}

function Chip({ label, accent }: { label: string; accent?: boolean }) {
  return (
    <span
      className={[
        'inline-flex items-center px-3 py-1.5 rounded-full text-[13px] font-medium border transition-colors duration-200',
        accent
          ? 'bg-[var(--chestnut)] text-white border-[var(--chestnut)]'
          : 'bg-[var(--bg-card)] text-[var(--ink-2)] border-[var(--line)] hover:bg-[var(--bg-paper-2)]',
      ].join(' ')}
    >
      {label}
    </span>
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
  const quality = data.quality

  const hasExperience = useMemo(
    () =>
      (profile.internships?.length ?? 0) > 0 ||
      (profile.projects?.length ?? 0) > 0 ||
      !!profile.education?.school,
    [profile]
  )

  const hasSoftSkills = useMemo(() => {
    const ss = profile.soft_skills as Record<string, unknown> | undefined
    if (!ss) return false
    return Object.keys(ss).filter((k) => !k.startsWith('_')).length > 0
  }, [profile])

  const dimensions = useMemo(
    () => quality.dimensions?.filter((d) => (d.score ?? 0) > 0) ?? [],
    [quality]
  )

  const primaryGoal = data.career_goals?.find((g) => g.is_primary)

  return (
    <div className="max-w-[920px] mx-auto px-6 md:px-10 pt-[80px] pb-32">
      {/* ── Top Bar ── */}
      <motion.div
        custom={0}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        className="flex items-center justify-between mb-16"
      >
        <Kicker text="AI 职业能力画像" />
        <button
          onClick={onEdit}
          className="inline-flex items-center gap-2 text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--chestnut)] transition-colors duration-200"
          style={sans}
        >
          <PenLine className="w-4 h-4" />
          编辑档案
        </button>
      </motion.div>

      {/* ── Prologue: Name & Meta ── */}
      <motion.section custom={1} variants={fadeUp} initial="hidden" animate="visible" className="mb-20">
        <h1
          style={{
            ...serif,
            fontSize: 'clamp(36px, 4vw, 52px)',
            lineHeight: 1.12,
            letterSpacing: '0.01em',
            color: ink(1),
          }}
        >
          {data.name || '你的职业档案'}
        </h1>

        <div
          className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2"
          style={{ ...sans, fontSize: '14px', color: ink(3) }}
        >
          {profile.education?.school && (
            <span className="inline-flex items-center gap-1.5">
              <GraduationCap className="w-3.5 h-3.5" />
              {profile.education.school}
              {profile.education.major && ` · ${profile.education.major}`}
            </span>
          )}
          {profile.experience_years != null && profile.experience_years > 0 && (
            <span className="inline-flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5" />
              {profile.experience_years} 年经验
            </span>
          )}
          <span className="inline-flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            {data.source === 'resume' ? '基于简历解析' : '手动创建'}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" />
            更新于 {formatDate(data.updated_at)}
          </span>
        </div>
      </motion.section>

      {/* ── Chapter I: Overview + Skills ── */}
      <motion.section custom={2} variants={fadeUp} initial="hidden" animate="visible" className="mb-20">
        <div className="grid gap-10 md:grid-cols-12">
          {/* Left: AI Summary */}
          <div className="md:col-span-5">
            <SectionTitle>能力概览</SectionTitle>
            <div className="space-y-4" style={{ ...sans, fontSize: '15px', lineHeight: 1.75, color: ink(2) }}>
              {quality.overall_score != null && (
                <div className="flex items-center gap-3">
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center text-white text-sm font-semibold shrink-0"
                    style={{ background: scoreColor(quality.overall_score) }}
                  >
                    {Math.round(quality.overall_score)}
                  </div>
                  <div>
                    <p className="text-[13px] font-medium" style={{ color: ink(1) }}>
                      综合竞争力
                    </p>
                    <p className="text-[12px]" style={{ color: ink(3) }}>
                      {quality.overall_score >= 80
                        ? '高于行业平均水准'
                        : quality.overall_score >= 60
                          ? '具备扎实的基础'
                          : '仍有成长空间'}
                    </p>
                  </div>
                </div>
              )}
              <p>
                {data.name || '你'} 的职业档案显示
                {profile.skills?.length ? ` 掌握 ${profile.skills.length} 项核心技能` : ''}
                {hasExperience ? '，具备多段实践经历' : ''}
                {primaryGoal ? `，目标方向为 ${primaryGoal.target_label}` : ''}。
              </p>
              {quality.completeness != null && (
                <p className="text-[13px]" style={{ color: ink(3) }}>
                  档案完整度 {Math.round(quality.completeness)}%
                  {quality.completeness < 80 ? '，补充更多细节可获得更精准的分析。' : '。'}
                </p>
              )}
            </div>
          </div>

          {/* Right: Skills */}
          <div className="md:col-span-7">
            <SectionTitle>技能结构</SectionTitle>
            <div className="flex flex-wrap gap-2">
              {profile.skills?.map((s, i) => (
                <Chip key={`${s.name}-${i}`} label={`${s.name}${levelLabel(s.level) ? ` · ${levelLabel(s.level)}` : ''}`} />
              ))}
              {profile.knowledge_areas?.map((k, i) => (
                <Chip key={`ka-${i}`} label={k} />
              ))}
              {(!profile.skills || profile.skills.length === 0) && (
                <p className="text-[14px] italic" style={{ color: ink(3) }}>
                  暂无技能数据
                </p>
              )}
            </div>
          </div>
        </div>
      </motion.section>

      {/* ── Chapter II: Experience Timeline ── */}
      {hasExperience && (
        <motion.section custom={3} variants={fadeUp} initial="hidden" animate="visible" className="mb-20">
          <SectionTitle>经历</SectionTitle>
          <div className="space-y-8">
            {/* Education */}
            {profile.education?.school && (
              <div className="grid gap-4 md:grid-cols-12">
                <div className="md:col-span-3">
                  <div className="flex items-center gap-2" style={{ color: ink(3) }}>
                    <GraduationCap className="w-4 h-4" />
                    <span className="text-[12px] font-medium uppercase tracking-wider" style={sans}>
                      教育
                    </span>
                  </div>
                </div>
                <div className="md:col-span-9">
                  <p className="text-[15px] font-medium" style={{ ...sans, color: ink(1) }}>
                    {profile.education.school}
                  </p>
                  <p className="text-[14px] mt-0.5" style={{ ...sans, color: ink(2) }}>
                    {profile.education.degree && `${profile.education.degree} · `}
                    {profile.education.major}
                  </p>
                </div>
              </div>
            )}

            {/* Divider */}
            {profile.education?.school && (profile.internships?.length || profile.projects?.length) && (
              <div className="h-px bg-[var(--line)] ml-0 md:ml-[25%]" />
            )}

            {/* Internships */}
            {profile.internships?.map((intern, i) => (
              <div key={`intern-${i}`} className="grid gap-4 md:grid-cols-12">
                <div className="md:col-span-3">
                  <div className="flex items-center gap-2" style={{ color: ink(3) }}>
                    <Briefcase className="w-4 h-4" />
                    <span className="text-[12px] font-medium uppercase tracking-wider" style={sans}>
                      {intern.duration || '实习'}
                    </span>
                  </div>
                  {intern.tier && (
                    <span
                      className="inline-block mt-1.5 px-2 py-0.5 rounded text-[11px] font-medium border"
                      style={{ borderColor: 'var(--line)', color: ink(3) }}
                    >
                      {intern.tier}
                    </span>
                  )}
                </div>
                <div className="md:col-span-9">
                  <p className="text-[15px] font-medium" style={{ ...sans, color: ink(1) }}>
                    {intern.role}
                  </p>
                  <p className="text-[14px] mt-0.5" style={{ ...sans, color: ink(2) }}>
                    {intern.company}
                  </p>
                  {intern.highlights && (
                    <p className="text-[13px] mt-2 leading-relaxed" style={{ ...sans, color: ink(3) }}>
                      {intern.highlights}
                    </p>
                  )}
                  {intern.tech_stack && intern.tech_stack.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {intern.tech_stack.map((t) => (
                        <span
                          key={t}
                          className="px-2 py-0.5 rounded text-[11px] border"
                          style={{ borderColor: 'var(--line)', color: ink(3) }}
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Divider */}
            {(profile.internships?.length ?? 0) > 0 && (profile.projects?.length ?? 0) > 0 && (
              <div className="h-px bg-[var(--line)] ml-0 md:ml-[25%]" />
            )}

            {/* Projects */}
            {profile.projects?.map((proj, i) => {
              const title = typeof proj === 'string' ? proj : (proj as { name?: string }).name || ''
              const desc = typeof proj === 'string' ? '' : (proj as { description?: string }).description || ''
              const techs =
                typeof proj === 'string'
                  ? []
                  : (proj as { tech_stack?: string[] }).tech_stack ?? []
              return (
                <div key={`proj-${i}`} className="grid gap-4 md:grid-cols-12">
                  <div className="md:col-span-3">
                    <div className="flex items-center gap-2" style={{ color: ink(3) }}>
                      <FolderKanban className="w-4 h-4" />
                      <span className="text-[12px] font-medium uppercase tracking-wider" style={sans}>
                        项目
                      </span>
                    </div>
                  </div>
                  <div className="md:col-span-9">
                    <p className="text-[15px] font-medium" style={{ ...sans, color: ink(1) }}>
                      {title}
                    </p>
                    {desc && (
                      <p className="text-[13px] mt-1.5 leading-relaxed" style={{ ...sans, color: ink(3) }}>
                        {desc}
                      </p>
                    )}
                    {techs.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {techs.map((t) => (
                          <span
                            key={t}
                            className="px-2 py-0.5 rounded text-[11px] border"
                            style={{ borderColor: 'var(--line)', color: ink(3) }}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </motion.section>
      )}

      {/* ── Chapter III: Dimensions ── */}
      {dimensions.length > 0 && (
        <motion.section custom={4} variants={fadeUp} initial="hidden" animate="visible" className="mb-20">
          <SectionTitle>能力维度</SectionTitle>
          <div className="grid gap-6 sm:grid-cols-2">
            {dimensions.map((d) => (
              <div key={d.key || d.label || d.name} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[13px] font-medium" style={{ ...sans, color: ink(1) }}>
                    {d.label || d.name || d.key}
                  </span>
                  <span className="text-[12px] tabular-nums" style={{ ...sans, color: ink(3) }}>
                    {Math.round(d.score)}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--line)] overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: scoreColor(d.score) }}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(d.score, 100)}%` }}
                    transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.section>
      )}

      {/* ── Chapter IV: Soft Skills ── */}
      {hasSoftSkills && (
        <motion.section custom={5} variants={fadeUp} initial="hidden" animate="visible" className="mb-20">
          <SectionTitle>特质</SectionTitle>
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
            {Object.entries(profile.soft_skills as Record<string, unknown>)
              .filter(([k]) => !k.startsWith('_'))
              .map(([key, val]) => {
                const score = typeof val === 'number' ? val : (val as { score?: number })?.score ?? 0
                const evidence =
                  typeof val === 'number' ? '' : (val as { evidence?: string })?.evidence ?? ''
                return (
                  <div
                    key={key}
                    className="rounded-lg border border-[var(--line)] bg-[var(--bg-card)] p-4 hover:bg-[var(--bg-card-hover)] transition-colors duration-200"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[13px] font-medium" style={{ ...sans, color: ink(1) }}>
                        {key}
                      </span>
                      <Award className="w-3.5 h-3.5" style={{ color: ink(3) }} />
                    </div>
                    <div className="h-1 rounded-full bg-[var(--line)] overflow-hidden mb-2">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(score * 10, 100)}%`,
                          background: scoreColor(score * 10),
                        }}
                      />
                    </div>
                    {evidence && (
                      <p className="text-[11px] leading-relaxed" style={{ ...sans, color: ink(3) }}>
                        {evidence}
                      </p>
                    )}
                  </div>
                )
              })}
          </div>
        </motion.section>
      )}

      {/* ── Chapter V: Goal & Recommendations ── */}
      {(primaryGoal || (data.career_goals && data.career_goals.length > 0)) && (
        <motion.section custom={6} variants={fadeUp} initial="hidden" animate="visible" className="mb-20">
          <SectionTitle>方向</SectionTitle>
          <div className="grid gap-6 md:grid-cols-2">
            {/* Primary Goal */}
            {primaryGoal && (
              <div
                className="rounded-lg border p-6"
                style={{ borderColor: 'var(--chestnut)', background: 'var(--bg-card)' }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <Target className="w-4 h-4" style={{ color: 'var(--chestnut)' }} />
                  <span className="text-[11px] font-medium uppercase tracking-wider" style={{ ...sans, color: 'var(--chestnut)' }}>
                    当前目标
                  </span>
                </div>
                <p
                  className="text-[18px] font-medium"
                  style={{ ...serif, color: ink(1) }}
                >
                  {primaryGoal.target_label}
                </p>
                <p className="text-[13px] mt-1" style={{ ...sans, color: ink(2) }}>
                  {primaryGoal.from_node_label && `从 ${primaryGoal.from_node_label} 出发`}
                </p>
                <div className="mt-4 flex flex-wrap gap-3 text-[12px]" style={{ ...sans, color: ink(3) }}>
                  {primaryGoal.gap_skills && primaryGoal.gap_skills.length > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      待补 {primaryGoal.gap_skills.length} 项技能
                    </span>
                  )}
                  {primaryGoal.total_hours != null && primaryGoal.total_hours > 0 && (
                    <span>预估 {Math.round(primaryGoal.total_hours)} 小时</span>
                  )}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {data.career_goals && data.career_goals.length > (primaryGoal ? 1 : 0) && (
              <div className="rounded-lg border border-[var(--line)] bg-[var(--bg-card)] p-6">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-4 h-4" style={{ color: ink(3) }} />
                  <span className="text-[11px] font-medium uppercase tracking-wider" style={{ ...sans, color: ink(3) }}>
                    推荐方向
                  </span>
                </div>
                <div className="space-y-3">
                  {data.career_goals
                    .filter((g) => !g.is_primary)
                    .slice(0, 3)
                    .map((g) => (
                      <div key={g.id} className="flex items-center justify-between">
                        <span className="text-[14px]" style={{ ...sans, color: ink(1) }}>
                          {g.target_label}
                        </span>
                        <span className="text-[11px] tabular-nums" style={{ ...sans, color: ink(3) }}>
                          {g.safety_gain != null && `安全增益 ${Math.round(g.safety_gain * 100)}%`}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </motion.section>
      )}

      {/* ── Epilogue: CTAs ── */}
      <motion.section
        custom={7}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        className="pt-12 border-t border-[var(--line)]"
      >
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={onEdit}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full text-[14px] font-medium text-white transition-all duration-200 hover:opacity-90 active:scale-[0.98]"
            style={{ background: '#6B3E2E', ...sans }}
          >
            <PenLine className="w-4 h-4" />
            编辑档案
          </button>
          {onReport && (
            <button
              onClick={onReport}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full text-[14px] font-medium border transition-all duration-200 hover:bg-[var(--bg-card)] active:scale-[0.98]"
              style={{ borderColor: 'var(--line)', color: ink(1), ...sans }}
            >
              <FileText className="w-4 h-4" />
              生成成长报告
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
        <p className="text-center mt-6 text-[11px]" style={{ ...sans, color: ink(3) }}>
          档案仅用于系统分析，不会分享给任何第三方。
        </p>
      </motion.section>
    </div>
  )
}
