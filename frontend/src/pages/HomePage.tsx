import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { motion } from 'framer-motion'
import { ArrowRight, Upload, PenLine, MapPin, Target, User, Flame, BookOpen, FileSearch, Zap } from 'lucide-react'
import { UploadProgress } from '@/components/profile'
import { useGuidance } from '@/hooks/useGuidance'
import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'
import { useResumeUpload } from '@/hooks/useResumeUpload'
import { useDashboardStats } from '@/hooks/useDashboard'
import { useActivityHeatmap } from '@/hooks/useActivityHeatmap'
import { SignatureHero } from '@/components/SignatureHero'
import { ActivityHeatmap } from '@/components/ActivityHeatmap'

const ease = [0.23, 1, 0.32, 1] as const

/* ── Zone label map ── */
const zoneLabel: Record<string, { text: string; color: string }> = {
  safe:       { text: '安全区', color: 'text-emerald-600 bg-emerald-50' },
  thrive:     { text: '成长区', color: 'text-blue-600 bg-blue-50' },
  transition: { text: '转型区', color: 'text-amber-600 bg-amber-50' },
  danger:     { text: '风险区', color: 'text-red-500 bg-red-50' },
}



/* ═══════════════════════════════════════════════
   HomePage — welcome / guidance landing
   ═══════════════════════════════════════════════ */
