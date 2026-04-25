import { useState } from 'react'
import { Pencil } from 'lucide-react'
import type { ReportV2Data } from '@/api/report'
import { ChapterOpener, Chapter, DropCap } from './index'
import { splitParagraphs } from './reportUtils'

interface ChapterIIProps {
  data: ReportV2Data
  onSave?: (text: string) => Promise<void>
  saving?: boolean
}

export function ChapterII({ data, onSave, saving }: ChapterIIProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  const override = data.chapter_narratives?.['chapter-2']
  const baseObs = data.career_alignment?.observations ?? ''
  const proseText = (override ?? baseObs).trim()
  const paras = splitParagraphs(proseText, 2, 3)

  const alignments = (data.career_alignment?.alignments ?? []).slice(0, 3)

  const marketBits: string[] = []
  if (data.market?.salary_p50)
    marketBits.push(`薪资 p50 ¥${data.market.salary_p50.toLocaleString()}`)
  if (data.market?.timing_label) marketBits.push(data.market.timing_label)
  if (data.market?.demand_change_pct != null) {
    const sign = data.market.demand_change_pct >= 0 ? '+' : ''
    marketBits.push(`需求 ${sign}${data.market.demand_change_pct}%`)
  }

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
      /* keep draft for retry */
    }
  }

  return (
    <div id="chapter-2">
      <ChapterOpener
        numeral="II"
        label="你能去哪"
        headline={`在${data.target.label}方向上，你还能走多远。`}
      />
      <Chapter>
        {editing ? (
          <div className="mt-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={Math.max(6, Math.min(20, draft.split('\n').length + 2))}
              className="w-full p-4 text-[17px] leading-[1.8] text-slate-800 bg-slate-50 border border-slate-200 rounded-sm focus:outline-none focus:border-slate-400 resize-y"
              placeholder="写下你对这个方向的理解。空行分段。"
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
            {paras.length === 0 ? (
              <p className="text-[17px] leading-[1.8] text-slate-500">
                关于这个方向的整体判断暂时还没有生成。点右上角「编辑」可以自己写，或点上方「再生成」重跑。
              </p>
            ) : (
              <>
                <DropCap>{paras[0]}</DropCap>
                {paras.slice(1).map((p, i) => (
                  <p key={i} className="mt-5">
                    {p}
                  </p>
                ))}
              </>
            )}
          </>
        )}

        {alignments.length > 0 && (
          <div className="mt-10">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-4">
              与你的吻合度
            </p>
            <div className="space-y-5">
              {alignments.map((a) => (
                <div key={a.node_id} className="flex items-baseline gap-5">
                  <span className="text-[26px] font-extrabold tabular-nums text-slate-900 w-14 shrink-0 leading-none">
                    {a.score}
                  </span>
                  <div className="flex-1">
                    <p className="text-[15px] font-semibold text-slate-900">{a.label}</p>
                    {a.evidence && (
                      <p className="text-[13px] text-slate-500 mt-1 leading-relaxed">{a.evidence}</p>
                    )}
                    {a.gap && <p className="text-[12px] text-slate-400 mt-1">差距：{a.gap}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(data.market_narrative || marketBits.length > 0) && (
          <div className="mt-10 pt-5 border-t border-slate-200">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-2">
              市场信号
            </p>
            {data.market_narrative ? (
              <p className="text-[15px] text-slate-700 leading-relaxed">{data.market_narrative}</p>
            ) : (
              <p className="text-[14px] text-slate-700 tabular-nums">{marketBits.join(' · ')}</p>
            )}
          </div>
        )}
      </Chapter>
    </div>
  )
}
