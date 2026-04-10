import { Brain } from 'lucide-react'

const LEVEL_STYLE: Record<string, { bg: string; text: string }> = {
  '待发展': { bg: 'bg-slate-100', text: 'text-slate-600' },
  '基础': { bg: 'bg-blue-100', text: 'text-blue-700' },
  '良好': { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  '优秀': { bg: 'bg-amber-100', text: 'text-amber-700' },
}

const DIM_LABEL: Record<string, string> = {
  communication: '沟通能力',
  learning: '学习能力',
  collaboration: '协作能力',
  innovation: '创新能力',
  resilience: '抗压能力',
}

interface SoftSkills {
  _version?: number
  communication?: { score: number; level: string; advice: string } | null
  learning?: { score: number; level: string; advice: string } | null
  collaboration?: { score: number; level: string; advice: string } | null
  innovation?: { score: number; level: string; advice: string } | null
  resilience?: { score: number; level: string; advice: string } | null
}

interface Props {
  softSkills: SoftSkills | undefined
  onStartAssessment?: () => void
}

export default function SoftSkillsCard({ softSkills, onStartAssessment }: Props) {
  const isV2 = softSkills?._version === 2
  const dims = ['communication', 'learning', 'collaboration', 'innovation', 'resilience'] as const
  const hasData = isV2 && dims.some((d) => softSkills?.[d] != null)

  // Not assessed or old version
  if (!hasData) {
    return (
      <div className="glass p-5">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-4 h-4 text-[var(--blue)]" />
          <h3 className="text-[14px] font-semibold text-slate-700">软技能画像</h3>
        </div>
        <p className="text-[13px] text-slate-500 mb-3">
          {isV2 ? '完成情境评估后，这里将展示你的软技能画像' : '评估系统已升级，请重新测评'}
        </p>
        {onStartAssessment && (
          <button
            onClick={onStartAssessment}
            className="text-[13px] font-semibold text-[var(--blue)] hover:underline cursor-pointer"
          >
            去评估
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="glass p-5">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-4 h-4 text-[var(--blue)]" />
        <h3 className="text-[14px] font-semibold text-slate-700">软技能画像</h3>
      </div>
      <div className="space-y-3">
        {dims.map((key) => {
          const dim = softSkills?.[key]
          if (!dim) return null
          const style = LEVEL_STYLE[dim.level] || LEVEL_STYLE['待发展']
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="text-[13px] text-slate-600 w-16 shrink-0">{DIM_LABEL[key]}</span>
              <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-lg ${style.bg} ${style.text}`}>
                {dim.level}
              </span>
            </div>
          )
        })}
      </div>
      {onStartAssessment && (
        <button
          onClick={onStartAssessment}
          className="mt-4 text-[12px] text-slate-400 hover:text-[var(--blue)] transition-colors cursor-pointer"
        >
          重新评估
        </button>
      )}
    </div>
  )
}