export default function HomePage() {
  const navigate = useNavigate()
  const { data: guidance } = useGuidance('home')
  const { token } = useAuth()
  const { profile, loading: profileLoading, loadProfile, handleDelete, deleteConfirm, setDeleteConfirm } = useProfileData(token)
  const { data: stats } = useDashboardStats(profile?.id ?? null)
  const { data: heatmapData } = useActivityHeatmap(52)
  const { fileInputRef, triggerFileDialog, onFileSelected, uploading, uploadStep, uploadError } = useResumeUpload(loadProfile)

  const hasProfile = (profile?.profile?.skills?.length ?? 0) > 0
    || (profile?.profile?.experience_years ?? 0) > 0
    || !!profile?.profile?.education?.school
  const graphPos = profile?.graph_position
  const careerGoals = profile?.career_goals ?? []
  const extraGoalCount = careerGoals.length > 1 ? careerGoals.length - 1 : 0
  // 有手动设目标时 target_node_id != from_node_id
  const hasGoal = !!(graphPos && graphPos.target_node_id && graphPos.target_node_id !== graphPos.from_node_id)
  const zone = graphPos?.target_zone ? zoneLabel[graphPos.target_zone] : null
  const skillCount = profile?.profile?.skills?.length ?? 0

  return (
    <div className="flex flex-col items-center h-full w-full px-4 sm:px-6 overflow-y-auto">
      <input id="home-file-input" ref={fileInputRef} type="file" accept=".pdf,.doc,.docx" className="hidden" onChange={onFileSelected} />
      {(!profileLoading && !hasProfile) ? (
        /* ── Cold-start: editorial onboarding ── */
        <div className="flex items-center justify-center flex-1 w-full">
          <div className="w-full max-w-[600px]">

            {/* Upload progress / error */}
            {uploading && <div className="mb-6"><UploadProgress step={uploadStep} /></div>}
            {uploadError && !uploading && (
              <div className="mb-6 px-4 py-3 bg-red-50 border border-red-200 text-sm text-red-700 rounded-xl">
                {uploadError}
              </div>
            )}

            {/* Headline */}
            <motion.h2
              initial={{ opacity: 0, y: 22, filter: 'blur(8px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{ delay: 0.08, duration: 0.6, ease }}
              className="text-[52px] font-bold text-slate-900 leading-[1.15] tracking-tight mb-5"
            >
              还没想清楚<br />
              <span className="text-gradient-hero">去哪、差什么</span>？
            </motion.h2>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.22, duration: 0.45, ease }}
              className="text-[16px] text-slate-500 leading-relaxed mb-8"
            >
              上传简历，告诉我你是谁——<br />
              我来帮你找方向、准备面试、分析差距。
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.58, duration: 0.35, ease }}
              className="flex items-center gap-4"
            >
              <label
                htmlFor="home-file-input"
                className="flex items-center gap-2 px-7 py-3.5 rounded-xl bg-[var(--blue)] text-white text-[15px] font-semibold hover:brightness-110 transition-all cursor-pointer shadow-lg shadow-blue-500/25"
              >
                <Upload className="w-4 h-4" />
                上传简历
              </label>
              <button
                onClick={() => navigate('/profile')}
                className="flex items-center gap-2 px-4 py-3.5 text-slate-500 text-[14px] font-medium hover:text-slate-800 transition-colors cursor-pointer"
              >
                <PenLine className="w-4 h-4" />
                手动填写
              </button>
            </motion.div>

          </div>
        </div>
      ) : (
        /* ── Returning user: hero + dashboard content ── */
        <div className="flex flex-col items-center w-full max-w-[860px] pb-12">

          {/* ── Hero section ── */}
          <div className="relative w-full flex flex-col items-center justify-center min-h-[40dvh] pt-8 pb-10">
            <SignatureHero />

            <motion.h1
              initial={{ opacity: 0, y: 22, filter: 'blur(8px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{ delay: 0.08, duration: 0.6, ease }}
              className="text-[52px] font-bold text-slate-900 tracking-tight mb-6 text-center leading-[1.15] relative z-10"
            >
              路不会消失，<br />
              只是还没被<span className="text-gradient-hero">问起</span>
            </motion.h1>

            {guidance?.message && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.9, duration: 0.35 }}
                className={cn(
                  'px-5 py-2.5 rounded-[40px] backdrop-blur-sm flex items-center gap-3 max-w-xl w-full relative z-10',
                  guidance.tone === 'urgent'
                    ? 'bg-amber-50/80 border border-amber-200/80'
                    : guidance.tone === 'celebrating'
                    ? 'bg-blue-50/80 border border-blue-200/80'
                    : 'bg-white/50 border border-white/40',
                )}
              >
                <span className={cn(
                  'text-[13px] flex-1',
                  guidance.tone === 'urgent' ? 'text-amber-800' : guidance.tone === 'celebrating' ? 'text-blue-800' : 'text-slate-600',
                )}>{guidance.message}</span>
                {guidance.cta_text && guidance.cta_route && (
                  <button
                    onClick={() => navigate(guidance.cta_route)}
                    className={cn(
                      'flex items-center gap-1 text-[13px] font-semibold hover:underline whitespace-nowrap cursor-pointer',
                      guidance.tone === 'urgent' ? 'text-amber-700' : 'text-[var(--blue)]',
                    )}
                  >
                    {guidance.cta_text}
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </motion.div>
            )}
          </div>

          {/* ── Dashboard: unified card ── */}
          {hasProfile && (
            <div className="w-full mt-2 page-enter">
              <div className="glass p-6">
                <div className="g-inner flex flex-col gap-5">

                  {/* ── Top row: profile info + metrics + actions ── */}
                  <div className="flex items-center gap-4 flex-wrap">
                    {/* Avatar + name */}
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-[16px] font-bold text-white shrink-0 select-none shadow-sm">
                        {(profile?.name ?? '?').charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <p className="text-[16px] font-semibold text-slate-800 truncate tracking-tight">{profile?.name ?? '我的画像'}</p>
                        <p className="text-[12px] text-slate-400 mt-0.5">更新于 {profile?.updated_at?.slice(0, 10) ?? '--'}</p>
                      </div>
                    </div>

                    {/* Divider */}
                    <div className="w-px h-9 bg-slate-200/60 hidden sm:block" />

                    {/* Inline metrics */}
                    <div className="flex items-center gap-6">
                      {[
                        { label: '技能', value: skillCount, suffix: '项' },
                        ...(stats ? [
                          { label: '诊断', value: stats.jd_diagnosis_count, suffix: '次' },
                          { label: '练习', value: stats.review_count, suffix: '次' },
                          { label: '连续', value: heatmapData?.streak ?? stats.streak_days, suffix: '天' },
                        ] : []),
                      ].map(({ label, value, suffix }) => (
                        <div key={label} className="flex flex-col items-center">
                          <span className="text-[20px] font-bold text-slate-800 tabular-nums leading-none tracking-tight">
                            {value}<span className="text-[12px] font-medium text-slate-400 ml-0.5">{suffix}</span>
                          </span>
                          <span className="text-[12px] text-slate-400 mt-1">{label}</span>
                        </div>
                      ))}
                    </div>

                    {/* Spacer */}
                    <div className="flex-1" />

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {/* Graph position / goal */}
                      {graphPos ? (
                        <button
                          onClick={() => navigate(hasGoal ? `/graph?node=${encodeURIComponent(graphPos.target_node_id)}` : '/graph')}
                          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-left group transition-colors hover:bg-white/30 cursor-pointer"
                        >
                          {hasGoal ? (
                            <>
                              <Target className="w-4 h-4 text-[var(--blue)] shrink-0" />
                              <span className="text-[13px] font-semibold text-slate-700 group-hover:text-[var(--blue)] transition-colors truncate max-w-[140px]">
                                {graphPos.target_label}
                              </span>
                              {zone && (
                                <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ${zone.color}`}>
                                  {zone.text}
                                </span>
                              )}
                            </>
                          ) : (
                            <>
                              <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
                              <div className="flex flex-col">
                                <span className="text-[11px] text-slate-400 leading-tight">当前定位</span>
                                <span className="text-[13px] font-semibold text-slate-600 group-hover:text-[var(--blue)] transition-colors truncate max-w-[120px] leading-tight">
                                  {graphPos.from_node_label || graphPos.target_label}
                                </span>
                              </div>
                            </>
                          )}
                        </button>
                      ) : (
                        <button onClick={() => navigate('/graph')} className="flex items-center gap-1.5 px-3 py-2 rounded-lg hover:bg-white/30 transition-colors cursor-pointer">
                          <MapPin className="w-4 h-4 text-slate-300 shrink-0" />
                          <span className="text-[13px] text-slate-400">探索图谱</span>
                        </button>
                      )}

                      <label
                        htmlFor="home-file-input"
                        className={`flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#2563EB] text-white text-[13px] font-semibold hover:bg-[#1d4ed8] transition-colors cursor-pointer shadow-sm shadow-blue-500/25 ${uploading ? 'opacity-60 pointer-events-none' : ''}`}
                      >
                        <Upload className="w-3.5 h-3.5" />
                        {uploading ? '上传中…' : '补充画像'}
                      </label>
                      <button
                        onClick={() => navigate('/profile')}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-[13px] font-semibold text-slate-600 cursor-pointer transition-all hover:text-slate-800 btn-glass"
                      >
                        <User className="w-3.5 h-3.5" />
                        画像
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(true)}
                        className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50/60 transition-colors cursor-pointer shrink-0"
                        title="重置画像"
                      >
                        <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>
                      </button>
                    </div>
                  </div>

                  {deleteConfirm && (
                    <div className="rounded-xl border border-red-200 bg-red-50 p-4">
                      <p className="text-[14px] font-bold text-red-700 mb-1">确认重置画像？</p>
                      <p className="text-[13px] text-red-500 mb-3">将清空全部技能、项目和背景数据</p>
                      <div className="flex gap-2">
                        <button onClick={handleDelete} className="flex-1 bg-red-600 text-white text-[13px] py-2 rounded-lg font-bold cursor-pointer hover:bg-red-700">
                          确认重置
                        </button>
                        <button onClick={() => setDeleteConfirm(false)} className="flex-1 bg-white text-slate-600 border border-slate-200 text-[13px] py-2 rounded-lg font-bold cursor-pointer hover:bg-slate-50">
                          取消
                        </button>
                      </div>
                    </div>
                  )}

                  {/* ── Journey: next step ── */}
                  {(() => {
                    const jdCount = stats?.jd_diagnosis_count ?? 0
                    const reviewCount = stats?.review_count ?? 0

                    // Determine next step based on journey stage
                    let step: { icon: React.ReactNode; title: string; desc: string; action: string; onClick: () => void } | null = null

                    if (!hasGoal) {
                      step = {
                        icon: <Target className="w-4 h-4 text-[var(--blue)]" />,
                        title: '设定目标岗位',
                        desc: '去图谱页浏览岗位方向，选一个作为成长目标',
                        action: '探索图谱',
                        onClick: () => navigate('/graph'),
                      }
                    } else if (jdCount === 0) {
                      step = {
                        icon: <FileSearch className="w-4 h-4 text-amber-500" />,
                        title: '诊断第一份 JD',
                        desc: '找一份目标岗位的招聘要求，看看你和市场需求的差距',
                        action: '搜索 JD',
                        onClick: () => {
                          import('@/hooks/useCoachTrigger').then(m => m.sendToCoach('帮我搜索目标岗位相关的招聘'))
                        },
                      }
                    } else if (reviewCount === 0) {
                      step = {
                        icon: <Zap className="w-4 h-4 text-purple-500" />,
                        title: '练一道面试题',
                        desc: '根据你的缺口技能出一道面试题，边练边补',
                        action: '开始练习',
                        onClick: () => {
                          import('@/hooks/useCoachTrigger').then(m => m.sendToCoach('根据我的技能缺口，帮我出一道面试题'))
                        },
                      }
                    } else {
                      step = {
                        icon: <BookOpen className="w-4 h-4 text-emerald-500" />,
                        title: '继续学习路径',
                        desc: '按计划补强缺口技能，每完成一项画像自动更新',
                        action: '查看路径',
                        onClick: () => navigate('/profile/learning'),
                      }
                    }

                    return step ? (
                      <button
                        onClick={step.onClick}
                        className="w-full flex items-center gap-4 px-5 py-4 rounded-xl bg-gradient-to-r from-blue-50/60 to-indigo-50/40 border border-blue-100/60 hover:border-blue-200 hover:shadow-sm transition-all cursor-pointer text-left group"
                      >
                        <div className="w-10 h-10 rounded-xl bg-white border border-slate-200/80 flex items-center justify-center shrink-0 shadow-sm">
                          {step.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[14px] font-bold text-slate-800 group-hover:text-[var(--blue)] transition-colors">{step.title}</p>
                          <p className="text-[13px] text-slate-400 mt-0.5 truncate">{step.desc}</p>
                        </div>
                        <span className="text-[13px] font-semibold text-[var(--blue)] shrink-0 group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                          {step.action}
                          <ArrowRight className="w-3.5 h-3.5" />
                        </span>
                      </button>
                    ) : null
                  })()}

                  {/* ── Divider ── */}
                  <div className="h-px bg-slate-200/50" />

                  {/* ── Activity Heatmap (full width) ── */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[14px] font-bold text-slate-700">学习活动</span>
                      <div className="flex items-center gap-3">
                        {heatmapData && heatmapData.streak > 0 && (
                          <span className="flex items-center gap-1 text-[13px] font-semibold text-amber-600">
                            <Flame className="w-4 h-4" /> 连续 {heatmapData.streak} 天
                          </span>
                        )}
                        <span className="text-[12px] text-slate-400">最近一年</span>
                      </div>
                    </div>
                    <ActivityHeatmap days={heatmapData?.days ?? []} weeks={52} />
                  </div>

                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
