import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { getCoachResult } from '@/api/coach'
import { TableOfContents } from '@/components/editorial'
import {
  CoachResultPrologue,
  MarkdownNarrativeView,
  CoachResultEpilogue,
  NextStepsCard,
} from '@/components/coach-v2'
import { Block, BlockGrid, InlineTag, Callout, Tooltip } from '@/components/ui'
import { GLOSSARY } from '@/lib/glossary'
import { mockJdDiagnosis, mockCareerReport, mockInterviewReview } from '@/components/coach-v2/mockData'
import { bucketOf } from '@/lib/resultTypeBuckets'
import type { CoachResultDetail } from '@/types/coach'

function useCoachResult(id: string | undefined, isMock: boolean, mockData: CoachResultDetail | null) {
  return useQuery<CoachResultDetail>({
    queryKey: ['coach-result', id],
    queryFn: () => getCoachResult(Number(id)),
    enabled: !!id && !isMock,
    initialData: isMock && mockData ? mockData : undefined,
  })
}

function DiagnosisDashboard({ data }: { data: CoachResultDetail }) {
  const detail = data.detail
  const score = (detail?.match_score as number) ?? 0
  const matched = (detail?.matched_skills as string[]) || []
  const gaps = (detail?.gap_skills as { skill: string; priority: string; match_delta: number }[]) || []
  const totalSkills = matched.length + gaps.length
  const readiness = totalSkills > 0 ? Math.round((matched.length / totalSkills) * 100) : score
  const highPriGaps = gaps.filter((g) => g.priority === 'high')

  const assessment =
    readiness >= 70
      ? `你已经具备这个岗位的大部分核心技能，可以开始投递了。简历中重点突出已掌握的 ${matched.length} 项技能，同时关注缺口技能的补强。`
      : readiness >= 40
        ? `基础不错，还需要补强 ${gaps.length} 项技能。建议先集中精力搞定${highPriGaps.length > 0 ? `「${highPriGaps[0].skill}」等 ${highPriGaps.length} 项高优先级缺口` : `最关键的 ${gaps[0] ? `「${gaps[0].skill}」` : '缺口技能'}`}，准备度过 70% 就可以开始投递了。`
        : `和这个岗位还有不小的差距。建议先补强 ${highPriGaps.length} 项高优先级技能，或者考虑寻找和你当前技能更匹配的方向。`

  return (
    <div className="space-y-[var(--space-5)]">
      <BlockGrid>
        <Block
          kicker={
            <Tooltip content={GLOSSARY.match_score.desc} storageKey="match_score">
              <span>准备度</span>
            </Tooltip>
          }
          title="你有多接近这个岗位"
        >
          <p className="text-[var(--text-3xl)] font-semibold text-[var(--chestnut)] tabular-nums">
            {readiness}<span className="text-[var(--text-xl)]">%</span>
          </p>
          <div className="mt-3">
            <Callout tone="accent">
              <p className="font-serif italic text-[var(--text-base)]">{assessment}</p>
            </Callout>
          </div>
        </Block>

        <Block kicker="已具备" title={`${matched.length} 项核心技能`}>
          {matched.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {matched.map((skill) => (
                <InlineTag key={skill} tone="accent">
                  {skill}
                </InlineTag>
              ))}
            </div>
          ) : (
            <p className="text-[var(--text-sm)] text-[var(--ink-3)]">暂无匹配技能记录</p>
          )}
        </Block>

        <Block
          kicker={
            <Tooltip content={GLOSSARY.gap_skills.desc} storageKey="gap_skills">
              <span>缺口</span>
            </Tooltip>
          }
          title={`${gaps.length} 项待补齐`}
        >
          {gaps.length > 0 ? (
            <div className="space-y-2">
              {gaps.map((gap) => {
                const tone = gap.priority === 'high' ? 'warn' : gap.priority === 'medium' ? 'accent' : 'neutral'
                return (
                  <div key={gap.skill} className="flex items-center justify-between gap-3 py-1">
                    <span className="text-[var(--text-base)] text-[var(--ink-1)]">{gap.skill}</span>
                    <InlineTag tone={tone}>
                      {gap.priority === 'high' ? '高优先级' : gap.priority === 'medium' ? '中优先级' : '低优先级'}
                    </InlineTag>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-[var(--text-sm)] text-[var(--ink-3)]">暂无缺口记录</p>
          )}
        </Block>

        <Block kicker="下一步" title="可以立刻做的事">
          <NextStepsCard data={data} />
        </Block>
      </BlockGrid>
    </div>
  )
}

export default function CoachResultPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isMock = searchParams.get('mock') === '1'
  const mockType = searchParams.get('type') || 'jd'

  const mockData = isMock
    ? mockType === 'narrative'
      ? mockCareerReport
      : mockType === 'review'
        ? mockInterviewReview
        : mockJdDiagnosis
    : null

  const { data, isLoading, error } = useCoachResult(id, isMock, mockData)

  if (isLoading) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-[var(--space-5)]">
        <p className="font-serif italic text-[var(--text-lg)] text-[var(--ink-2)]">
          正在打开分析结果…
        </p>
      </main>
    )
  }

  if (error || !data) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-[var(--space-5)]">
        <div className="text-center max-w-md">
          <p className="text-[var(--text-lg)] text-[var(--ink-1)]">结果加载失败</p>
          <p className="mt-2 text-[var(--text-base)] text-[var(--ink-3)]">
            {error instanceof Error ? error.message : '找不到这份分析结果'}
          </p>
          <button
            onClick={() => navigate(-1)}
            className="mt-5 inline-flex items-center px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-[var(--text-sm)] font-medium"
          >
            返回
          </button>
        </div>
      </main>
    )
  }

  const isStructured = !!data.detail?._structured
  const bucket = bucketOf(data.result_type, isStructured)
  const jdTitle = (data.detail?.jd_title as string) || data.title || ''

  if (bucket === 'diagnosis') {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
        <div className="max-w-[860px] mx-auto px-[var(--space-6)] md:px-[var(--space-7)] py-[var(--space-6)]">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1.5 text-[var(--text-sm)] text-[var(--ink-3)] hover:text-[var(--ink-1)] transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            返回
          </button>

          <h1 className="text-[var(--text-xl)] font-semibold text-[var(--ink-1)] tracking-tight">
            {jdTitle}
          </h1>
          <p className="mt-1 text-[var(--text-sm)] text-[var(--ink-3)] font-serif italic">
            {data.created_at?.slice(0, 10)}
          </p>

          <div className="mt-[var(--space-5)]">
            <DiagnosisDashboard data={data} />
          </div>
        </div>
      </main>
    )
  }

  const tocItems = [{ id: 'chapter-1', numeral: 'I', label: '全文' }]

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <div className="max-w-[720px] mx-auto px-6 md:px-12 lg:px-20 pb-32">
        <CoachResultPrologue data={data} />
        <div id="chapter-1">
          <MarkdownNarrativeView data={data} />
        </div>
        <CoachResultEpilogue data={data} />
      </div>
      <TableOfContents items={tocItems} />
    </main>
  )
}
