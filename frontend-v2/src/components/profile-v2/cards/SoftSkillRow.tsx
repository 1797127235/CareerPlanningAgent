const DIM_NAME: Record<string, string> = {
  communication: '沟通表达',
  learning: '学习成长',
  collaboration: '团队协作',
  innovation: '创新思维',
  resilience: '抗压韧性',
}

const LEVEL_TEXT: Record<string, string> = {
  high: '明显',
  medium: '清楚',
  low: '在路上',
}

export function SoftSkillRow({
  dimKey,
  level,
  advice,
  evidence,
}: {
  dimKey: string
  level?: string
  advice?: string
  evidence?: string
}) {
  const name = DIM_NAME[dimKey] || dimKey
  const levelText = LEVEL_TEXT[level || ''] || level || ''
  return (
    <div className="py-4 border-b border-[var(--line)] last:border-0">
      <div className="flex items-baseline gap-3 mb-1">
        <span className="font-sans text-[var(--text-lg)] font-medium text-[var(--ink-1)]">
          {name}
        </span>
        {levelText && (
          <span className="text-[var(--text-xs)] font-semibold text-[var(--chestnut)]">
            · {levelText}
          </span>
        )}
      </div>
      {advice && (
        <p className="text-[var(--text-base)] text-[var(--ink-2)] leading-[var(--lh-body-zh)]">
          {advice}
        </p>
      )}
      {evidence && (
        <p className="mt-2 font-serif italic text-[var(--text-base)] text-[var(--chestnut)]">
          {evidence}
        </p>
      )}
    </div>
  )
}
