import { useState, useMemo, useEffect, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Sparkles } from 'lucide-react'
import { AnimatePresence } from 'framer-motion'

import { getGrowthDashboard, getGoalJourney, getGoalHistory } from '@/api/growthLog'

import { FilterChips } from '@/components/growth-log/FilterChips'
import type { FilterKey } from '@/components/growth-log/FilterChips'
import { RecordRow } from '@/components/growth-log/RecordRow'
import type { UnifiedRecord, RecordType } from '@/components/growth-log/RecordRow'
import { NewRecordDialog } from '@/components/growth-log/NewRecordDialog'
import { AddProjectForm } from '@/components/growth-log/ProjectsSection'
import { AddPursuitForm } from '@/components/growth-log/PursuitsSection'
import { RefineSection } from '@/components/growth-log/RefineSection'
import { GrowthDashboard } from '@/components/growth-log/GrowthDashboard'
import { Chapter } from '@/components/growth-log/Chapter'
import { SectionDivider } from '@/components/growth-log/SectionDivider'
import { PaperCard } from '@/components/growth-log/PaperCard'
import { JourneyTimeline } from '@/components/growth-log/JourneyTimeline'

interface DateGroup {
  label: string
  items: UnifiedRecord[]
}

function groupByDate(records: UnifiedRecord[]): DateGroup[] {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterdayStart = new Date(todayStart.getTime() - 86400000)
  const weekStart = new Date(todayStart.getTime() - todayStart.getDay() * 86400000)

  const groups: Record<string, UnifiedRecord[]> = {
    '今天': [], '昨天': [], '本周': [], '更早': [],
  }

  records.forEach(r => {
    const d = new Date(r.date)
    if (d >= todayStart) groups['今天'].push(r)
    else if (d >= yesterdayStart) groups['昨天'].push(r)
    else if (d >= weekStart) groups['本周'].push(r)
    else groups['更早'].push(r)
  })

  return Object.entries(groups)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }))
}

interface SimpleProject {
  id: number
  name: string
  status?: string
  created_at: string
}

interface SimpleApplication {
  id: number
  company?: string
  position?: string
  status?: string
  created_at: string
}

function mergeGoalRecords(
  projects: SimpleProject[],
  applications: SimpleApplication[],
): UnifiedRecord[] {
  const records: UnifiedRecord[] = [
    ...projects.map(p => ({
      id: `proj-${p.id}`,
      type: 'project' as RecordType,
      title: p.name,
      subtitle: '',
      status: p.status,
      tags: [],
      date: p.created_at,
      raw: p as unknown as RecordType extends 'project' ? SimpleProject : never,
    })),
    ...applications.map(a => ({
      id: `app-${a.id}`,
      type: 'pursuit' as RecordType,
      title: `${a.company || '未知公司'} · ${a.position || '未命名岗位'}`,
      subtitle: '',
      status: a.status,
      tags: [],
      date: a.created_at,
      raw: a as unknown as RecordType extends 'pursuit' ? SimpleApplication : never,
    })),
  ]
  return records.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
}

