import { useEffect, useRef, useState, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { PenLine } from 'lucide-react'
import { useProfileDataV2 } from '@/hooks/useProfileDataV2'
import { useResumeUpload } from '@/hooks/useResumeUpload'
import { saveProfile, patchProfileData } from '@/api/profiles-v2'
import type { V2ParsePreviewResponse, V2ProfileData } from '@/api/profiles-v2'
import type { ManualProfilePayload } from '@/types/profile'
import { useToast } from '@/components/ui'
import Navbar from '@/components/shared/Navbar'
import { SjtQuiz } from '@/components/profile-v2/SjtQuiz'
import { ManualProfileForm } from '@/components/profile-v2/ManualProfileForm'
import { CeremonyUpload } from '@/components/profile-v2/CeremonyUpload'
import { mockProfileData } from '@/components/profile-v2/mockData'
import ProfileReadonlyView from '@/components/profile-v2/ProfileReadonlyView'
import ProfileEditForm from '@/components/profile-v2/ProfileEditForm'
import type { Internship, Skill } from '@/types/profile'
import type { V2Education, V2Project } from '@/types/profile-v2'

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

  const { v2Profile, source, updatedAt, loading, error: loadError, loadProfile, deleteProfile } = useProfileDataV2(!isMock)
  const { uploadStep, uploadError, justUploaded, selectedFileName, fileInputRef, triggerFileDialog, onFileSelected, previewData, clearPreviewData } = useResumeUpload()
  const [savingEdit, setSavingEdit] = useState(false)

  const [ceremonyAnimating, setCeremonyAnimating] = useState(false)
  useEffect(() => {
    if (justUploaded) setCeremonyAnimating(true)
  }, [justUploaded])

  const [showManual, setShowManual] = useState(false)
  const [sjtOpen, setSjtOpen] = useState(false)
  const [showNamePrompt, setShowNamePrompt] = useState(false)
  const [pendingName, setPendingName] = useState('')
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [savingPreview, setSavingPreview] = useState(false)
  const [previewFormData, setPreviewFormData] = useState<ManualProfilePayload | null>(null)
  const [pendingPreviewForEdit, setPendingPreviewForEdit] = useState<V2ParsePreviewResponse | null>(null)
  const [editOpen, setEditOpen] = useState(false)
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
    const baseEducation = base.education[0] || { degree: '', major: '', school: '', duration: '', graduation_year: undefined }

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

  const v2Data = isMock ? mockProfileData : v2Profile

  const hasProfile = isMock
    ? true
    : !!(v2Data?.name || v2Data?.skills?.length || v2Data?.projects?.length || v2Data?.internships?.length || v2Data?.education?.length)

  useEffect(() => {
    if (justUploaded && !loading && hasProfile && !isMock && !v2Data?.name && !namePromptShown.current) {
      namePromptShown.current = true
      setPendingName('')
      setShowNamePrompt(true)
    }
  }, [justUploaded, loading, hasProfile, v2Data?.name, isMock])

  const handleNameConfirm = useCallback(async () => {
    if (!pendingName.trim()) return
    setShowNamePrompt(false)
    try {
      await patchProfileData({ name: pendingName.trim() })
      await loadProfile()
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败')
    }
  }, [pendingName, loadProfile, toast])

  const handleSaveEdit = useCallback(async (payload: ManualProfilePayload) => {
    setSavingEdit(true)
    try {
      if (hasProfile && v2Data) {
        const patch = manualPayloadToV2Profile(payload, v2Data)
        await patchProfileData({
          name: patch.name,
          job_target_text: patch.job_target_text,
          education: patch.education,
          skills: patch.skills,
          projects: patch.projects,
          internships: patch.internships,
          certificates: patch.certificates,
          awards: patch.awards,
        })
      } else {
        const emptyBase: V2ProfileData = {
          name: '',
          job_target_text: '',
          domain_hint: '',
          education: [],
          skills: [],
          projects: [],
          internships: [],
          awards: [],
          certificates: [],
          raw_text: '',
        }
        const confirmedProfile = manualPayloadToV2Profile(payload, emptyBase)
        await saveProfile({
          raw_profile: confirmedProfile,
          confirmed_profile: confirmedProfile,
          document: {
            filename: 'manual-input.txt',
            content_type: 'text/plain',
            raw_text: '',
            text_format: 'plain',
            extraction_method: 'manual',
            ocr_used: false,
            file_hash: '',
            warnings: [],
          },
          parse_meta: {
            llm_model: '',
            evidence_sources: ['manual'],
            json_repaired: false,
            retry_count: 0,
            quality_score: 0,
            quality_checks: {},
            warnings: [],
          },
        })
      }
      await loadProfile()
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSavingEdit(false)
    }
  }, [hasProfile, v2Data, manualPayloadToV2Profile, loadProfile, toast])

  const handleSaveEducation = useCallback(async (edu: V2Education) => {
    try {
      await patchProfileData({ education: [edu] })
      await loadProfile()
      toast('已保存')
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败')
    }
  }, [loadProfile, toast])

  const handleSaveSkills = useCallback(async (newSkills: Skill[]) => {
    try {
      await patchProfileData({
        skills: newSkills
          .filter((s) => s.name.trim())
          .map((s) => ({ name: s.name.trim(), level: normalizeV2SkillLevel(s.level) })),
      })
      await loadProfile()
      toast('已保存')
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败')
    }
  }, [loadProfile, toast])

  const handleSaveInternships = useCallback(async (newInterns: Internship[]) => {
    try {
      await patchProfileData({
        internships: newInterns.map((i) => ({
          company: i.company,
          role: i.role,
          duration: i.duration || '',
          tech_stack: i.tech_stack || [],
          highlights: i.highlights || '',
        })),
      })
      await loadProfile()
      toast('已保存')
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败')
    }
  }, [loadProfile, toast])

  const handleSaveProjects = useCallback(async (newProjects: V2Project[]) => {
    try {
      await patchProfileData({
        projects: newProjects.filter((p) => p.name || p.description || p.tech_stack.length || p.highlights),
      })
      await loadProfile()
      toast('已保存')
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败')
    }
  }, [loadProfile, toast])

  const handlePatchProfile = useCallback(async (patch: Partial<V2ProfileData>) => {
    try {
      await patchProfileData(patch)
      await loadProfile()
      toast('已保存')
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败')
    }
  }, [loadProfile, toast])

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
                : v2Data
                  ? v2ToManualPayload(v2Data)
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
        {/* Header + Profile View */}
        <section className="mb-16">
          {hasProfile && v2Data ? (
            <ProfileReadonlyView
              profile={v2Data}
              source={isMock ? 'resume' : (source || 'resume')}
              updatedAt={updatedAt ?? undefined}
              onDelete={deleteProfile}
              onSaveEducation={handleSaveEducation}
              onSaveSkills={handleSaveSkills}
              onSaveInternships={handleSaveInternships}
              onSaveProjects={handleSaveProjects}
              onOpenEdit={() => setEditOpen(true)}
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
                      个人画像
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
                    上传简历或补充关键经历，整理你的技能结构、项目经历与偏好约束，形成可编辑的个人画像。
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
                    alt="职业能力档案"
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

        {/* ProfileEditForm */}
        {v2Data && (
          <ProfileEditForm
            open={editOpen}
            onClose={() => setEditOpen(false)}
            initialData={v2Data}
            onSave={handlePatchProfile}
          />
        )}
      </div>

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
