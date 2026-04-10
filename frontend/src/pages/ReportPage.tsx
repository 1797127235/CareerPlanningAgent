import { useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, Plus, Clock, ChevronLeft, Download, Sparkles, Trash2, Pen, Save, Wand2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'
import { useReportListQuery, useReportDetailQuery, useGenerateReportMutation, useDeleteReportMutation, useEditReportMutation, usePolishReportMutation } from '@/hooks/useReport'
import { EmptyState, AiDisclaimer } from '@/components/shared'
import { ReportHero, ReportChapterCard, ReportActions } from '@/components/report'
import type { ReportListItem } from '@/api/report'

function SectionDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 my-5">
      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 whitespace-nowrap">{label}</span>
      <div className="flex-1 h-px bg-slate-200" />
    </div>
  )
}

function formatDate(dateStr: string): string {
  try {
    const s = /Z|[+-]\d{2}:?\d{2}$/.test(dateStr) ? dateStr : dateStr + 'Z'
    const d = new Date(s)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return dateStr
  }
}

function ReportCard({ item, onClick, onDelete, isDeleting }: { item: ReportListItem; onClick: () => void; onDelete: () => void; isDeleting: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full text-left glass p-5 group"
    >
      <div className="flex items-start gap-4">
        <button onClick={onClick} className="shrink-0 w-10 h-10 rounded-xl bg-[var(--blue)]/10 flex items-center justify-center group-hover:bg-[var(--blue)]/15 transition-colors cursor-pointer">
          <FileText className="w-5 h-5 text-[var(--blue)]" />
        </button>
        <button onClick={onClick} className="flex-1 min-w-0 text-left cursor-pointer">
          <h3 className="text-[15px] font-semibold text-slate-800 truncate">{item.title}</h3>
          <p className="text-[13px] text-slate-500 mt-1 line-clamp-2">{item.summary}</p>
          <div className="flex items-center gap-1.5 text-[12px] text-slate-400 mt-2">
            <Clock className="w-3 h-3" />
            {formatDate(item.created_at)}
          </div>
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete() }}
          disabled={isDeleting}
          className="shrink-0 p-2 text-slate-300 hover:text-red-500 transition-colors cursor-pointer opacity-0 group-hover:opacity-100 disabled:opacity-50"
          title="删除报告"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  )
}

