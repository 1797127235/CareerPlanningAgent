import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Upload, PenLine } from 'lucide-react'
import { useProfileData, type ManualProfilePayload } from '@/hooks/useProfileData'
import { useResumeUpload } from '@/hooks/useResumeUpload'
import { setProfileName, updateProfile } from '@/api/profiles'
import { fetchRecommendations, type Recommendation as ApiRecommendation } from '@/api/recommendations'
import { Block, BlockGrid, Tooltip, useToast } from '@/components/ui'
import { GLOSSARY } from '@/lib/glossary'
import {
  EducationCard,
  InternshipCard,
  ProjectCard,
  SkillChips,
  KnowledgeChips,
  SoftSkillRow,
  SjtCta,
  GoalCard,
  RecommendationCard,
} from '@/components/profile-v2/cards'
import {
  EducationEdit,
  InternshipEdit,
  ProjectEdit,
  SkillEdit,
} from '@/components/profile-v2/forms'
import { SjtQuiz } from '@/components/profile-v2/SjtQuiz'
import { ManualProfileForm } from '@/components/profile-v2/ManualProfileForm'
import { UploadCta } from '@/components/profile-v2/UploadCta'
import { mockProfileData } from '@/components/profile-v2/mockData'
import type { ProfileData, Education, Internship, Skill } from '@/types/profile'
import type { ProjectItem } from '@/components/profile-v2/cards/ProjectCard'

function useRecommendations(hasProfile: boolean) {
  const [recs, setRecs] = useState<ApiRecommendation[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!hasProfile) return
    setLoading(true)
    fetchRecommendations(6)
      .then((res) => setRecs(res.recommendations || []))
      .catch(() => setRecs([]))
      .finally(() => setLoading(false))
  }, [hasProfile])

  return { recs, loading }
}

const sjtDims = ['communication', 'learning', 'collaboration', 'innovation', 'resilience'] as const

const EASE_OUT = [0.22, 1, 0.36, 1] as const
const PAGE_FADE = { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.15, ease: EASE_OUT } }
const MODAL_BACKDROP = { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: 0.15 } }
const MODAL_CARD = {
  initial: { opacity: 0, scale: 0.96, y: 8 },
  animate: { opacity: 1, scale: 1, y: 0 },
  exit: { opacity: 0, scale: 0.96, y: 8 },
  transition: { duration: 0.2, ease: EASE_OUT },
}

