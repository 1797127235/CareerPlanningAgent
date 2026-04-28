import { useEffect, useRef, useState, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, PenLine, AlertTriangle, RefreshCw } from 'lucide-react'
import { useProfileData, type ManualProfilePayload } from '@/hooks/useProfileData'
import { useResumeUpload } from '@/hooks/useResumeUpload'
import { setProfileName, updateProfile } from '@/api/profiles'
import { saveProfile } from '@/api/profiles-v2'
import type { V2ParsePreviewResponse, V2ProfileData } from '@/api/profiles-v2'
import { fetchRecommendations, type Recommendation as ApiRecommendation } from '@/api/recommendations'
import { setCareerGoal } from '@/api/graph'
import { useToast } from '@/components/ui'
import Navbar from '@/components/shared/Navbar'
import { SjtQuiz } from '@/components/profile-v2/SjtQuiz'
import { ManualProfileForm } from '@/components/profile-v2/ManualProfileForm'
import { CeremonyUpload } from '@/components/profile-v2/CeremonyUpload'
import { mockProfileData } from '@/components/profile-v2/mockData'
import ProfileReadonlyView from '@/components/profile-v2/ProfileReadonlyView'
import type { Education, Internship, Skill } from '@/types/profile'

function useRecommendations(hasProfile: boolean, justUploaded: boolean) {
  const [recs, setRecs] = useState<ApiRecommendation[]>([])
  const inFlight = useRef(false)
  const retryCount = useRef(0)
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const clearTimer = useCallback(() => {
    if (retryTimer.current) {
      clearTimeout(retryTimer.current)
      retryTimer.current = null
    }
  }, [])

  const doFetch = useCallback(async (isRetry = false) => {
    if (inFlight.current) return
    inFlight.current = true
    if (!isRetry) retryCount.current = 0
    try {
      const res = await fetchRecommendations(6)
      const list = res.recommendations || []
      setRecs(list)
      if (list.length === 0 && retryCount.current < 10) {
        retryCount.current += 1
        retryTimer.current = setTimeout(() => doFetch(true), 6000)
      } else {
        retryCount.current = 0
      }
    } catch {
      // silently retry on next cycle
    } finally {
      inFlight.current = false
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => clearTimer, [clearTimer])

  // Fetch when profile exists
  useEffect(() => {
    if (!hasProfile) return
    doFetch()
    return clearTimer
  }, [hasProfile, doFetch, clearTimer])

  // Re-fetch when upload completes (background thread may now be done)
  useEffect(() => {
    if (justUploaded && hasProfile && recs.length === 0) {
      retryCount.current = 0
      clearTimer()
      doFetch()
    }
  }, [justUploaded, hasProfile, recs.length, doFetch, clearTimer])

  return { recs }
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
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isMock = searchParams.get('mock') === '1'
  const { toast } = useToast()

  const { profile, loading, loadError, loadProfile, savingEdit, handleSaveEdit, handleDelete } = useProfileData(!isMock)
  const { uploadStep, uploadError, justUploaded, selectedFileName, fileInputRef, triggerFileDialog, onFileSelected, previewData, clearPreviewData } = useResumeUpload()

  const [ceremonyAnimating, setCeremonyAnimating] = useState(false)
  useEffect(() => {
    if (justUploaded) setCeremonyAnimating(true)
  }, [justUploaded])

  const [showManual, setShowManual] = useState(false)
  const [sjtOpen, setSjtOpen] = useState(false)
  const [showNamePrompt, setShowNamePrompt] = useState(false)
  const [pendingName, setPendingName] = useState('')
  const [showChangeGoalConfirm, setShowChangeGoalConfirm] = useState(false)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [savingPreview, setSavingPreview] = useState(false)
  const [previewFormData, setPreviewFormData] = useState<ManualProfilePayload | null>(null)
  const [pendingPreviewForEdit, setPendingPreviewForEdit] = useState<V2ParsePreviewResponse | null>(null)
  const namePromptShown = useRef(false)

  // 当 parse-preview 返回数据时自动打开预览模态框
  useEffect(() => {
    if (previewData) setShowPreviewModal(true)
  }, [previewData])

  const handleSavePreviewDirect = useCallback(async () => {
    if (!previewData) return
    setSavingPreview(true)
    try {
      await saveProfile({
        raw_profile: previewData.profile,
        confirmed_profile: previewData.profile,
        document: previewData.document,
        parse_meta: previewData.meta,
      })
      clearPreviewData()
      setShowPreviewModal(false)
      await loadProfile()
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSavingPreview(false)
    }
  }, [previewData, clearPreviewData, loadProfile, toast])

  const v2ToManualPayload = useCallback((v2: V2ProfileData): ManualProfilePayload => {
    const edu = v2.education[0] || { degree: '', major: '', school: '' }
    return {
      name: v2.name,
      education: {
        degree: edu.degree || '',
        major: edu.major || '',
        school: edu.school || '',
      },
      experience_years: 0,
      job_target: v2.job_target_text,
      skills: v2.skills.map((s) => ({
        name: s.name,
        level: (s.level as Skill['level']) || 'familiar',
      })),
      knowledge_areas: [],
      projects: v2.projects.map((p) => ({
        name: p.name,
        description: p.description,
        tech_stack: p.tech_stack,
      })),
      internships: v2.internships.map((i) => ({
        company: i.company,
        role: i.role,
        duration: i.duration,
        tech_stack: i.tech_stack,
        highlights: i.highlights,
      })),
      certificates: v2.certificates,
      awards: v2.awards,
    }
  }, [])

  const normalizeV2SkillLevel = useCallback((level: Skill['level']): V2ProfileData['skills'][number]['level'] => {
    if (level === 'advanced' || level === 'expert') return 'advanced'
    if (level === 'intermediate' || level === 'proficient') return 'intermediate'
    if (level === 'beginner') return 'beginner'
    return 'familiar'
  }, [])

  const manualPayloadToV2Profile = useCallback((payload: ManualProfilePayload, base: V2ProfileData): V2ProfileData => {
    const baseEducation = base.education[0] || { degree: '', major: '', school: '', duration: '', graduation_year: null }

    return {
      ...base,
      name: payload.name,
      job_target_text: payload.job_target,
      education: payload.education.school || payload.education.major || payload.education.degree
        ? [{
            ...baseEducation,
            degree: payload.education.degree,
            major: payload.education.major,
            school: payload.education.school,
          }]
        : [],
      skills: payload.skills
        .filter((s) => s.name.trim())
        .map((s) => ({ name: s.name.trim(), level: normalizeV2SkillLevel(s.level) })),
      projects: payload.projects.map((project, index) => {
        const baseProject = base.projects[index] || { name: '', description: '', tech_stack: [], duration: '', highlights: '' }
        if (typeof project === 'string') {
          return { ...baseProject, description: project.trim() }
        }
        return {
          ...baseProject,
          name: typeof project.name === 'string' ? project.name : baseProject.name,
          description: typeof project.description === 'string' ? project.description : baseProject.description,
          tech_stack: Array.isArray(project.tech_stack) ? project.tech_stack.map(String) : baseProject.tech_stack,
          highlights: typeof project.highlights === 'string' ? project.highlights : baseProject.highlights,
        }
      }).filter((p) => p.name || p.description || p.tech_stack.length || p.highlights),
      internships: payload.internships.map((i) => ({
        company: i.company,
        role: i.role,
        duration: i.duration || '',
        tech_stack: i.tech_stack || [],
        highlights: i.highlights || '',
      })),
      certificates: payload.certificates,
      awards: payload.awards,
    }
  }, [normalizeV2SkillLevel])

  const handleEditThenSave = useCallback(() => {
    if (!previewData) return
    setPendingPreviewForEdit(previewData)
    setPreviewFormData(v2ToManualPayload(previewData.profile))
    clearPreviewData()
    setShowPreviewModal(false)
    setShowManual(true)
  }, [previewData, clearPreviewData, v2ToManualPayload])

  const data = isMock ? mockProfileData : profile
  const hasProfile = isMock
    ? true
    : !!(data?.profile?.skills?.length || data?.profile?.knowledge_areas?.length || data?.profile?.projects?.length || data?.profile?.internships?.length || data?.profile?.education?.school || data?.name)

  const { recs } = useRecommendations(hasProfile && !isMock, justUploaded)
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

  const profileObj = data?.profile || {}
  const education = profileObj.education as Education | undefined
  const internships = (profileObj.internships as Internship[]) || []
  const skills = (profileObj.skills as Skill[]) || []
  const softSkills = data?.profile?.soft_skills as Record<string, { score?: number; level?: string; advice?: string; evidence?: string }> | undefined
  const hasSjt = softSkills?._version === 2 && sjtDims.some((d) => softSkills[d] != null)
  const goal = data?.career_goals?.find((g) => g.is_primary) || data?.career_goals?.[0]
  const hasGoal = !!goal && !!goal.target_node_id
  const [showAllRecs, setShowAllRecs] = useState(false)
  const visibleRecs = showAllRecs ? recommendations : recommendations.slice(0, 3)

  const savePatch = useCallback(async (patch: Record<string, unknown>) => {
    try {
      await updateProfile({ profile: { ...profileObj, ...patch }, quality: null })
      await loadProfile()
      toast('已保存')
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败')
    }
  }, [profileObj, loadProfile, toast])

  const handleSaveEducation = useCallback(async (edu: Education) => {
    await savePatch({ education: edu })
  }, [savePatch])

  const handleSaveSkills = useCallback(async (newSkills: Skill[]) => {
    await savePatch({ skills: newSkills })
  }, [savePatch])

  const handleSaveInternships = useCallback(async (newInterns: Internship[]) => {
    await savePatch({ internships: newInterns })
  }, [savePatch])

  const handleSaveProjects = useCallback(async (newProjects: Array<string | Record<string, unknown>>) => {
    await savePatch({ projects: newProjects })
  }, [savePatch])

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
        <Navbar />
        <div className="max-w-[860px] mx-auto px-[var(--space-6)] md:px-[var(--space-7)] pt-[80px] pb-[var(--space-6)]">
          <ManualProfileForm
            onSave={async (payload: ManualProfilePayload) => {
              if (pendingPreviewForEdit) {
                setSavingPreview(true)
                try {
                  const confirmedProfile = manualPayloadToV2Profile(payload, pendingPreviewForEdit.profile)
                  await saveProfile({
                    raw_profile: pendingPreviewForEdit.profile,
                    confirmed_profile: confirmedProfile,
                    document: pendingPreviewForEdit.document,
                    parse_meta: pendingPreviewForEdit.meta,
                  })
                  await loadProfile()
                } finally {
                  setSavingPreview(false)
                }
              } else {
                await handleSaveEdit(payload)
              }
              setPendingPreviewForEdit(null)
              setPreviewFormData(null)
              setShowManual(false)
            }}
            onCancel={() => {
              setPendingPreviewForEdit(null)
              setPreviewFormData(null)
              setShowManual(false)
            }}
            saving={savingEdit || savingPreview}
            initialData={
              previewFormData
                ? previewFormData
                : data
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
      <Navbar />
      <input ref={fileInputRef} type="file" accept=".pdf,.doc,.docx,.txt" className="hidden" onChange={onFileSelected} />

      <div className="max-w-[1200px] mx-auto px-6 md:px-12 pt-[80px] pb-24">
        {/* Header + Progress */}
        <section className="mb-16">
          {hasProfile ? (
            <ProfileReadonlyView
              data={data}
              onReport={() => navigate('/report')}
              onSetGoal={() => navigate('/graph')}
              onChangeGoal={() => setShowChangeGoalConfirm(true)}
              onDelete={handleDelete}
              onStartAssessment={() => setSjtOpen(true)}
              recommendations={recommendations.map((r) => ({
                role_id: r.role_id,
                label: r.label,
                reason: r.reason,
                zone: r.zone,
                replacement_pressure: r.replacement_pressure,
              }))}
              onSaveEducation={handleSaveEducation}
              onSaveSkills={handleSaveSkills}
              onSaveInternships={handleSaveInternships}
              onSaveProjects={handleSaveProjects}
            />
          ) : (
            <>
              {/* Empty State — Ceremony Upload */}
              <div className="grid gap-8 md:grid-cols-2 md:gap-12 items-center" style={{ minHeight: 'calc(100vh - 180px)' }}>
                {/* Left — Copy */}
                <div>
                  {/* Kicker */}
                  <div className="flex items-center gap-3 mb-6">
                    <span className="inline-block h-px w-8" style={{ background: '#9A9590' }} />
                    <p className="text-[11px] font-medium tracking-[0.12em]" style={{ fontFamily: 'var(--font-sans)', color: '#9A9590' }}>
                      AI 职业能力画像
                    </p>
                  </div>

                  <h1
                    style={{
                      fontFamily: 'var(--font-serif)',
                      fontSize: 'clamp(40px, 5vw, 64px)',
                      lineHeight: 1.12,
                      letterSpacing: '0.01em',
                      color: 'var(--ink-1)',
                    }}
                  >
                    <span style={{ fontWeight: 400 }}>创建你的</span>
                    <br />
                    <span style={{ fontWeight: 600 }}>AI </span>
                    <span style={{ fontWeight: 600, color: '#B85C38' }}>职业能力档案</span>
                  </h1>

                  <p
                    className="mt-5 leading-[1.7]"
                    style={{
                      fontFamily: 'var(--font-sans)',
                      fontSize: '15px',
                      color: 'var(--ink-2)',
                      maxWidth: '460px',
                    }}
                  >
                    上传简历或补充关键经历，CareerPlan 将自动识别你的技能结构、项目亮点与潜在优势，生成一份专属成长分析。
                  </p>

                  {/* Ceremony Upload */}
                  <div className="mt-8 max-w-[560px]">
                    <CeremonyUpload
                      uploadStep={uploadStep}
                      uploadError={uploadError}
                      justUploaded={justUploaded}
                      fileName={selectedFileName}
                      onUpload={triggerFileDialog}
                      onManual={() => setShowManual(true)}
                      onCeremonyComplete={() => setCeremonyAnimating(false)}
                    />
                  </div>

                  {uploadError && !ceremonyAnimating && (
                    <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700 max-w-[500px]">
                      {uploadError}
                    </div>
                  )}

                  <div className="mt-6 flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9A9590" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    </svg>
                    <p className="text-[12px]" style={{ color: 'var(--ink-3)', fontFamily: 'var(--font-sans)' }}>
                      档案仅用于系统分析，不会分享给任何第三方。
                    </p>
                  </div>
                </div>

                {/* Right — 3D Illustration */}
                <div className="flex items-center justify-center">
                  <img
                    src="/profile-hero.png"
                    alt="AI 职业能力档案"
                    className="w-full max-w-[380px] md:max-w-[430px]"
                    style={{ objectFit: 'contain' }}
                  />
                </div>
              </div>
            </>
          )}
        </section>

        {/* SJT Quiz Modal */}
        <AnimatePresence>
          {sjtOpen && (
            <motion.div
              {...MODAL_BACKDROP}
              className="fixed inset-0 bg-[var(--ink-1)]/20 backdrop-blur-sm z-[999] flex items-center justify-center p-6"
              onClick={() => setSjtOpen(false)}
            >
              <motion.div
                {...MODAL_CARD}
                className="bg-[var(--bg-card)] rounded-[var(--radius-lg)] shadow-[var(--shadow-float)] p-6 max-w-2xl w-full border border-[var(--line)] max-h-[80vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <SjtQuiz onComplete={() => { setSjtOpen(false); loadProfile() }} onCancel={() => setSjtOpen(false)} />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Change goal confirmation modal */}
      <AnimatePresence>
        {showChangeGoalConfirm && goal && (
          <motion.div
            {...MODAL_BACKDROP}
            className="fixed inset-0 bg-[var(--ink-1)]/20 backdrop-blur-sm z-[999] flex items-center justify-center p-6"
            onClick={() => setShowChangeGoalConfirm(false)}
          >
            <motion.div
              {...MODAL_CARD}
              className="bg-[var(--bg-card)] rounded-[var(--radius-lg)] shadow-[var(--shadow-float)] p-6 max-w-sm w-full border border-[var(--line)]"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4" style={{ background: '#FDF5E8' }}>
                <AlertTriangle className="w-6 h-6" style={{ color: '#C4853F' }} />
              </div>
              <h3 className="text-[var(--text-lg)] font-semibold text-[var(--ink-1)] text-center mb-2">确认更换目标方向？</h3>
              <div className="text-[var(--text-sm)] text-[var(--ink-2)] space-y-1.5 mb-5">
                <p>你当前的目标方向是「{goal.target_label}」。</p>
                <p style={{ color: 'var(--ink-3)' }}>更换目标后：</p>
                <ul className="text-[12px] space-y-1 pl-1" style={{ color: 'var(--ink-3)' }}>
                  <li>已掌握的技能会保留在画像中</li>
                  <li>差距分析将基于新目标重新计算</li>
                  <li>学习路径将切换到新方向</li>
                </ul>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowChangeGoalConfirm(false)}
                  className="flex-[2] py-2.5 rounded-full text-[var(--text-sm)] font-medium border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors duration-200 active:scale-[0.98]"
                >
                  继续当前目标
                </button>
                <button
                  onClick={async () => {
                    setShowChangeGoalConfirm(false)
                    await setCareerGoal({
                      profile_id: data!.id,
                      target_node_id: '',
                      target_label: '',
                      target_zone: '',
                      gap_skills: [],
                      estimated_hours: 0,
                      safety_gain: 0,
                      salary_p50: 0,
                    })
                    await loadProfile()
                  }}
                  className="flex-1 py-2.5 rounded-full text-[var(--text-sm)] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors duration-200 active:scale-[0.98]"
                >
                  确认更换
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Preview modal — parse-preview 结果确认 */}
      <AnimatePresence>
        {showPreviewModal && previewData && (
          <motion.div
            {...MODAL_BACKDROP}
            className="fixed inset-0 bg-[var(--ink-1)]/20 backdrop-blur-sm z-[999] flex items-center justify-center p-6"
            onClick={() => {
              setShowPreviewModal(false)
              clearPreviewData()
            }}
          >
            <motion.div
              {...MODAL_CARD}
              className="bg-[var(--bg-card)] rounded-[var(--radius-lg)] shadow-[var(--shadow-float)] p-6 max-w-2xl w-full border border-[var(--line)] max-h-[85vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="text-[var(--text-xl)] font-semibold text-[var(--ink-1)]">简历解析完成</h3>
                  <p className="text-[var(--text-sm)] text-[var(--ink-3)] mt-0.5">
                    质量评分 <span className="font-medium text-[var(--ink-1)]">{previewData.meta.quality_score}</span> / 100
                  </p>
                </div>
                <button
                  onClick={() => {
                    setShowPreviewModal(false)
                    clearPreviewData()
                  }}
                  className="text-[var(--ink-3)] hover:text-[var(--ink-1)] transition-colors"
                >
                  ✕
                </button>
              </div>

              {/* Parsed content */}
              <div className="space-y-4 text-[var(--text-sm)]">
                {/* Name & Target */}
                {(previewData.profile.name || previewData.profile.job_target_text) && (
                  <div className="pb-3 border-b border-[var(--line)]">
                    {previewData.profile.name && (
                      <p className="text-[var(--ink-1)] font-medium">{previewData.profile.name}</p>
                    )}
                    {previewData.profile.job_target_text && (
                      <p className="text-[var(--ink-3)] mt-0.5">求职意向：{previewData.profile.job_target_text}</p>
                    )}
                  </div>
                )}

                {/* Education */}
                {previewData.profile.education.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium tracking-wider text-[var(--ink-3)] uppercase mb-1.5">教育经历</p>
                    {previewData.profile.education.map((edu, i) => (
                      <div key={i} className="text-[var(--ink-1)]">
                        {edu.school} {edu.degree && `· ${edu.degree}`} {edu.major && `· ${edu.major}`}
                      </div>
                    ))}
                  </div>
                )}

                {/* Skills */}
                {previewData.profile.skills.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium tracking-wider text-[var(--ink-3)] uppercase mb-1.5">技能</p>
                    <div className="flex flex-wrap gap-1.5">
                      {previewData.profile.skills.map((s, i) => (
                        <span key={i} className="px-2 py-0.5 rounded-full bg-[var(--line)]/40 text-[var(--ink-2)] text-[12px]">
                          {s.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Projects */}
                {previewData.profile.projects.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium tracking-wider text-[var(--ink-3)] uppercase mb-1.5">项目经历</p>
                    <div className="space-y-1">
                      {previewData.profile.projects.map((p, i) => (
                        <div key={i} className="text-[var(--ink-1)]">
                          {p.name} {p.tech_stack.length > 0 && (
                            <span className="text-[var(--ink-3)]">· {p.tech_stack.join(', ')}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Internships */}
                {previewData.profile.internships.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium tracking-wider text-[var(--ink-3)] uppercase mb-1.5">实习 / 工作经历</p>
                    <div className="space-y-1">
                      {previewData.profile.internships.map((intern, i) => (
                        <div key={i} className="text-[var(--ink-1)]">
                          {intern.company} {intern.role && `· ${intern.role}`}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Awards & Certificates */}
                {(previewData.profile.awards.length > 0 || previewData.profile.certificates.length > 0) && (
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-[var(--ink-2)]">
                    {previewData.profile.awards.length > 0 && (
                      <span>获奖：{previewData.profile.awards.length} 项</span>
                    )}
                    {previewData.profile.certificates.length > 0 && (
                      <span>证书：{previewData.profile.certificates.length} 项</span>
                    )}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="mt-6 pt-4 border-t border-[var(--line)] flex gap-3">
                <button
                  onClick={handleEditThenSave}
                  disabled={savingPreview}
                  className="flex-[2] py-2.5 rounded-full text-[var(--text-sm)] font-medium border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors duration-200 active:scale-[0.98] disabled:opacity-50"
                >
                  先编辑再保存
                </button>
                <button
                  onClick={handleSavePreviewDirect}
                  disabled={savingPreview}
                  className="flex-1 py-2.5 rounded-full text-[var(--text-sm)] font-medium bg-[var(--chestnut)] text-white hover:opacity-90 transition-opacity duration-200 active:scale-[0.98] disabled:opacity-50"
                >
                  {savingPreview ? '保存中…' : '确认并保存'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

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
