import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Sprout, Sparkles, Check, ArrowRight } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchReportList, fetchReportDetail } from '@/api/report'
import { updateProject } from '@/api/growthLog'
import { refineProfileProject } from '@/api/profile'

interface DiagnosisItem {
  source: string
  source_type: 'resume' | 'growth_log'
  source_id: number | string
  current_text: string
  status: 'pass' | 'needs_improvement'
  highlight: string
  issues: string[]
  suggestion: string
}

// —— 前端软校验：数字 / 长度>=30 / 含"负责|主导|..." ——
// 全通过才让按钮点亮，温和文案提示缺什么，不说"错误"
function validateDraft(text: string) {
  const trimmed = text.trim()
  const hasNumber = /\d/.test(trimmed)
  const hasLength = trimmed.length >= 30
  const hasAction = /负责|主导|实现|设计|构建|开发|优化|完成|搭建|重构/.test(trimmed)
  return {
    hasNumber,
    hasLength,
    hasAction,
    allPass: hasNumber && hasLength && hasAction,
  }
}

function buildHint(v: ReturnType<typeof validateDraft>) {
  const tips: string[] = []
  if (!v.hasNumber) tips.push('加一个具体数字会更有说服力哦')
  if (!v.hasLength) tips.push('再多写几句，让读者看清楚你做了什么')
  if (!v.hasAction) tips.push('写清你"负责/主导/实现"了哪一块')
  return tips
}

