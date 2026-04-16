import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { GoalBar } from '@/components/growth-log/GoalBar'
import { QuickInput } from '@/components/growth-log-v2/QuickInput'
import { EntryCard } from '@/components/growth-log-v2/EntryCard'
import { PlanRow } from '@/components/growth-log-v2/PlanRow'
import { LegacyRecordRow, type UnifiedRecord } from '@/components/growth-log-v2/LegacyRecordRow'
import { useGrowthEntries } from '@/components/growth-log-v2/useEntries'
import type { GrowthEntry } from '@/components/growth-log-v2/mockData'
import { listProjects } from '@/api/growthLog'
import { listApplications } from '@/api/applications'
import type { ProjectRecord } from '@/api/growthLog'
import type { JobApplication } from '@/types/application'

type FilterKey = 'all' | 'project' | 'interview' | 'learning' | 'plan'

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'project', label: '#项目' },
  { key: 'interview', label: '#面试' },
  { key: 'learning', label: '#学习' },
  { key: 'plan', label: '计划' },
]

interface DateGroup {
  label: string
  items: TimelineItem[]
}

type TimelineItem =
  | { kind: 'entry'; entry: GrowthEntry; date: string }
  | { kind: 'legacy'; record: UnifiedRecord; date: string }

function groupByDate(items: TimelineItem[]): DateGroup[] {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterdayStart = new Date(todayStart.getTime() - 86400000)
  const weekStart = new Date(todayStart.getTime() - todayStart.getDay() * 86400000)

  const groups: Record<string, TimelineItem[]> = {
    今天: [],
    昨天: [],
    本周: [],
    更早: [],
  }

  items.forEach((item) => {
    const d = new Date(item.date)
    if (d >= todayStart) groups['今天'].push(item)
    else if (d >= yesterdayStart) groups['昨天'].push(item)
    else if (d >= weekStart) groups['本周'].push(item)
    else groups['更早'].push(item)
  })

  return Object.entries(groups)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }))
}

function mergeLegacyRecords(
  projects: ProjectRecord[],
  applications: JobApplication[],
): UnifiedRecord[] {
  const records: UnifiedRecord[] = [
    ...projects.map((p) => ({
      id: `proj-${p.id}`,
      type: 'project' as const,
      title: p.name,
      subtitle: p.description || '',
      status: p.status,
      tags: p.skills_used,
      date: p.created_at,
      raw: p,
    })),
    ...applications.map((a) => ({
      id: `app-${a.id}`,
      type: 'pursuit' as const,
      title: `${a.company || '未知公司'} · ${a.position || a.jd_title || '未命名岗位'}`,
      subtitle: '',
      status: a.status,
      tags: [],
      date: a.created_at,
      raw: a,
    })),
  ]
  return records.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
}

function FilterChips({ value, onChange }: { value: FilterKey; onChange: (v: FilterKey) => void }) {
  return (
    <div className="flex items-center gap-4">
      {FILTERS.map((f) => {
        const active = value === f.key
        return (
          <button
            key={f.key}
            onClick={() => onChange(f.key)}
            className={[
              'relative text-[13px] font-medium transition-colors cursor-pointer pb-1',
              active ? 'text-slate-900' : 'text-slate-500 hover:text-slate-900',
            ].join(' ')}
          >
            {f.label}
            <span
              className={[
                'absolute left-0 right-0 -bottom-0 h-[2px] bg-slate-900 transition-opacity',
                active ? 'opacity-100' : 'opacity-0',
              ].join(' ')}
            />
          </button>
        )
      })}
    </div>
  )
}

