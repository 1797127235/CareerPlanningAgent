import { PaperCard } from '@/components/editorial'

export default function DemoPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <PaperCard className="max-w-sm">
        <h1 className="font-display text-[length:var(--fs-display-lg)]">Demo</h1>
        <p className="mt-2 text-[length:var(--fs-body)] text-[var(--ink-2)]">
          PaperCard with warm shadow
        </p>
      </PaperCard>
    </main>
  )
}