function FormModal({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0"
        style={{ background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(4px)' }}
        onClick={onClose}
      />
      <div className="relative w-full max-w-[480px] z-10">
        {children}
      </div>
    </div>
  )
}

export default function GrowthLogPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filterParam = (searchParams.get('filter') || 'all') as FilterKey
  const qc = useQueryClient()

  const setFilter = (f: FilterKey) => {
    if (f === 'all') {
      searchParams.delete('filter')
    } else {
      searchParams.set('filter', f)
    }
    setSearchParams(searchParams, { replace: true })
  }

  const [showNewDialog, setShowNewDialog] = useState(false)
  const [activeForm, setActiveForm] = useState<RecordType | null>(null)

  useQuery({ queryKey: ['growth-dashboard'], queryFn: getGrowthDashboard, staleTime: 120_000 })
  const { data: journeyData } = useQuery({ queryKey: ['goal-journey'], queryFn: getGoalJourney, staleTime: 120_000 })
  const { data: historyData } = useQuery({ queryKey: ['goal-history'], queryFn: getGoalHistory, staleTime: 120_000 })

  const projects = journeyData?.projects_under_goal ?? []
  const applications = journeyData?.applications_under_goal ?? []

  const allRecords = useMemo(() => mergeGoalRecords(projects, applications), [projects, applications])
  const filtered = filterParam === 'all' || filterParam === 'refine' ? allRecords : allRecords.filter(r => r.type === filterParam)
  const groups = useMemo(() => groupByDate(filtered), [filtered])

  useEffect(() => {
    const urlTab = searchParams.get('tab')
    const tabToFilter: Record<string, FilterKey> = {
      refine: 'refine',
      pursuits: 'pursuit',
      pursuit: 'pursuit',
      projects: 'project',
      project: 'project',
    }
    const mapped = urlTab ? tabToFilter[urlTab] : undefined
    if (mapped) {
      setFilter(mapped)
    }
  }, [searchParams])

  const handleRecordSelect = (type: RecordType) => {
    setShowNewDialog(false)
    setActiveForm(type)
  }

  const handleFormSuccess = () => {
    setActiveForm(null)
    qc.invalidateQueries({ queryKey: ['growth-projects'] })
    qc.invalidateQueries({ queryKey: ['pursuits-apps'] })
    qc.invalidateQueries({ queryKey: ['goal-journey'] })
  }

  const hasGoal = !!(journeyData?.has_goal)
  const goalLabel = journeyData?.goal?.target_label
  const setAt = journeyData?.goal?.set_at

  const daysSinceStart = useMemo(() => {
    if (!setAt) return 0
    return Math.floor((Date.now() - new Date(setAt).getTime()) / 86400000)
  }, [setAt])

  const chapterITitle = hasGoal
    ? <>你选了 {goalLabel}，<br/>从那天到今天，{daysSinceStart} 天。</>
    : <>先看清你在哪，<br/>再决定往哪走。</>

  const chapterIIntro = hasGoal
    ? `系统看见你在这条路上走了 ${allRecords.length} 步。继续走下去，每一步都算数。`
    : `职业规划不是从"选方向"开始的。但总得先知道想去哪。`

  const hasHistory = (historyData?.goals?.length ?? 0) > 1

  return (
    <div className="max-w-[900px] mx-auto px-6 md:px-16 lg:px-24 min-h-screen bg-[var(--bg-paper)]">
      <Chapter numeral="I" label="你的旅程" title={chapterITitle} intro={chapterIIntro}>
        {hasGoal && setAt && (
          <div className="mb-8">
            <JourneyTimeline
              targetLabel={goalLabel!}
              setAt={setAt}
              stageEvents={journeyData?.stage_events ?? []}
            />
          </div>
        )}
        <GrowthDashboard />
      </Chapter>

      {filterParam === 'refine' ? (
        <>
          <SectionDivider numeral="II" />
          <Chapter numeral="II" label="档案精修" title="精修一下你的档案" intro="补一笔细节，未来的你会感谢现在的自己。">
            <RefineSection />
            <div className="mt-8 pt-6 border-t border-[var(--line)]">
              <button
                onClick={() => setFilter('all')}
                className="text-[12px] text-[var(--ink-3)] hover:text-[var(--ink-1)] underline underline-offset-4 transition-colors cursor-pointer"
              >
                ← 回到全部记录
              </button>
            </div>
          </Chapter>
        </>
      ) : (
        <>
          <SectionDivider numeral="II" />
          <Chapter
            numeral="II"
            label="在这条路上"
            title={
              allRecords.length === 0
                ? <>还没有第一笔，<br/>不急。</>
                : <>到今天，<br/>你已经记下了 {allRecords.length} 笔。</>
            }
            intro="下面是你给自己留的脚印。不用每天都有 — 但每一笔都算数。"
          >
            {/* Action bar: 记一笔 + 档案精修 + filter */}
            <div className="flex items-center justify-between gap-3 flex-wrap mb-8">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowNewDialog(true)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-[var(--chestnut)] text-white rounded-md text-[13px] font-semibold hover:bg-[var(--ink-1)] transition-colors cursor-pointer"
                >
                  <Plus className="w-4 h-4" /> 记一笔
                </button>
                <button
                  onClick={() => setFilter('refine')}
                  className="inline-flex items-center gap-1.5 px-4 py-2 border border-[var(--line)] bg-[var(--bg-card)] text-[var(--ink-1)] rounded-md text-[13px] font-medium hover:bg-[var(--bg-paper)] transition-colors cursor-pointer"
                >
                  <Sparkles className="w-4 h-4 text-[var(--ember)]" /> 档案精修
                </button>
              </div>
              {allRecords.length > 0 && (
                <FilterChips value={filterParam} onChange={setFilter} />
              )}
            </div>

            <div className="space-y-6">
              {allRecords.length === 0 ? (
                <PaperCard className="text-center py-14">
                  <p className="text-[14px] text-[var(--ink-2)]">点上面「记一笔」 — 从一件最小的开始就好。</p>
                </PaperCard>
              ) : groups.length === 0 ? (
                <div className="text-center py-12 text-[var(--ink-3)] text-[13px]">这个分类下还是空的</div>
              ) : (
                groups.map(group => (
                  <div key={group.label}>
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-[11px] font-bold text-[var(--ink-3)] uppercase">{group.label}</span>
                      <div className="flex-1 h-px bg-[var(--line)]" />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {group.items.map(record => (
                        <RecordRow key={record.id} record={record} />
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Chapter>
        </>
      )}

      {hasHistory && (
        <>
          <SectionDivider numeral="III" />
          <Chapter
            numeral="III"
            label="回头看"
            title={<>你曾经选过 {historyData!.goals.filter(g => !g.is_active).length} 个方向。</>}
            intro="这些不是走错的路 — 是你一步步走过来的轨迹。"
          >
            <div className="space-y-3">
              {historyData!.goals.filter(g => !g.is_active).map(g => (
                <div key={g.id} className="flex items-center gap-3 text-[13px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--ink-3)]" />
                  <span className="font-medium text-[var(--ink-1)]">{g.target_label}</span>
                  <span className="text-[var(--ink-3)] tabular-nums">
                    {g.set_at ? new Date(g.set_at).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }) : ''}
                    {' → '}
                    {g.cleared_at ? new Date(g.cleared_at).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }) : '现在'}
                  </span>
                  <span className="text-[var(--ink-3)] tabular-nums">· {g.duration_days} 天</span>
                </div>
              ))}
            </div>
          </Chapter>
        </>
      )}

      <AnimatePresence>
        {showNewDialog && (
          <NewRecordDialog
            onClose={() => setShowNewDialog(false)}
            onSelect={handleRecordSelect}
          />
        )}
      </AnimatePresence>

      {/* ── 表单弹窗 ── */}
      <AnimatePresence>
        {activeForm && (
          <FormModal onClose={() => setActiveForm(null)}>
            {activeForm === 'project' && (
              <AddProjectForm onSuccess={handleFormSuccess} onCancel={() => setActiveForm(null)} />
            )}
            {activeForm === 'pursuit' && (
              <AddPursuitForm onSuccess={handleFormSuccess} onCancel={() => setActiveForm(null)} />
            )}
          </FormModal>
        )}
      </AnimatePresence>
    </div>
  )
}
