import { useState } from 'react'
import { Chapter, ChapterOpener } from '@/components/editorial'
import { SoftSkillRow, SjtCta } from './cards'
import type { ProfileData } from '@/types/profile'

const sjtDims = ['communication', 'learning', 'collaboration', 'innovation', 'resilience'] as const

export function ProfileChapterIII({
  data,
  onStartSjt,
}: {
  data: ProfileData
  onStartSjt: () => void
}) {
  const softSkills = data.profile?.soft_skills as Record<string, { score?: number; level?: string; advice?: string; evidence?: string }> | undefined
  const hasSjt = softSkills?._version === 2 && sjtDims.some((d) => softSkills[d] != null)
  const topDim = sjtDims.find((d) => softSkills?.[d]?.level === 'high') || sjtDims.find((d) => softSkills?.[d])
  const topName = topDim
    ? ({ communication: '沟通表达', learning: '学习成长', collaboration: '团队协作', innovation: '创新思维', resilience: '抗压韧性' } as Record<string, string>)[topDim]
    : ''

  return (
    <Chapter
      numeral="III"
      label="HOW YOU WORK"
      title={
        hasSjt
          ? `你做事的方式里，最突出的是 ${topName}。`
          : '想知道你在团队里怎么做事吗？3 分钟小测。'
      }
    >
      <ChapterOpener numeral="III" title="你是怎样的人" />

      <div className="mt-8">
        <h3 className="font-sans text-[13px] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-3">
          3.1 · 软技能画像
        </h3>
        {hasSjt ? (
          <>
            <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">这是系统根据你的自评给出的观察，不是打分，只是一种描述方式。</p>
            <div className="mt-6">
              {sjtDims.map((d) => {
                const info = softSkills[d]
                if (!info) return null
                return (
                  <SoftSkillRow
                    key={d}
                    dimKey={d}
                    level={info.level}
                    advice={info.advice}
                    evidence={info.evidence}
                  />
                )
              })}
            </div>
          </>
        ) : (
          <p className="text-[length:var(--fs-body)] text-[var(--ink-3)] italic">还没有软技能评估 —— 有兴趣的话可以做做看，没有标准答案。</p>
        )}
      </div>

      <div className="mt-10">
        <h3 className="font-sans text-[13px] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-3">
          3.2 · 情境判断（SJT）
        </h3>
        {!hasSjt ? (
          <SjtCta onStart={onStartSjt} />
        ) : (
          <p className="text-[length:var(--fs-body)] text-[var(--ink-2)]">你已经完成过情境判断测评了。如果想重新测，可以回到原页面操作。</p>
        )}
      </div>
    </Chapter>
  )
}
