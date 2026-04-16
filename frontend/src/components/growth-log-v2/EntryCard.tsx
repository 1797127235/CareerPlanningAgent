import { useState } from 'react'
import { Lightbulb, Pencil, Trash2, Folder, Tag, Link as LinkIcon } from 'lucide-react'
import type { GrowthEntry, InterviewData, ProjectData } from './mockData'
import { AiSuggestions } from './AiSuggestions'
import { TagChips } from './TagChips'
import { ConfirmDialog } from './ConfirmDialog'
import { InterviewForm } from './InterviewForm'
import { ProjectForm } from './ProjectForm'

function fmtRelative(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const RATING_TEXT: Record<string, string> = {
  good: '好',
  medium: '一般',
  bad: '差',
}

const RESULT_TEXT: Record<string, string> = {
  passed: '通过',
  failed: '未通过',
  pending: '待定',
}

const STATUS_TEXT: Record<string, string> = {
  planning: '计划中',
  in_progress: '进行中',
  completed: '已完成',
}

const STATUS_DOT: Record<string, string> = {
  planning: 'bg-slate-400',
  in_progress: 'bg-blue-600',
  completed: 'bg-green-600',
}

const STATUS_COLOR_TEXT: Record<string, string> = {
  planning: 'text-slate-500',
  in_progress: 'text-blue-600',
  completed: 'text-green-600',
}

function TagList({ tags }: { tags: string[] }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-400">
      {tags.slice(0, 6).map((t) => (
        <span key={t}>#{t}</span>
      ))}
    </div>
  )
}

function AiButton({
  count,
  expanded,
  loading,
  onClick,
}: {
  count: number
  expanded: boolean
  loading: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-blue-600 transition-colors cursor-pointer"
    >
      <Lightbulb className="w-3.5 h-3.5" />
      {loading ? '生成中…' : count > 0 ? `AI 建议 ✓(${count})` : 'AI 建议'}
      <span
        className={[
          'inline-block w-3 h-3 text-[10px] leading-3 text-center transition-transform',
          expanded ? 'rotate-180' : '',
        ].join(' ')}
      >
        ▼
      </span>
    </button>
  )
}

