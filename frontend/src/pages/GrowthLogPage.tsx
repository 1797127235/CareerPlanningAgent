import { useState, useMemo, useEffect, useRef, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { AnimatePresence } from 'framer-motion'

import { listProjects, getGrowthDashboard, deleteProject } from '@/api/growthLog'
import type { ProjectRecord } from '@/api/growthLog'
import { listApplications, deleteApplication } from '@/api/applications'
import type { JobApplication } from '@/types/application'

import { GoalBar } from '@/components/growth-log/GoalBar'
import { FilterChips } from '@/components/growth-log/FilterChips'
import type { FilterKey } from '@/components/growth-log/FilterChips'
import { RecordRow } from '@/components/growth-log/RecordRow'
import type { UnifiedRecord, RecordType } from '@/components/growth-log/RecordRow'
import { NewRecordDialog } from '@/components/growth-log/NewRecordDialog'
import { AddProjectForm } from '@/components/growth-log/ProjectsSection'
import { AddPursuitForm } from '@/components/growth-log/PursuitsSection'
import { ToastContainer, type ToastState } from '@/components/shared/Toast'

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
    <div className="pt-16 pb-8 px-1">
      <p className="text-[14px] text-slate-500 leading-relaxed">
        这一页还是空白 —— 从任何一笔开始都可以。
      </p>
      <div className="mt-5 flex items-center gap-5">
        <button
          onClick={onAddRecord}
          className="flex items-center gap-1 text-[13px] font-medium text-blue-600 hover:text-blue-800 transition-colors cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" /> 记第一笔
        </button>
        {!hasGoal && (
          <a href="/graph" className="text-[13px] text-slate-500 hover:text-slate-800 underline underline-offset-4 decoration-slate-300 transition-colors">
            或先选一个方向
          </a>
        )}
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
  const [toast, setToast] = useState<ToastState | null>(null)

  const { data: dashboardData } = useQuery({ queryKey: ['growth-dashboard'], queryFn: getGrowthDashboard, staleTime: 120_000 })
  const { data: projectsData } = useQuery({ queryKey: ['growth-projects'], queryFn: listProjects })
  const { data: appsData } = useQuery({ queryKey: ['pursuits-apps'], queryFn: listApplications })

  // Deferred delete — optimistic remove + undo toast. Commits to server after 4.5s.
  const pendingDeleteRef = useRef<{
    record: UnifiedRecord
    timer: number
    prevProjects?: { projects: ProjectRecord[] } | undefined
    prevApps?: JobApplication[] | undefined
  } | null>(null)

  const stageDelete = (record: UnifiedRecord) => {
    // Snapshot cache so undo can restore exactly.
    const prevProjects = qc.getQueryData<{ projects: ProjectRecord[] }>(['growth-projects'])
    const prevApps = qc.getQueryData<JobApplication[]>(['pursuits-apps'])

    if (record.type === 'project') {
      qc.setQueryData<{ projects: ProjectRecord[] }>(['growth-projects'], (old) => ({
        projects: (old?.projects ?? []).filter(p => `proj-${p.id}` !== record.id),
      }))
    } else if (record.type === 'pursuit') {
      qc.setQueryData<JobApplication[]>(['pursuits-apps'], (old) =>
        (old ?? []).filter(a => `app-${a.id}` !== record.id)
      )
    }

    const timer = window.setTimeout(async () => {
      try {
        if (record.type === 'project') await deleteProject((record.raw as ProjectRecord).id)
        else if (record.type === 'pursuit') await deleteApplication((record.raw as JobApplication).id)
      } catch {
        // Roll back cache on server failure.
        if (prevProjects) qc.setQueryData(['growth-projects'], prevProjects)
        if (prevApps) qc.setQueryData(['pursuits-apps'], prevApps)
        setToast({ message: '删除失败，已恢复', type: 'error' })
      } finally {
        pendingDeleteRef.current = null
      }
    }, 4500)

    pendingDeleteRef.current = { record, timer, prevProjects, prevApps }

    setToast({
      message: `已删除「${record.title}」`,
      type: 'info',
      durationMs: 4500,
      action: {
        label: '撤销',
        onClick: () => {
          const pending = pendingDeleteRef.current
          if (!pending) return
          window.clearTimeout(pending.timer)
          if (pending.prevProjects) qc.setQueryData(['growth-projects'], pending.prevProjects)
          if (pending.prevApps) qc.setQueryData(['pursuits-apps'], pending.prevApps)
          pendingDeleteRef.current = null
        },
      },
    })
  }

  const projects = projectsData?.projects ?? []
  const applications = appsData ?? []

  const allRecords = useMemo(() => mergeRecords(projects, applications), [projects, applications])
  const filtered = filterParam === 'all' ? allRecords : allRecords.filter(r => r.type === filterParam)
  const groups = useMemo(() => groupByDate(filtered), [filtered])

  useEffect(() => {
    const urlTab = searchParams.get('tab')
    // tab → filter 映射：前端 FilterChips 用单数 key（pursuit/project），URL 惯用复数
    const tabToFilter: Record<string, FilterKey> = {
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
      {/* Header cluster — goal + actions packed tight */}
      <section className="space-y-2 mb-8">
        <GoalBar />
        <div className="flex items-center justify-between flex-wrap gap-2">
          <button
            onClick={() => setShowNewDialog(true)}
            className="group inline-flex items-center gap-1.5 text-[13px] font-semibold text-slate-900 pb-1 border-b-2 border-slate-900 hover:border-blue-700 hover:text-blue-700 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" /> 新记一笔
          </button>
          <FilterChips value={filterParam} onChange={setFilter} />
        </div>
      </section>

      <div>
        {allRecords.length === 0 ? (
          <EmptyState onAddRecord={() => setShowNewDialog(true)} hasGoal={!!(dashboardData as any)?.has_goal} />
        ) : groups.length === 0 ? (
          <div className="pt-12 text-slate-400 text-[13px]">没有符合条件的记录</div>
        ) : (
          groups.map((group, idx) => (
            <div key={group.label}>
              {/* Date group head — editorial section marker */}
              <div className={`flex items-center gap-4 ${idx === 0 ? 'pt-2' : 'pt-10'} pb-5`}>
                <div className="flex-1 h-px bg-slate-300" />
                <span className="text-[11px] font-bold text-slate-500 tracking-[0.2em]">
                  {group.label}
                </span>
                <div className="flex-1 h-px bg-slate-300" />
              </div>
              <div
                className="grid gap-3"
                style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}
              >
                {group.items.map(record => (
                  <RecordRow key={record.id} record={record} onDelete={stageDelete} />
                ))}
              </div>
            </div>
          ))
        )}
      </div>

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

      <ToastContainer toast={toast} onClose={() => setToast(null)} />
    </div>
  )
}
