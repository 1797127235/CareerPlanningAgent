export function ReportEpilogue({ generatedAt }: { generatedAt: string }) {
  const dateText = generatedAt
    ? new Date(generatedAt).toLocaleDateString('zh-CN')
    : new Date().toLocaleDateString('zh-CN')

  return (
    <section className="relative py-24 md:py-32 text-center">
      <div className="max-w-[58ch] mx-auto">
        <p className="font-sans text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
          这份报告不是一个诊断。是一个起点。你会变，它也会。
        </p>
        <p className="mt-4 font-sans text-[length:var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-2)]">
          每记一笔，这封信就会被重写一次 — 等你下次回来看。
        </p>
        <p className="mt-12 font-mono text-[length:var(--fs-caption)] text-[var(--ink-3)]">
          generated at {dateText}
        </p>
      </div>
    </section>
  )
}
