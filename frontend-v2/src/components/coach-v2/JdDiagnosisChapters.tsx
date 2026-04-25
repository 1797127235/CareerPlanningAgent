import { useState } from 'react'
import { motion } from 'framer-motion'
import { Chapter, PaperCard, PullQuote } from '@/components/editorial'
import { NextStepsCard } from './NextStepsCard'
import type { CoachResultDetail } from '@/types/coach'

export function JdDiagnosisChapters({ data }: { data: CoachResultDetail }) {
  const detail = data.detail
  const score = (detail?.match_score as number) ?? 0
  const matched = (detail?.matched_skills as string[]) || []
  const gaps = (detail?.gap_skills as { skill: string; priority: string; match_delta: number }[]) || []
  const totalSkills = matched.length + gaps.length
  const readiness = totalSkills > 0 ? Math.round((matched.length / totalSkills) * 100) : score
  const highPriGaps = gaps.filter((g) => g.priority === 'high')

  const assessment =
    readiness >= 70
      ? `准备度 ${readiness}%，你已经具备这个岗位的大部分核心技能，可以开始投递了。简历中重点突出已掌握的 ${matched.length} 项技能，同时关注缺口技能的补强。`
      : readiness >= 40
        ? `准备度 ${readiness}%，基础不错，还需要补强 ${gaps.length} 项技能。建议先集中精力搞定${highPriGaps.length > 0 ? `「${highPriGaps[0].skill}」等 ${highPriGaps.length} 项高优先级缺口` : `最关键的 ${gaps[0] ? `「${gaps[0].skill}」` : '缺口技能'}`}，准备度过 70% 就可以开始投递了。`
        : `准备度 ${readiness}%，和这个岗位还有不小的差距。建议先补强 ${highPriGaps.length} 项高优先级技能，或者考虑寻找和你当前技能更匹配的方向。`

  return (
    <>
      <Chapter numeral="I" label="准备度" title="你有多接近这个岗位">
        <div className="flex items-center gap-6">
          <p className="font-display font-medium text-[length:var(--fs-display-md)] text-[var(--chestnut)] tabular-nums">
            {readiness}
            <span className="text-[length:var(--fs-body-lg)]">%</span>
          </p>
          <p className="font-sans text-[length:var(--fs-body-lg)] text-[var(--ink-2)]">
            已具备 {matched.length} 项核心技能
            {gaps.length > 0 && <>，还有 {gaps.length} 项待补齐</>}
          </p>
        </div>
        <div className="mt-8">
          <PullQuote>{assessment}</PullQuote>
        </div>
      </Chapter>

      {matched.length > 0 && (
        <Chapter numeral="II" label="已具备" title="这些技能你已经有了">
          <div className="flex flex-wrap gap-2">
            {matched.map((skill, i) => (
              <motion.span
                key={skill}
                initial={{ opacity: 0, y: 4 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.03, duration: 0.3 }}
                className="inline-flex items-center px-3 py-1.5 rounded-full border border-[var(--line)] text-[length:var(--fs-body)] text-[var(--ink-1)]"
              >
                <span className="font-serif text-[var(--chestnut)] mr-2">·</span>
                {skill}
              </motion.span>
            ))}
          </div>
        </Chapter>
      )}

      {gaps.length > 0 && (
        <Chapter numeral="III" label="缺口" title="还需要补强什么">
          <PaperCard>
            <dl className="space-y-4">
              {gaps.map((gap) => {
                const pri =
                  gap.priority === 'high'
                    ? { label: 'HIGH', cls: 'text-[var(--ember)]' }
                    : gap.priority === 'medium'
                      ? { label: 'MEDIUM', cls: 'text-[var(--moss)]' }
                      : { label: 'LOW', cls: 'text-[var(--ink-3)]' }
                return (
                  <div key={gap.skill} className="flex items-center justify-between gap-4">
                    <dt className="font-serif italic text-[length:var(--fs-body-lg)] text-[var(--ink-1)]">
                      {gap.skill}
                    </dt>
                    <dd className={`font-sans text-[length:var(--fs-caption)] font-bold uppercase tracking-[0.15em] ${pri.cls}`}>
                      {pri.label}
                    </dd>
                  </div>
                )
              })}
            </dl>
          </PaperCard>
        </Chapter>
      )}

      <Chapter numeral="IV" label="下一步" title="可以立刻做的事">
        <NextStepsCard data={data} />
      </Chapter>
    </>
  )
}
