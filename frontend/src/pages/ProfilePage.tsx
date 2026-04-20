import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Target, Brain, Upload, PenLine, RefreshCw, AlertTriangle, Check, ArrowUpRight, Crosshair
} from 'lucide-react'

import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'
import { useResumeUpload } from '@/hooks/useResumeUpload'
import { dispatchCoachTrigger } from '@/hooks/useCoachTrigger'
import { fetchRecommendations, type Recommendation } from '@/api/recommendations'
import { setCareerGoal } from '@/api/graph'
import { rawFetch } from '@/api/client'

import { PreferencesCard } from '@/components/profile/PreferencesCard'
import {
  ProfileSkeleton,
  ProfileEmptyState,
  SkillsCard,
  KnowledgeCard,
  EducationCard,
  ProjectsCard,
  SoftSkillsCard,
  SjtCtaCard,
  UploadProgress,
  ManualProfileForm,
} from '@/components/profile'
import { cardVariants } from '@/components/profile/constants'

const ZONE_STYLE: Record<string, string> = {
  safe:       'bg-emerald-50 text-emerald-700',
  leverage:   'bg-blue-50 text-blue-700',
  transition: 'bg-amber-50 text-amber-700',
  danger:     'bg-red-50 text-red-700',
}
const ZONE_TEXT: Record<string, string> = {
  safe: '安全区', leverage: '杠杆区', transition: '过渡区', danger: '危险区',
}


function SectionHeader({ title, count }: { title: string; count?: string }) {
  return (
    <div className="flex items-center gap-2 mb-3 mt-1">
      <h2 className="text-[15px] font-bold text-slate-800">{title}</h2>
      {count && (
        <span className="text-[11px] font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-md">
          {count}
        </span>
      )}
    </div>
  )
}

function RecommendationCard({
  rec,
  onExplore,
}: {
  rec: Recommendation
  onExplore: (r: Recommendation) => void
  }) {
  const zoneStyle = ZONE_STYLE[rec.zone] || 'bg-slate-100 text-slate-600'
  const zoneText = ZONE_TEXT[rec.zone] || rec.zone
  const rp = rec.replacement_pressure ?? 50
  const rpColor = rp < 30 ? 'bg-emerald-400' : rp < 55 ? 'bg-amber-400' : 'bg-rose-400'
  const rpLabel = rp < 30 ? 'AI安全' : rp < 55 ? 'AI中等' : 'AI风险'

  return (
    <div
      onClick={() => onExplore(rec)}
      className="glass p-3.5 cursor-pointer hover:shadow-[0_4px_20px_rgba(0,0,0,0.06)] transition-all"
    >
      <div className="g-inner">
        <div className="flex items-center justify-between mb-1.5">
          <h3 className="text-[14px] font-bold text-slate-800 leading-tight truncate">
            {rec.label}
          </h3>
        </div>
        <div className="flex items-center gap-2 mb-1.5">
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${zoneStyle}`}>{zoneText}</span>
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full text-white ${rpColor}`}>{rpLabel}</span>
        </div>
        <p className="text-[11px] text-slate-500 line-clamp-1">{rec.reason}</p>
      </div>
    </div>
  )
}