function ReportView({ reportId, onBack }: { reportId: number; onBack: () => void }) {
  const { data: report, isLoading, isError } = useReportDetailQuery(reportId)
  const editMutation = useEditReportMutation(reportId)
  const polishMutation = usePolishReportMutation(reportId)

  const [editing, setEditing] = useState(false)
  const editedRef = useRef<{ summary?: string; chapters: Record<string, string> }>({ chapters: {} })

  const handleExportPdf = useCallback(() => {
    window.print()
  }, [])

  const handleSave = useCallback(() => {
    const edits: { narrative_summary?: string; chapter_narratives?: Record<string, string> } = {}
    if (editedRef.current.summary !== undefined) {
      edits.narrative_summary = editedRef.current.summary
    }
    if (Object.keys(editedRef.current.chapters).length > 0) {
      edits.chapter_narratives = editedRef.current.chapters
    }
    if (!edits.narrative_summary && !edits.chapter_narratives) {
      setEditing(false)
      return
    }
    editMutation.mutate(edits, {
      onSuccess: () => {
        setEditing(false)
        editedRef.current = { chapters: {} }
      },
    })
  }, [editMutation])

  const handlePolish = useCallback(() => {
    polishMutation.mutate()
  }, [polishMutation])

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 glass animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError || !report) {
    return (
      <div className="text-center py-12 text-slate-500">
        <p>加载报告失败</p>
        <button onClick={onBack} className="mt-3 text-[var(--blue)] hover:text-[var(--blue-deep)] text-[14px] font-medium">
          返回列表
        </button>
      </div>
    )
  }

  const { data } = report
  const narrative = data?.narrative
  const chapters = (data?.chapters ?? []) as Array<{
    key: string; title: string; subtitle?: string;
    has_data: boolean; locked_hint?: string; data: Record<string, unknown>
  }>
  const matchScore = (data?.match_score ?? 0) as number
  const targetJob = (data?.target_job ?? '') as string
  const reportVersion = data?.report_version as number | undefined

  return (
    <div>
      <div className="flex items-center justify-between mb-6 print:hidden">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-[13px] font-medium text-slate-500 hover:text-slate-700 transition-colors cursor-pointer"
        >
          <ChevronLeft className="w-4 h-4" />
          返回列表
        </button>
        <div className="flex items-center gap-2">
          {editing ? (
            <button
              onClick={handleSave}
              disabled={editMutation.isPending}
              className="btn-cta flex items-center gap-1.5 px-4 py-2 text-[13px] font-semibold cursor-pointer disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {editMutation.isPending ? '保存中...' : '保存'}
            </button>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="btn-glass flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium text-[var(--text-2)] cursor-pointer"
            >
              <Pen className="w-3.5 h-3.5 text-slate-400" />
              编辑
            </button>
          )}
          <button
            onClick={handlePolish}
            disabled={polishMutation.isPending}
            className="btn-glass flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium text-[var(--text-2)] cursor-pointer disabled:opacity-50"
          >
            <Wand2 className="w-3.5 h-3.5 text-amber-500" />
            {polishMutation.isPending ? '润色中...' : '智能润色'}
          </button>
          <button
            onClick={handleExportPdf}
            className="btn-glass flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium text-[var(--text-2)] cursor-pointer"
          >
            <Download className="w-4 h-4 text-slate-400" />
            导出 PDF
          </button>
        </div>
      </div>

      {polishMutation.isSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-2.5 text-[13px] text-emerald-700 mb-4 flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          报告已智能润色完成
        </div>
      )}

      {editing && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-2.5 text-[13px] text-blue-700 mb-4 flex items-center gap-2">
          <Pen className="w-4 h-4" />
          编辑模式 — 点击蓝色 AI 洞察文字可直接修改，完成后点击"保存"
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-[22px] font-bold text-slate-900">{report.title}</h1>
        <div className="flex items-center gap-3 mt-2 text-[12px] text-slate-400">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDate(report.created_at)}
          </span>
          <span className="flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            AI 生成{data?.polished ? ' · 已润色' : ''}{data?.user_edited ? ' · 已编辑' : ''}
          </span>
        </div>
      </div>

      <ReportHero matchScore={matchScore} targetJob={targetJob} narrative={narrative} reportVersion={reportVersion} />

      {/* ── Section divider: 当前状态 ── */}
      <SectionDivider label="当前状态" />

      {/* ── Bento row: 能力画像(3) | 岗位匹配+面试记录(2) ── */}
      {(() => {
        const ability   = chapters.find(c => c.key === 'ability')
        const jobMatch  = chapters.find(c => c.key === 'job_match')
        const interview = chapters.find(c => c.key === 'interview')
        const rest      = chapters.filter(c => !['ability','job_match','interview'].includes(c.key))
        return (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-4">
              {/* left: ability */}
              <div className="lg:col-span-3">
                {ability && (
                  <ReportChapterCard
                    chapter={ability}
                    narrativeText={narrative?.chapters?.ability}
                    index={0}
                    editing={editing}
                    onNarrativeChange={(text) => { editedRef.current.chapters.ability = text }}
                  />
                )}
              </div>
              {/* right: job_match + interview stacked */}
              <div className="lg:col-span-2 flex flex-col gap-4">
                {jobMatch && (
                  <ReportChapterCard
                    chapter={jobMatch}
                    narrativeText={narrative?.chapters?.job_match}
                    index={1}
                    editing={editing}
                    onNarrativeChange={(text) => { editedRef.current.chapters.job_match = text }}
                  />
                )}
                {interview && (
                  <ReportChapterCard
                    chapter={interview}
                    narrativeText={narrative?.chapters?.interview}
                    index={2}
                    editing={editing}
                    onNarrativeChange={(text) => { editedRef.current.chapters.interview = text }}
                  />
                )}
              </div>
            </div>

            {/* ── Section divider: 向前看 ── */}
            <SectionDivider label="向前看" />

            {/* ── Full-width: career_path, action_plan ── */}
            <div className="space-y-4 mb-6">
              {rest.map((ch, i) => (
                <ReportChapterCard
                  key={ch.key}
                  chapter={ch}
                  narrativeText={narrative?.chapters?.[ch.key]}
                  index={i + 3}
                  editing={editing}
                  onNarrativeChange={(text) => { editedRef.current.chapters[ch.key] = text }}
                />
              ))}
            </div>
          </>
        )
      })()}

      {narrative?.actions && narrative.actions.length > 0 && (
        <div className="mb-6">
          <ReportActions actions={narrative.actions} />
        </div>
      )}

      <AiDisclaimer />
    </div>
  )
}

