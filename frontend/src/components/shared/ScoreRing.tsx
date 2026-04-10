import { useEffect, useState } from 'react'
import { useReducedMotion } from 'framer-motion'

interface ScoreRingProps {
  score: number
  label?: string
  size?: number
}

function scoreColor(score: number): string {
  if (score <= 30) return '#ef4444'  // red-500
  if (score <= 70) return '#eab308'  // yellow-500
  return '#22c55e'                   // green-500
}

export function ScoreRing({ score, label, size = 120 }: ScoreRingProps) {
  const shouldReduceMotion = useReducedMotion()
  const [display, setDisplay] = useState(shouldReduceMotion ? score : 0)

  const strokeWidth = 8
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (display / 100) * circumference

  useEffect(() => {
    if (shouldReduceMotion) {
      setDisplay(score)
      return
    }
    let frame: number
    const start = performance.now()
    const duration = 600
    const animate = (now: number) => {
      const t = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3) // easeOutCubic
      setDisplay(Math.round(eased * score))
      if (t < 1) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [score, shouldReduceMotion])

  const color = scoreColor(display)

  return (
    <div className="relative flex flex-col items-center gap-2">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-300"
        />
      </svg>
      <div
        className="absolute flex flex-col items-center justify-center"
        style={{ width: size, height: size }}
      >
        <span className="text-[28px] font-bold text-[var(--text-1)]">{display}%</span>
        {label && <span className="text-[12px] text-[var(--text-3)]">{label}</span>}
      </div>
    </div>
  )
}