export default function ProfilePage() {
  const { token } = useAuth()
  const { profile, loading, loadError, loadProfile, handleSaveEdit, savingEdit } = useProfileData(token)
  const { fileInputRef, triggerFileDialog, onFileSelected, uploading, uploadStep, uploadError, justUploaded, clearJustUploaded } = useResumeUpload(loadProfile)
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [recs, setRecs] = useState<Recommendation[]>([])
  const [recsLoading, setRecsLoading] = useState(true)
  const [recsFetchFailed, setRecsFetchFailed] = useState(false)
  const [editing, setEditing] = useState(false)
  const [showSjtInline, setShowSjtInline] = useState(false)
  const [showChangeGoalConfirm, setShowChangeGoalConfirm] = useState(false)

  // Name prompt — shown after first upload when profile has no name
  const [showNamePrompt, setShowNamePrompt] = useState(false)
  const [pendingName, setPendingName] = useState('')
  const namePromptShown = useRef(false)

  const sjtRef = useRef<HTMLDivElement>(null)
  const newSkillParam = searchParams.get('newSkill')

  const hasProfile = (profile?.profile?.skills?.length ?? 0) > 0
    || (profile?.profile?.knowledge_areas?.length ?? 0) > 0
    || (profile?.profile?.projects?.length ?? 0) > 0
    || (profile?.profile?.internships?.length ?? 0) > 0
    || (profile?.profile?.experience_years ?? 0) > 0
    || !!profile?.profile?.education?.school
    || !!profile?.profile?.education?.major
    || !!profile?.name
    || !!profile?.profile?.raw_text

  // True ONLY when: has profile data, not loading, no graph position set, AND no recs yet
  // (recs loading = location done; graph_position set = location done)
  const isLocating = hasProfile && !loading
    && !profile?.graph_position?.from_node_id
    && recs.length === 0
    && recsLoading

  // Auto-refresh at most 3 times (18s total) while waiting for async graph location
  const locateRefetchCount = useRef(0)
  useEffect(() => {
    if (!hasProfile || loading) return
    if (!!profile?.graph_position?.from_node_id) { locateRefetchCount.current = 0; return }
    if (locateRefetchCount.current >= 3) return  // Hard stop — prevent infinite loop
    const timer = setTimeout(() => {
      locateRefetchCount.current += 1
      loadProfile()
    }, 6000)
    return () => clearTimeout(timer)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.updated_at, profile?.graph_position?.from_node_id])

  // Load recommendations only when no goal is set
  const goal = profile?.career_goals?.find((g: any) => g.is_primary) || profile?.career_goals?.[0]
  const hasGoal = !!goal && !!goal.target_node_id
  const profileUpdatedAt = profile?.updated_at

  // 防止并发 fetch：profile 每 6s 轮询一次，上次 LLM 还没回又起一次会导致请求堆积
  const recsFetchInFlight = useRef(false)
  const recsRefetchCount = useRef(0)
  const recsRetryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 清理推荐重试定时器
  useEffect(() => {
    return () => {
      if (recsRetryTimer.current) {
        clearTimeout(recsRetryTimer.current)
        recsRetryTimer.current = null
      }
    }
  }, [])

  const doFetchRecs = useCallback(async (isRetry = false) => {
    if (recsFetchInFlight.current) return
    recsFetchInFlight.current = true
    setRecsLoading(true)
    if (!isRetry) setRecsFetchFailed(false)
    try {
      const res = await fetchRecommendations(6)
      const list = res.recommendations || []
      setRecs(list)
      if (list.length === 0) {
        // 空数组可能是后端还在生成，自动重试最多 3 次（18s）
        if (recsRefetchCount.current < 3) {
          recsRefetchCount.current += 1
          recsRetryTimer.current = setTimeout(() => {
            doFetchRecs(true)
          }, 6000)
        } else {
          setRecsFetchFailed(true)
        }
      } else {
        recsRefetchCount.current = 0
      }
    } catch (err) {
      console.error(err)
      setRecsFetchFailed(true)
    } finally {
      setRecsLoading(false)
      recsFetchInFlight.current = false
    }
  }, [])

  useEffect(() => {
    if (hasProfile && !editing && !hasGoal && recs.length === 0) {
      recsRefetchCount.current = 0
      doFetchRecs()
    } else if (hasGoal) {
      setRecsLoading(false)
      setRecsFetchFailed(false)
      recsRefetchCount.current = 0
      if (recsRetryTimer.current) {
        clearTimeout(recsRetryTimer.current)
        recsRetryTimer.current = null
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasProfile, editing, hasGoal])

  // profile 更新时若已有推荐/已失败/已在重试中则不重刷；若仍为空则再试一次
  useEffect(() => {
    if (hasProfile && !editing && !hasGoal && recs.length === 0 && !recsFetchFailed && !recsRetryTimer.current) {
      doFetchRecs()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileUpdatedAt])

  const retryFetchRecs = () => {
    recsRefetchCount.current = 0
    doFetchRecs()
  }

  // Reset name prompt guard when profile is deleted/cleared
  useEffect(() => {
    if (!hasProfile) {
      namePromptShown.current = false
    }
  }, [hasProfile])

  // Name prompt — after profile + recs are loaded, if no name set yet
  useEffect(() => {
    if (
      hasProfile &&
      !loading &&
      !recsLoading &&
      !profile?.name &&
      !namePromptShown.current &&
      !showNamePrompt
    ) {
      namePromptShown.current = true
      setPendingName('')
      setShowNamePrompt(true)
    }
  }, [hasProfile, loading, recsLoading, profile?.name, showNamePrompt])

  // After upload: fire coach greeting AFTER recommendations are ready
  const coachTriggered = useRef(false)
  useEffect(() => {
    if (coachTriggered.current) return
    if (!justUploaded || loading || !hasProfile) return
    if (recsLoading || recs.length === 0) return
    coachTriggered.current = true
    clearJustUploaded()
    const topLabels = recs.slice(0, 4).map(r => r.label).join('、')
    dispatchCoachTrigger('resume-uploaded', `用户刚上传了简历，画像已生成。系统推荐方向：${topLabels}。`)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [justUploaded, hasProfile, loading, recsLoading, recs])

  function handleNameConfirm() {
    if (!pendingName.trim()) return
    setShowNamePrompt(false)
    // Save name in background — no need to block UI
    rawFetch('/profiles/name', {
      method: 'PATCH',
      body: JSON.stringify({ name: pendingName.trim() }),
    })
      .then(() => loadProfile())
      .catch(console.error)
  }

  // Clear newSkill param after display
  useEffect(() => {
    if (newSkillParam) {
      const timer = setTimeout(() => {
        setSearchParams({}, { replace: true })
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [newSkillParam, setSearchParams])

  const handleManualEntry = () => {
    setEditing(true)
  }

  if (loading) return <ProfileSkeleton />
  if (loadError) return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-6">
      <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center">
        <AlertTriangle className="w-6 h-6 text-red-400" />
      </div>
      <div>
        <p className="text-[15px] font-semibold text-slate-700 mb-1">画像加载失败</p>
        <p className="text-[12px] text-slate-400">{loadError}</p>
      </div>
      <button
        onClick={loadProfile}
        className="px-4 py-2 rounded-xl bg-blue-50 text-blue-600 text-[13px] font-semibold hover:bg-blue-100 transition-colors cursor-pointer"
      >
        重新加载
      </button>
    </div>
  )
  const fromParam = searchParams.get('from')
  const profileHint = fromParam === 'goal-set'
    ? '建立画像后才能计算你与目标岗位的真实差距，先完善你的背景信息吧 →'
    : undefined
  if (!hasProfile && !editing) return <ProfileEmptyState onUpload={triggerFileDialog} onManualEntry={handleManualEntry} hint={profileHint} />
  if (!hasProfile && editing) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => setEditing(false)} className="w-8 h-8 rounded-full bg-white border border-slate-200 flex items-center justify-center hover:bg-slate-50 cursor-pointer transition-colors">
            <ArrowUpRight className="w-4 h-4 text-slate-500 rotate-[-135deg]" />
          </button>
          <h1 className="text-[18px] font-bold text-slate-800">手动创建画像</h1>
        </div>
        <ManualProfileForm
          onSave={async (data) => {
            await handleSaveEdit(data)
            setEditing(false)
          }}
          onCancel={() => setEditing(false)}
          saving={savingEdit}
        />
      </div>
    )
  }

  const { name, updated_at, profile: prof } = profile!

  // Left Panel Data
  const skills = prof.skills ?? []
  const gapTotal = goal?.gap_skills?.length ?? 0

  // Right Panel Data
  const rawProjects = prof.projects ?? []
  const projects = rawProjects.map((p: unknown) => {
    if (typeof p === 'string') return p
    if (typeof p === 'object' && p !== null) {
      const obj = p as Record<string, unknown>
      const name = obj.project_name || obj.name || obj.title || ''
      const desc = obj.project_description || obj.description || obj.details || obj.desc || ''
      if (typeof name === 'string' && name.trim()) {
        return typeof desc === 'string' && desc.trim() && desc.trim() !== name.trim()
          ? `${name.trim()} — ${desc.trim()}`
          : name.trim()
      }
      if (typeof desc === 'string' && desc.trim()) return desc.trim()
    }
    return String(p)
  })
  const education = prof.education ?? {}
  const experienceYears = prof.experience_years ?? 0
  const knowledgeAreas = prof.knowledge_areas ?? []
  const softSkills = prof.soft_skills
  const rawInternships = (prof.internships ?? []) as unknown[]
  const internships = rawInternships.map((item) => {
    if (typeof item === 'string') return { company: item, role: '', highlights: '' }
    const obj = item as Record<string, unknown>
    return {
      company: String(obj.company ?? obj.title ?? ''),
      role: String(obj.role ?? obj.position ?? ''),
      duration: obj.duration ? String(obj.duration) : undefined,
      tech_stack: Array.isArray(obj.tech_stack) ? obj.tech_stack.map(String) : undefined,
      highlights: typeof obj.highlights === 'string' ? obj.highlights
        : Array.isArray(obj.highlights) ? obj.highlights.join('；')
        : typeof obj.highlights === 'object' && obj.highlights ? JSON.stringify(obj.highlights)
        : '',
      tier: obj.tier ? String(obj.tier) : undefined,
    }
  })
  const certificates = (prof.certificates ?? [])
    .map((c: unknown) => {
      if (typeof c === 'string') return c
      if (c && typeof c === 'object') {
        const obj = c as Record<string, unknown>
        const name = obj.certificate_name || obj.name || obj.title || obj.cert_name
        if (typeof name === 'string' && name.trim()) return name.trim()
      }
      return ''
    })
    .filter((c): c is string => c.length > 0)

  const sjtDims = ['communication', 'learning', 'collaboration', 'innovation', 'resilience'] as const
  const DIM_LABEL: Record<string, string> = {
    communication: '沟通', learning: '学习', collaboration: '协作', innovation: '创新', resilience: '抗压',
  }
  const hasSjtResults = !!(softSkills && (softSkills as Record<string, unknown>)?._version === 2
    && sjtDims.some(d => (softSkills as Record<string, unknown>)?.[d] != null))

  const directionRecs = recs.sort((a, b) => b.affinity_pct - a.affinity_pct)

  return (
    <div className="max-w-[1000px] mx-auto px-4 py-6 flex gap-6 items-start">
      
      {/* 左栏 */}
      <div className="w-[280px] shrink-0 sticky top-20 max-h-[calc(100vh-5rem)] overflow-y-auto no-scrollbar" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
        <div className="glass-static p-6 hover:border-slate-300/60 transition-colors duration-200">
          <div className="g-inner flex flex-col gap-5">
            {/* A. 身份区 */}
            <div className="flex items-center gap-3">
              <div 
                className="w-11 h-11 rounded-xl flex items-center justify-center text-[16px] font-bold text-[var(--blue)]"
                style={{ background: 'rgba(37,99,235,0.10)', border: '1px solid rgba(37,99,235,0.18)' }}
              >
                {name?.charAt(0) || 'U'}
              </div>
              <div>
                <p className="text-[16px] font-semibold text-slate-800">{name}</p>
                <p className="text-[11px] text-slate-400">更新于 {updated_at?.slice(0, 10)}</p>
              </div>
            </div>

            {/* B. 核心指标 */}
            {hasGoal ? (
              <>
                <div className="rounded-xl border border-white/30 bg-white/10 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="w-3.5 h-3.5 text-[var(--blue)]" />
                    <span className="text-[13px] font-semibold text-slate-700 truncate">{goal!.target_label}</span>
                  </div>
                  <div className="text-[12px] text-slate-500 space-y-1">
                    {gapTotal > 0 && (
                      <p>差距技能 {gapTotal} 项待补</p>
                    )}
                  </div>
                  <button
                    onClick={() => navigate('/growth-log')}
                    className="mt-2 w-full text-[12px] font-semibold text-[var(--blue)] hover:text-blue-700 transition-colors cursor-pointer text-left"
                  >
                    去成长档案追踪 &rarr;
                  </button>
                </div>
                {/* 更换目标 — 次要操作 */}
                <button
                  onClick={() => setShowChangeGoalConfirm(true)}
                  className="flex items-center justify-center gap-1.5 py-2 text-[11px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-3 h-3" /> 更换目标方向
                </button>
              </>
            ) : (
              <>
                <div className="flex justify-center">
                  {isLocating ? (
                    <div className="flex flex-col items-center gap-1.5">
                      <div className="w-[60px] h-[60px] rounded-full bg-blue-50 border-2 border-blue-200 flex items-center justify-center">
                        <svg className="w-6 h-6 text-blue-400 animate-spin" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"/>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
                        </svg>
                      </div>
                      <span className="text-[12px] font-medium text-blue-500">AI 定位中...</span>
                      <span className="text-[10px] text-slate-400 text-center leading-relaxed">正在匹配最适合的方向</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-1.5">
                      <div className="w-[60px] h-[60px] rounded-full bg-emerald-50 border-2 border-emerald-200 flex items-center justify-center">
                        <Check className="w-6 h-6 text-emerald-500" />
                      </div>
                      <span className="text-[12px] font-medium text-slate-500">画像已建立</span>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => {
                    // Scroll to recommendations section
                    document.getElementById('recs-section')?.scrollIntoView({ behavior: 'smooth' })
                  }}
                  className="w-full py-3 rounded-xl btn-cta text-[13px] font-semibold cursor-pointer"
                >
                  选择目标方向
                </button>
              </>
            )}

            {/* D. 软技能迷你状态 */}
            <button 
              onClick={() => {
                if (editing) setEditing(false)
                setTimeout(() => sjtRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
              }}
              className="rounded-xl border border-white/30 bg-white/10 p-3 text-left w-full hover:bg-white/20 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-2 mb-1.5">
                <Brain className="w-3.5 h-3.5 text-[var(--blue)]" />
                <span className="text-[12px] font-semibold text-slate-600">
                  {hasSjtResults ? '软技能：已评估' : '软技能：未评估'}
                </span>
              </div>
              {hasSjtResults && (
                <div className="flex flex-wrap gap-1.5">
                  {sjtDims.map(d => {
                    const dim = (softSkills as Record<string, { level?: string } | undefined>)?.[d]
                    if (!dim?.level) return null
                    return (
                      <span key={d} className="text-[10px] text-slate-500 bg-white/40 px-1.5 py-0.5 rounded">
                        {DIM_LABEL[d]}:{dim.level}
                      </span>
                    )
                  })}
                </div>
              )}
            </button>

            {/* 上传进度 */}
            {uploading && <UploadProgress step={uploadStep} />}
            {uploadError && !uploading && (
              <div className="px-3 py-2 bg-red-50 border border-red-200 text-[11px] text-red-700 rounded-xl">
                {uploadError}
              </div>
            )}

            {/* E. 操作按钮 */}
            <div className="flex gap-2 pt-2" style={{ borderTop: '1px solid rgba(255,255,255,0.38)' }}>
              <input ref={fileInputRef} type="file" accept=".pdf,.doc,.docx" className="hidden" onChange={onFileSelected} />
              <label
                onClick={triggerFileDialog}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-[#2563EB] text-white text-[12px] font-semibold cursor-pointer hover:bg-blue-700 transition-colors ${uploading ? 'opacity-60 pointer-events-none' : ''}`}
              >
                <Upload className="w-3.5 h-3.5" />
                {uploading ? '上传中...' : '补充画像'}
              </label>
              
              <button 
                onClick={() => setEditing(true)}
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-[12px] font-semibold text-slate-600 btn-glass cursor-pointer"
              >
                <PenLine className="w-3.5 h-3.5" />
                编辑画像
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 右栏 */}
      <div className="flex-1 min-w-0">
        {editing ? (
          <ManualProfileForm
            onSave={async (data) => {
              await handleSaveEdit(data)
              setEditing(false)
            }}
            onCancel={() => setEditing(false)}
            saving={savingEdit}
            initialData={{
              name: name || '',
              education: {
                degree: (education as { degree?: string }).degree || '',
                major: (education as { major?: string }).major || '',
                school: (education as { school?: string }).school || '',
              },
              experience_years: experienceYears,
              job_target: (prof.job_target as string) || '',
              skills: skills,
              knowledge_areas: knowledgeAreas,
              projects: projects,
              internships: internships,
              certificates: certificates,
              awards: (prof.awards ?? [])
                .map((a: unknown) => {
                  if (typeof a === 'string') return a
                  if (a && typeof a === 'object') {
                    const obj = a as Record<string, unknown>
                    const name = obj.award_name || obj.name || obj.title
                    if (typeof name === 'string' && name.trim()) return name.trim()
                  }
                  return ''
                })
                .filter((a): a is string => a.length > 0),
            }}
          />
        ) : (
          <div className="space-y-8 pb-12">

            {/* JD 诊断常驻入口 */}
            <div className="glass-static p-5 flex items-center justify-between hover:border-slate-300/60 transition-colors duration-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
                  <Crosshair className="w-5 h-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-[14px] font-semibold text-slate-700">诊断目标岗位</p>
                  <p className="text-[12px] text-slate-400">粘贴 JD，看自己与岗位的真实差距</p>
                </div>
              </div>
              <button
                onClick={() => navigate('/jd-diagnosis')}
                className="px-4 py-2 rounded-lg bg-[var(--blue)] text-white text-[12px] font-semibold hover:brightness-110 transition-all cursor-pointer"
              >
                去诊断
              </button>
            </div>

            {/* 区块 1：有目标 → 目标概览卡  |  无目标 → 推荐方向 */}
            {hasGoal ? (
              <div className="glass-static p-6 hover:border-slate-300/60 transition-colors duration-200">
                <div className="g-inner">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">目标方向</p>
                      <h3 className="text-[18px] font-bold text-slate-800 mb-1">{goal!.target_label}</h3>
                      <p className="text-[12px] text-slate-500">
                        {gapTotal > 0
                          ? `差距技能 ${gapTotal} 项待补 · 通过实战项目逐项跨过`
                          : '技能已全部覆盖，继续深化经验'}
                      </p>
                    </div>
                    <button
                      onClick={() => navigate('/growth-log')}
                      className="shrink-0 px-4 py-2 bg-blue-600 text-white text-[12px] font-semibold rounded-xl hover:bg-blue-700 transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      去成长档案追踪 <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  {Array.isArray(goal!.gap_skills) && goal!.gap_skills.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/40">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">差距技能</p>
                      <div className="flex flex-wrap gap-1.5">
                        {goal!.gap_skills.slice(0, 8).map(s => (
                          <span
                            key={s}
                            className="text-[11px] px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 font-medium border border-blue-100 hover:scale-[1.05] hover:shadow-sm transition-all duration-150 cursor-default"
                          >
                            {s}
                          </span>
                        ))}
                        {goal!.gap_skills.length > 8 && (
                          <span className="text-[11px] text-slate-400 px-1">
                            +{goal!.gap_skills.length - 8} 项
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (recsLoading || (hasProfile && !hasGoal && recs.length === 0 && !recsFetchFailed)) ? (
              <div className="space-y-3">
                {(isLocating || (hasProfile && !hasGoal && recs.length === 0)) && (
                  <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-blue-50/60 border border-blue-100">
                    <svg className="w-4 h-4 text-blue-400 animate-spin shrink-0" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
                    </svg>
                    <div>
                      <p className="text-[13px] font-semibold text-blue-700">AI 正在分析你的技术方向</p>
                      <p className="text-[11px] text-blue-400 mt-0.5">根据简历技能匹配最适合的职业路径，通常需要 1-3 分钟</p>
                    </div>
                  </div>
                )}
                <div className="animate-pulse space-y-4">
                  <div className="h-4 bg-slate-200 rounded w-1/4"></div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="h-32 bg-slate-200 rounded-xl"></div>
                    <div className="h-32 bg-slate-200 rounded-xl"></div>
                    <div className="h-32 bg-slate-200 rounded-xl"></div>
                    <div className="h-32 bg-slate-200 rounded-xl"></div>
                  </div>
                </div>
              </div>
            ) : (hasProfile && !hasGoal && recs.length === 0 && recsFetchFailed) ? (
              <div className="flex items-start gap-3 px-4 py-4 rounded-xl bg-amber-50 border border-amber-100">
                <svg className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-semibold text-amber-800">暂时没拿到推荐</p>
                  <p className="text-[11px] text-amber-600 mt-0.5">AI 服务可能繁忙，过一会儿再试。</p>
                  <button
                    onClick={retryFetchRecs}
                    className="mt-2 text-[12px] font-semibold text-amber-700 border-b border-amber-700 pb-0.5 hover:text-amber-900 hover:border-amber-900 cursor-pointer"
                  >
                    重试 →
                  </button>
                </div>
              </div>
            ) : (
              <div id="recs-section">
                {/* Guidance text — show top skills as trust anchor */}
                {directionRecs.length > 0 && skills.length > 0 && (
                  <p className="text-[13px] text-slate-500 mb-4 leading-relaxed">
                    基于你的
                    <span className="font-semibold text-slate-700">
                      {' '}{skills.slice(0, 4).map(s => s.name).join('、')}{' '}
                    </span>
                    等技能背景，以下方向与你的经历最为契合。点击了解详情，不急着做决定。
                  </p>
                )}
                {directionRecs.length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Target className="w-3.5 h-3.5 text-slate-400" />
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">推荐方向</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      {directionRecs.map(rec => (
                        <RecommendationCard key={rec.role_id} rec={rec} onExplore={(r) => navigate(`/roles/${r.role_id}`)} />
                      ))}
                    </div>
                  </div>
                )}

              </div>
            )}

            {/* 区块 1.5：就业意愿 */}
            <PreferencesCard
              initialPreferences={(profile?.profile?.preferences as any) ?? null}
              onSaved={() => loadProfile()}
            />

            {/* 区块 2：技能 + 项目 (双列) */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <SectionHeader title="技能" count={skills.length + '项'} />
                <SkillsCard 
                  skills={skills} 
                  stagger={0.08} 
                  cardVariants={cardVariants} 
                />
              </div>
              <div>
                <SectionHeader title="项目" count={projects.length + '项'} />
                <ProjectsCard 
                  projects={projects} 
                  stagger={0.08} 
                  cardVariants={cardVariants} 
                />
              </div>
            </div>

            {/* 区块 2.5：实习经历 + 证书 (仅当有数据时显示) */}
            {(internships.length > 0 || certificates.length > 0) && (
              <div className="glass-static p-5 hover:border-slate-300/60 transition-colors duration-200">
                <div className="g-inner space-y-4">

                  {/* 实习经历 */}
                  {internships.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <h2 className="text-[14px] font-bold text-slate-800">实习经历</h2>
                        <span className="text-[11px] font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-md">{internships.length} 段</span>
                        {internships.filter(i => i.tier === '顶级大厂').length > 0 && (
                          <span className="ml-auto text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                            {internships.filter(i => i.tier === '顶级大厂').length} 顶级大厂
                          </span>
                        )}
                      </div>
                      <div className="space-y-2.5">
                        {internships.map((intern, idx) => (
                          <div key={idx} className="flex items-start gap-3">
                            {/* 时间线点 */}
                            <div className="mt-1.5 flex-shrink-0">
                              <div className={`w-2 h-2 rounded-full ring-2 ${
                                intern.tier === '顶级大厂'
                                  ? 'bg-blue-500 ring-blue-100'
                                  : 'bg-slate-300 ring-slate-100'
                              }`} />
                            </div>
                            <div className="flex-1 min-w-0 pb-2.5 border-b border-slate-50 last:border-0 last:pb-0">
                              <div className="flex items-start justify-between gap-2 mb-1">
                                <div className="min-w-0">
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="text-[13px] font-bold text-slate-800">{intern.company}</span>
                                    {intern.tier && (
                                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-[5px] ${
                                        intern.tier === '顶级大厂'
                                          ? 'bg-blue-50 text-blue-600'
                                          : 'bg-slate-100 text-slate-500'
                                      }`}>{intern.tier}</span>
                                    )}
                                  </div>
                                  <p className="text-[11px] text-slate-500 mt-0.5">{intern.role}</p>
                                </div>
                                {intern.duration && (
                                  <span className="text-[10px] text-slate-400 shrink-0 whitespace-nowrap">{intern.duration}</span>
                                )}
                              </div>
                              {intern.highlights && (
                                <p className="text-[11px] text-slate-600 leading-relaxed mb-1.5">{intern.highlights}</p>
                              )}
                              {intern.tech_stack && intern.tech_stack.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {intern.tech_stack.slice(0, 5).map(t => (
                                    <span key={t} className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">{t}</span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 分割线（两个区块都有时显示） */}
                  {internships.length > 0 && certificates.length > 0 && (
                    <div className="h-px bg-slate-100" />
                  )}

                  {/* 证书 */}
                  {certificates.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-2.5">
                        <h2 className="text-[14px] font-bold text-slate-800">证书</h2>
                        <span className="text-[11px] font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-md">{certificates.length} 项</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {certificates.map((cert, idx) => (
                          <span key={idx} className="flex items-center gap-1 px-2.5 py-1 rounded-[8px] text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-100">
                            <svg className="w-3 h-3 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                            </svg>
                            {cert}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                </div>
              </div>
            )}

            {/* 区块 3：教育 + 软技能 (双列) */}
            <div className="grid grid-cols-2 gap-4" ref={sjtRef}>
              <div>
                <SectionHeader title="教育 & 经验" />
                <EducationCard 
                  education={education} 
                  experienceYears={experienceYears} 
                  stagger={0.08} 
                  cardVariants={cardVariants} 
                />
                
                {knowledgeAreas.length > 0 && (
                  <div className="mt-4">
                    <SectionHeader title="知识领域" />
                    <KnowledgeCard 
                      knowledgeAreas={knowledgeAreas} 
                      stagger={0.08} 
                      cardVariants={cardVariants} 
                    />
                  </div>
                )}
              </div>
              <div>
                <SectionHeader title="软技能" />
                {showSjtInline ? (
                  <SjtCtaCard 
                    onComplete={() => { 
                      setShowSjtInline(false)
                      loadProfile() 
                    }} 
                  />
                ) : (
                  <SoftSkillsCard
                    softSkills={softSkills}
                    onStartAssessment={() => setShowSjtInline(true)}
                  />
                )}
              </div>
            </div>

          </div>
        )}
      </div>

      {/* Change goal confirmation modal */}
      <AnimatePresence>
        {showChangeGoalConfirm && goal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-slate-900/30 backdrop-blur-sm z-[999] flex items-center justify-center p-4"
            onClick={() => setShowChangeGoalConfirm(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full"
              onClick={e => e.stopPropagation()}
            >
              <div className="w-12 h-12 rounded-xl bg-amber-50 flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="w-6 h-6 text-amber-500" />
              </div>
              <h3 className="text-[16px] font-bold text-slate-800 text-center mb-2">
                确认更换目标方向？
              </h3>
              <div className="text-[13px] text-slate-500 space-y-1.5 mb-5">
                <p>你当前的目标方向是「{goal.target_label}」。</p>
                <p className="text-slate-400">更换目标后：</p>
                <ul className="text-[12px] text-slate-400 space-y-1 pl-1">
                  <li>✅ 已掌握的技能会保留在画像中</li>
                  <li>🔄 差距分析将基于新目标重新计算</li>
                  <li>📚 学习路径将切换到新方向</li>
                </ul>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowChangeGoalConfirm(false)}
                  className="flex-[2] py-2.5 rounded-xl text-[13px] font-bold btn-cta cursor-pointer"
                >
                  继续当前目标
                </button>
                <button
                  onClick={async () => {
                    // Clear goal — set is_primary=false by re-setting without a target
                    // For now, navigate to recommendations to pick a new one
                    setShowChangeGoalConfirm(false)
                    // Clear the current goal from server
                    await setCareerGoal({
                      profile_id: profile!.id,
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
                  className="flex-1 py-2.5 rounded-xl text-[13px] font-medium text-slate-500 btn-glass cursor-pointer"
                >
                  确认更换
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Name prompt — shown after first upload, once profile + recs are loaded */}
      {showNamePrompt && (
        <div className="fixed inset-0 bg-slate-900/30 backdrop-blur-sm z-[999] flex items-center justify-center p-6">
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full" onClick={e => e.stopPropagation()}>
            <h3 className="text-[16px] font-bold text-slate-800 mb-2">为你的画像命名</h3>
            <p className="text-[12px] text-slate-400 mb-4">画像已建立完成，请确认或修改你的姓名</p>
            <input
              type="text"
              value={pendingName}
              onChange={e => setPendingName(e.target.value)}
              className="w-full px-3 py-2 text-[14px] border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-200 mb-4"
              placeholder="请输入姓名"
              autoFocus
              onKeyDown={e => e.key === 'Enter' && handleNameConfirm()}
            />
            <button
              onClick={handleNameConfirm}
              disabled={!pendingName.trim()}
              className="w-full btn-cta py-2 text-[14px] font-semibold cursor-pointer disabled:opacity-50"
            >
              确认
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
