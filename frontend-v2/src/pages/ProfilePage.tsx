import { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useProfileData, type ManualProfilePayload } from '@/hooks/useProfileData'
import { useResumeUpload } from '@/hooks/useResumeUpload'
import { setProfileName } from '@/api/profiles'
import { fetchRecommendations, type Recommendation as ApiRecommendation } from '@/api/recommendations'
import { TableOfContents } from '@/components/editorial'
import { ProfilePrologue, ProfileChapterI, ProfileChapterII, ProfileChapterIII, ProfileChapterIV, ProfileEpilogue } from '@/components/profile-v2'
import { SjtQuiz } from '@/components/profile-v2/SjtQuiz'
import { ManualProfileForm } from '@/components/profile-v2/ManualProfileForm'
import { mockProfileData } from '@/components/profile-v2/mockData'

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

export default function ProfilePage() {
  const [searchParams] = useSearchParams()
  const isMock = searchParams.get('mock') === '1'

  const { profile, loading, loadError, loadProfile, savingEdit, handleSaveEdit } = useProfileData()
  const { uploading, uploadStep, uploadError, justUploaded, clearJustUploaded, fileInputRef, triggerFileDialog, onFileSelected } = useResumeUpload(loadProfile)

  const [showManual, setShowManual] = useState(false)
  const [sjtOpen, setSjtOpen] = useState(false)

  // Name prompt after upload
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

  if (loading && !isMock) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <p className="font-serif italic text-[var(--fs-body-lg)] text-[var(--ink-2)]">正在打开档案…</p>
      </main>
    )
  }

  if (loadError && !isMock) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <p className="font-sans text-[var(--fs-body-lg)] text-[var(--ink-1)]">画像加载失败</p>
          <p className="mt-2 text-[var(--fs-body)] text-[var(--ink-3)]">{loadError}</p>
          <button
            onClick={loadProfile}
            className="mt-6 inline-flex items-center px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-sm font-medium"
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
        <div className="max-w-[720px] mx-auto px-6 md:px-12 lg:px-20 py-12">
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
    <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <input ref={fileInputRef} type="file" accept=".pdf,.doc,.docx,.txt" className="hidden" onChange={onFileSelected} />

      <div className="max-w-[1200px] mx-auto px-6 md:px-12 lg:px-20 pb-32">
        <div className="lg:grid lg:grid-cols-[1fr_200px] lg:gap-12">
          <div className="max-w-[720px] mx-auto lg:mx-0">
            <ProfilePrologue
              hasProfile={hasProfile}
              name={data?.name}
              createdAt={data?.created_at}
              updatedAt={data?.updated_at}
              uploading={uploading}
              uploadStep={uploadStep}
              uploadError={uploadError}
              onUpload={triggerFileDialog}
              onManual={() => setShowManual(true)}
            />
            {hasProfile && (
              <>
                <div id="chapter-1"><ProfileChapterI data={data!} onRefresh={loadProfile} /></div>
                <div id="chapter-2"><ProfileChapterII data={data!} onRefresh={loadProfile} /></div>
                <div id="chapter-3">
                  {sjtOpen ? (
                    <div className="py-16 md:py-24">
                      <SjtQuiz onComplete={() => { setSjtOpen(false); loadProfile() }} onCancel={() => setSjtOpen(false)} />
                    </div>
                  ) : (
                    <ProfileChapterIII data={data!} onStartSjt={() => setSjtOpen(true)} />
                  )}
                </div>
                <div id="chapter-4">
                  <ProfileChapterIV
                    data={data!}
                    recommendations={recommendations.map((r) => ({ role_id: r.role_id, label: r.label, reason: r.reason }))}
                    onExploreGoal={() => { /* navigate to graph */ }}
                    onChangeGoal={() => { /* navigate or open modal */ }}
                    onExploreRec={() => { /* navigate to role */ }}
                  />
                </div>
                <ProfileEpilogue
                  name={data?.name}
                  sectionsCompleted={sectionsCompleted}
                  totalSections={6}
                  updatedAt={data?.updated_at}
                />
              </>
            )}
          </div>

          {hasProfile && (
            <TableOfContents
              items={[
                { id: 'chapter-1', numeral: 'I', label: '你从哪里来' },
                { id: 'chapter-2', numeral: 'II', label: '你会什么' },
                { id: 'chapter-3', numeral: 'III', label: '你是怎样的人' },
                { id: 'chapter-4', numeral: 'IV', label: '你想去哪' },
              ]}
            />
          )}
        </div>
      </div>

      {/* Name prompt modal */}
      {showNamePrompt && (
        <div className="fixed inset-0 bg-[var(--ink-1)]/20 backdrop-blur-sm z-[999] flex items-center justify-center p-6">
          <div className="bg-[var(--bg-card)] rounded-2xl shadow-2xl p-6 max-w-sm w-full border border-[var(--line)]">
            <h3 className="font-display text-[var(--fs-display-sm)] text-[var(--ink-1)] mb-2">为你的档案命名</h3>
            <p className="text-[var(--fs-body)] text-[var(--ink-2)] mb-4">档案已建立，请确认或修改你的姓名</p>
            <input
              type="text"
              value={pendingName}
              onChange={(e) => setPendingName(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[var(--bg-paper)] border border-[var(--line)] text-[var(--ink-1)] focus:outline-none focus:border-[var(--chestnut)]/50 mb-4"
              placeholder="请输入姓名"
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && handleNameConfirm()}
            />
            <button
              onClick={handleNameConfirm}
              disabled={!pendingName.trim()}
              className="w-full py-2.5 rounded-full bg-[var(--chestnut)] text-white text-[14px] font-medium hover:opacity-90 disabled:opacity-50"
            >
              确认
            </button>
          </div>
        </div>
      )}
    </main>
  )
}
