import { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, X } from 'lucide-react'
import { createLearningNote } from '@/api/growthLog'

export function LearningNoteForm({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) {
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function addTag(s: string) {
    const t = s.trim()
    if (t && !tags.includes(t)) setTags([...tags, t])
    setTagInput('')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) { setError('标题不能为空'); return }
    if (!summary.trim()) { setError('摘要不能为空'); return }
    setSaving(true); setError('')
    try {
      await createLearningNote({
        title: title.trim(),
        summary: summary.trim(),
        tags,
      })
      onSuccess()
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
      transition={{ duration: 0.15 }}
      className="rounded-[20px] p-5 mb-4 max-w-full"
      style={{
        background: 'rgba(255,255,255,0.72)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(22,163,74,0.15)',
        boxShadow: '0 4px 20px rgba(22,163,74,0.08)',
      }}
    >
      <p className="text-[13px] font-bold text-[#1a1a1a] mb-4">记录学习心得</p>
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="学习主题（如：Redis 持久化机制） *"
          autoFocus
          className="w-full px-3 py-2.5 text-[14px] font-semibold rounded-[12px] outline-none"
          style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.06)' }}
          onFocus={e => { e.currentTarget.style.border = '1px solid rgba(22,163,74,0.4)'; e.currentTarget.style.background = '#fff' }}
          onBlur={e => { e.currentTarget.style.border = '1px solid rgba(0,0,0,0.06)'; e.currentTarget.style.background = 'rgba(0,0,0,0.04)' }}
        />

        <textarea
          value={summary}
          onChange={e => setSummary(e.target.value)}
          placeholder="总结心得... *"
          rows={3}
          className="w-full px-3 py-2.5 text-[12px] rounded-[12px] outline-none resize-none"
          style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.06)' }}
          onFocus={e => { e.currentTarget.style.border = '1px solid rgba(22,163,74,0.4)'; e.currentTarget.style.background = '#fff' }}
          onBlur={e => { e.currentTarget.style.border = '1px solid rgba(0,0,0,0.06)'; e.currentTarget.style.background = 'rgba(0,0,0,0.04)' }}
        />

        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tags.map(s => (
              <span key={s}
                className="flex items-center gap-1 text-[11px] font-medium px-2.5 py-1 rounded-[8px] cursor-pointer bg-green-50 text-green-700 border border-green-200"
                onClick={() => setTags(tags.filter(x => x !== s))}>
                {s} <X className="w-2.5 h-2.5" />
              </span>
            ))}
          </div>
        )}

        <input
          value={tagInput}
          onChange={e => setTagInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(tagInput) } }}
          placeholder="添加标签（回车确认）"
          className="w-full px-3 py-2 text-[12px] rounded-[10px] outline-none"
          style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.06)' }}
          onFocus={e => { e.currentTarget.style.border = '1px solid rgba(22,163,74,0.4)'; e.currentTarget.style.background = '#fff' }}
          onBlur={e => { e.currentTarget.style.border = '1px solid rgba(0,0,0,0.06)'; e.currentTarget.style.background = 'rgba(0,0,0,0.04)' }}
        />

        {error && <p className="text-[11px] text-red-500">{error}</p>}

        <div className="flex gap-2 pt-1">
          <button type="submit" disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-semibold text-white rounded-[10px] cursor-pointer transition-colors"
            style={{ background: saving ? 'rgba(22,163,74,0.5)' : '#16A34A' }}>
            {saving ? <div className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : <Check className="w-3.5 h-3.5" />}
            {saving ? '保存中...' : '记录学习'}
          </button>
          <button type="button" onClick={onCancel}
            className="px-4 py-2 text-[12px] text-[#8E8E93] font-medium rounded-[10px] cursor-pointer"
            style={{ border: '1px solid rgba(0,0,0,0.08)' }}>
            取消
          </button>
        </div>
      </form>
    </motion.div>
  )
}
