import { useState } from 'react'
import { Plus } from 'lucide-react'
import { Chapter, ChapterOpener, DropCap } from '@/components/editorial'
import { SkillChips, KnowledgeChips } from './cards'
import { SkillEdit } from './forms'
import { updateProfile } from '@/api/profiles'
import type { ProfileData, Skill } from '@/types/profile'

export function ProfileChapterII({ data, onRefresh }: { data: ProfileData; onRefresh: () => void }) {
  const profile = data.profile || {}
  const skills = (profile.skills as Skill[]) || []
  const areas = (profile.knowledge_areas as string[]) || []
  const hasData = skills.length > 0 || areas.length > 0

  const [addingSkill, setAddingSkill] = useState(false)
  const [saving, setSaving] = useState(false)

  const save = async (patch: Record<string, unknown>) => {
    setSaving(true)
    try {
      await updateProfile({ profile: { ...profile, ...patch }, quality: null })
      await onRefresh()
    } finally {
      setSaving(false)
    }
  }

  const handleAddSkill = async (s: Skill) => {
    const next = [...skills, s]
    await save({ skills: next })
    setAddingSkill(false)
  }

  const handleDeleteSkill = async (s: Skill) => {
    const next = skills.filter((x) => x.name !== s.name)
    await save({ skills: next })
  }

  const handleDeleteArea = async (a: string) => {
    const next = areas.filter((x) => x !== a)
    await save({ knowledge_areas: next })
  }

  return (
    <Chapter
      numeral="II"
      label="WHAT YOU KNOW"
      title={
        hasData
          ? `你提到了 ${skills.length} 个技能，${areas.length} 个知识领域。`
          : '技能和知识，加一个是一个 —— 以后 Growth Log 会帮你记住新学到的。'
      }
    >
      <ChapterOpener numeral="II" title="你会什么" />

      <div className="mt-8">
        <h3 className="font-sans text-[13px] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-3">
          2.1 · 技能清单
        </h3>
        <DropCap>下面是你告诉系统的技能，以及你对自己熟练度的估计。随时可以调整。</DropCap>
        <div className="mt-6">
          <SkillChips skills={skills} onDelete={handleDeleteSkill} />
        </div>
        {addingSkill ? (
          <div className="mt-4">
            <SkillEdit onAdd={handleAddSkill} onCancel={() => setAddingSkill(false)} saving={saving} />
          </div>
        ) : (
          <button
            onClick={() => setAddingSkill(true)}
            className="mt-4 inline-flex items-center gap-1 text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]"
          >
            <Plus className="w-4 h-4" /> 加一个技能
          </button>
        )}
      </div>

      <div className="mt-10">
        <h3 className="font-sans text-[13px] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-3">
          2.2 · 知识领域
        </h3>
        <div className="mt-2">
          <KnowledgeChips areas={areas} onDelete={handleDeleteArea} />
        </div>
        <button
          onClick={() => {
            const val = window.prompt('输入要添加的知识领域（多个可用顿号分隔）：')
            if (!val) return
            const next = [...new Set([...areas, ...val.split(/[,，、\s]+/).map((s) => s.trim()).filter(Boolean)])]
            save({ knowledge_areas: next })
          }}
          className="mt-4 inline-flex items-center gap-1 text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]"
        >
          <Plus className="w-4 h-4" /> 加一个领域
        </button>
      </div>
    </Chapter>
  )
}
