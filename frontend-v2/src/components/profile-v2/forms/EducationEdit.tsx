import { useState } from 'react'
import type { Education } from '@/types/profile'

export function EducationEdit({
  education,
  onSave,
  onCancel,
  saving,
}: {
  education?: Education
  onSave: (data: Education) => void
  onCancel: () => void
  saving?: boolean
}) {
  const [school, setSchool] = useState(education?.school || '')
  const [major, setMajor] = useState(education?.major || '')
  const [degree, setDegree] = useState(education?.degree || '')

  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--bg-card)] p-4 md:p-5">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <input
          value={school}
          onChange={(e) => setSchool(e.target.value)}
          placeholder="学校"
          className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
        />
        <input
          value={major}
          onChange={(e) => setMajor(e.target.value)}
          placeholder="专业"
          className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
        />
        <input
          value={degree}
          onChange={(e) => setDegree(e.target.value)}
          placeholder="学位"
          className="w-full px-3 py-2 rounded-md bg-[var(--bg-paper)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] border border-[var(--line)] focus:outline-none focus:border-[var(--chestnut)]/50 text-[13px]"
        />
      </div>
      <div className="mt-4 flex items-center gap-3">
        <button
          disabled={saving}
          onClick={() => onSave({ school: school.trim(), major: major.trim(), degree: degree.trim() })}
          className="px-4 py-2 rounded-full bg-[var(--chestnut)] text-white text-[13px] font-medium hover:opacity-90 disabled:opacity-50"
        >
          {saving ? '保存中…' : '保存'}
        </button>
        <button
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 rounded-full text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] disabled:opacity-50"
        >
          取消
        </button>
      </div>
    </div>
  )
}