function LearningCardBody({
  entry,
  expanded,
  loading,
  onToggleAi,
  onUpdate,
}: {
  entry: GrowthEntry
  expanded: boolean
  loading: boolean
  onToggleAi: () => void
  onUpdate?: (id: number, data: Partial<GrowthEntry>) => Promise<unknown>
}) {
  const [editing, setEditing] = useState(false)
  const [draftContent, setDraftContent] = useState(entry.content)
  const [draftTags, setDraftTags] = useState<string[]>(entry.tags)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const startEdit = () => {
    setDraftContent(entry.content)
    setDraftTags(entry.tags)
    setErr(null)
    setEditing(true)
  }

  const cancelEdit = () => {
    setEditing(false)
    setErr(null)
  }

  const saveEdit = async () => {
    const text = draftContent.trim()
    if (!text) {
      setErr('内容不能为空')
      return
    }
    if (draftTags.length === 0) {
      setErr('请至少选一个标签')
      return
    }
    if (!onUpdate) return
    setSaving(true)
    setErr(null)
    try {
      await onUpdate(entry.id, { content: text, tags: draftTags })
      setEditing(false)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  if (editing) {
    return (
      <>
        <textarea
          value={draftContent}
          onChange={(e) => setDraftContent(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 text-[14px] text-slate-800 border border-slate-300 rounded-md outline-none focus:border-blue-500 resize-none"
        />
        <div className="mt-2">
          <TagChips tags={draftTags} onChange={setDraftTags} />
        </div>
        {err && <div className="mt-2 text-[12px] text-red-700">{err}</div>}
        <div className="mt-3 flex items-center justify-end gap-2">
          <button
            onClick={cancelEdit}
            disabled={saving}
            className="px-3 py-1 text-[12px] font-medium text-slate-600 hover:text-slate-900 disabled:opacity-40 cursor-pointer"
          >
            取消
          </button>
          <button
            onClick={saveEdit}
            disabled={saving}
            className="px-3 py-1 text-[12px] font-semibold text-white bg-slate-900 hover:bg-blue-700 disabled:opacity-40 rounded-md cursor-pointer"
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </>
    )
  }

  return (
    <>
      <p className="text-[15px] text-slate-800 leading-relaxed whitespace-pre-wrap">{entry.content}</p>
      <div className="mt-3 flex items-end justify-between gap-3">
        <TagList tags={entry.tags} />
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-slate-400 tabular-nums">{fmtRelative(entry.created_at)}</span>
          {onUpdate && (
            <button
              onClick={startEdit}
              title="编辑"
              className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-blue-600 transition-colors cursor-pointer"
            >
              <Pencil className="w-3 h-3" />
              编辑
            </button>
          )}
          <AiButton count={entry.ai_suggestions?.length || 0} expanded={expanded} loading={loading} onClick={onToggleAi} />
        </div>
      </div>
    </>
  )
}

function InterviewCardBody({
  entry,
  expanded,
  loading,
  onToggleAi,
  onEdit,
}: {
  entry: GrowthEntry
  expanded: boolean
  loading: boolean
  onToggleAi: () => void
  onEdit?: () => void
}) {
  const data = entry.structured_data as InterviewData | null
  return (
    <>
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-[16px] font-bold text-slate-900">
          {data?.company || '未知公司'} · {data?.round || '面试'}
        </h4>
        <TagList tags={entry.tags} />
      </div>
      {data && data.questions.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {data.questions.map((qa, idx) => (
            <div key={idx} className="text-[13px] text-slate-600 leading-relaxed">
              <span className="text-slate-400">Q:</span> {qa.q} <span className="text-slate-300">→</span>{' '}
              {qa.a || '未回答'}
            </div>
          ))}
        </div>
      )}
      {data && (
        <div className="mt-3 text-[12px] text-slate-500">
          自评: <span className="font-medium text-slate-700">{RATING_TEXT[data.self_rating]}</span>
          <span className="mx-2 text-slate-300">·</span>
          结果: <span className="font-medium text-slate-700">{RESULT_TEXT[data.result]}</span>
        </div>
      )}
      {data?.reflection && <p className="mt-2 text-[13px] text-slate-500 leading-relaxed">感受: {data.reflection}</p>}
      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-[11px] text-slate-400 tabular-nums">{fmtRelative(entry.created_at)}</span>
        <div className="flex items-center gap-3">
          {onEdit && (
            <button
              onClick={onEdit}
              title="编辑面试"
              className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-blue-600 transition-colors cursor-pointer"
            >
              <Pencil className="w-3 h-3" />
              编辑
            </button>
          )}
          <AiButton count={entry.ai_suggestions?.length || 0} expanded={expanded} loading={loading} onClick={onToggleAi} />
        </div>
      </div>
    </>
  )
}

function ProjectCardBody({
  entry,
  expanded,
  loading,
  onToggleAi,
  onEdit,
}: {
  entry: GrowthEntry
  expanded: boolean
  loading: boolean
  onToggleAi: () => void
  onEdit?: () => void
}) {
  const data = entry.structured_data as ProjectData | null
  return (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="text-[15px] text-slate-800 leading-relaxed">{entry.content}</p>
        <TagList tags={entry.tags} />
      </div>
      {data && (
        <div className="mt-3 space-y-1">
          <div className="flex items-center gap-1.5 text-[13px] text-slate-700 font-medium">
            <Folder className="w-3.5 h-3.5 text-slate-400" />
            {data.name}
          </div>
          {data.description && <div className="text-[12px] text-slate-500">{data.description}</div>}
          {data.skills_used.length > 0 && (
            <div className="flex items-center gap-1.5 text-[12px] text-slate-500">
              <Tag className="w-3 h-3 text-slate-400" />
              {data.skills_used.join(' · ')}
            </div>
          )}
          {data.github_url && (
            <a
              href={data.github_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-[12px] text-blue-600 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              <LinkIcon className="w-3 h-3" />
              {data.github_url.replace(/^https?:\/\//, '')}
            </a>
          )}
          <div className="flex items-center gap-1.5 pt-1">
            <span className={['w-1.5 h-1.5 rounded-full', STATUS_DOT[data.status]].join(' ')} />
            <span className={['text-[11px] font-medium', STATUS_COLOR_TEXT[data.status]].join(' ')}>
              {STATUS_TEXT[data.status]}
            </span>
          </div>
        </div>
      )}
      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-[11px] text-slate-400 tabular-nums">{fmtRelative(entry.created_at)}</span>
        <div className="flex items-center gap-3">
          {onEdit && (
            <button
              onClick={onEdit}
              title="编辑项目"
              className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-blue-600 transition-colors cursor-pointer"
            >
              <Pencil className="w-3 h-3" />
              编辑
            </button>
          )}
          <AiButton count={entry.ai_suggestions?.length || 0} expanded={expanded} loading={loading} onClick={onToggleAi} />
        </div>
      </div>
    </>
  )
}

export function EntryCard({
  entry,
  onMutate,
  onRequestAi,
  onConvertAi,
  onUpdate,
  onDelete,
}: {
  entry: GrowthEntry
  onMutate?: () => void
  onRequestAi: (id: number) => Promise<unknown>
  onConvertAi: (text: string) => Promise<unknown> | unknown
  onUpdate?: (id: number, data: Partial<GrowthEntry>) => Promise<unknown>
  onDelete?: (id: number) => Promise<unknown>
}) {
  const [expanded, setExpanded] = useState(!!entry.ai_suggestions && entry.ai_suggestions.length > 0)
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [editStructured, setEditStructured] = useState(false)

  const hasAi = !!(entry.ai_suggestions && entry.ai_suggestions.length > 0)

  // 关键：结构化 body 只在 structured_data 非空时使用，否则按 learning 文本笔记渲染
  const hasStructured = entry.structured_data != null
  const effectiveCategory =
    hasStructured && (entry.category === 'interview' || entry.category === 'project')
      ? entry.category
      : 'learning'

  const toggleAi = async () => {
    if (hasAi) {
      setExpanded((v) => !v)
      return
    }
    setLoading(true)
    try {
      await onRequestAi(entry.id)
    } finally {
      setLoading(false)
      setExpanded(true)
    }
  }

  const doDelete = async () => {
    if (!onDelete || deleting) return
    setConfirmOpen(false)
    setDeleting(true)
    try {
      await onDelete(entry.id)
    } catch (e) {
      window.alert('删除失败：' + (e instanceof Error ? e.message : String(e)))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <article className="group relative pt-4 pb-5 pr-7 border-t-2 border-slate-900 hover:border-blue-700 transition-colors">
        {onDelete && (
          <button
            onClick={() => setConfirmOpen(true)}
            disabled={deleting}
            title="删除"
            aria-label="删除这条记录"
            className="absolute top-3 right-0 p-1 text-slate-300 hover:text-red-600 disabled:opacity-40 transition-colors cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
        {effectiveCategory === 'interview' ? (
          <InterviewCardBody
            entry={entry}
            expanded={expanded}
            loading={loading}
            onToggleAi={toggleAi}
            onEdit={onUpdate ? () => setEditStructured(true) : undefined}
          />
        ) : effectiveCategory === 'project' ? (
          <ProjectCardBody
            entry={entry}
            expanded={expanded}
            loading={loading}
            onToggleAi={toggleAi}
            onEdit={onUpdate ? () => setEditStructured(true) : undefined}
          />
        ) : (
          <LearningCardBody entry={entry} expanded={expanded} loading={loading} onToggleAi={toggleAi} onUpdate={onUpdate} />
        )}

        {expanded && entry.ai_suggestions && entry.ai_suggestions.length > 0 && (
          <AiSuggestions
            suggestions={entry.ai_suggestions}
            onConvert={async (text) => {
              await onConvertAi(text)
              onMutate?.()
              setExpanded(false)
            }}
          />
        )}
      </article>

      <ConfirmDialog
        open={confirmOpen}
        title="删除这条记录？"
        message="删除后无法恢复。"
        confirmLabel="删除"
        danger
        onConfirm={doDelete}
        onCancel={() => setConfirmOpen(false)}
      />

      {editStructured && effectiveCategory === 'interview' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-slate-900/20"
            style={{ backdropFilter: 'blur(4px)' }}
            onClick={() => setEditStructured(false)}
          />
          <div className="relative w-full max-w-[520px] z-10">
            <InterviewForm
              onClose={() => setEditStructured(false)}
              onAddEntry={async () => { /* not used in edit mode */ }}
              initialEntry={entry}
              onUpdate={onUpdate}
            />
          </div>
        </div>
      )}

      {editStructured && effectiveCategory === 'project' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-slate-900/20"
            style={{ backdropFilter: 'blur(4px)' }}
            onClick={() => setEditStructured(false)}
          />
          <div className="relative w-full max-w-[520px] z-10">
            <ProjectForm
              onClose={() => setEditStructured(false)}
              onAddEntry={async () => { /* not used in edit mode */ }}
              initialEntry={entry}
              onUpdate={onUpdate}
            />
          </div>
        </div>
      )}
    </>
  )
}
