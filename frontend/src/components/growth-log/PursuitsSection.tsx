import { useState } from 'react'
import { createApplication } from '@/api/applications'
import type { JobApplication } from '@/types/application'

const SOURCES = ['BOSS直聘', '牛客', '内推', '校招', '实习僧', '官网', '其他']

export function AddPursuitForm({ onSuccess, onCancel }: {
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
        notes: source ? `来源: ${source}` : undefined,
      })
      onSuccess(app)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally { setSaving(false) }
  }

  const inputCls = "w-full px-3.5 py-2.5 text-[13px] rounded-xl outline-none bg-slate-50 border border-slate-200 focus:border-blue-400 focus:bg-white transition-colors"

  return (
    <div className="bg-white rounded-2xl p-6 shadow-xl">
      <p className="text-[15px] font-bold text-slate-800 mb-5">添加投递记录</p>
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          value={company}
          onChange={e => setCompany(e.target.value)}
          placeholder="公司名称 *"
          autoFocus
          className={inputCls + ' font-semibold'}
        />
        <input
          value={position}
          onChange={e => setPosition(e.target.value)}
          placeholder="投递岗位 *"
          className={inputCls}
        />

        {/* Source chips */}
        <div>
          <p className="text-[11px] text-slate-400 mb-2">投递来源（选填）</p>
          <div className="flex flex-wrap gap-1.5">
            {SOURCES.map(s => (
              <button
                type="button"
                key={s}
                onClick={() => setSource(source === s ? '' : s)}
                className="px-2.5 py-1 text-[11px] font-medium rounded-lg border transition-all cursor-pointer"
                style={{
                  background: source === s ? 'rgba(37,99,235,0.08)' : 'transparent',
                  borderColor: source === s ? 'rgba(37,99,235,0.4)' : 'rgba(0,0,0,0.1)',
                  color: source === s ? '#2563EB' : '#94A3B8',
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="text-[11px] text-red-500">{error}</p>}

        <div className="flex gap-2 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="flex-1 py-2.5 text-[13px] font-semibold text-white rounded-xl cursor-pointer disabled:opacity-50 transition-colors"
            style={{ background: '#2563EB' }}
          >
            {saving ? '添加中...' : '添加'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2.5 text-[13px] text-slate-500 rounded-xl cursor-pointer border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  )
}
