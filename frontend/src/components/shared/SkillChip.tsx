import { Check, X } from 'lucide-react'

interface SkillChipProps {
  name: string
  matched: boolean
}

export function SkillChip({ name, matched }: SkillChipProps) {
  return (
    <span
      className={`chip inline-flex items-center gap-1 !py-1 !px-2.5 text-[13px] font-medium ${
        matched ? 'text-green-700' : 'text-red-700'
      }`}
    >
      {matched ? (
        <Check className="w-3.5 h-3.5" />
      ) : (
        <X className="w-3.5 h-3.5" />
      )}
      {name}
    </span>
  )
}
