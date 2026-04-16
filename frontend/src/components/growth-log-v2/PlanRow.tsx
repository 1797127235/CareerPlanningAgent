import { useState } from 'react'
import { Pencil, Trash2, X, Check } from 'lucide-react'
import type { GrowthEntry } from './mockData'
import { ConfirmDialog } from './ConfirmDialog'

interface PlanRowProps {
  entry: GrowthEntry
  onToggle: (id: number) => void
  onDrop: (id: number) => void
  onUpdate?: (id: number, data: Partial<GrowthEntry>) => Promise<unknown>
}

function fmtDue(dueAt: string | null) {
  if (!dueAt) return ''
  const now = new Date()
  const due = new Date(dueAt)
  const diffDays = Math.ceil((due.getTime() - now.getTime()) / 86400000)
  if (diffDays < 0) return '已逾期'
  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '明天'
  const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  if (diffDays < 7 && due.getDay() !== now.getDay()) return `${weekDays[due.getDay()]}截止`
  return `${diffDays}天后`
}

export function PlanRow({ entry, onToggle, onDrop, onUpdate }: PlanRowProps) {
  const [checked, setChecked] = useState(false)
  const [fading, setFading] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(entry.content)
  const [saving, setSaving] = useState(false)

  const handleCheck = () => {
    setChecked(true)
    setTimeout(() => {
      setFading(true)
      setTimeout(() => {
        onToggle(entry.id)
      }, 200)
    }, 200)
  }

  const saveEdit = async () => {
    const text = draft.trim()
    if (!text || !onUpdate) {
      setEditing(false)
      return
    }
    setSaving(true)
    try {
      await onUpdate(entry.id, { content: text })
      setEditing(false)
    } catch (e) {
      window.alert('保存失败：' + (e instanceof Error ? e.message : String(e)))
    } finally {
      setSaving(false)
    }
  }

  if (editing) {
    return (
      <div className="flex items-center gap-2 py-3 border-t border-slate-200">
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') saveEdit()
            if (e.key === 'Escape') {
              setDraft(entry.content)
              setEditing(false)
            }
          }}
          className="flex-1 px-2 py-1 text-[14px] border border-slate-300 rounded-md outline-none focus:border-blue-500"
        />
        <button
          onClick={saveEdit}
          disabled={saving}
          title="保存"
          className="p-1 text-slate-400 hover:text-blue-600 disabled:opacity-40 cursor-pointer"
        >
          <Check className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setDraft(entry.content)
            setEditing(false)
          }}
          disabled={saving}
          title="取消"
          className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-40 cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    )
  }

  return (
    <>
      <div
        className={[
          'group flex items-center justify-between gap-3 py-3 border-t border-slate-200 select-none',
          fading ? 'opacity-0 transition-opacity duration-200' : 'opacity-100',
        ].join(' ')}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <button
            onClick={handleCheck}
            className={[
              'shrink-0 w-5 h-5 rounded border flex items-center justify-center transition-colors cursor-pointer',
              checked
                ? 'bg-blue-600 border-blue-600'
                : 'bg-white border-slate-300 hover:border-blue-500',
            ].join(' ')}
            aria-label="完成计划"
          >
            {checked && <Check className="w-3.5 h-3.5 text-white" />}
          </button>
          <span className="text-[14px] text-slate-800 truncate">{entry.content}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[12px] text-slate-400">{fmtDue(entry.due_at)}</span>
          {onUpdate && (
            <button
              onClick={() => {
                setDraft(entry.content)
                setEditing(true)
              }}
              title="编辑"
              aria-label="编辑计划"
              className="p-1 text-slate-300 hover:text-blue-600 transition-colors cursor-pointer"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={() => setConfirmOpen(true)}
            title="放弃计划"
            aria-label="放弃计划"
            className="p-1 text-slate-300 hover:text-red-600 transition-colors cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="放弃这个计划？"
        message="计划会被标记为已放弃，不会出现在待完成列表里。"
        confirmLabel="放弃"
        danger
        onConfirm={() => {
          setConfirmOpen(false)
          onDrop(entry.id)
        }}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  )
}
