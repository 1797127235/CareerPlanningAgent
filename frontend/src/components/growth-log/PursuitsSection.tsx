/**
 * 实战经历页 — 全新实现
 * 与 ProjectsSection 保持同一玻璃卡风格
 * 卡片式布局 + 管道进度条 + 详情 Modal（后续实现）
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus } from 'lucide-react'
import { listApplications, createApplication } from '@/api/applications'
import { listInterviews } from '@/api/growthLog'
import type { JobApplication } from '@/types/application'
import { PursuitDetailModal } from './PursuitDetailModal'

/* ── Constants ── */

const APP_STATUS: Record<string, { label: string; color: string; bg: string }> = {
  pending:     { label: '待投递', color: '#8E8E93', bg: 'rgba(142,142,147,0.12)' },
  applied:     { label: '已投递', color: '#2563EB', bg: 'rgba(37,99,235,0.10)'   },
  screening:   { label: '筛选中', color: '#7C3AED', bg: 'rgba(124,58,237,0.10)'  },
  scheduled:   { label: '已约面', color: '#D97706', bg: 'rgba(217,119,6,0.10)'   },
  interviewed: { label: '已面试', color: '#EA580C', bg: 'rgba(234,88,12,0.10)'   },
  debriefed:   { label: '已复盘', color: '#0891B2', bg: 'rgba(8,145,178,0.10)'   },
  offer:       { label: 'Offer',  color: '#16A34A', bg: 'rgba(22,163,74,0.10)'   },
  rejected:    { label: '未通过', color: '#EF4444', bg: 'rgba(239,68,68,0.10)'   },
  withdrawn:   { label: '已放弃', color: '#8E8E93', bg: 'rgba(142,142,147,0.12)' },
}

const PIPELINE = [
  { key: 'applied',     label: '投递' },
  { key: 'screening',   label: '筛选' },
  { key: 'scheduled',   label: '约面' },
  { key: 'interviewed', label: '面试' },
  { key: 'debriefed',   label: '复盘' },
]

const TERMINAL = ['offer', 'rejected', 'withdrawn']
const SOURCES = ['BOSS直聘', '牛客', '内推', '校招', '实习僧', '官网', '其他']

