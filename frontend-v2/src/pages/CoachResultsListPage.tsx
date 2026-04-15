import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listCoachResults } from '@/api/coach'
import { ResultListRow } from '@/components/coach-v2'
import { mockCoachResultsList } from '@/components/coach-v2/mockData'
import { Kicker } from '@/components/editorial'

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
      <div className="max-w-[720px] mx-auto px-6 md:px-12 lg:px-20 pb-32">
        <section className="pt-12 pb-8">
          <Kicker>ARCHIVE · 档案</Kicker>
          <h1 className="font-display font-medium text-[length:var(--fs-display-lg)] leading-[var(--lh-display)] tracking-tight text-[var(--ink-1)] max-w-[20ch]">
            你写过的分析
          </h1>
          <p className="mt-4 font-sans text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[58ch]">
            每一次诊断、每一次复盘，都在这里。点开继续读，或者删掉。
          </p>
        </section>

        {isLoading ? (
          <p className="font-serif italic text-[length:var(--fs-body-lg)] text-[var(--ink-2)]">
            正在整理档案…
          </p>
        ) : items.length === 0 ? (
          <div className="py-12">
            <p className="font-sans text-[length:var(--fs-body-lg)] text-[var(--ink-2)]">
              还没有任何分析结果。
            </p>
            <Link
              to="/coach/chat"
              className="inline-block mt-4 text-[var(--chestnut)] hover:opacity-90 underline underline-offset-4 text-[length:var(--fs-body)]"
            >
              去聊聊 →
            </Link>
          </div>
        ) : (
          <section className="space-y-5">
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
