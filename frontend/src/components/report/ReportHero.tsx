import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { ScoreRing } from '@/components/shared'
import type { ReportNarrative } from '@/api/report'

interface ReportHeroProps {
  matchScore: number
  targetJob: string
  narrative?: ReportNarrative
  reportVersion?: number
}

export function ReportHero({ matchScore, targetJob, narrative, reportVersion }: ReportHeroProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
      className="glass-static p-6 mb-6"
    >
      <div className="relative z-[1] flex flex-col sm:flex-row gap-6 items-start">
        {/* Score ring */}
        {matchScore > 0 && (
          <div className="shrink-0">
            <ScoreRing score={matchScore} label={targetJob ? '岗位匹配' : '准备度'} size={100} />
          </div>
        )}

        {/* Summary text */}
        <div className="flex-1 min-w-0">
          {reportVersion && reportVersion > 1 && (
            <span className="stat-cap text-[11px] font-medium text-[var(--text-3)] mb-2 inline-block">
              第 {reportVersion} 版报告
            </span>
          )}

          {narrative?.summary ? (
            <p className="text-[14px] text-[var(--text-2)] leading-relaxed">
              {narrative.summary}
            </p>
          ) : (
            targetJob && (
              <p className="text-[14px] text-[var(--text-2)]">
                目标岗位：{targetJob}，匹配度 {matchScore}%
              </p>
            )
          )}

          {narrative?.comparison && (
            <div className="mt-3 flex items-start gap-2 p-3 rounded-xl bg-white/30">
              {narrative.comparison.includes('提升') || narrative.comparison.includes('进步') ? (
                <TrendingUp className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
              ) : (
                <TrendingDown className="w-4 h-4 text-orange-500 mt-0.5 shrink-0" />
              )}
              <p className="text-[13px] text-[var(--text-2)] leading-relaxed">
                {narrative.comparison}
              </p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
