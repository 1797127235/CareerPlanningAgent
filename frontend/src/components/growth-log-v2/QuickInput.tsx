import { useState, useEffect, useRef } from 'react'
import { TagChips } from './TagChips'
import { InterviewForm } from './InterviewForm'
import { ProjectForm } from './ProjectForm'
import type { GrowthEntry } from './mockData'

interface QuickInputProps {
  onSent?: () => void
  onAddEntry: (data: Partial<GrowthEntry>) => Promise<unknown> | unknown
  initialText?: string
}

export function QuickInput({ onSent, onAddEntry, initialText = '' }: QuickInputProps) {
  const [content, setContent] = useState(initialText)
  const [tags, setTags] = useState<string[]>([])
  const [isPlan, setIsPlan] = useState(false)
  const [dueType, setDueType] = useState<'daily' | 'weekly' | 'custom'>('daily')
  const [customDate, setCustomDate] = useState('')
  const [showInterview, setShowInterview] = useState(false)
  const [showProject, setShowProject] = useState(false)
  const [sending, setSending] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // 只在 initialText 首次非空时应用（例如从报告跳转过来带 prefill），避免覆盖用户草稿
  const appliedInitial = useRef(false)
  useEffect(() => {
    if (!appliedInitial.current && initialText) {
      setContent(initialText)
      appliedInitial.current = true
    }
  }, [initialText])

  // 用户修改 content 或 tags 时清除旧的错误提示
  useEffect(() => {
    if (errorMsg) setErrorMsg(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content, tags])

  const handleSend = async () => {
    const text = content.trim()
    if (sending) return
    if (!text) {
      setErrorMsg('请先写点内容')
      return
    }
    if (tags.length === 0) {
      setErrorMsg('请至少选一个标签（#项目 / #面试 / #学习 或自定义）')
      return
    }

    let due_at: string | null = null
    if (isPlan) {
      if (dueType === 'daily') {
        due_at = new Date(new Date().setHours(23, 59, 59, 999)).toISOString()
      } else if (dueType === 'weekly') {
        const now = new Date()
        const endOfWeek = new Date(now)
        endOfWeek.setDate(now.getDate() + (6 - now.getDay()))
        endOfWeek.setHours(23, 59, 59, 999)
        due_at = endOfWeek.toISOString()
      } else if (dueType === 'custom' && customDate) {
        due_at = new Date(customDate).toISOString()
      }
    }

    setSending(true)
    setErrorMsg(null)
    try {
      // 快速发送通道永远创建 learning（纯文本笔记 + 标签）。
      // 要记结构化项目/面试走下方的"记录项目"/"面试复盘"按钮。
      await onAddEntry({
        content: text,
        category: 'learning',
        tags,
        structured_data: null,
        is_plan: isPlan,
        status: isPlan ? 'pending' : 'done',
        due_type: isPlan ? dueType : null,
        due_at,
        completed_at: null,
        ai_suggestions: null,
      })

      setContent('')
      setTags([])
      setIsPlan(false)
      setDueType('daily')
      setCustomDate('')
      onSent?.()
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      console.error('[QuickInput] 发送失败:', e)
      setErrorMsg(msg)
    } finally {
      setSending(false)
    }
  }

  const sendable = content.trim().length > 0 && tags.length > 0 && !sending

  return (
    <>
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <textarea
          aria-label="档案内容"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 text-[14px] text-slate-800 placeholder:text-slate-400 outline-none resize-none"
          placeholder="写点什么…"
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            <TagChips tags={tags} onChange={setTags} />
            <label className="flex items-center gap-1.5 text-[12px] text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isPlan}
                onChange={(e) => setIsPlan(e.target.checked)}
                className="cursor-pointer"
              />
              标记为计划
            </label>
            {isPlan && (
              <div className="flex items-center gap-2">
                <select
                  value={dueType}
                  onChange={(e) => setDueType(e.target.value as any)}
                  className="text-[12px] border border-slate-300 rounded-md px-2 py-1 outline-none focus:border-blue-500 bg-white"
                >
                  <option value="daily">今天</option>
                  <option value="weekly">本周</option>
                  <option value="custom">自定义</option>
                </select>
                {dueType === 'custom' && (
                  <input
                    type="datetime-local"
                    value={customDate}
                    onChange={(e) => setCustomDate(e.target.value)}
                    className="text-[12px] border border-slate-300 rounded-md px-2 py-1 outline-none focus:border-blue-500"
                  />
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowInterview(true)}
              className="px-3 py-1.5 text-[12px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer"
            >
              面试复盘
            </button>
            <button
              onClick={() => setShowProject(true)}
              className="px-3 py-1.5 text-[12px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer"
            >
              记录项目
            </button>
            <button
              onClick={handleSend}
              className={[
                'px-4 py-1.5 text-[12px] font-semibold rounded-md transition-colors cursor-pointer',
                sendable
                  ? 'text-white bg-slate-900 hover:bg-blue-700'
                  : 'text-slate-400 bg-slate-100 hover:bg-slate-200',
              ].join(' ')}
            >
              {sending ? '发送中…' : '发送'}
            </button>
          </div>
        </div>
        <div className="mt-2 text-[11px] text-slate-400 min-h-[16px]">
          {!content.trim()
            ? '先写点内容再发送'
            : tags.length === 0
              ? '选一个标签就能发送'
              : isPlan
                ? '会记为待完成计划'
                : ''}
        </div>
        {errorMsg && (
          <div className="mt-1 px-3 py-2 text-[12px] text-red-700 bg-red-50 border border-red-200 rounded-md">
            {errorMsg}
          </div>
        )}
      </div>

      {showInterview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-slate-900/20"
            style={{ backdropFilter: 'blur(4px)' }}
            onClick={() => setShowInterview(false)}
          />
          <div className="relative w-full max-w-[520px] z-10">
            <InterviewForm
              onClose={() => setShowInterview(false)}
              onSaved={onSent}
              onAddEntry={onAddEntry}
            />
          </div>
        </div>
      )}

      {showProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-slate-900/20"
            style={{ backdropFilter: 'blur(4px)' }}
            onClick={() => setShowProject(false)}
          />
          <div className="relative w-full max-w-[520px] z-10">
            <ProjectForm
              onClose={() => setShowProject(false)}
              onSaved={onSent}
              onAddEntry={onAddEntry}
            />
          </div>
        </div>
      )}
    </>
  )
}