export default function ProfilePage() {
  const [searchParams] = useSearchParams()
  const isMock = searchParams.get('mock') === '1'
  const { toast } = useToast()

  const { profile, loading, loadError, loadProfile, savingEdit, handleSaveEdit } = useProfileData(!isMock)
  const { uploading, uploadStep, uploadError, justUploaded, fileInputRef, triggerFileDialog, onFileSelected } = useResumeUpload(loadProfile)

  const [showManual, setShowManual] = useState(false)
  const [sjtOpen, setSjtOpen] = useState(false)
  const [showNamePrompt, setShowNamePrompt] = useState(false)
  const [pendingName, setPendingName] = useState('')
  const namePromptShown = useRef(false)

  const data = isMock ? mockProfileData : profile
  const hasProfile = isMock
    ? true
    : !!(data?.profile?.skills?.length || data?.profile?.knowledge_areas?.length || data?.profile?.projects?.length || data?.profile?.internships?.length || data?.profile?.education?.school || data?.name)

  const { recs } = useRecommendations(hasProfile && !isMock)
  const recommendations = isMock
    ? [
        { role_id: 'backend-engineer', label: '后端开发工程师', reason: '你的 Python 和数据库经验很适合这个方向' },
        { role_id: 'data-analyst', label: '数据分析师', reason: 'SQL 基础加上项目中的数据处理经历是不错的起点' },
        { role_id: 'ai-engineer', label: 'AI 工程师', reason: '对 LangChain 有兴趣，可以继续补深度学习' },
      ]
    : recs

  useEffect(() => {
    if (justUploaded && !loading && hasProfile && !isMock && !data?.name && !namePromptShown.current) {
      namePromptShown.current = true
      setPendingName('')
      setShowNamePrompt(true)
    }
  }, [justUploaded, loading, hasProfile, data?.name, isMock])

  const handleNameConfirm = () => {
    if (!pendingName.trim()) return
    setShowNamePrompt(false)
    setProfileName(pendingName.trim())
      .then(() => loadProfile())
      .catch(console.error)
  }

  const sectionsCompleted = [
    !!data?.name,
    !!data?.profile?.education?.school,
    ((data?.profile?.internships?.length ?? 0) > 0) || ((data?.profile?.projects?.length ?? 0) > 0),
    (data?.profile?.skills?.length ?? 0) > 0,
    Object.keys((data?.profile?.soft_skills as Record<string, unknown>) ?? {}).filter((k) => k !== '_version').length > 0,
    (data?.career_goals?.length ?? 0) > 0,
  ].filter(Boolean).length

  const daysSince = data?.created_at
    ? Math.max(1, Math.floor((Date.now() - new Date(data.created_at).getTime()) / (1000 * 60 * 60 * 24)))
    : 1

  // Edit states
  const [editingEdu, setEditingEdu] = useState(false)
  const [editingInternships, setEditingInternships] = useState(false)
  const [editingProjects, setEditingProjects] = useState(false)
  const [addingSkill, setAddingSkill] = useState(false)
  const [saving, setSaving] = useState(false)

  const profileObj = data?.profile || {}
  const education = profileObj.education as Education | undefined
  const experienceYears = (profileObj.experience_years as number) || 0
  const internships = (profileObj.internships as Internship[]) || []
  const projects = (profileObj.projects || []) as Array<string | ProjectItem>
  const skills = (profileObj.skills as Skill[]) || []
  const areas = (profileObj.knowledge_areas as string[]) || []
  const softSkills = data?.profile?.soft_skills as Record<string, { score?: number; level?: string; advice?: string; evidence?: string }> | undefined
  const hasSjt = softSkills?._version === 2 && sjtDims.some((d) => softSkills[d] != null)
  const goal = data?.career_goals?.find((g) => g.is_primary) || data?.career_goals?.[0]
  const hasGoal = !!goal && !!goal.target_node_id
  const [showAllRecs, setShowAllRecs] = useState(false)
  const visibleRecs = showAllRecs ? recommendations : recommendations.slice(0, 3)

  const savePatch = async (patch: Record<string, unknown>) => {
    setSaving(true)
    try {
      await updateProfile({ profile: { ...profileObj, ...patch }, quality: null })
      await loadProfile()
      toast('已保存')
    } finally {
      setSaving(false)
    }
  }

  const handleAddSkill = async (s: Skill) => {
    const next = [...skills, s]
    await savePatch({ skills: next })
    setAddingSkill(false)
  }

  const handleDeleteSkill = async (s: Skill) => {
    const next = skills.filter((x) => x.name !== s.name)
    await savePatch({ skills: next })
  }

  const handleDeleteArea = async (a: string) => {
    const next = areas.filter((x) => x !== a)
    await savePatch({ knowledge_areas: next })
  }

  if (loading && !isMock) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-[var(--space-5)]">
        <p className="font-serif italic text-[var(--text-lg)] text-[var(--ink-2)]">正在打开档案…</p>
      </main>
    )
  }

  if (loadError && !isMock) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-[var(--space-5)]">
        <div className="text-center max-w-md">
          <p className="text-[var(--text-lg)] text-[var(--ink-1)]">画像加载失败</p>
          <p className="mt-2 text-[var(--text-base)] text-[var(--ink-3)]">{loadError}</p>
          <button
            onClick={loadProfile}
            className="mt-5 inline-flex items-center px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-[var(--text-sm)] font-medium"
          >
            重试
          </button>
        </div>
      </main>
    )
  }

  if (showManual) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
        <div className="max-w-[860px] mx-auto px-[var(--space-6)] md:px-[var(--space-7)] py-[var(--space-6)]">
          <ManualProfileForm
            onSave={async (payload: ManualProfilePayload) => {
              await handleSaveEdit(payload)
              setShowManual(false)
            }}
            onCancel={() => setShowManual(false)}
            saving={savingEdit}
            initialData={
              data
                ? {
                    name: data.name || '',
                    education: {
                      degree: (data.profile?.education as { degree?: string })?.degree || '',
                      major: (data.profile?.education as { major?: string })?.major || '',
                      school: (data.profile?.education as { school?: string })?.school || '',
                    },
                    experience_years: (data.profile?.experience_years as number) || 0,
                    job_target: (data.profile?.job_target as string) || '',
                    skills: (data.profile?.skills as ManualProfilePayload['skills']) || [],
                    knowledge_areas: (data.profile?.knowledge_areas as string[]) || [],
                    projects: (data.profile?.projects as ManualProfilePayload['projects']) || [],
                    internships: (data.profile?.internships as ManualProfilePayload['internships']) || [],
                    certificates: (data.profile?.certificates as string[]) || [],
                    awards: (data.profile?.awards as string[]) || [],
                  }
                : undefined
            }
          />
        </div>
      </main>
    )
  }

  return (
    <motion.main {...PAGE_FADE} className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <input ref={fileInputRef} type="file" accept=".pdf,.doc,.docx,.txt" className="hidden" onChange={onFileSelected} />

      <div className="max-w-[860px] mx-auto px-[var(--space-6)] md:px-[var(--space-7)] py-[var(--space-6)]">
        {/* Header + Progress */}
        <section className="mb-[var(--space-5)]">
          {hasProfile ? (
            <>
              <h1 className="text-[var(--text-2xl)] font-semibold text-[var(--ink-1)] tracking-tight">
                我们已经认识 {daysSince} 天了
              </h1>
              <p className="mt-1 text-[var(--text-sm)] text-[var(--ink-3)] font-serif italic">
                最近更新于 {data?.updated_at ? data.updated_at.slice(0, 10) : '今天'}
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                {['名字', '教育', '经历', '技能', '软技能', '目标'].map((label, i) => {
                  const done = [
                    !!data?.name,
                    !!data?.profile?.education?.school,
                    ((data?.profile?.internships?.length ?? 0) > 0) || ((data?.profile?.projects?.length ?? 0) > 0),
                    (data?.profile?.skills?.length ?? 0) > 0,
                    Object.keys((data?.profile?.soft_skills as Record<string, unknown>) ?? {}).filter((k) => k !== '_version').length > 0,
                    (data?.career_goals?.length ?? 0) > 0,
                  ][i]
                  return (
                    <span
                      key={label}
                      className={[
                        'inline-flex items-center px-2.5 py-1 rounded-[var(--radius-pill)] text-[var(--text-xs)] border',
                        done ? 'bg-[var(--chestnut)] text-white border-[var(--chestnut)]' : 'bg-transparent text-[var(--ink-3)] border-[var(--line)]',
                      ].join(' ')}
                    >
                      {done ? '✓ ' : ''}{label}
                    </span>
                  )
                })}
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  onClick={triggerFileDialog}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full text-[var(--text-sm)] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] border border-[var(--line)] hover:bg-[var(--line)]/10 transition-[color,background-color] duration-200 active:scale-[0.98]"
                >
                  <Upload className="w-4 h-4" /> 重新上传简历
                </button>
                <button
                  onClick={() => setShowManual(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full text-[var(--text-sm)] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors duration-200 active:scale-[0.98]"
                >
                  <PenLine className="w-4 h-4" /> 手动补一笔
                </button>
              </div>
            </>
          ) : (
            <>
              <h1 className="text-[var(--text-2xl)] font-semibold text-[var(--ink-1)] tracking-tight">
                还没开始讲给我听
              </h1>
              <p className="mt-2 text-[var(--text-base)] text-[var(--ink-2)] max-w-[68ch]">
                这份档案只给系统看，不会给任何第三方。你可以传一份简历让系统自动提取，也可以先手动填几句，以后随时补。
              </p>
              <div className="mt-6 space-y-3 max-w-md">
                <UploadCta
                  step={uploadStep}
                  label="上传一份简历"
                  subLabel="PDF / Word / TXT，10MB 以内"
                  onClick={triggerFileDialog}
                />
                {uploadError && (
                  <div className="rounded-[var(--radius-md)] border border-red-200 bg-red-50 px-4 py-3 text-[var(--text-sm)] text-red-700">
                    {uploadError}
                  </div>
                )}
                <button
                  onClick={() => setShowManual(true)}
                  className="w-full text-left rounded-[var(--radius-md)] border border-[var(--line)] bg-[var(--bg-card)] px-5 py-4 hover:shadow-[var(--shadow-block)] transition-shadow"
                >
                  <p className="text-[var(--text-base)] font-medium text-[var(--ink-1)]">手动讲给我听</p>
                  <p className="text-[var(--text-sm)] text-[var(--ink-2)]">几个字就够了，不用一次填完</p>
                </button>
              </div>
            </>
          )}
        </section>

        {hasProfile && (
          <>
            {sjtOpen ? (
              <div className="mb-[var(--space-5)]">
                <SjtQuiz onComplete={() => { setSjtOpen(false); loadProfile() }} onCancel={() => setSjtOpen(false)} />
              </div>
            ) : (
              <BlockGrid className="mb-[var(--space-5)]">
                {/* Education & Experience */}
                <Block kicker="PROFILE" title="教育背景与经历" span={2}>
                  <div className="space-y-4">
                    <div>
                      <p className="text-[var(--text-xs)] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-2">教育</p>
                      {editingEdu ? (
                        <EducationEdit
                          education={education}
                          saving={saving}
                          onCancel={() => setEditingEdu(false)}
                          onSave={async (edu) => {
                            await savePatch({ education: edu })
                            setEditingEdu(false)
                          }}
                        />
                      ) : (
                        <>
                          {education?.school ? (
                            <p className="text-[var(--text-base)] text-[var(--ink-1)]">
                              {education.school} · {education.major || '…'} · {education.degree || '…'}
                              {experienceYears > 0 ? `（${experienceYears} 年经验）` : ''}
                            </p>
                          ) : (
                            <p className="text-[var(--text-sm)] text-[var(--ink-3)] italic">还没有教育背景记录</p>
                          )}
                          <EducationCard education={education} onEdit={() => setEditingEdu(true)} />
                        </>
                      )}
                    </div>

                    <div>
                      <p className="text-[var(--text-xs)] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-2">实习</p>
                      {editingInternships ? (
                        <InternshipEdit
                          internships={internships}
                          saving={saving}
                          onCancel={() => setEditingInternships(false)}
                          onSave={async (items) => {
                            await savePatch({ internships: items })
                            setEditingInternships(false)
                          }}
                        />
                      ) : (
                        <div className="space-y-3">
                          {internships.length > 0 ? (
                            internships.map((it, idx) => <InternshipCard key={idx} internship={it} />)
                          ) : (
                            <p className="text-[var(--text-sm)] text-[var(--ink-3)] italic">还没有实习记录</p>
                          )}
                          <button
                            onClick={() => setEditingInternships(true)}
                            className="inline-flex items-center gap-1 text-[var(--text-sm)] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors duration-200"
                          >
                            <Plus className="w-4 h-4" /> {internships.length > 0 ? '再加一段实习' : '加一段实习'}
                          </button>
                        </div>
                      )}
                    </div>

                    <div>
                      <p className="text-[var(--text-xs)] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-2">项目</p>
                      {editingProjects ? (
                        <ProjectEdit
                          projects={projects}
                          saving={saving}
                          onCancel={() => setEditingProjects(false)}
                          onSave={async (items) => {
                            await savePatch({ projects: items })
                            setEditingProjects(false)
                          }}
                        />
                      ) : (
                        <div className="space-y-3">
                          {projects.length > 0 ? (
                            projects.map((p, idx) => <ProjectCard key={idx} project={p} onEdit={() => setEditingProjects(true)} />)
                          ) : (
                            <p className="text-[var(--text-sm)] text-[var(--ink-3)] italic">还没有项目记录</p>
                          )}
                          <button
                            onClick={() => setEditingProjects(true)}
                            className="inline-flex items-center gap-1 text-[var(--text-sm)] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors duration-200"
                          >
                            <Plus className="w-4 h-4" /> {projects.length > 0 ? '再加一个项目' : '加一个项目'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </Block>

                {/* Skills */}
                <Block kicker="SKILLS" title="技能与知识">
                  <div className="space-y-4">
                    <div>
                      <p className="text-[var(--text-xs)] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-2">技能清单</p>
                      <SkillChips skills={skills} onDelete={handleDeleteSkill} />
                      {addingSkill ? (
                        <div className="mt-3">
                          <SkillEdit onAdd={handleAddSkill} onCancel={() => setAddingSkill(false)} saving={saving} />
                        </div>
                      ) : (
                        <button
                          onClick={() => setAddingSkill(true)}
                          className="mt-3 inline-flex items-center gap-1 text-[var(--text-sm)] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors duration-200"
                        >
                          <Plus className="w-4 h-4" /> 加一个技能
                        </button>
                      )}
                    </div>
                    <div>
                      <p className="text-[var(--text-xs)] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-2">知识领域</p>
                      <KnowledgeChips areas={areas} onDelete={handleDeleteArea} />
                      <button
                        onClick={() => {
                          const val = window.prompt('输入要添加的知识领域（多个可用顿号分隔）：')
                          if (!val) return
                          const next = [...new Set([...areas, ...val.split(/[,，、\s]+/).map((s) => s.trim()).filter(Boolean)])]
                          savePatch({ knowledge_areas: next })
                        }}
                        className="mt-3 inline-flex items-center gap-1 text-[var(--text-sm)] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors duration-200"
                      >
                        <Plus className="w-4 h-4" /> 加一个领域
                      </button>
                    </div>
                  </div>
                </Block>

                {/* Soft Skills */}
                <Block kicker="TRAITS" title="软技能画像">
                  {hasSjt ? (
                    <>
                      <p className="text-[var(--text-sm)] text-[var(--ink-2)] mb-3">这是系统根据你的自评给出的观察。</p>
                      <div>
                        {sjtDims.map((d) => {
                          const info = softSkills?.[d]
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
                    <>
                      <p className="text-[var(--text-sm)] text-[var(--ink-3)] italic mb-3">还没有软技能评估</p>
                      <div className="flex items-center gap-2">
                        <SjtCta onStart={() => setSjtOpen(true)} />
                        <Tooltip content={GLOSSARY.sjt.desc} storageKey="sjt">
                          <span className="text-[var(--text-sm)] text-[var(--ink-3)]">情境判断（SJT）</span>
                        </Tooltip>
                      </div>
                    </>
                  )}
                </Block>

                {/* Goals & Recommendations */}
                <Block kicker="DIRECTION" title="目标与推荐" accent>
                  <div className="space-y-4">
                    <div>
                      <p className="text-[var(--text-xs)] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-2">当前目标</p>
                      {hasGoal ? (
                        <GoalCard
                          goal={goal}
                          onExplore={() => { /* navigate to graph */ }}
                          onChange={() => { /* navigate or open modal */ }}
                        />
                      ) : (
                        <div className="rounded-[var(--radius-md)] border border-[var(--line)] bg-[var(--bg-card)] p-4">
                          <p className="text-[var(--text-base)] text-[var(--ink-1)]">还没有明确的目标</p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <button className="px-3 py-1.5 rounded-full bg-[var(--chestnut)] text-white text-[var(--text-xs)] font-medium hover:opacity-90 transition-opacity duration-200 active:scale-[0.98]">
                              让 AI 帮我推荐
                            </button>
                            <button className="px-3 py-1.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] text-[var(--text-xs)] font-medium hover:bg-[var(--line)]/10 transition-colors duration-200 active:scale-[0.98]">
                              我去图谱探索
                            </button>
                          </div>
                        </div>
                      )}
                    </div>

                    <div>
                      <p className="text-[var(--text-xs)] font-bold uppercase tracking-[0.15em] text-[var(--ink-3)] mb-2">推荐方向</p>
                      {recommendations.length > 0 ? (
                        <>
                          <div className="space-y-3">
                            <AnimatePresence initial={false}>
                              {visibleRecs.map((rec) => (
                                <motion.div
                                  key={rec.role_id}
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: 'auto' }}
                                  exit={{ opacity: 0, height: 0 }}
                                  transition={{ duration: 0.2, ease: EASE_OUT }}
                                >
                                  <RecommendationCard
                                    rec={{ role_id: rec.role_id, label: rec.label, reason: rec.reason }}
                                    onExplore={() => { /* navigate to role */ }}
                                  />
                                </motion.div>
                              ))}
                            </AnimatePresence>
                          </div>
                          {recommendations.length > 3 && (
                            <button
                              onClick={() => setShowAllRecs((v) => !v)}
                              className="mt-3 text-[var(--text-sm)] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors duration-200 active:scale-[0.98]"
                            >
                              {showAllRecs ? '收起' : `展开更多（还有 ${recommendations.length - 3} 个）`}
                            </button>
                          )}
                        </>
                      ) : (
                        <p className="text-[var(--text-sm)] text-[var(--ink-3)] italic">还没有推荐方向</p>
                      )}
                    </div>
                  </div>
                </Block>
              </BlockGrid>
            )}

            {/* Epilogue */}
            <div className="pt-[var(--space-5)] border-t border-[var(--line)]">
              {(() => {
                const incomplete = 6 - sectionsCompleted
                const todos = [
                  !data?.name ? '补一个名字' : null,
                  sectionsCompleted < 2 ? '补充教育背景' : null,
                  sectionsCompleted < 3 ? '加一段实习或项目' : null,
                  sectionsCompleted < 4 ? '加几个技能' : null,
                  sectionsCompleted < 5 ? '做一次软技能小测' : null,
                  sectionsCompleted < 6 ? '选一个目标方向' : null,
                ].filter(Boolean) as string[]
                return (
                  <>
                    {incomplete > 0 && todos.length > 0 && (
                      <>
                        <p className="text-[var(--text-base)] font-medium text-[var(--ink-1)] mb-3">
                          还有几件事可以讲 —— 但不用现在做完。
                        </p>
                        <div className="flex flex-wrap gap-2 mb-4">
                          {todos.map((t) => (
                            <span
                              key={t}
                              className="px-2.5 py-1 rounded-[var(--radius-pill)] text-[var(--text-xs)] font-medium bg-[var(--bg-card)] text-[var(--ink-2)] border border-[var(--line)]"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </>
                    )}
                    <p className="text-[var(--text-xs)] text-[var(--ink-3)] font-mono">
                      上次更新 {data?.updated_at ? data.updated_at.slice(0, 10) : '—'}
                    </p>
                    <p className="mt-2 text-[var(--text-sm)] text-[var(--ink-2)] italic">
                      这份档案只给你自己和懂你的系统看。
                    </p>
                  </>
                )
              })()}
            </div>
          </>
        )}
      </div>

      {/* Name prompt modal */}
      <AnimatePresence>
        {showNamePrompt && (
          <motion.div
            {...MODAL_BACKDROP}
            className="fixed inset-0 bg-[var(--ink-1)]/20 backdrop-blur-sm z-[999] flex items-center justify-center p-6"
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                e.preventDefault()
                setShowNamePrompt(false)
              }
            }}
          >
            <motion.div
              {...MODAL_CARD}
              className="bg-[var(--bg-card)] rounded-[var(--radius-lg)] shadow-[var(--shadow-float)] p-6 max-w-sm w-full border border-[var(--line)]"
            >
              <h3 className="text-[var(--text-xl)] font-semibold text-[var(--ink-1)] mb-2">为你的档案命名</h3>
              <p className="text-[var(--text-base)] text-[var(--ink-2)] mb-4">档案已建立，请确认或修改你的姓名</p>
              <input
                type="text"
                value={pendingName}
                onChange={(e) => setPendingName(e.target.value)}
                className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--bg-paper)] border border-[var(--line)] text-[var(--ink-1)] focus:outline-none focus:border-[var(--chestnut)]/50 transition-[border-color] duration-200 mb-4"
                placeholder="请输入姓名"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && handleNameConfirm()}
              />
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={() => setShowNamePrompt(false)}
                  className="px-4 py-2 rounded-full text-[var(--text-sm)] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors duration-200 active:scale-[0.98]"
                >
                  稍后再说
                </button>
                <button
                  onClick={handleNameConfirm}
                  disabled={!pendingName.trim()}
                  className="px-5 py-2 rounded-full bg-[var(--chestnut)] text-white text-[var(--text-sm)] font-medium hover:opacity-90 disabled:opacity-50 transition-opacity duration-200 active:scale-[0.98]"
                >
                  确认
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.main>
  )
}