function timeAgo(iso: string) {
  const d = new Date(iso), now = new Date()
  const days = Math.floor((now.getTime() - d.getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/* ── Pipeline Step Indicator ── */
function PipelineIndicator({ status }: { status: string }) {
  if (TERMINAL.includes(status)) {
    const st = APP_STATUS[status] ?? APP_STATUS.applied
    return (
      <div className="flex justify-center py-3">
        <span className="text-[12px] font-bold px-5 py-2 rounded-full"
          style={{ background: st.bg, color: st.color }}>
          {st.label}
        </span>
      </div>
    )
  }

  const currentIdx = PIPELINE.findIndex(p => p.key === status)

  return (
    <div className="py-3 px-1">
      <div className="flex items-start">
        {PIPELINE.map((step, i) => {
          const isPast    = i < currentIdx
          const isCurrent = i === currentIdx
          const isFuture  = i > currentIdx
          const dotColor  = isCurrent ? '#2563EB' : isPast ? '#93C5FD' : '#E5E7EB'
          const lineColor = i < currentIdx ? '#93C5FD' : '#E5E7EB'

          return (
            <div key={step.key} className="flex items-center flex-1">
              <div className="flex flex-col items-center w-full">
                <div className="flex items-center w-full">
                  {/* dot */}
                  <div className="shrink-0 w-[8px] h-[8px] rounded-full mx-auto"
                    style={{
                      background: dotColor,
                      boxShadow: isCurrent ? '0 0 0 3px rgba(37,99,235,0.20)' : 'none',
                    }}
                  />
                </div>
                <span className="text-[9px] font-medium mt-1.5 text-center"
                  style={{ color: isCurrent ? '#2563EB' : isFuture ? '#D1D5DB' : '#9CA3AF' }}>
                  {step.label}
                </span>
              </div>
              {i < PIPELINE.length - 1 && (
                <div className="h-px flex-1 -mt-3.5 mx-0.5 shrink-0" style={{ background: lineColor }} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── Pursuit Card ── */
function PursuitCard({ app, roundCount, onClick }: {
  app: JobApplication
  roundCount: number
  onClick: () => void
}) {
  const st = APP_STATUS[app.status] ?? APP_STATUS.applied

  return (
    <motion.div
      layout
      onClick={onClick}
      className="relative cursor-pointer select-none"
      whileHover={{ y: -3 }}
      transition={{ duration: 0.15 }}
    >
      <div
        className="h-full rounded-[20px] p-5 flex flex-col gap-3"
        style={{
          background: 'rgba(255,255,255,0.58)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          border: '1px solid rgba(255,255,255,0.65)',
          boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
          transition: 'box-shadow 0.2s ease, background 0.2s ease',
        }}
        onMouseEnter={e => {
          const el = e.currentTarget as HTMLDivElement
          el.style.boxShadow = '0 8px 28px rgba(0,0,0,0.08)'
          el.style.background = 'rgba(255,255,255,0.72)'
        }}
        onMouseLeave={e => {
          const el = e.currentTarget as HTMLDivElement
          el.style.boxShadow = '0 2px 12px rgba(0,0,0,0.04)'
          el.style.background = 'rgba(255,255,255,0.58)'
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="text-[15px] font-bold text-[#1a1a1a] truncate leading-snug">
              {app.company || '未知公司'}
            </h3>
            <p className="text-[11px] mt-0.5 text-[#8E8E93] truncate">
              {app.position || (app as { jd_title?: string }).jd_title || '未命名岗位'}
            </p>
          </div>
          <span className="text-[10px] font-semibold px-2.5 py-1 rounded-[8px] shrink-0"
            style={{ background: st.bg, color: st.color }}>
            {st.label}
          </span>
        </div>

        {/* Pipeline progress */}
        <PipelineIndicator status={app.status} />

        {/* Footer */}
        <div className="flex items-center justify-between pt-1"
          style={{ borderTop: '1px solid rgba(0,0,0,0.05)', marginTop: 'auto' }}>
          <span className="text-[11px] font-semibold" style={{ color: '#2563EB' }}>查看详情</span>
          <div className="flex items-center gap-2">
            {roundCount > 0 && (
              <span className="text-[10px] text-[#C7C7CC]">{roundCount} 轮面试</span>
            )}
            <span className="text-[10px] text-[#C7C7CC]">{timeAgo(app.created_at)}</span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

/* ── Add Pursuit Form ── */
function AddPursuitForm({ onSuccess, onCancel }: {
  onSuccess: (app: JobApplication) => void
  onCancel: () => void
}) {
  const [company, setCompany]   = useState('')
  const [position, setPosition] = useState('')
  const [source, setSource]     = useState('')
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!company.trim())  { setError('公司不能为空'); return }
    if (!position.trim()) { setError('岗位不能为空'); return }
    setSaving(true); setError('')
    try {
      const app = await createApplication({
        company: company.trim(),
        position: position.trim(),
        status: 'applied',
        notes: source ? `来源: ${source}` : undefined,
      })
      onSuccess(app)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="rounded-[20px] p-5 mb-4"
      style={{
        background: 'rgba(255,255,255,0.72)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(37,99,235,0.15)',
        boxShadow: '0 4px 20px rgba(37,99,235,0.08)',
      }}
    >
      <p className="text-[13px] font-bold text-[#1a1a1a] mb-4">添加岗位追踪</p>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {([
            { val: company, set: setCompany, placeholder: '公司名称 *' },
            { val: position, set: setPosition, placeholder: '投递岗位 *' },
          ] as const).map(({ val, set, placeholder }) => (
            <input key={placeholder} value={val} onChange={e => set(e.target.value)} placeholder={placeholder}
              className="w-full px-3 py-2.5 text-[12px] rounded-[10px] outline-none"
              style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.07)', color: '#1a1a1a' }}
              onFocus={e => { e.currentTarget.style.border = '1px solid rgba(37,99,235,0.4)'; e.currentTarget.style.background = '#fff' }}
              onBlur={e => { e.currentTarget.style.border = '1px solid rgba(0,0,0,0.07)'; e.currentTarget.style.background = 'rgba(0,0,0,0.04)' }}
            />
          ))}
        </div>

        {/* Source chips */}
        <div>
          <p className="text-[10px] text-[#8E8E93] mb-1.5">投递来源（选填）</p>
          <div className="flex flex-wrap gap-1.5">
            {SOURCES.map(s => (
              <button type="button" key={s} onClick={() => setSource(source === s ? '' : s)}
                className="px-2.5 py-1 text-[10px] font-medium rounded-[7px] cursor-pointer transition-all"
                style={{
                  background: source === s ? 'rgba(37,99,235,0.08)' : 'rgba(0,0,0,0.03)',
                  border: source === s ? '1px solid rgba(37,99,235,0.3)' : '1px solid rgba(0,0,0,0.07)',
                  color: source === s ? '#2563EB' : '#8E8E93',
                }}>
                {s}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="text-[10px] text-red-500">{error}</p>}

        <div className="flex gap-2 pt-1">
          <button type="submit" disabled={saving}
            className="px-4 py-2 text-[12px] font-semibold text-white rounded-[10px] cursor-pointer disabled:opacity-50"
            style={{ background: '#2563EB' }}>
            {saving ? '添加中...' : '添加'}
          </button>
          <button type="button" onClick={onCancel}
            className="px-4 py-2 text-[12px] text-[#8E8E93] rounded-[10px] cursor-pointer"
            style={{ background: 'rgba(0,0,0,0.04)' }}>
            取消
          </button>
        </div>
      </form>
    </motion.div>
  )
}

/* ── Main export ── */
export function PursuitsSection({ onCardClick }: { onCardClick?: (appId: number) => void }) {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { data: apps = [], isLoading: appsLoading } = useQuery({
    queryKey: ['pursuits-apps'],
    queryFn: listApplications,
    staleTime: 3 * 60_000,
  })
  const { data: ivData, isLoading: ivLoading } = useQuery({
    queryKey: ['pursuits-interviews'],
    queryFn: listInterviews,
    staleTime: 3 * 60_000,
  })
  const interviews = ivData?.interviews ?? []
  const isLoading  = appsLoading || ivLoading

  // round count per application
  const roundCount: Record<number, number> = {}
  interviews.forEach(iv => {
    if (iv.application_id != null)
      roundCount[iv.application_id] = (roundCount[iv.application_id] ?? 0) + 1
  })

  const sorted = [...apps].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['pursuits-apps'] })
    qc.invalidateQueries({ queryKey: ['pursuits-interviews'] })
    qc.invalidateQueries({ queryKey: ['growth-timeline'] })
    qc.invalidateQueries({ queryKey: ['growth-summary'] })
    qc.invalidateQueries({ queryKey: ['growth-applications'] })
    qc.invalidateQueries({ queryKey: ['growth-interviews'] })
  }

  /* Loading skeleton */
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-[200px] rounded-[20px] animate-pulse"
            style={{ background: 'rgba(255,255,255,0.4)' }} />
        ))}
      </div>
    )
  }

  return (
    <div>
      <AnimatePresence>
        {showAdd && (
          <AddPursuitForm
            onSuccess={() => { setShowAdd(false); refresh() }}
            onCancel={() => setShowAdd(false)}
          />
        )}
      </AnimatePresence>

      {/* Card grid — always shown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {sorted.map(app => (
          <PursuitCard
            key={app.id}
            app={app}
            roundCount={roundCount[app.id] ?? 0}
            onClick={() => setSelectedId(app.id)}
          />
        ))}
        {/* Add card — always in DOM, opacity-hidden while form is open */}
        <div
          onClick={() => { if (!showAdd) setShowAdd(true) }}
          className="rounded-[20px] flex flex-col items-center justify-center gap-2 min-h-[200px]"
          style={{
            background: 'rgba(255,255,255,0.3)',
            border: '2px dashed rgba(37,99,235,0.2)',
            opacity: showAdd ? 0 : 1,
            pointerEvents: showAdd ? 'none' : 'auto',
            cursor: showAdd ? 'default' : 'pointer',
            transition: 'opacity 0.15s, background 0.15s',
          }}
          onMouseEnter={e => { if (!showAdd) (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.5)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.3)' }}
        >
          <div className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(37,99,235,0.08)' }}>
            <Plus className="w-5 h-5" style={{ color: '#2563EB' }} />
          </div>
          <p className="text-[12px] font-semibold" style={{ color: '#2563EB' }}>添加岗位追踪</p>
        </div>
      </div>

      {/* Detail Modal */}
      <AnimatePresence>
        {selectedId != null && (
          <PursuitDetailModal
            appId={selectedId}
            onClose={() => setSelectedId(null)}
            onRefresh={refresh}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
