/**
 * GrowthDashboard — 顶部成长看板
 *
 * 展示学生当前成长状态：目标方向、分层技能覆盖率、匹配度曲线、成长天数
 * 数据源：GET /growth-log/dashboard（基于 skill_tiers + GrowthSnapshot）
 */
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ArrowRight } from 'lucide-react'

import { getGrowthDashboard } from '@/api/growthLog'
import type { GrowthDashboardData, TierCoverage } from '@/api/growthLog'
import { PaperCard } from '@/components/growth-log/PaperCard'

/* ── Tier bar ── */
function TierBar({ label, tier, color }: { label: string; tier: TierCoverage; color: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between">
        <span className="text-[11px] font-semibold text-[var(--ink-2)]">{label}</span>
        <span className="text-[11px] font-bold tabular-nums" style={{ color }}>
          {tier.covered}/{tier.total}
          <span className="ml-1 text-[10px] text-[var(--ink-3)] font-medium">({tier.pct}%)</span>
        </span>
      </div>
      <div className="h-2 rounded-full bg-[var(--line)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${tier.pct}%`, background: color }}
        />
      </div>
    </div>
  )
}

/* ── Readiness curve chart ── */
function ReadinessCurve({ data }: { data: { date: string; score: number }[] }) {
  if (!data || data.length < 2) {
    return (
      <div className="h-[140px] flex items-center justify-center">
        <p className="text-[11px] text-[var(--ink-3)]">数据不足，继续积累后将看到曲线变化</p>
      </div>
    )
  }

  const latest = data[data.length - 1]?.score ?? 0
  const earliest = data[0]?.score ?? 0
  const delta = latest - earliest

  return (
    <div className="h-[160px]">
      <div className="flex items-baseline justify-between mb-2">
        <div>
          <p className="text-[10px] font-semibold text-[var(--ink-3)] uppercase tracking-wider">技能覆盖率</p>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="text-[22px] font-bold text-[var(--ink-1)] tabular-nums">{latest.toFixed(0)}%</span>
            {delta > 0 && (
              <span className="text-[11px] font-semibold text-[var(--moss)] tabular-nums">
                ↑ {delta.toFixed(1)}%
              </span>
            )}
            {delta < 0 && (
              <span className="text-[11px] font-semibold text-[var(--ember)] tabular-nums">
                ↓ {Math.abs(delta).toFixed(1)}%
              </span>
            )}
          </div>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={100}>
        <AreaChart data={data} margin={{ top: 5, right: 4, left: -24, bottom: 0 }}>
          <defs>
            <linearGradient id="readinessFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--moss)" stopOpacity={0.25} />
              <stop offset="100%" stopColor="var(--moss)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            stroke="var(--ink-3)"
            fontSize={9}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="var(--ink-3)"
            fontSize={9}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
            ticks={[0, 50, 100]}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-card)',
              border: '1px solid var(--line)',
              borderRadius: 6,
              fontSize: 11,
              padding: '6px 10px',
            }}
            formatter={(value: number) => [`${value.toFixed(1)}%`, '覆盖率']}
            labelStyle={{ color: 'var(--ink-2)', fontWeight: 600 }}
          />
          <Area
            type="monotone"
            dataKey="score"
            stroke="var(--moss)"
            strokeWidth={2}
            fill="url(#readinessFill)"
            dot={{ r: 3, fill: 'var(--moss)', stroke: 'var(--bg-card)', strokeWidth: 1.5 }}
            activeDot={{ r: 5, fill: 'var(--moss)', stroke: 'var(--bg-card)', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

/* ── Empty state (Editorial / Prologue style) ── */
function EmptyDashboard({ hasProfile }: { hasProfile: boolean }) {
  const config = hasProfile
    ? {
        label: 'CHAPTER I · 第一章',
        title: <>选择一个方向，<br/>然后开始看见差距。</>,
        body: (
          <>
            你的画像已经建好了，但系统还不知道你要往哪里去。
            <br />
            去图谱选一个目标方向，这里就会显示你和目标岗位的真实差距。
          </>
        ),
        primaryCta: { label: '去看看可能的方向', href: '/graph' },
        secondaryCta: { label: '让 AI 帮我推荐', href: '/profile' },
      }
    : {
        label: 'PROLOGUE · 序章',
        title: <>先看清你在哪，<br/>再决定往哪走。</>,
        body: (
          <>
            职业规划不是从"选方向"开始的。
            <br />
            先让系统看懂你现有的技能，再告诉它你想成为谁。
          </>
        ),
        primaryCta: { label: '想看你的画像 — 上传一份简历就好', href: '/profile' },
        secondaryCta: { label: '先去图谱探索', href: '/graph' },
      }

  const romanNumeral = hasProfile ? 'I' : '0'

  return (
    <PaperCard className="relative overflow-hidden">
      {/* Decorative large Roman numeral (background) */}
      <div
        aria-hidden="true"
        className="pointer-events-none select-none absolute -right-4 top-1/2 -translate-y-1/2 text-[180px] md:text-[220px] font-black leading-none tracking-tighter z-0"
        style={{ fontFamily: 'Georgia, serif', color: 'var(--line)' }}
      >
        {romanNumeral}
      </div>

      {/* Foreground content */}
      <div className="relative z-10">
        <div className="max-w-[520px]">
          <p className="font-serif text-[10px] font-bold tracking-[0.18em] mb-2.5 text-[var(--chestnut)]">
            {config.label}
          </p>
          <h2 className="font-display text-[22px] md:text-[26px] font-medium leading-[1.3] mb-3 tracking-tight text-[var(--ink-1)]">
            {config.title}
          </h2>
          <p className="text-[12px] leading-relaxed mb-5 text-[var(--ink-2)]">
            {config.body}
          </p>
          <div className="flex items-center gap-4 flex-wrap">
            <a
              href={config.primaryCta.href}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-[var(--chestnut)] text-white text-[12px] font-semibold rounded-md hover:bg-[var(--ink-1)] transition-colors cursor-pointer"
            >
              {config.primaryCta.label}
              <ArrowRight className="w-3 h-3" />
            </a>
            <a
              href={config.secondaryCta.href}
              className="text-[11px] text-[var(--ink-3)] hover:text-[var(--ink-1)] underline underline-offset-4 transition-colors cursor-pointer"
            >
              {config.secondaryCta.label}
            </a>
          </div>
        </div>
      </div>
    </PaperCard>
  )
}

/* ── Main Dashboard ── */
export function GrowthDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['growth-dashboard'],
    queryFn: getGrowthDashboard,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })

  if (isLoading) {
    return (
      <PaperCard className="animate-pulse">
        <div className="h-5 w-1/3 bg-[var(--line)] rounded mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="space-y-3">
            <div className="h-2 bg-[var(--line)] rounded" />
            <div className="h-2 bg-[var(--line)] rounded" />
            <div className="h-2 bg-[var(--line)] rounded" />
          </div>
          <div className="h-[140px] bg-[var(--line)] rounded" />
        </div>
      </PaperCard>
    )
  }

  if (!data || !data.has_goal) {
    return <EmptyDashboard hasProfile={data?.has_profile ?? false} />
  }

  const d = data as Required<Pick<GrowthDashboardData, 'goal' | 'skill_coverage' | 'readiness_curve' | 'days_since_start'>> & GrowthDashboardData
  const coverage = d.skill_coverage!
  const curve = d.readiness_curve ?? []

  return (
    <PaperCard>
      {/* Grid: Tier bars + Readiness curve */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Tiered skill coverage */}
        <div className="space-y-4">
          <p className="text-[10px] font-semibold text-[var(--ink-3)] uppercase tracking-wider">
            技能覆盖（按市场重要性分层）
          </p>
          <TierBar label="核心技能" tier={coverage.core} color="var(--moss)" />
          <TierBar label="重要技能" tier={coverage.important} color="var(--ember)" />
          <TierBar label="加分技能" tier={coverage.bonus} color="var(--ink-3)" />
          {coverage.core.missing && coverage.core.missing.length > 0 && (
            <div className="pt-2 border-t border-[var(--line)]">
              <p className="text-[10px] text-[var(--ink-3)] mb-1.5">核心缺口：</p>
              <div className="flex flex-wrap gap-1">
                {coverage.core.missing.slice(0, 4).map(s => (
                  <span
                    key={s}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-paper)] text-[var(--chestnut)] font-medium border border-[var(--line)]"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Readiness curve */}
        <div>
          <ReadinessCurve data={curve} />
        </div>
      </div>
    </PaperCard>
  )
}
