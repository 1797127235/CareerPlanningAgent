import { useState } from 'react'
import { Chapter, ChapterOpener, DropCap } from '@/components/editorial'
import { GoalCard, RecommendationCard } from './cards'
import type { ProfileData } from '@/types/profile'
import type { Recommendation } from './cards/RecommendationCard'

export function ProfileChapterIV({
  data,
  recommendations,
  onExploreGoal,
  onChangeGoal,
  onExploreRec,
}: {
  data: ProfileData
  recommendations: Recommendation[]
  onExploreGoal?: () => void
  onChangeGoal?: () => void
  onExploreRec?: (rec: Recommendation) => void
}) {
  const goal = data.career_goals?.find((g) => g.is_primary) || data.career_goals?.[0]
  const hasGoal = !!goal && !!goal.target_node_id
  const [showAll, setShowAll] = useState(false)
  const visibleRecs = showAll ? recommendations : recommendations.slice(0, 3)

  return (
    <Chapter
      numeral="IV"
      label="WHERE YOU WANT TO GO"
      title={hasGoal ? `你现在瞄的是 ${goal.target_label}。` : '先不急着定方向 —— 先看看有什么选项。'}
    >
      <ChapterOpener numeral="IV" title="你想去哪" />

      <div className="mt-8">
        <h3 className="font-sans text-[13px] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-3">
          4.1 · 你的目标
        </h3>
        {hasGoal ? (
          <GoalCard goal={goal} onExplore={onExploreGoal} onChange={onChangeGoal} />
        ) : (
          <div className="rounded-lg border border-[var(--line)] bg-[var(--bg-card)] p-5 md:p-6">
            <DropCap>还没有明确的目标 —— 这很正常。</DropCap>
            <div className="mt-4 flex flex-wrap gap-3">
              <button className="px-4 py-2 rounded-full bg-[var(--chestnut)] text-white text-[13px] font-medium hover:opacity-90">
                让 AI 帮我推荐
              </button>
              <button className="px-4 py-2 rounded-full border border-[var(--line)] text-[var(--ink-1)] text-[13px] font-medium hover:bg-[var(--line)]/10">
                我去图谱探索
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="mt-10">
        <h3 className="font-sans text-[13px] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-3">
          4.2 · 还可能去的方向
        </h3>
        {recommendations.length > 0 ? (
          <>
            <div className="mt-4 space-y-4">
              {visibleRecs.map((rec) => (
                <RecommendationCard key={rec.role_id} rec={rec} onExplore={() => onExploreRec?.(rec)} />
              ))}
            </div>
            {recommendations.length > 3 && (
              <button
                onClick={() => setShowAll((v) => !v)}
                className="mt-4 text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]"
              >
                {showAll ? '收起' : `展开更多（还有 ${recommendations.length - 3} 个）`}
              </button>
            )}
          </>
        ) : (
          <p className="text-[var(--fs-body)] text-[var(--ink-3)] italic">还没有推荐方向 —— 等画像再完善一点，系统会帮你列几个选项。</p>
        )}
      </div>
    </Chapter>
  )
}
