import { useMemo } from 'react'

interface SkillItem {
  module: string
  reason: string
  priority?: string
}

interface SkillRadarProps {
  mastered: SkillItem[]
  gaps: SkillItem[]
  coveragePct: number
}

export function SkillRadar({ mastered, gaps, coveragePct }: SkillRadarProps) {
  const size = 340
  const cx = size / 2
  const cy = size / 2
  const maxR = 130

  /* ── Merge & limit to avoid crowding ── */
  const all = useMemo(() => {
    const m = mastered.map((s) => ({ ...s, kind: 'mastered' as const }))
    const g = gaps.map((s) => ({ ...s, kind: 'gap' as const }))
    const combined = [...m, ...g]
    // If too many, keep all mastered + top gaps by priority
    if (combined.length <= 10) return combined
    const sortedGaps = g.sort((a, b) => {
      const order = { high: 0, medium: 1, low: 2 }
      return (order[a.priority as keyof typeof order] ?? 1) -
             (order[b.priority as keyof typeof order] ?? 1)
    })
    return [...m, ...sortedGaps.slice(0, 10 - m.length)]
  }, [mastered, gaps])

  const count = all.length
  if (count === 0) return null

  const angleStep = (2 * Math.PI) / count

  /* ── Helpers ── */
  const pt = (angle: number, r: number) => ({
    x: cx + r * Math.cos(angle),
    y: cy + r * Math.sin(angle),
  })

  const labelPt = (angle: number, r: number) => {
    const p = pt(angle, r)
    const cos = Math.cos(angle)
    const sin = Math.sin(angle)
    let tx = p.x
    let ty = p.y
    if (Math.abs(cos) < 0.15) tx -= 30      // near top/bottom: center-ish
    else if (cos > 0) tx += 8               // right side
    else tx -= 68                           // left side
    ty += sin > 0 ? 10 : -4                 // slight vertical offset
    return { x: tx, y: ty, align: cos < -0.15 ? 'end' : cos > 0.15 ? 'start' : 'middle' as const }
  }

  /* ── Build paths ── */
  const masteredPoly: string[] = []
  const gapPoly: string[] = []

  all.forEach((item, i) => {
    const angle = i * angleStep - Math.PI / 2 // start from top
    const isMastered = item.kind === 'mastered'
    const r = isMastered ? maxR : maxR * 0.45
    const p = pt(angle, r)
    ;(isMastered ? masteredPoly : gapPoly).push(`${p.x},${p.y}`)
  })

  const masteredPath = masteredPoly.length > 2
    ? `M ${masteredPoly[0]} L ${masteredPoly.slice(1).join(' L ')} Z`
    : ''

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ display: 'block' }}>
      <defs>
        {/* Warm radial glow */}
        <radialGradient id="radarGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#B85C38" stopOpacity="0.25" />
          <stop offset="60%" stopColor="#B85C38" stopOpacity="0.08" />
          <stop offset="100%" stopColor="#B85C38" stopOpacity="0" />
        </radialGradient>
        {/* Gap area pattern */}
        <pattern id="gapHatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="4" stroke="#8A7E6B" strokeOpacity="0.25" strokeWidth="1" />
        </pattern>
      </defs>

      {/* Background rings */}
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <circle
          key={f}
          cx={cx}
          cy={cy}
          r={maxR * f}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={1}
          strokeDasharray={f === 1 ? undefined : '2 4'}
        />
      ))}

      {/* Axis lines */}
      {all.map((_, i) => {
        const angle = i * angleStep - Math.PI / 2
        const p = pt(angle, maxR)
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={p.x}
            y2={p.y}
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={1}
          />
        )
      })}

      {/* Gap area (hatched) */}
      {gapPoly.length > 2 && (
        <polygon
          points={gapPoly.join(' ')}
          fill="url(#gapHatch)"
          stroke="#8A7E6B"
          strokeOpacity="0.3"
          strokeWidth={1}
          strokeDasharray="4 3"
        />
      )}

      {/* Warm glow behind mastered area */}
      {masteredPath && (
        <path d={masteredPath} fill="url(#radarGlow)" />
      )}

      {/* Mastered area fill */}
      {masteredPath && (
        <path
          d={masteredPath}
          fill="rgba(184,92,56,0.18)"
          stroke="#B85C38"
          strokeWidth={2}
          strokeLinejoin="round"
        />
      )}

      {/* Data points */}
      {all.map((item, i) => {
        const angle = i * angleStep - Math.PI / 2
        const isMastered = item.kind === 'mastered'
        const r = isMastered ? maxR : maxR * 0.45
        const p = pt(angle, r)
        return (
          <g key={i}>
            <circle
              cx={p.x}
              cy={p.y}
              r={isMastered ? 5 : 4}
              fill={isMastered ? '#B85C38' : '#1F1F1F'}
              stroke={isMastered ? '#F9F4EE' : '#8A7E6B'}
              strokeWidth={isMastered ? 2 : 1.5}
            />
            {/* Labels */}
            {(() => {
              const lp = labelPt(angle, maxR + 18)
              return (
                <text
                  x={lp.x}
                  y={lp.y}
                  textAnchor={lp.align}
                  fill={isMastered ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.45)'}
                  fontSize={11}
                  fontWeight={isMastered ? 500 : 400}
                  style={{ fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }}
                >
                  {item.module.length > 7 ? item.module.slice(0, 6) + '…' : item.module}
                </text>
              )
            })()}
          </g>
        )
      })}

      {/* Center: coverage percentage */}
      <circle cx={cx} cy={cy} r={38} fill="#1F1F1F" stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
      <text
        x={cx}
        y={cy - 2}
        textAnchor="middle"
        fill="#F9F4EE"
        fontSize={22}
        fontWeight={700}
        style={{ fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }}
      >
        {coveragePct}%
      </text>
      <text
        x={cx}
        y={cy + 16}
        textAnchor="middle"
        fill="rgba(255,255,255,0.45)"
        fontSize={10}
        letterSpacing={1}
        style={{ fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }}
      >
        技能覆盖
      </text>
    </svg>
  )
}
