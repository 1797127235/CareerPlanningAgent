import {
  Chapter,
  ChapterOpener,
  SectionDivider,
  PaperCard,
  DropCap,
  PullQuote,
  Kicker,
} from '@/components/editorial'

export default function DemoPage() {
  return (
    <main className="min-h-screen px-6 md:px-12 lg:px-20">
      {/* ChapterOpener */}
      <section className="py-12">
        <ChapterOpener numeral="I" title="晨光编辑体" />
      </section>

      {/* Kicker */}
      <section className="py-8">
        <Kicker>Component Showcase · 组件展示</Kicker>
        <p className="text-[var(--ink-2)] max-w-[68ch]">
          下面是 7 个 editorial 原子组件的实例演示，用于验证 v2.0 视觉系统的正确性。
        </p>
      </section>

      {/* Chapter */}
      <Chapter
        numeral="II"
        label="章节容器"
        title="Chapter 组件"
        intro="这是一个章节容器组件，带有渐入动画、章节编号和导语。它替代了 v1 中的 version 标记，作为 v2 页面结构的核心原子。"
      >
        <PaperCard>
          <p className="text-[var(--ink-2)]">
            Chapter 内部可以嵌套 PaperCard、PullQuote、DropCap 等任意组件。
          </p>
        </PaperCard>
      </Chapter>

      {/* SectionDivider */}
      <SectionDivider numeral="§" />

      {/* DropCap */}
      <section className="py-12 max-w-[68ch]">
        <h3 className="font-display text-[var(--fs-display-md)] text-[var(--ink-1)] mb-6">DropCap 首字下沉</h3>
        <DropCap>晨光编辑体的设计理念源于传统纸质杂志的阅读体验，通过温暖的色调、优雅的衬线字体和细腻的纸感纹理，营造出一种沉静而有力的信息呈现方式。</DropCap>
        <div className="mt-8">
          <DropCap>The morning light editorial system draws inspiration from classical print magazines, using warm palettes, elegant serifs, and subtle paper grain to create a calm yet powerful reading experience.</DropCap>
        </div>
      </section>

      {/* PullQuote */}
      <PullQuote attribution="Editorial Team">
        设计不是装饰，而是让信息更容易被理解的秩序。
      </PullQuote>

      {/* PaperCard variations */}
      <section className="py-12 grid gap-6 md:grid-cols-2">
        <PaperCard>
          <Kicker>PaperCard · 基础</Kicker>
          <p className="text-[var(--ink-2)] mt-2">
            纸感卡片基础容器，带有柔和阴影和微妙的背景色变化。
          </p>
        </PaperCard>
        <PaperCard>
          <Kicker>PaperCard · 嵌套</Kicker>
          <p className="text-[var(--ink-2)] mt-2">
            可以放置任何内容，是构建信息模块的通用容器。
          </p>
        </PaperCard>
      </section>

      {/* ChapterOpener again */}
      <section className="py-12">
        <ChapterOpener numeral="III" title="The End" />
      </section>
    </main>
  )
}
