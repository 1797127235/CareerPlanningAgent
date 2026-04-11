/**
 * GrowthDashboard — 顶部成长看板
 *
 * 展示学生当前成长状态：目标方向、分层技能覆盖率、匹配度曲线、成长天数
 * 数据源：GET /growth-log/dashboard（基于 skill_tiers + GrowthSnapshot）
 */
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { TrendingUp, Target, Calendar, ArrowRight } from 'lucide-react'

import { getGrowthDashboard } from '@/api/growthLog'
import type { GrowthDashboardData, TierCoverage } from '@/api/growthLog'

/* ── Tier bar ── */
function TierBar({ label, tier, color }: { label: string; tier: TierCoverage; color: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between">
        <span className="text-[11px] font-semibold text-slate-600">{label}</span>
        <span className="text-[11px] font-bold tabular-nums" style={{ color }}>
          {tier.covered}/{tier.total}
          <span className="ml-1 text-[10px] text-slate-400 font-medium">({tier.pct}%)</span>
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
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
        <p className="text-[11px] text-slate-400">数据不足，继续积累后将看到曲线变化</p>
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
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">技能覆盖率</p>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="text-[22px] font-bold text-slate-900 tabular-nums">{latest.toFixed(0)}%</span>
            {delta > 0 && (
              <span className="text-[11px] font-semibold text-emerald-600 tabular-nums">
                ↑ {delta.toFixed(1)}%
              </span>
            )}
            {delta < 0 && (
              <span className="text-[11px] font-semibold text-amber-600 tabular-nums">
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
              <stop offset="0%" stopColor="#2563EB" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            stroke="#94A3B8"
            fontSize={9}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#94A3B8"
            fontSize={9}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
            ticks={[0, 50, 100]}
          />
          <Tooltip
            contentStyle={{
              background: '#fff',
              border: '1px solid #E2E8F0',
              borderRadius: 8,
              fontSize: 11,
              padding: '6px 10px',
            }}
            formatter={(value: number) => [`${value.toFixed(1)}%`, '覆盖率']}
            labelStyle={{ color: '#475569', fontWeight: 600 }}
          />
          <Area
            type="monotone"
            dataKey="score"
            stroke="#2563EB"
            strokeWidth={2}
            fill="url(#readinessFill)"
            dot={{ r: 3, fill: '#2563EB', stroke: '#fff', strokeWidth: 1.5 }}
            activeDot={{ r: 5, fill: '#2563EB', stroke: '#fff', strokeWidth: 2 }}
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
        primaryCta: { label: '去图谱选方向', href: '/graph' },
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
        primaryCta: { label: '上传简历', href: '/profile' },
        secondaryCta: { label: '先去图谱探索', href: '/graph' },
      }

  const romanNumeral = hasProfile ? 'I' : '0'

  return (
    <div className="glass-static relative">
      {/* Decorative large Roman numeral (background) */}
      <div
        aria-hidden="true"
        className="pointer-events-none select-none absolute -right-4 top-1/2 -translate-y-1/2 text-[180px] md:text-[220px] font-black leading-none tracking-tighter z-0"
        style={{ fontFamily: 'Georgia, serif', color: 'rgba(37, 99, 235, 0.08)' }}
      >
        {romanNumeral}
      </div>

      {/* Foreground content */}
      <div className="relative z-10 px-7 py-8 md:px-10 md:py-10">
        <div className="max-w-[520px]">
          <p className="text-[10px] font-bold tracking-[0.18em] mb-2.5" style={{ color: '#2563EB' }}>
            {config.label}
          </p>
          <h2 className="text-[22px] md:text-[26px] font-bold leading-[1.3] mb-3 tracking-tight" style={{ color: '#0F172A' }}>
            {config.title}
          </h2>
          <p className="text-[12px] leading-relaxed mb-5" style={{ color: '#475569' }}>
            {config.body}
          </p>
          <div className="flex items-center gap-4 flex-wrap">
            <a
              href={config.primaryCta.href}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-900 text-white text-[12px] font-semibold rounded-full hover:bg-slate-800 transition-colors cursor-pointer"
            >
              {config.primaryCta.label}
              <ArrowRight className="w-3 h-3" />
            </a>
            <a
              href={config.secondaryCta.href}
              className="text-[11px] text-slate-500 hover:text-slate-800 underline underline-offset-4 transition-colors cursor-pointer"
            >
              {config.secondaryCta.label}
            </a>
          </div>
        </div>
      </div>
    </div>
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
      <div className="glass-static p-5 animate-pulse">
        <div className="h-5 w-1/3 bg-white/40 rounded mb-4" />
        <div className="grid grid-cols-2 gap-5">
          <div className="space-y-3">
            <div className="h-2 bg-white/40 rounded" />
            <div className="h-2 bg-white/40 rounded" />
            <div className="h-2 bg-white/40 rounded" />
          </div>
          <div className="h-[140px] bg-white/30 rounded" />
        </div>
      </div>
    )
  }

  if (!data || !data.has_goal) {
    return <EmptyDashboard hasProfile={data?.has_profile ?? false} />
  }

  const d = data as Required<Pick<GrowthDashboardData, 'goal' | 'skill_coverage' | 'readiness_curve' | 'days_since_start'>> & GrowthDashboardData
  const coverage = d.skill_coverage!
  const curve = d.readiness_curve ?? []

  return (
    <div className="glass-static p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-blue-600" />
          <h2 className="text-[14px] font-bold text-slate-800">成长看板</h2>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-slate-500">
          <div className="flex items-center gap-1">
            <Target className="w-3 h-3" />
            <span className="font-semibold text-slate-700">{d.goal!.target_label}</span>
          </div>
          <div className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            <span className="tabular-nums">已坚持 {d.days_since_start ?? 0} 天</span>
          </div>
        </div>
      </div>

      {/* Grid: Tier bars + Readiness curve */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Tiered skill coverage */}
        <div className="space-y-4">
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            技能覆盖（按市场重要性分层）
          </p>
          <TierBar label="核心技能" tier={coverage.core} color="#2563EB" />
          <TierBar label="重要技能" tier={coverage.important} color="#0891B2" />
          <TierBar label="加分技能" tier={coverage.bonus} color="#94A3B8" />
          {coverage.core.missing && coverage.core.missing.length > 0 && (
            <div className="pt-2 border-t border-slate-100">
              <p className="text-[10px] text-slate-400 mb-1.5">核心缺口：</p>
              <div className="flex flex-wrap gap-1">
                {coverage.core.missing.slice(0, 4).map(s => (
                  <span
                    key={s}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-medium border border-blue-100"
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
    </div>
  )
}
