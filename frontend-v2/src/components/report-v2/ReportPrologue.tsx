import { Kicker, SectionDivider } from '@/components/editorial'

export function ReportPrologue({ targetLabel }: { targetLabel: string }) {
  return (
    <section className="relative py-16 md:py-24">
      <SectionDivider numeral="·" />
      <div className="text-center">
        <Kicker>EDITORIAL · 编辑部来信</Kicker>
        <p className="mt-6 font-sans text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[58ch] mx-auto">
          这份报告是基于你的<strong className="text-[var(--ink-1)]">{targetLabel}</strong>
          方向履历写的。不是模板 — 每一段都在回答一个具体问题：
        </p>
        <p className="mt-4 font-sans text-[var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[58ch] mx-auto">
          你是谁？你能去哪？你们之间差什么？下一步怎么动？
        </p>
      </div>
    </section>
  )
}
