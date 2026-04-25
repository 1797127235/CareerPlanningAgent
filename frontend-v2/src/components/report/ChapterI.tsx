import { useState } from 'react'
import { Pencil } from 'lucide-react'
import type { ReportV2Data } from '@/api/report'
import { ChapterOpener, Chapter, DropCap, PullQuote } from './index'
import { splitParagraphs } from './reportUtils'

interface ChapterIProps {
  data: ReportV2Data
  onSave?: (text: string) => Promise<void>
  saving?: boolean
}

export function ChapterI({ data, onSave, saving }: ChapterIProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  const narrative = data.narrative || ''
  const paragraphs = splitParagraphs(narrative, 2, 3)

  const fallback = [
    `你的履历里已经有${data.target.label}方向的技术痕迹，项目经历和技能标签正在慢慢拼成一条路径。`,
    `这些描述目前停留在"做了什么"，下次如果加上"做成了什么"的具体数字，会更有说服力。`,
    `现有项目里再补一些量化数据和技术文档，面试时会更容易被看到。`,
  ]

  const paras = paragraphs.length >= 2 ? paragraphs : fallback

  const diag = data.diagnosis || []
  const quote =
    diag.find((d) => d.status === 'pass' && d.current_text?.length > 10) ??
    diag.find((d) => d.current_text?.length > 10)
  const quoteText = quote
    ? quote.current_text.length > 60
      ? quote.current_text.slice(0, 60) + '…'
      : quote.current_text
    : null
  const quoteSource = quote?.source ?? '你的成长轨迹'

  // Hardcoded thematic headline (consistent with Chapter II/III/IV style) —
  // previously this was extracted from the body's first sentence, which
  // duplicated what the DropCap paragraph below showed.
  const headline = '先把你自己看清楚。'

  const enterEdit = () => {
    setDraft(narrative || paras.join('\n\n'))
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
      // keep draft; parent surfaces the error
    }
  }

  return (
    <div id="chapter-1">
      <ChapterOpener numeral="I" label="你是谁" headline={headline} />
      <Chapter>
        {editing ? (
          <div className="mt-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={Math.max(6, Math.min(20, draft.split('\n').length + 2))}
              className="w-full p-4 text-[17px] leading-[1.8] text-slate-800 bg-slate-50 border border-slate-200 rounded-sm focus:outline-none focus:border-slate-400 resize-y"
              placeholder="写下这一章的叙事。空行分段。"
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
            <DropCap>{paras[0]}</DropCap>
            {paras[1] && <p className="mt-5">{paras[1]}</p>}
            {paras[2] && <p className="mt-5">{paras[2]}</p>}
            {quoteText ? (
              <PullQuote attribution={`摘自你的「${quoteSource}」`}>{quoteText}</PullQuote>
            ) : (
              <PullQuote>先把自己正在做的记下来 —— 回看时你会看到自己走了多远。</PullQuote>
            )}
            {paras[3] && <p className="mt-5">{paras[3]}</p>}
            {paras[4] && <p className="mt-5">{paras[4]}</p>}
          </>
        )}
      </Chapter>
    </div>
  )
}
