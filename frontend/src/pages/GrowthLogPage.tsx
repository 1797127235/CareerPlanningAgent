import { useState, useMemo, useEffect, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { AnimatePresence } from 'framer-motion'

import { listProjects, getGrowthDashboard } from '@/api/growthLog'
import type { ProjectRecord } from '@/api/growthLog'
import { listApplications } from '@/api/applications'
import type { JobApplication } from '@/types/application'

import { GoalBar } from '@/components/growth-log/GoalBar'
import { FilterChips } from '@/components/growth-log/FilterChips'
import type { FilterKey } from '@/components/growth-log/FilterChips'
import { RecordRow } from '@/components/growth-log/RecordRow'
import type { UnifiedRecord, RecordType } from '@/components/growth-log/RecordRow'
import { NewRecordDialog } from '@/components/growth-log/NewRecordDialog'
import { AddProjectForm } from '@/components/growth-log/ProjectsSection'
import { AddPursuitForm } from '@/components/growth-log/PursuitsSection'
import { RefineSection } from '@/components/growth-log/RefineSection'

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

function mergeRecords(
  projects: ProjectRecord[],
  applications: JobApplication[],
): UnifiedRecord[] {
  const records: UnifiedRecord[] = [
    ...projects.map(p => ({
      id: `proj-${p.id}`,
      type: 'project' as RecordType,
      title: p.name,
      subtitle: p.description || '',
      status: p.status,
      tags: p.skills_used,
      date: p.created_at,
      raw: p,
    })),
    ...applications.map(a => ({
      id: `app-${a.id}`,
      type: 'pursuit' as RecordType,
      title: `${a.company || '未知公司'} · ${a.position || (a as any).jd_title || '未命名岗位'}`,
      subtitle: '',
      status: a.status,
      tags: [],
      date: a.created_at,
      raw: a,
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

function EmptyState({ onAddRecord, hasGoal }: { onAddRecord: () => void; hasGoal: boolean }) {
  return (
    <div className="glass-static rounded-2xl py-14 flex flex-col items-center gap-4">
      <p className="text-[14px] text-slate-500">还没有任何记录</p>
      <div className="flex items-center gap-2">
        {!hasGoal && (
          <a href="/graph" className="px-4 py-2 rounded-xl bg-slate-800 text-white text-[12px] font-semibold hover:bg-slate-700 transition-colors cursor-pointer">
            选方向
          </a>
        )}
        <button
          onClick={onAddRecord}
          className="flex items-center gap-1 px-4 py-2 rounded-xl bg-white/60 text-slate-700 text-[12px] font-semibold border border-slate-200 hover:bg-white/80 transition-colors cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" /> 新记录
        </button>
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

  const { data: dashboardData } = useQuery({ queryKey: ['growth-dashboard'], queryFn: getGrowthDashboard, staleTime: 120_000 })
  const { data: projectsData } = useQuery({ queryKey: ['growth-projects'], queryFn: listProjects })
  const { data: appsData } = useQuery({ queryKey: ['pursuits-apps'], queryFn: listApplications })

  const projects = projectsData?.projects ?? []
  const applications = appsData ?? []

  const allRecords = useMemo(() => mergeRecords(projects, applications), [projects, applications])
  const filtered = filterParam === 'all' || filterParam === 'refine' ? allRecords : allRecords.filter(r => r.type === filterParam)
  const groups = useMemo(() => groupByDate(filtered), [filtered])

  useEffect(() => {
    const urlTab = searchParams.get('tab')
    // tab → filter 映射：前端 FilterChips 用单数 key（pursuit/project），URL 惯用复数
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
  }

  return (
    <div className="max-w-[900px] mx-auto px-4 py-5 md:px-8 min-h-screen">
      <GoalBar />

      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => setShowNewDialog(true)}
          className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 text-white rounded-xl text-[12px] font-semibold hover:bg-slate-700 transition-colors shadow-sm cursor-pointer"
        >
          <Plus className="w-4 h-4" /> 新记录
        </button>
        <FilterChips value={filterParam} onChange={setFilter} />
      </div>

      {filterParam === 'refine' ? (
        <RefineSection />
      ) : (
        <div className="space-y-4">
          {allRecords.length === 0 ? (
            <EmptyState onAddRecord={() => setShowNewDialog(true)} hasGoal={!!(dashboardData as any)?.has_goal} />
          ) : groups.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-[12px]">没有符合条件的记录</div>
          ) : (
            groups.map(group => (
              <div key={group.label}>
                <div className="flex items-center gap-3 mb-3 mt-5">
                  <span className="text-[11px] font-bold text-slate-400 uppercase">{group.label}</span>
                  <div className="flex-1 h-px bg-slate-200/60" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {group.items.map(record => (
                    <RecordRow key={record.id} record={record} />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
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
