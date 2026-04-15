import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { FolderKanban, Crosshair, Target, Search, ArrowRight } from 'lucide-react'
import { PaperCard } from '@/components/editorial'
import { createApplication } from '@/api/applications'
import { patchCareerGoalGaps } from '@/api/graph'
import { parseJdTitle } from '@/lib/parseJdTitle'
import type { CoachResultDetail } from '@/types/coach'

export function NextStepsCard({ data }: { data: CoachResultDetail }) {
  const navigate = useNavigate()
  const gaps = (data.detail?.gap_skills as { skill: string; priority: string }[] | undefined) || []
  const highPriGaps = gaps.filter((g) => g.priority === 'high')
  const gapNames = (highPriGaps.length > 0 ? highPriGaps : gaps).slice(0, 3).map((g) => g.skill).join('、')
  const title = data.detail?.jd_title || data.title || ''
  const { company, position } = parseJdTitle(title)

  const [trackingDone, setTrackingDone] = useState(false)
  const [gapsDone, setGapsDone] = useState(false)

  const addToGrowthMut = useMutation({
    mutationFn: () => createApplication({ company: company || undefined, position: position || undefined }),
    onSuccess: () => setTrackingDone(true),
  })

  const applyGapsMut = useMutation({
    mutationFn: () => patchCareerGoalGaps(gaps.map((g) => g.skill), 'jd_diagnosis'),
    onSuccess: () => setGapsDone(true),
  })

  const goChat = (prompt: string) => {
    navigate('/coach/chat?prompt=' + encodeURIComponent(prompt))
  }

  const steps = [
    {
      icon: <FolderKanban className="w-4 h-4" />,
      label: trackingDone ? '已加入成长档案' : '加入成长档案实战经历',
      desc: trackingDone ? '在成长档案 → 实战经历中查看' : '记录这次实战经历，追踪投递进展',
      onClick: trackingDone ? () => navigate('/growth-log') : () => addToGrowthMut.mutate(),
    },
    {
      icon: <Crosshair className="w-4 h-4" />,
      label: gapsDone ? '已加入目标缺口' : `将 ${gaps.length} 项缺口纳入追踪目标`,
      desc: gapsDone ? '前往成长档案追踪进度' : '写入成长档案，用项目驱动补齐缺口',
      onClick: gapsDone ? () => navigate('/growth-log') : () => applyGapsMut.mutate(),
      disabled: gaps.length === 0,
    },
    {
      icon: <Target className="w-4 h-4" />,
      label: '练缺口面试题',
      desc: gapNames ? `针对 ${gapNames} 出题` : '针对缺口技能出面试题',
      onClick: () =>
        goChat(
          gapNames
            ? `根据我的JD诊断缺口，帮我出几道关于 ${gapNames} 的面试题`
            : '根据上次JD诊断的缺口技能，帮我出几道相关面试题练练',
        ),
    },
    {
      icon: <Search className="w-4 h-4" />,
      label: '搜索类似岗位',
      desc: title ? `搜索更多${title}相关招聘` : '搜索类似的招聘岗位',
      onClick: () =>
        goChat(
          title ? `帮我搜索和「${title}」类似的其他招聘` : '帮我搜索和刚才诊断的JD类似的其他招聘',
        ),
    },
  ]

  return (
    <div className="space-y-3">
      {steps.map((step, i) => (
        <PaperCard
          key={i}
          className={`group flex items-center gap-4 cursor-pointer ${step.disabled ? 'opacity-50 pointer-events-none' : ''}`}
          onClick={step.onClick}
        >
          <span className="text-[var(--chestnut)]">{step.icon}</span>
          <div className="flex-1 min-w-0">
            <p className="font-sans text-[length:var(--fs-body)] font-medium text-[var(--ink-1)] group-hover:text-[var(--chestnut)] transition-colors">
              {step.label}
            </p>
            <p className="text-[length:var(--fs-body-sm)] text-[var(--ink-3)]">{step.desc}</p>
          </div>
          <ArrowRight className="w-4 h-4 text-[var(--ink-3)] group-hover:text-[var(--chestnut)] transition-transform group-hover:translate-x-0.5" />
        </PaperCard>
      ))}
    </div>
  )
}
