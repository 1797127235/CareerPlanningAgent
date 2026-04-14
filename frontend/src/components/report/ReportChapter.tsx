import { motion } from 'framer-motion'
import { Lock, ArrowRight } from 'lucide-react'
import { SkillChip } from '@/components/shared'
import type { ReportChapter as ChapterType } from '@/api/report'

const LEVEL_ZH: Record<string, string> = {
  advanced: '精通',
  proficient: '精通',
  intermediate: '熟练',
  beginner: '入门',
}

const LEVEL_PCT: Record<string, number> = {
  advanced: 87,
  proficient: 80,
  intermediate: 60,
  beginner: 28,
}

interface ReportChapterProps {
  chapter: ChapterType
  narrativeText?: string | null
  index: number
  editing?: boolean
  onNarrativeChange?: (text: string) => void
}

export function ReportChapterCard({ chapter, narrativeText, index, editing, onNarrativeChange }: ReportChapterProps) {
  if (!chapter.has_data) {
    return <LockedCard title={chapter.title} hint={chapter.locked_hint} />
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.06 * index, ease: [0.23, 1, 0.32, 1] }}
      className="glass-static p-5"
    >
      <div className="relative z-[1]">
        <h3 className="text-[15px] font-semibold text-[var(--text-1)] mb-0.5">{chapter.title}</h3>
        {chapter.subtitle && (
          <p className="text-[11px] text-[var(--text-3)] mb-4">{chapter.subtitle}</p>
        )}

        <ChapterContent chapter={chapter} />

        {narrativeText && <AiInsight text={narrativeText} editing={editing} onChange={onNarrativeChange} />}
      </div>
    </motion.div>
  )
}

/* ── AI Insight callout ── */
function AiInsight({ text, editing, onChange }: { text: string; editing?: boolean; onChange?: (text: string) => void }) {
  return (
    <div className={`mt-4 pl-3.5 border-l-2 border-blue-300 bg-blue-50/60 rounded-r-xl py-2.5 pr-3 ${editing ? 'ring-1 ring-blue-300' : ''}`}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <svg className="w-3 h-3 text-blue-600 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M9.663 17h4.673M12 3v1m6.364 1.636-.707.707M21 12h-1M4 12H3m3.343-5.657-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600">AI 洞察{editing ? ' · 可编辑' : ''}</span>
      </div>
      {editing ? (
        <div
          contentEditable
          suppressContentEditableWarning
          className="text-[12.5px] leading-relaxed text-[var(--text-2)] outline-none focus:bg-white/80 rounded px-1 -mx-1 min-h-[2em]"
          onBlur={(e) => onChange?.(e.currentTarget.textContent ?? '')}
          dangerouslySetInnerHTML={{ __html: text }}
        />
      ) : (
        <p className="text-[12.5px] leading-relaxed text-[var(--text-2)]">{text}</p>
      )}
    </div>
  )
}

/* ── Per-chapter structured content ── */
function ChapterContent({ chapter }: { chapter: ChapterType }) {
  const d = chapter.data
  switch (chapter.key) {
    case 'ability':    return <AbilityContent data={d} />
    case 'job_match':  return <JobMatchContent data={d} />
    case 'career_path': return <CareerPathContent data={d} />
    case 'action_plan': return <ActionPlanContent data={d} />
    case 'interview':  return <InterviewContent data={d} />
    default: return null
  }
}

