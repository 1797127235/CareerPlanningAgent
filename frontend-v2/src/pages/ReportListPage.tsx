import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Loader2,
  FileText,
  Trash2,
  Sparkles,
  Target,
  Calendar,
  CheckCircle2,
  Download,
  ArrowUpDown,
} from 'lucide-react'
import { fetchReportList, generateReportV2, deleteReport, exportReportPdf } from '@/api/report'
import { fetchProfile } from '@/api/profiles'
import Navbar from '@/components/shared/Navbar'

const serif = { fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }

export default function ReportListPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [generating, setGenerating] = useState(false)
  const [exportingId, setExportingId] = useState<number | null>(null)
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc')

  const { data: list, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: fetchReportList,
    staleTime: 30_000,
  })

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: fetchProfile,
    staleTime: 60_000,
  })

  const deleteMut = useMutation({
    mutationFn: deleteReport,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] }),
  })

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const detail = await generateReportV2()
      if (detail.data?.target) {
        navigate(`/report/${detail.id}`)
      }
    } catch (e) {
      alert(e instanceof Error ? e.message : '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const targetLabel = useMemo(() => {
    if (profile?.graph_position?.target_label) return profile.graph_position.target_label
    if (profile?.career_goals && profile.career_goals.length > 0) {
      const primary = profile.career_goals.find((g) => g.is_primary)
      return primary?.target_label || profile.career_goals[0].target_label
    }
    return null
  }, [profile])

  const latestReportId = useMemo(() => {
    if (!list || list.length === 0) return null
    return list.reduce((latest, r) =>
      new Date(r.created_at) > new Date(latest.created_at) ? r : latest
    , list[0]).id
  }, [list])

  const sortedReports = useMemo(() => {
    const arr = [...(list ?? [])]
    arr.sort((a, b) => {
      const ta = new Date(a.created_at).getTime()
      const tb = new Date(b.created_at).getTime()
      return sortOrder === 'desc' ? tb - ta : ta - tb
    })
    return arr
  }, [list, sortOrder])

  if (isLoading) {
    return (
      <div className="min-h-screen" style={{ background: 'var(--bg-paper)' }}>
        <Navbar />
        <main className="min-h-screen flex items-center justify-center pt-[64px]">
          <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--ink-3)' }} />
        </main>
      </div>
    )
  }

  const reports = sortedReports

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-paper)', color: 'var(--ink-1)' }}>
      <Navbar />

      <main className="pt-[80px] pb-24">
        <div className="mx-auto max-w-[1200px] px-6 md:px-10">
          {/* Hero */}
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8 mb-16">
            <div className="flex-1 min-w-0">
              <p
                className="text-[11px] font-medium tracking-[0.15em] uppercase mb-4"
                style={{ ...sans, color: 'var(--ink-3)' }}
              >
                <span style={{ color: 'var(--line)' }}>——</span> Career Reports
              </p>
              <h1 className="text-[40px] md:text-[52px] font-bold tracking-tight leading-[1.15]" style={serif}>
                职业报告
              </h1>
              <p className="mt-4 text-[14px] leading-relaxed" style={{ ...sans, color: 'var(--ink-2)' }}>
                基于你的用户画像生成阶段性职业规划报告，<br className="hidden sm:block" />
                帮助你梳理当前能力、目标差距与下一步行动建议。
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-end gap-4 lg:gap-5">
              {/* Info cards */}
              <div className="flex flex-wrap items-end gap-3">
                <div
                  className="px-5 py-3"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--line)', borderRadius: '6px' }}
                >
                  <p className="text-[11px] leading-none mb-1.5" style={{ ...sans, color: 'var(--ink-3)' }}>目标岗位</p>
                  <p className="text-[14px] font-medium" style={{ ...sans, color: 'var(--ink-1)' }}>
                    {targetLabel || '未设置'}
                  </p>
                </div>
                <div
                  className="px-5 py-3"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--line)', borderRadius: '6px' }}
                >
                  <p className="text-[11px] leading-none mb-1.5" style={{ ...sans, color: 'var(--ink-3)' }}>画像来源</p>
                  <p className="text-[14px] font-medium" style={{ ...sans, color: 'var(--ink-1)' }}>
                    当前用户画像
                  </p>
                </div>
                <div
                  className="px-5 py-3"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--line)', borderRadius: '6px' }}
                >
                  <p className="text-[11px] leading-none mb-1.5" style={{ ...sans, color: 'var(--ink-3)' }}>阶段报告</p>
                  <p className="text-[14px] font-medium" style={{ ...sans, color: 'var(--ink-1)' }}>
                    {reports.length} 份
                  </p>
                </div>
              </div>

              {/* Generate button */}
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 text-[14px] font-medium text-white transition-all duration-200 disabled:opacity-50 cursor-pointer"
                style={{ ...sans, background: 'var(--chestnut)', borderRadius: '6px' }}
                onMouseEnter={(e) => { if (!generating) e.currentTarget.style.background = 'oklch(0.36 0.09 30)' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--chestnut)' }}
              >
                {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {generating ? '生成中…' : reports.length === 0 ? '生成第一份报告' : '生成新报告'}
              </button>
            </div>
          </div>

          {/* Content */}
          {reports.length === 0 ? (
            <div className="text-center py-20">
              <FileText
                className="w-12 h-12 mx-auto mb-6"
                strokeWidth={1}
                style={{ color: 'var(--ink-3)' }}
              />
              <h3 className="text-[24px] font-medium" style={serif}>
                还没有报告
              </h3>
              <p className="mt-3 text-[14px]" style={{ ...sans, color: 'var(--ink-3)' }}>
                所有判断，都从一次清晰的回望开始。
              </p>

              {/* Decorative line + quote */}
              <div className="flex items-center justify-center gap-4 mt-8 mb-8">
                <div className="w-16 md:w-24" style={{ height: '1px', background: 'var(--line)' }} />
                <p className="text-[13px] italic" style={{ ...serif, color: 'var(--ink-3)' }}>
                  先立其意，再定其行。
                </p>
                <div className="w-16 md:w-24" style={{ height: '1px', background: 'var(--line)' }} />
              </div>

              <button
                onClick={handleGenerate}
                disabled={generating}
                className="inline-flex items-center gap-2 px-8 py-2.5 text-[14px] font-medium text-white transition-all duration-200 disabled:opacity-50 cursor-pointer"
                style={{ ...sans, background: 'var(--chestnut)', borderRadius: '6px' }}
                onMouseEnter={(e) => { if (!generating) e.currentTarget.style.background = 'oklch(0.36 0.09 30)' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--chestnut)' }}
              >
                {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {generating ? '生成中…' : '开始生成'}
              </button>
            </div>
          ) : (
            <>
              {/* Section header */}
              <div className="flex items-end justify-between mb-8" style={{ borderTop: '1px solid var(--line)', paddingTop: '32px' }}>
                <div>
                  <h2 className="text-[20px] font-semibold" style={serif}>
                    阶段记录
                  </h2>
                  <p className="mt-1 text-[13px]" style={{ ...sans, color: 'var(--ink-3)' }}>
                    你的每一次回顾，都会在这里沉淀为清晰的成长轨迹。
                  </p>
                </div>
                <button
                  onClick={() => setSortOrder((v) => v === 'desc' ? 'asc' : 'desc')}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium transition-colors cursor-pointer"
                  style={{ ...sans, color: 'var(--ink-3)', background: 'var(--bg-card)', border: '1px solid var(--line)', borderRadius: '6px' }}
                >
                  <ArrowUpDown className="w-3.5 h-3.5" />
                  {sortOrder === 'desc' ? '按时间倒序' : '按时间正序'}
                </button>
              </div>

              {/* Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {reports.map((r, i) => {
                  const isLatest = r.id === latestReportId
                  return (
                    <div
                      key={r.id}
                      className="group relative flex flex-col p-5 transition-all duration-200"
                      style={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--line)',
                        borderRadius: '6px',
                        animation: `reportItemIn 0.4s ease-out ${i * 0.05}s both`,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = 'oklch(0.42 0.10 30 / 0.25)'
                        e.currentTarget.style.boxShadow = 'var(--shadow-float)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = 'var(--line)'
                        e.currentTarget.style.boxShadow = 'none'
                      }}
                    >
                      {/* Status row */}
                      <div className="flex items-center justify-between mb-3">
                        <div
                          className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium"
                          style={{ background: 'oklch(0.95 0.03 145)', color: 'oklch(0.45 0.08 145)', borderRadius: '4px' }}
                        >
                          <CheckCircle2 className="w-3 h-3" />
                          已完成
                        </div>
                        {isLatest && (
                          <div
                            className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium"
                            style={{ background: 'oklch(0.94 0.04 40)', color: 'oklch(0.50 0.10 40)', borderRadius: '4px' }}
                          >
                            当前最新版
                          </div>
                        )}
                      </div>

                      {/* Title */}
                      <h3 className="text-[16px] font-semibold mb-2" style={{ ...sans, color: 'var(--ink-1)' }}>
                        {r.title || '职业分析报告'}
                      </h3>

                      {/* Meta */}
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-3 text-[12px]" style={{ ...sans, color: 'var(--ink-3)' }}>
                        {targetLabel && (
                          <span className="inline-flex items-center gap-1">
                            <Target className="w-3 h-3" />
                            目标岗位：{targetLabel}
                          </span>
                        )}
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          生成时间：{r.created_at?.slice(0, 10)}
                        </span>
                      </div>

                      {/* Summary */}
                      <p className="text-[13px] leading-relaxed mb-4 line-clamp-2" style={{ ...sans, color: 'var(--ink-2)' }}>
                        {r.summary || '基于你的用户画像与阶段分析，明确产品理解与用户洞察优势，结合行业趋势，确认职业发展方向并制定下一阶段成长计划。'}
                      </p>

                      {/* Actions */}
                      <div className="flex items-center gap-2 mt-auto">
                        <button
                          onClick={() => navigate(`/report/${r.id}`)}
                          className="inline-flex items-center px-4 py-1.5 text-[13px] font-medium text-white transition-colors cursor-pointer"
                          style={{ background: 'var(--chestnut)', borderRadius: '4px' }}
                          onMouseEnter={(e) => { e.currentTarget.style.background = 'oklch(0.36 0.09 30)' }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--chestnut)' }}
                        >
                          查看报告
                        </button>
                        <button
                          onClick={async () => {
                            setExportingId(r.id)
                            try {
                              await exportReportPdf(r.id)
                            } catch (e) {
                              alert(e instanceof Error ? e.message : '导出失败')
                            } finally {
                              setExportingId(null)
                            }
                          }}
                          disabled={exportingId === r.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-[13px] font-medium transition-colors cursor-pointer disabled:opacity-50"
                          style={{ ...sans, color: 'var(--ink-3)', borderRadius: '4px' }}
                          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--ink-1)'; e.currentTarget.style.background = 'var(--bg-paper-2)' }}
                          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--ink-3)'; e.currentTarget.style.background = 'transparent' }}
                        >
                          {exportingId === r.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Download className="w-3.5 h-3.5" />
                          )}
                          {exportingId === r.id ? '导出中…' : '导出 PDF'}
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('确定删除这份报告？')) deleteMut.mutate(r.id)
                          }}
                          className="ml-auto p-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200 cursor-pointer"
                          style={{ color: 'var(--ink-3)', borderRadius: '4px' }}
                          onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444' }}
                          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--ink-3)' }}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
