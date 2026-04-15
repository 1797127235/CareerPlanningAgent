import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listCoachResults } from '@/api/coach'
import { ResultListRow } from '@/components/coach-v2'
import { mockCoachResultsList } from '@/components/coach-v2/mockData'

export default function CoachResultsListPage() {
  const [searchParams] = useSearchParams()
  const isMock = searchParams.get('mock') === '1'

  const { data, isLoading } = useQuery({
    queryKey: ['coach-results'],
    queryFn: listCoachResults,
    enabled: !isMock,
    initialData: isMock ? mockCoachResultsList : undefined,
  })

  const items = data || []

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <div className="max-w-[860px] mx-auto px-[var(--space-6)] md:px-[var(--space-7)] py-[var(--space-6)]">
        <section className="mb-[var(--space-5)]">
          <h1 className="text-[var(--text-2xl)] font-semibold text-[var(--ink-1)] tracking-tight">
            你写过的分析
          </h1>
          <p className="mt-2 text-[var(--text-base)] text-[var(--ink-2)] max-w-[58ch]">
            每一次诊断、每一次复盘，都在这里。点开继续读，或者删掉。
          </p>
        </section>

        {isLoading ? (
          <p className="font-serif italic text-[var(--text-lg)] text-[var(--ink-2)]">
            正在整理档案…
          </p>
        ) : items.length === 0 ? (
          <div className="py-8">
            <p className="text-[var(--text-base)] text-[var(--ink-2)]">
              还没有任何分析结果。
            </p>
            <Link
              to="/coach/chat"
              className="inline-block mt-3 text-[var(--chestnut)] hover:opacity-90 underline underline-offset-4 text-[var(--text-base)]"
            >
              去聊聊 →
            </Link>
          </div>
        ) : (
          <section className="space-y-4">
            {items.map((item) => (
              <div key={item.id}>
                <ResultListRow item={item} />
              </div>
            ))}
          </section>
        )}
      </div>
    </main>
  )
}