/* ── Chapter 1: Ability ── */
function AbilityContent({ data }: { data: Record<string, unknown> }) {
  const skills = (data.skills ?? []) as Array<{ name: string; level: string }>
  const counts = data.level_counts as Record<string, number> | undefined
  const knowledgeAreas = (data.knowledge_areas ?? []) as string[]

  if (!skills.length) return null

  return (
    <div>
      {/* level summary */}
      {counts && (
        <div className="flex gap-2 mb-3.5">
          {Object.entries(counts).map(([level, count]) =>
            count > 0 ? (
              <span key={level} className="stat-cap text-[10.5px] font-medium text-[var(--text-2)]">
                {LEVEL_ZH[level] ?? level} {count}
              </span>
            ) : null,
          )}
        </div>
      )}

      {/* skill bars */}
      <div className="flex flex-col gap-2.5 mb-4">
        {skills.slice(0, 10).map((s) => (
          <div key={s.name}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[12.5px] text-[var(--text-2)]">{s.name}</span>
              <span className="text-[10.5px] text-[var(--text-3)]">{LEVEL_ZH[s.level] ?? s.level}</span>
            </div>
            <div className="progress-track">
              <motion.div
                className="progress-fill"
                initial={{ width: 0 }}
                animate={{ width: `${LEVEL_PCT[s.level] ?? 50}%` }}
                transition={{ duration: 0.65, ease: [0.23, 1, 0.32, 1], delay: 0.3 }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* knowledge areas — new */}
      {knowledgeAreas.length > 0 && (
        <>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-3)] mb-2">
            知识领域 · {knowledgeAreas.length} 项
          </p>
          <div className="flex flex-wrap gap-1.5">
            {knowledgeAreas.map((k) => (
              <span
                key={k}
                className="inline-flex items-center px-2.5 py-1 rounded-full text-[11.5px] font-medium bg-emerald-50 border border-emerald-200 text-emerald-700"
              >
                {k}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

/* ── Chapter 2: Job Match ── */
function JobMatchContent({ data }: { data: Record<string, unknown> }) {
  const matched = (data.matched_skills ?? []) as string[]
  const missing = (data.missing_skills ?? []) as Array<string | { skill: string }>
  const verdict = data.verdict as string | undefined

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-[13px] text-[var(--text-2)]">目标岗位</span>
        <span className="text-[14px] font-semibold text-[var(--text-1)]">{data.jd_title as string}</span>
        <span className="ml-auto text-[22px] font-bold tabular-nums text-[var(--blue)]">
          {data.match_score as number}%
        </span>
      </div>

      {matched.length > 0 && (
        <>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-3)] mb-1.5">已匹配</p>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {matched.map((s) => <SkillChip key={s} name={s} matched />)}
          </div>
        </>
      )}
      {missing.length > 0 && (
        <>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-3)] mb-1.5">缺失技能</p>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {missing.map((s) => {
              const name = typeof s === 'string' ? s : s.skill
              return <SkillChip key={name} name={name} matched={false} />
            })}
          </div>
        </>
      )}
      {verdict && (
        <p className="text-[12.5px] text-[var(--text-2)] leading-relaxed mt-1">{verdict}</p>
      )}
    </div>
  )
}

/* ── Chapter 3: Career Path ── */
const ZONE_ZH: Record<string, string> = { safe: '安全区', transition: '过渡区', danger: '危险区', leverage: '杠杆区' }
const ZONE_CLS: Record<string, string> = {
  safe:       'bg-emerald-50 border-emerald-200 text-emerald-700',
  leverage:   'bg-blue-50 border-blue-200 text-blue-700',
  danger:     'bg-red-50 border-red-200 text-red-600',
  transition: 'bg-amber-50 border-amber-200 text-amber-700',
}

