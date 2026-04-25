import { useState } from 'react'
import { Pencil } from 'lucide-react'
import type { ReportV2Data } from '@/api/report'
import { ChapterOpener, Chapter } from './index'
import { splitParagraphs } from './reportUtils'

interface ChapterIIIProps {
  data: ReportV2Data
  onSave?: (text: string) => Promise<void>
  saving?: boolean
}

export function ChapterIII({ data, onSave, saving }: ChapterIIIProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  // User override takes precedence over AI-generated differentiation_advice.
  const override = data.chapter_narratives?.['chapter-3']
  const baseAdvice = (data.differentiation_advice ?? '').trim()
  const proseText = (override ?? baseAdvice).trim()
  const paras = splitParagraphs(proseText, 2, 3)

  const needsImp = (data.diagnosis ?? [])
    .filter((d) => d.status === 'needs_improvement')
    .slice(0, 3)

  const hasContent = paras.length > 0 || needsImp.length > 0

  const enterEdit = () => {
    setDraft(proseText)
    setEditing(true)
  }
  const cancel = () => {
    setDraft('')
    setEditing(false)
  }
  const save = async () => {
    if (!onSave) return
    const trimmed = draft.trim()
    if (!trimmed) return
    try {
      await onSave(trimmed)
      setEditing(false)
    } catch {
      /* keep draft */
    }
  }

  return (
    <div id="chapter-3">
      <ChapterOpener numeral="III" label="差距" headline="你还差的，说清楚。" />
      <Chapter>
        {editing ? (
          <div className="mt-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={Math.max(6, Math.min(20, draft.split('\n').length + 2))}
              className="w-full p-4 text-[17px] leading-[1.8] text-slate-800 bg-slate-50 border border-slate-200 rounded-sm focus:outline-none focus:border-slate-400 resize-y"
              placeholder="写下你看到的差距。空行分段。"
              autoFocus
            />
            <div className="mt-3 flex items-center gap-4">
              <button
                onClick={save}
                disabled={saving || !draft.trim()}
                className="inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-wait"
              >
                {saving ? '保存中…' : '保存 →'}
              </button>
              <button
                onClick={cancel}
                disabled={saving}
                className="text-[13px] text-slate-400 hover:text-slate-700 transition-colors cursor-pointer disabled:opacity-50"
              >
                取消
              </button>
            </div>
          </div>
        ) : (
          <>
            {onSave && (
              <div className="flex justify-end mb-2 -mt-2 print:hidden">
                <button
                  onClick={enterEdit}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-slate-900 transition-colors cursor-pointer"
                  aria-label="编辑这一章"
                >
                  <Pencil className="w-3 h-3" />
                  编辑
                </button>
              </div>
            )}
            {!hasContent && (
              <p className="text-[17px] leading-[1.8] text-slate-500">
                关于差距的分析还没写出来。点右上角「编辑」可以自己写，或点上方「再生成」重跑。
              </p>
            )}
            {paras.map((p, i) => (
              <p key={i} className={i === 0 ? '' : 'mt-5'}>
                {p}
              </p>
            ))}

            {needsImp.length > 0 && (
              <div className="mt-10">
                <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-4">
                  几件具体要改的事
                </p>
                <div className="pl-5 border-l-2 border-slate-300 space-y-5">
                  {needsImp.map((d, i) => (
                    <div key={(d.source_id ?? 0) + '-' + i}>
                      <p className="text-[15px] text-slate-800 leading-relaxed">
                        {d.highlight && <span className="font-semibold">{d.highlight}</span>}
                        {d.suggestion && (
                          <span className="text-slate-600">
                            {d.highlight ? ' —— ' : ''}
                            {d.suggestion}
                          </span>
                        )}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </Chapter>
    </div>
  )
}
