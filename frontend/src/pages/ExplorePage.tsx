import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchGraphMap } from '@/api/graph'
import { setCareerGoal } from '@/api/graph'
import type { GraphNode } from '@/types/graph'
import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'
import { JobPickerButton } from '@/components/explore/JobPickerButton'
import { ComparisonRow } from '@/components/explore/ComparisonRow'

const FIELD_ORDER: Array<{ key: keyof NonNullable<GraphNode['contextual_narrative']>; label: string }> = [
  { key: 'what_you_actually_do', label: '你每天真正在做的事' },
  { key: 'what_drains_you',      label: '什么会耗尽你' },
  { key: 'three_year_outlook',   label: '3 年后这岗位的样子' },
  { key: 'who_fits',             label: '什么样的人适合' },
  { key: 'ai_impact_today',      label: 'AI 今天在这岗位里做什么' },
  { key: 'common_entry_path',    label: '学生怎么切进去' },
]

export default function ExplorePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { token } = useAuth()
  const { profile, loading: profileLoading } = useProfileData(token)

  const leftId = searchParams.get('left') ?? ''
  const rightId = searchParams.get('right') ?? ''

  const { data: graphData, isLoading } = useQuery({
    queryKey: ['graph-map'],
    queryFn: fetchGraphMap,
    staleTime: 10 * 60 * 1000,
  })

  const availableNodes = useMemo(
    () => graphData?.nodes ?? [],
    [graphData?.nodes],
  )

  const allNodes = graphData?.nodes ?? []

  const leftNode = allNodes.find(n => n.node_id === leftId) ?? null
  const rightNode = allNodes.find(n => n.node_id === rightId) ?? null

  const setLeft = (nid: string) => {
    searchParams.set('left', nid)
    setSearchParams(searchParams)
  }
  const setRight = (nid: string) => {
    searchParams.set('right', nid)
    setSearchParams(searchParams)
  }

  const chooseAsTarget = async (nid: string) => {
    const node = allNodes.find(n => n.node_id === nid)
    if (!node || !profile) {
      alert('设置目标失败，请稍后重试')
      return
    }
    try {
      await setCareerGoal({
        profile_id: profile.id,
        target_node_id: node.node_id,
        target_label: node.label,
        target_zone: node.zone,
        gap_skills: node.must_skills || [],
        estimated_hours: 0,
        safety_gain: 0,
        salary_p50: node.salary_p50 || 0,
      })
      navigate('/profile')
    } catch (e) {
      console.error('设置目标失败', e)
      alert('设置目标失败，请稍后重试')
    }
  }

  if (isLoading) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <p className="text-[13px] text-slate-400">加载岗位信息…</p>
      </main>
    )
  }

  return (
    <motion.main
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="min-h-screen px-6 py-10"
    >
      <div className="mx-auto max-w-[880px]">
        <header className="mb-10">
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-400 mb-3">
            EXPLORE
          </p>
          <h1 className="text-[32px] md:text-[40px] font-extrabold text-slate-900 leading-[1.1] tracking-[-0.02em]">
            并排看两个方向。
          </h1>
          <p className="mt-3 text-[13px] text-slate-500 max-w-[56ch]">
            先弄懂每个岗位真实的样子，再决定往哪走。{availableNodes.length} 个方向可对比。
          </p>
        </header>

        <div className="grid grid-cols-2 gap-6 mb-10">
          <JobPickerButton
            label="左"
            selectedNode={leftNode}
            availableNodes={availableNodes}
            allNodes={allNodes}
            onSelect={setLeft}
          />
          <JobPickerButton
            label="右"
            selectedNode={rightNode}
            availableNodes={availableNodes}
            allNodes={allNodes}
            onSelect={setRight}
          />
        </div>

        {leftNode?.contextual_narrative && rightNode?.contextual_narrative && (
          <>
            <div className="space-y-8 mb-10">
              {FIELD_ORDER.map(({ key, label }, index) => (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04, duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                >
                  <ComparisonRow
                    label={label}
                    leftText={leftNode.contextual_narrative![key]}
                    rightText={rightNode.contextual_narrative![key]}
                  />
                </motion.div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-6 pt-8 border-t border-slate-200">
              <button
                onClick={() => chooseAsTarget(leftNode.node_id)}
                className="text-[13px] font-semibold text-slate-900 border border-slate-900 py-3 px-4 hover:bg-slate-900 hover:text-white hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:scale-[0.98] transition-all duration-200 cursor-pointer"
              >
                选 {leftNode.label} 作为我的目标 →
              </button>
              <button
                onClick={() => chooseAsTarget(rightNode.node_id)}
                className="text-[13px] font-semibold text-slate-900 border border-slate-900 py-3 px-4 hover:bg-slate-900 hover:text-white hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:scale-[0.98] transition-all duration-200 cursor-pointer"
              >
                选 {rightNode.label} 作为我的目标 →
              </button>
            </div>
          </>
        )}

        {(!leftNode || !rightNode) && (
          <div className="text-center py-16">
            <p className="text-[13px] text-slate-400">
              在上方选择两个岗位开始对比。
            </p>
          </div>
        )}
      </div>
    </motion.main>
  )
}
