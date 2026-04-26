import { Kicker, SectionDivider } from '@/components/editorial'

export function ReportPrologue({ targetLabel }: { targetLabel: string }) {
  return (
    <section className="relative pt-2 md:pt-4 pb-8 md:pb-10">
      <div className="max-w-[46rem] mx-auto">
        <SectionDivider numeral="·" className="mt-0 mb-10 md:mb-12" />
        <div className="text-center">
          <Kicker className="mb-4">Editorial · 编辑部来信</Kicker>
          <p
            className="mx-auto max-w-[18ch] md:max-w-[22ch] text-[clamp(24px,2.8vw,34px)] leading-[1.72] text-[var(--ink-2)]"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            这份报告是基于你的 <strong className="font-semibold text-[var(--ink-1)]">{targetLabel}</strong> 方向履历写的。不是模板——每一段都在回答一个具体问题。
          </p>
          <p className="mt-6 font-sans text-[length:var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-3)] max-w-[44ch] mx-auto">
            你是谁？你能去哪？你们之间差什么？下一步怎么动？
          </p>
        </div>
      </div>
    </section>
  )
}