export default function GrowthLogV2Page() {
  const location = useLocation()
  const prefillText = (location.state as { prefill?: string } | null)?.prefill || ''

  const {
    entries,
    loading: entriesLoading,
    addEntry,
    updateEntry,
    deleteEntry,
    requestAiSuggestions,
  } = useGrowthEntries()

  const { data: projectsData } = useQuery({
    queryKey: ['growth-projects'],
    queryFn: listProjects,
    staleTime: 120_000,
  })
  const { data: appsData } = useQuery<JobApplication[]>({
    queryKey: ['pursuits-apps'],
    queryFn: listApplications,
    staleTime: 120_000,
  })

  const [filter, setFilter] = useState<FilterKey>('all')

  const plans = entries.filter((e) => e.is_plan && e.status === 'pending')

  const legacyRecords = useMemo(() => {
    const projects = projectsData?.projects ?? []
    const applications = (appsData as JobApplication[] | undefined) ?? []
    return mergeLegacyRecords(projects, applications)
  }, [projectsData, appsData])

  const timelineItems = useMemo<TimelineItem[]>(() => {
    const newItems: TimelineItem[] = entries
      .filter((e) => !e.is_plan || e.status !== 'pending')
      .map((e) => ({ kind: 'entry', entry: e, date: e.created_at }))

    const oldItems: TimelineItem[] = legacyRecords.map((r) => ({
      kind: 'legacy',
      record: r,
      date: r.date,
    }))

    const all = [...newItems, ...oldItems].sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    )

    if (filter === 'all') return all
    if (filter === 'project') {
      return all.filter(
        (i) =>
          (i.kind === 'entry' && i.entry.category === 'project') ||
          (i.kind === 'legacy' && i.record.type === 'project')
      )
    }
    if (filter === 'interview') {
      return all.filter((i) => i.kind === 'entry' && i.entry.category === 'interview')
    }
    if (filter === 'learning') {
      return all.filter((i) => i.kind === 'entry' && i.entry.category === 'learning')
    }
    // filter === 'plan' -> timeline empty, plans shown separately
    return []
  }, [entries, legacyRecords, filter])

  const groups = useMemo(() => groupByDate(timelineItems), [timelineItems])

  const handleTogglePlan = async (id: number) => {
    await updateEntry(id, { status: 'done', completed_at: new Date().toISOString() })
  }

  const handleDropPlan = async (id: number) => {
    await updateEntry(id, { status: 'dropped' })
  }

  const handleConvertAi = async (text: string) => {
    await addEntry({
      content: text,
      category: 'learning',
      tags: ['计划', '来自AI建议'],
      structured_data: null,
      is_plan: true,
      status: 'pending',
      due_type: 'daily',
      due_at: new Date(new Date().setHours(23, 59, 59, 999)).toISOString(),
      completed_at: null,
      ai_suggestions: null,
    })
  }

  return (
    <div className="max-w-[900px] mx-auto px-4 py-5 md:px-8 min-h-screen">
      <section className="space-y-2 mb-8">
        <GoalBar />
      </section>

      <section className="mb-6">
        <QuickInput onSent={() => {}} onAddEntry={addEntry} initialText={prefillText} />
      </section>

      <section className="mb-6">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <FilterChips value={filter} onChange={setFilter} />
        </div>
      </section>

      {filter !== 'plan' && plans.length > 0 && (
        <section className="mb-8">
          <div className="flex items-center gap-4 pt-2 pb-4">
            <div className="flex-1 h-px bg-slate-300" />
            <span className="text-[11px] font-bold text-slate-500 tracking-[0.2em]">待完成的计划</span>
            <div className="flex-1 h-px bg-slate-300" />
          </div>
          <div className="bg-white border border-slate-200 rounded-xl px-4">
            {plans.map((plan) => (
              <PlanRow key={plan.id} entry={plan} onToggle={handleTogglePlan} onDrop={handleDropPlan} onUpdate={updateEntry} />
            ))}
          </div>
        </section>
      )}

      {filter === 'plan' && plans.length > 0 && (
        <section className="mb-8">
          <div className="flex items-center gap-4 pt-2 pb-4">
            <div className="flex-1 h-px bg-slate-300" />
            <span className="text-[11px] font-bold text-slate-500 tracking-[0.2em]">计划</span>
            <div className="flex-1 h-px bg-slate-300" />
          </div>
          <div className="bg-white border border-slate-200 rounded-xl px-4">
            {plans.map((plan) => (
              <PlanRow key={plan.id} entry={plan} onToggle={handleTogglePlan} onDrop={handleDropPlan} onUpdate={updateEntry} />
            ))}
          </div>
        </section>
      )}

      <div>
        {entriesLoading ? (
          <div className="pt-12 text-slate-400 text-[13px] text-center">加载中…</div>
        ) : groups.length === 0 ? (
          <div className="pt-12 text-slate-400 text-[13px] text-center">没有符合条件的记录</div>
        ) : (
          groups.map((group, idx) => (
            <div key={group.label}>
              <div className={`flex items-center gap-4 ${idx === 0 ? 'pt-2' : 'pt-10'} pb-5`}>
                <div className="flex-1 h-px bg-slate-300" />
                <span className="text-[11px] font-bold text-slate-500 tracking-[0.2em]">{group.label}</span>
                <div className="flex-1 h-px bg-slate-300" />
              </div>
              <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
                {group.items.map((item, i) =>
                  item.kind === 'entry' ? (
                    <EntryCard
                      key={`entry-${item.entry.id}-${i}`}
                      entry={item.entry}
                      onMutate={() => {}}
                      onRequestAi={requestAiSuggestions}
                      onConvertAi={handleConvertAi}
                      onUpdate={updateEntry}
                      onDelete={deleteEntry}
                    />
                  ) : (
                    <LegacyRecordRow key={`legacy-${item.record.id}-${i}`} record={item.record} />
                  )
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
