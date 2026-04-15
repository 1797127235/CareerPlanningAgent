import { useState } from 'react'
import { Plus } from 'lucide-react'
import { Chapter, ChapterOpener } from '@/components/editorial'
import { EducationCard, InternshipCard, ProjectCard } from './cards'
import { EducationEdit, InternshipEdit, ProjectEdit } from './forms'
import { updateProfile } from '@/api/profiles'
import type { ProfileData, Education, Internship } from '@/types/profile'
import type { ProjectItem } from './cards/ProjectCard'

export function ProfileChapterI({ data, onRefresh }: { data: ProfileData; onRefresh: () => void }) {
  const profile = data.profile || {}
  const education = profile.education as Education | undefined
  const experienceYears = (profile.experience_years as number) || 0
  const internships = (profile.internships as Internship[]) || []
  const projects = (profile.projects || []) as Array<string | ProjectItem>

  const hasData = education?.school || internships.length > 0 || projects.length > 0
  const internshipCount = internships.length
  const projectCount = projects.length

  const [editingEdu, setEditingEdu] = useState(false)
  const [editingInternships, setEditingInternships] = useState(false)
  const [editingProjects, setEditingProjects] = useState(false)
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

  return (
    <Chapter
      numeral="I"
      label="WHERE YOU COME FROM"
      title={
        hasData
          ? `你在 ${education?.school || '…'}，学 ${education?.major || '…'}，已经走过 ${internshipCount} 段实习 + ${projectCount} 个项目。`
          : '先讲讲你从哪里来 —— 学校、专业、做过的事。'
      }
    >
      <ChapterOpener numeral="I" title={hasData ? '你从哪里来' : '你从哪里来'} />

      {/* 1.1 教育背景 */}
      <div className="mt-8">
        <h3 className="font-sans text-[13px] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-3">
          1.1 · 你在读哪里
        </h3>
        {education?.school ? (
          <p className="text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
            你在 {education.school} 学 {education.major || '…'}，
            {experienceYears > 0 ? `已有 ${experienceYears} 年经验。` : '目前还在积累经验的路上。'}
          </p>
        ) : (
          <p className="text-[var(--fs-body)] text-[var(--ink-3)] italic">还没有教育背景记录 —— 有也好，没有也行，这些都可以晚点补。</p>
        )}
        {editingEdu ? (
          <div className="mt-4">
            <EducationEdit
              education={education}
              saving={saving}
              onCancel={() => setEditingEdu(false)}
              onSave={async (edu) => {
                await save({ education: edu })
                setEditingEdu(false)
              }}
            />
          </div>
        ) : (
          <div className="mt-4">
            <EducationCard education={education} onEdit={() => setEditingEdu(true)} />
          </div>
        )}
      </div>

      {/* 1.2 实习 */}
      <div className="mt-10">
        <h3 className="font-sans text-[13px] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-3">
          1.2 · 你实习过哪些地方
        </h3>
        {editingInternships ? (
          <div className="mt-4">
            <InternshipEdit
              internships={internships}
              saving={saving}
              onCancel={() => setEditingInternships(false)}
              onSave={async (items) => {
                await save({ internships: items })
                setEditingInternships(false)
              }}
            />
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            {internships.length > 0 ? (
              internships.map((it, idx) => <InternshipCard key={idx} internship={it} />)
            ) : (
              <p className="text-[var(--fs-body)] text-[var(--ink-3)] italic">还没有实习记录 —— 如果有，加一段；没有也没关系。</p>
            )}
            <button
              onClick={() => setEditingInternships(true)}
              className="inline-flex items-center gap-1 text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]"
            >
              <Plus className="w-4 h-4" /> {internships.length > 0 ? '再加一段实习' : '加一段实习'}
            </button>
          </div>
        )}
      </div>

      {/* 1.3 项目 */}
      <div className="mt-10">
        <h3 className="font-sans text-[13px] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-3">
          1.3 · 你做过哪些项目
        </h3>
        {editingProjects ? (
          <div className="mt-4">
            <ProjectEdit
              projects={projects}
              saving={saving}
              onCancel={() => setEditingProjects(false)}
              onSave={async (items) => {
                await save({ projects: items })
                setEditingProjects(false)
              }}
            />
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            {projects.length > 0 ? (
              projects.map((p, idx) => <ProjectCard key={idx} project={p} onEdit={() => setEditingProjects(true)} />)
            ) : (
              <p className="text-[var(--fs-body)] text-[var(--ink-3)] italic">还没有项目记录 —— 哪怕是一个小工具，也值得记下来。</p>
            )}
            <button
              onClick={() => setEditingProjects(true)}
              className="inline-flex items-center gap-1 text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]"
            >
              <Plus className="w-4 h-4" /> {projects.length > 0 ? '再加一个项目' : '加一个项目'}
            </button>
          </div>
        )}
      </div>
    </Chapter>
  )
}