export function RefineSection() {
  const queryClient = useQueryClient()
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [savingKey, setSavingKey] = useState<string | null>(null)
  // 保存成功后进入"已焕新"状态，3s 后转为 dismissed 从列表淡出
  const [justSaved, setJustSaved] = useState<Record<string, boolean>>({})
  // 已 dismiss 的 key，用于从 needsFix 中过滤掉（直到下次「更新报告」刷新 diagnosis）
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const reportListQuery = useQuery({
    queryKey: ['report-list-for-refine'],
    queryFn: fetchReportList,
  })
  const latestReportId = reportListQuery.data?.[0]?.id
  const reportQuery = useQuery({
    queryKey: ['report-for-refine', latestReportId],
    queryFn: () => fetchReportDetail(latestReportId!),
    enabled: !!latestReportId,
  })

  const diagnosis = (reportQuery.data?.data?.diagnosis ?? []) as DiagnosisItem[]
  const needsFix = diagnosis.filter(d => d.status === 'needs_improvement')

  const saveMut = useMutation({
    mutationFn: async ({ item, text }: { item: DiagnosisItem; text: string }) => {
      if (item.source_type === 'growth_log') {
        // 成长档案项目：ProjectRecord.id 是稳定主键，按 id 更新
        await updateProject(Number(item.source_id), { description: text })
      } else {
        // 简历项目：按 current_text（原文）内容匹配，不依赖数组下标
        await refineProfileProject(item.current_text, text)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['growth-projects'] })
      queryClient.invalidateQueries({ queryKey: ['profile'] })
    },
  })

  const getKey = (it: DiagnosisItem) => `${it.source_type}-${it.source_id}`

  // 已焕新 3s 后：从 justSaved 移除 + 加入 dismissed（AnimatePresence 负责淡出）
  useEffect(() => {
    const keys = Object.keys(justSaved)
    if (keys.length === 0) return
    const timers = keys.map(k =>
      setTimeout(() => {
        setJustSaved(prev => {
          const n = { ...prev }
          delete n[k]
          return n
        })
        setDismissed(prev => {
          const n = new Set(prev)
          n.add(k)
          return n
        })
      }, 3000)
    )
    return () => { timers.forEach(clearTimeout) }
  }, [justSaved])

  if (!latestReportId || !reportQuery.data) {
    return (
      <div className="text-center py-16 text-[var(--ink-3)] text-[13px]">
        请先生成一份报告
      </div>
    )
  }

  // 已 dismiss 的条目彻底移出列表；处于 3s 焕新中的仍然保留（绿色态）
  const visible = needsFix.filter(it => !dismissed.has(getKey(it)))
  const remaining = visible.length

  if (needsFix.length === 0 || remaining === 0) {
    return (
      <div className="text-center py-16">
        <Check size={32} className="mx-auto mb-3 text-[var(--moss)]" />
        <p className="text-[14px] text-[var(--ink-1)] font-medium">档案已经很棒了</p>
        <p className="text-[12px] text-[var(--ink-3)] mt-1">所有项目描述都完整</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <Sparkles size={15} className="text-[var(--ember)]" />
        <p className="text-[13px] font-semibold text-[var(--ink-1)]">
          还有 {remaining} 个项目可以更亮眼
        </p>
      </div>

      <div className="space-y-4">
        <AnimatePresence mode="popLayout">
        {visible.map((item) => {
          const key = getKey(item)
          const draft = drafts[key] ?? ''
          const v = validateDraft(draft)
          const hints = buildHint(v)
          const isSaving = savingKey === key
          const isFresh = !!justSaved[key]

          return (
            <motion.div
              key={key}
              layout
              initial={{ opacity: 0, y: 4 }}
              animate={{
                opacity: 1,
                y: 0,
                // 焕新态：border 由 indigo 过渡到 emerald
              }}
              exit={{ opacity: 0, y: -8, transition: { duration: 0.4 } }}
              transition={{ duration: 0.3 }}
              className="rounded-md p-5 bg-[var(--bg-card)] border"
              style={{
                borderColor: isFresh
                  ? 'var(--moss)'
                  : 'var(--line)',
                boxShadow: isFresh
                  ? '0 1px 2px rgba(60,40,20,0.04), 0 4px 12px rgba(60,40,20,0.05)'
                  : '0 1px 2px rgba(60,40,20,0.03)',
                transition: 'border-color 0.4s ease, box-shadow 0.4s ease',
              }}
            >
              {/* —— 焕新成功态：覆盖式提示 —— */}
              {isFresh ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex items-center gap-2 py-2"
                >
                  <Check size={16} className="text-[var(--moss)]" />
                  <span className="text-[13px] font-medium text-[var(--moss)]">
                    已焕新 · {item.source}
                  </span>
                </motion.div>
              ) : (
                <>
                  {/* Header：只保留图标 + 项目名；删除 source tag 和"还差一点"tag */}
                  <div className="flex items-center gap-2 mb-3">
                    <Sprout size={14} className="text-[var(--chestnut)]" />
                    <span className="text-[13px] font-medium text-[var(--ink-1)]">
                      {item.source}
                    </span>
                  </div>

                  {/* 现在的样子 */}
                  <div className="mb-3">
                    <p className="text-[11px] text-[var(--ink-3)] mb-1">现在的样子</p>
                    <p className="text-[12px] text-[var(--ink-2)] px-3 py-2 rounded-md bg-[var(--bg-paper)] border border-[var(--line)] leading-relaxed">
                      {item.current_text}
                    </p>
                  </div>

                  {/* 让它更亮 ✨ —— 启发式，不是罪状清单 */}
                  {item.issues.length > 0 && (
                    <div className="mb-3">
                      <p className="text-[11px] text-[var(--ink-3)] mb-1 flex items-center gap-1">
                        让它更亮 <Sparkles size={10} className="text-[var(--ember)]" />
                      </p>
                      <ul className="text-[12px] text-[var(--ink-2)] space-y-1 pl-1">
                        {item.issues.map((iss, i) => (
                          <li key={i} className="flex gap-1.5">
                            <span className="text-[var(--chestnut)]">·</span>
                            <span>{iss}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* 别人怎么写 */}
                  {item.suggestion && (
                    <div className="mb-3">
                      <p className="text-[11px] text-[var(--ink-3)] mb-1">别人怎么写</p>
                      <p className="text-[12px] text-[var(--chestnut)] px-3 py-2 rounded-md bg-[var(--bg-paper)] border border-[var(--line)] leading-relaxed">
                        {item.suggestion}
                      </p>
                    </div>
                  )}

                  {/* 你来写 */}
                  <div className="mb-2">
                    <p className="text-[11px] text-[var(--ink-3)] mb-1">你来写</p>
                    <textarea
                      value={draft}
                      onChange={e => setDrafts(d => ({ ...d, [key]: e.target.value }))}
                      rows={3}
                      placeholder="填入真实的性能数据、成果数字、你的具体贡献..."
                      className="w-full text-[12px] text-[var(--ink-1)] bg-[var(--bg-paper)] border border-[var(--line)] rounded-md p-3 resize-none outline-none focus:border-[var(--moss)] leading-relaxed transition-colors duration-200"
                    />
                  </div>

                  {/* 校验提示 + CTA */}
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-[11px] text-[var(--ink-3)] flex-1 min-w-0">
                      {draft.trim().length === 0 ? (
                        <span className="text-[var(--ink-3)]">写下来的文字只会保存到你自己的档案</span>
                      ) : v.allPass ? (
                        <span className="text-[var(--moss)]">看起来很不错 ✨</span>
                      ) : (
                        <span className="text-[var(--ember)]">
                          {hints[0]}
                        </span>
                      )}
                    </div>
                    <button
                      disabled={!v.allPass || isSaving}
                      onClick={async () => {
                        setSavingKey(key)
                        try {
                          await saveMut.mutateAsync({ item, text: draft.trim() })
                          setJustSaved(prev => ({ ...prev, [key]: true }))
                          setDrafts(d => { const n = { ...d }; delete n[key]; return n })
                        } finally {
                          setSavingKey(null)
                        }
                      }}
                      className="flex-shrink-0 flex items-center gap-1.5 px-4 py-1.5 text-[12px] font-medium text-white bg-[var(--chestnut)] rounded-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[var(--ink-1)] transition-colors"
                    >
                      {isSaving ? '保存中...' : (
                        <>
                          <Sparkles size={12} />
                          让它亮起来
                          <ArrowRight size={12} />
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </motion.div>
          )
        })}
        </AnimatePresence>
      </div>

      <p className="text-center text-[11px] text-[var(--ink-3)] mt-6">
        保存后再次「更新报告」，这些项目会变为"通过"状态
      </p>
    </div>
  )
}