function CareerPathContent({ data }: { data: Record<string, unknown> }) {
  const goal = data.goal as Record<string, unknown> | undefined
  const routes = (data.escape_routes ?? []) as Array<{
    target_label: string
    target_zone?: string
    gap_skills: Array<string | { name: string }>
    estimated_hours?: number
    safety_gain?: number
    salary_p50?: number
    tag?: string
  }>
  const trendInsight = data.trend_insight as { label: string; insight: string } | undefined

  if (!goal && !routes.length) return null

  return (
    <div>
      {/* Industry trend insight */}
      {trendInsight && (
        <div className="mb-4 flex items-start gap-2.5 p-3 bg-slate-50/80 border border-slate-100 rounded-xl">
          <span className="shrink-0 inline-flex px-1.5 py-0.5 rounded text-[9.5px] font-bold border bg-amber-50 border-amber-200 text-amber-700 mt-0.5">
            行业趋势 · {trendInsight.label}
          </span>
          <p className="text-[12px] text-[var(--text-2)] leading-relaxed">{trendInsight.insight}</p>
        </div>
      )}

      {goal && (
        <div className="mb-5 p-3.5 bg-blue-50 border border-blue-100 rounded-xl">
          <div className="flex items-center gap-2.5 mb-2">
            <span className="text-[13.5px] font-semibold text-[var(--text-1)]">{goal.target_label as string}</span>
            {!!goal.target_zone && (
              <span className={`inline-flex px-1.5 py-0.5 rounded text-[9.5px] font-bold border ${ZONE_CLS[goal.target_zone as string] ?? ZONE_CLS.transition}`}>
                {ZONE_ZH[goal.target_zone as string] ?? '过渡区'}
              </span>
            )}
          </div>
          {((goal.gap_skills ?? []) as Array<string | { name: string }>).length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {((goal.gap_skills ?? []) as Array<string | { name: string }>).map((g) => {
                const name = typeof g === 'string' ? g : g.name
                return <SkillChip key={name} name={name} matched={false} />
              })}
            </div>
          )}
        </div>
      )}

      {routes.length > 0 && (
        <>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-3)] mb-2.5">
            {goal ? 'AI 时代逃逸路线' : '推荐发展路线'}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {routes.map((route) => {
              const gaps = route.gap_skills.map(g => typeof g === 'string' ? g : g.name)
              const zoneCls = ZONE_CLS[route.target_zone ?? ''] ?? ZONE_CLS.transition
              return (
                <div key={route.target_label} className="bg-slate-50/80 rounded-xl p-3.5 border border-slate-100">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[12.5px] font-semibold text-[var(--text-1)]">{route.target_label}</span>
                      {route.tag && (
                        <span className="text-[9.5px] font-bold px-1.5 py-0.5 rounded bg-blue-600 text-white">{route.tag}</span>
                      )}
                    </div>
                    {route.target_zone && (
                      <span className={`inline-flex px-1.5 py-0.5 rounded text-[9.5px] font-bold border ${zoneCls}`}>
                        {ZONE_ZH[route.target_zone] ?? '过渡区'}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-3 text-[10.5px] text-[var(--text-3)] mb-2">
                    {route.safety_gain ? <span>+{route.safety_gain} 安全度</span> : null}
                    {route.salary_p50 ? <span>¥{(route.salary_p50 / 1000).toFixed(0)}k</span> : null}
                    {route.estimated_hours ? <span>{route.estimated_hours}h</span> : null}
                  </div>
                  {gaps.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {gaps.map(name => <SkillChip key={name} name={name} matched={false} />)}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

/* ── Chapter 4: Action Plan ── */
const SOURCE_BADGE: Record<string, { label: string; cls: string }> = {
  goal_gap:  { label: '职业目标', cls: 'bg-emerald-50 border-emerald-200 text-emerald-700' },
  jd_gap:    { label: 'JD 缺口',  cls: 'bg-blue-50 border-blue-200 text-blue-700' },
  review:    { label: '复盘弱项', cls: 'bg-purple-50 border-purple-200 text-purple-700' },
  mock_gap:  { label: '模拟面试', cls: 'bg-red-50 border-red-200 text-red-600' },
}

function ActionPlanContent({ data }: { data: Record<string, unknown> }) {
  const short = (data.short_term ?? []) as Array<{ skill: string; detail: string; priority: string; source?: string }>
  const mid   = (data.mid_term   ?? []) as Array<{ skill: string; detail: string; source?: string }>
  const checklist = data.checklist as { progress: number; passed: number; total: number; jd_title: string } | undefined
  const evalSchedule = data.evaluation_schedule as { short_term_label: string; mid_term_label: string; review_hint: string } | undefined

  return (
    <div className="space-y-4">
      {short.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-3)] mb-2.5">短期重点</p>
          <div className="space-y-2.5">
            {short.map((a) => {
              const src = SOURCE_BADGE[a.source ?? '']
              return (
                <div key={a.skill} className="flex items-start gap-2">
                  <div className="flex gap-1 shrink-0 mt-0.5">
                    <span className="inline-flex px-1.5 py-0.5 rounded text-[9.5px] font-bold bg-red-50 border border-red-200 text-red-600">
                      高优先
                    </span>
                    {src && (
                      <span className={`inline-flex px-1.5 py-0.5 rounded text-[9.5px] font-bold border ${src.cls}`}>
                        {src.label}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-[12.5px] font-medium text-[var(--text-1)]">{a.skill}</span>
                    {a.detail && (
                      <span className="text-[11.5px] text-[var(--text-3)]"> — {a.detail}</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {mid.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-3)] mb-2.5">中期提升</p>
          <div className="space-y-2.5">
            {mid.map((a) => {
              const src = SOURCE_BADGE[a.source ?? '']
              return (
                <div key={a.skill} className="flex items-start gap-2">
                  <div className="flex gap-1 shrink-0 mt-0.5">
                    <span className="inline-flex px-1.5 py-0.5 rounded text-[9.5px] font-bold bg-amber-50 border border-amber-200 text-amber-700">
                      中期
                    </span>
                    {src && (
                      <span className={`inline-flex px-1.5 py-0.5 rounded text-[9.5px] font-bold border ${src.cls}`}>
                        {src.label}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-[12.5px] font-medium text-[var(--text-2)]">{a.skill}</span>
                    {a.detail && (
                      <span className="text-[11.5px] text-[var(--text-3)]"> — {a.detail}</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {checklist && (
        <div className="pt-4 border-t border-black/[0.06]">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[12.5px] text-[var(--text-2)]">面试清单 · {checklist.jd_title}</span>
            <span className="text-[12px] font-medium tabular-nums text-[var(--text-1)]">
              {checklist.passed}/{checklist.total}
            </span>
          </div>
          <div className="progress-track">
            <motion.div
              className="progress-fill"
              style={{ background: 'linear-gradient(90deg, #f59e0b, #fbbf24)' }}
              initial={{ width: 0 }}
              animate={{ width: `${checklist.progress}%` }}
              transition={{ duration: 0.65, ease: [0.23, 1, 0.32, 1] }}
            />
          </div>
        </div>
      )}

      {evalSchedule && (
        <div className="pt-4 border-t border-black/[0.06]">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-3)] mb-2">评估周期</p>
          <div className="flex gap-2 mb-2.5">
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-blue-50 border border-blue-100 text-[11px] text-blue-700 font-medium">
              短期检查点 · {evalSchedule.short_term_label}
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-purple-50 border border-purple-100 text-[11px] text-purple-700 font-medium">
              中期复盘 · {evalSchedule.mid_term_label}
            </span>
          </div>
          <p className="text-[11.5px] text-[var(--text-3)] leading-relaxed">{evalSchedule.review_hint}</p>
        </div>
      )}
    </div>
  )
}

/* ── Chapter 5: Interview ── */
function InterviewContent({ data }: { data: Record<string, unknown> }) {
  const records = (data.records ?? []) as Array<{
    question: string
    score: number
    target_job: string
    strengths: Array<{ point: string } | string>
    weaknesses: Array<{ point: string; suggestion?: string } | string>
  }>
  const avg   = data.avg_score as number | undefined
  const total = data.total_count as number | undefined

  const latest = records[0]

  return (
    <div>
      {/* stats row */}
      <div className="grid grid-cols-3 bg-slate-50 border border-slate-100 rounded-xl overflow-hidden mb-4">
        {total != null && (
          <div className="text-center py-2.5 border-r border-slate-100">
            <span className="text-[18px] font-bold tabular-nums text-[var(--text-1)] block leading-none">{total}</span>
            <span className="text-[10px] text-[var(--text-3)] mt-0.5 block">复盘次数</span>
          </div>
        )}
        {avg != null && (
          <div className="text-center py-2.5 border-r border-slate-100">
            <span className="text-[18px] font-bold tabular-nums text-[var(--text-1)] block leading-none">{avg}</span>
            <span className="text-[10px] text-[var(--text-3)] mt-0.5 block">平均得分</span>
          </div>
        )}
        <div className="text-center py-2.5">
          <span className="text-[18px] font-bold text-emerald-500 block leading-none">↑</span>
          <span className="text-[10px] text-[var(--text-3)] mt-0.5 block">近期趋势</span>
        </div>
      </div>

      {/* recent records */}
      {records.length > 0 && (
        <div className="space-y-0 divide-y divide-slate-50 mb-4">
          {records.slice(0, 5).map((r, i) => {
            const scoreColor = r.score >= 80 ? 'text-emerald-600' : r.score >= 65 ? 'text-amber-600' : 'text-red-500'
            return (
              <div key={i} className="flex items-center gap-2 py-1.5">
                <span className="flex-1 text-[12px] text-[var(--text-2)] truncate">{r.question}</span>
                <span className={`text-[12.5px] font-semibold tabular-nums shrink-0 ${scoreColor}`}>{r.score} 分</span>
              </div>
            )
          })}
        </div>
      )}

      {/* latest record strengths / weaknesses — new */}
      {latest && (latest.strengths.length > 0 || latest.weaknesses.length > 0) && (
        <div className="grid grid-cols-2 gap-2">
          {latest.strengths.length > 0 && (
            <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-2.5">
              <p className="text-[9.5px] font-bold uppercase tracking-wider text-emerald-700 mb-1.5">优势亮点</p>
              <div className="space-y-1">
                {latest.strengths.slice(0, 3).map((s, i) => {
                  const text = typeof s === 'string' ? s : s.point
                  return (
                    <p key={i} className="text-[11px] text-[var(--text-2)] leading-snug pl-2.5 relative before:content-['·'] before:absolute before:left-0 before:text-emerald-500 before:font-bold">
                      {text}
                    </p>
                  )
                })}
              </div>
            </div>
          )}
          {latest.weaknesses.length > 0 && (
            <div className="bg-red-50 border border-red-100 rounded-xl p-2.5">
              <p className="text-[9.5px] font-bold uppercase tracking-wider text-red-600 mb-1.5">待改进项</p>
              <div className="space-y-1">
                {latest.weaknesses.slice(0, 3).map((w, i) => {
                  const text = typeof w === 'string' ? w : w.point
                  return (
                    <p key={i} className="text-[11px] text-[var(--text-2)] leading-snug pl-2.5 relative before:content-['·'] before:absolute before:left-0 before:text-red-400 before:font-bold">
                      {text}
                    </p>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Locked card ── */
function LockedCard({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="glass-static p-4 opacity-55">
      <div className="relative z-[1] flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-slate-200/50 flex items-center justify-center shrink-0">
          <Lock className="w-3.5 h-3.5 text-slate-400" />
        </div>
        <div>
          <h3 className="text-[13.5px] font-medium text-[var(--text-2)]">{title}</h3>
          {hint && <p className="text-[11.5px] text-[var(--text-3)]">{hint}</p>}
        </div>
        <ArrowRight className="w-4 h-4 text-slate-300 ml-auto" />
      </div>
    </div>
  )
}
