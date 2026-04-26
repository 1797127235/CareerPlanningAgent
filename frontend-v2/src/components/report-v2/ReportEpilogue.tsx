export function ReportEpilogue({ generatedAt }: { generatedAt: string }) {
  const dateText = generatedAt
    ? new Date(generatedAt).toLocaleDateString('zh-CN')
    : new Date().toLocaleDateString('zh-CN')

  return (
    <section className="relative py-16 md:py-20 text-center">
      <div className="max-w-[46rem] mx-auto">
        <p
          className="text-[clamp(28px,2.8vw,38px)] leading-[1.72] text-[var(--ink-1)]"
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          这份报告不是一个诊断。是一个起点。你会变，它也会。
        </p>
        <p className="mt-5 font-sans text-[length:var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-2)]">
          每记一笔，这封信就会被重写一次——等你下次回来看看。
        </p>
        <p className="mt-10 font-mono text-[length:var(--fs-caption)] uppercase tracking-[0.18em] text-[var(--ink-3)]">
          generated at {dateText}
        </p>
      </div>
    </section>
  )
}