export default function ReportPage() {
  const { token } = useAuth()
  const { profile, loading: profileLoading } = useProfileData(token)
  const { data: reports = [], isLoading: reportsLoading } = useReportListQuery()
  const generateMutation = useGenerateReportMutation()
  const deleteMutation = useDeleteReportMutation()

  const [viewingId, setViewingId] = useState<number | null>(null)

  const hasProfile = profile !== null
  const loading = profileLoading || reportsLoading

  const handleGenerate = useCallback(() => {
    generateMutation.mutate()
  }, [generateMutation])

  return (
    <div className="max-w-[860px] mx-auto px-8 pt-6 pb-12">
      {viewingId !== null ? (
        <ReportView reportId={viewingId} onBack={() => setViewingId(null)} />
      ) : (
        <AnimatePresence mode="wait">
          {loading ? (
            <div className="space-y-4 mt-4">
              {[1, 2].map((i) => (
                <div key={i} className="h-28 glass animate-pulse" />
              ))}
            </div>
          ) : !hasProfile ? (
            <EmptyState
              icon="📄"
              title="先建立画像才能生成报告"
              description="上传简历或手动填写画像后，AI 可以为你撰写职业发展报告。"
              ctaText="去建立画像"
              ctaHref="/profile"
            />
          ) : (
            <div className="flex flex-col gap-5">
              <div className="flex items-center justify-end">
                <button
                  onClick={handleGenerate}
                  disabled={generateMutation.isPending}
                  className="btn-cta flex items-center gap-1.5 px-4 py-1.5 text-[12px] font-semibold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Plus className="w-3.5 h-3.5" />
                  {generateMutation.isPending ? '生成中...' : '生成新报告'}
                </button>
              </div>

              {generateMutation.isPending && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass-static !rounded-2xl p-5 flex items-center gap-4"
                >
                  <div className="w-8 h-8 border-2 border-[var(--blue)] border-t-transparent rounded-full animate-spin shrink-0" />
                  <div>
                    <p className="text-[14px] font-medium text-[var(--text-1)]">AI 正在撰写报告...</p>
                    <p className="text-[12px] text-[var(--text-2)] mt-0.5">正在分析画像、诊断和训练数据，这可能需要 15-30 秒</p>
                  </div>
                </motion.div>
              )}

              {generateMutation.isError && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-[14px] text-red-700">
                  生成失败：{generateMutation.error instanceof Error ? generateMutation.error.message : '请稍后重试'}
                </div>
              )}

              {reports.length === 0 && !generateMutation.isPending ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
                    <FileText className="w-8 h-8 text-slate-400" />
                  </div>
                  <p className="text-[15px] font-medium text-slate-600 mb-1">还没有报告</p>
                  <p className="text-[13px] text-slate-400 mb-4">点击上方"生成新报告"，AI 将为你撰写职业发展报告</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {reports.map((item) => (
                    <ReportCard
                      key={item.id}
                      item={item}
                      onClick={() => setViewingId(item.id)}
                      onDelete={() => deleteMutation.mutate(item.id)}
                      isDeleting={deleteMutation.isPending}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </AnimatePresence>
      )}
    </div>
  )
}
