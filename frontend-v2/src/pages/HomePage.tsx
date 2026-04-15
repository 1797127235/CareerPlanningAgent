import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Kicker, Chapter, PaperCard } from '@/components/editorial'
import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'
import { useResumeUpload } from '@/hooks/useResumeUpload'
import { fetchReportList, type ReportListItem } from '@/api/report'
import { getActivityPulse, type ActivityPulseData } from '@/api/growthLog'

function useReportMeta(enabled: boolean) {
  const [report, setReport] = useState<ReportListItem | null>(null)
  useEffect(() => {
    if (!enabled) return
    fetchReportList()
      .then((list) => setReport(list[0] ?? null))
      .catch(() => setReport(null))
  }, [enabled])
  return report
}

function useActivityPulse(enabled: boolean) {
  const [pulse, setPulse] = useState<ActivityPulseData | null>(null)
  useEffect(() => {
    if (!enabled) return
    getActivityPulse()
      .then((data) => setPulse(data))
      .catch(() => setPulse(null))
  }, [enabled])
  return pulse
}

function formatRelativeTime(iso: string | null | undefined) {
  if (!iso) return '未知时间'
  const diff = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  if (days < 1) return '今天'
  if (days < 2) return '昨天'
  if (days < 30) return `${days} 天前`
  if (days < 365) return `${Math.floor(days / 30)} 个月前`
  return `${Math.floor(days / 365)} 年前`
}

export default function HomePage() {
  const { isAuthenticated } = useAuth()
  const { profile } = useProfileData(isAuthenticated)
  const navigate = useNavigate()

  const { uploading, uploadStep, uploadError, fileInputRef, triggerFileDialog, onFileSelected } =
    useResumeUpload(async () => {
      navigate('/profile')
    })

  const hasProfile = isAuthenticated && !!(
    profile?.profile?.skills?.length ||
    profile?.profile?.knowledge_areas?.length ||
    profile?.profile?.projects?.length ||
    profile?.profile?.internships?.length ||
    profile?.profile?.education?.school ||
    profile?.name
  )

  const report = useReportMeta(hasProfile)
  const pulse = useActivityPulse(hasProfile)

  const sectionsCompleted = [
    !!profile?.name,
    !!profile?.profile?.education?.school,
    ((profile?.profile?.internships?.length ?? 0) > 0) || ((profile?.profile?.projects?.length ?? 0) > 0),
    (profile?.profile?.skills?.length ?? 0) > 0,
    Object.keys((profile?.profile?.soft_skills as Record<string, unknown>) ?? {}).filter((k) => k !== '_version').length > 0,
    (profile?.career_goals?.length ?? 0) > 0,
  ].filter(Boolean).length

  let title: string
  let subtitle: string
  let primaryLabel: string
  let primaryAction: () => void
  let secondaryLabel: string
  let secondaryAction: () => void

  if (!isAuthenticated) {
    title = '一份只给你自己的档案'
    subtitle = '从简历解析到成长轨迹，职途智析帮你把零散的履历整理成清晰的路径。'
    primaryLabel = '开始建立档案'
    primaryAction = () => navigate('/login')
    secondaryLabel = '看看演示'
    secondaryAction = () => navigate('/__demo')
  } else if (!hasProfile) {
    title = '还没开始讲给我听呢'
    subtitle = '上传一份简历，或者手动填写几笔，我们就能开始整理你的职业画像。'
    primaryLabel = uploading ? `上传中（${uploadStep + 1}/4）…` : '上传简历'
    primaryAction = triggerFileDialog
    secondaryLabel = '手动填写'
    secondaryAction = () => navigate('/profile')
  } else {
    title = '你回来了'
    subtitle = `欢迎回来${profile?.name ? '，' + profile.name : ''}。你的画像、报告和成长日志都在等你。`
    primaryLabel = '查看画像'
    primaryAction = () => navigate('/profile')
    secondaryLabel = '去成长日志'
    secondaryAction = () => navigate('/growth-log')
  }

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.doc,.docx,.txt"
        className="hidden"
        onChange={onFileSelected}
      />

      <section className="min-h-[60vh] flex flex-col justify-center px-6 md:px-12 lg:px-20 py-20">
        <div className="max-w-[720px] mx-auto w-full">
          <Kicker>EDITORIAL · 职途智析</Kicker>
          <p className="font-serif italic text-[clamp(28px,4vw,42px)] text-[var(--chestnut)] mb-4">
            职途智析
          </p>
          <h1 className="font-display font-medium text-[length:var(--fs-display-xl)] leading-[var(--lh-display)] tracking-tight text-[var(--ink-1)]">
            {title}
          </h1>
          <p className="mt-6 font-sans text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[48ch]">
            {subtitle}
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-6">
            <button
              onClick={primaryAction}
              disabled={uploading}
              className="inline-flex items-center justify-center px-6 py-3 rounded-full bg-[var(--chestnut)] text-white text-[15px] font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {primaryLabel}
            </button>
            <button
              onClick={secondaryAction}
              className="text-[var(--ink-2)] hover:text-[var(--ink-1)] underline underline-offset-4 transition-colors text-[15px]"
            >
              {secondaryLabel}
            </button>
          </div>
          {uploadError && (
            <p className="mt-4 text-[var(--ember)] text-[13px]">{uploadError}</p>
          )}
        </div>
      </section>

      {hasProfile && (
        <div className="px-6 md:px-12 lg:px-20 pb-20">
          <div className="max-w-[720px] mx-auto w-full">
            <Chapter numeral="I" label="你的路径" title="从这里继续">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <PaperCard className="group cursor-pointer" onClick={() => navigate('/profile')}>
                  <Kicker>画像</Kicker>
                  <h3 className="font-display font-medium text-[length:var(--fs-body-lg)] text-[var(--ink-1)]">
                    {profile?.name || '我的画像'}
                  </h3>
                  <p className="mt-2 text-[length:var(--fs-body-sm)] text-[var(--ink-2)]">
                    已完成 {sectionsCompleted} / 6 个章节
                  </p>
                  <div className="mt-4 flex items-center text-[length:var(--fs-body-sm)] text-[var(--chestnut)] font-medium">
                    <span>去查看</span>
                    <ArrowRight className="ml-1 w-4 h-4 transition-transform group-hover:translate-x-0.5" />
                  </div>
                </PaperCard>

                <PaperCard className="group cursor-pointer" onClick={() => navigate('/report')}>
                  <Kicker>报告</Kicker>
                  <h3 className="font-display font-medium text-[length:var(--fs-body-lg)] text-[var(--ink-1)]">
                    职业分析报告
                  </h3>
                  <p className="mt-2 text-[length:var(--fs-body-sm)] text-[var(--ink-2)]">
                    {report ? `上次生成于 ${formatRelativeTime(report.created_at)}` : '还没生成'}
                  </p>
                  <div className="mt-4 flex items-center text-[length:var(--fs-body-sm)] text-[var(--chestnut)] font-medium">
                    <span>{report ? '查看报告' : '去生成'}</span>
                    <ArrowRight className="ml-1 w-4 h-4 transition-transform group-hover:translate-x-0.5" />
                  </div>
                </PaperCard>

                <PaperCard className="group cursor-pointer" onClick={() => navigate('/growth-log')}>
                  <Kicker>成长</Kicker>
                  <h3 className="font-display font-medium text-[length:var(--fs-body-lg)] text-[var(--ink-1)]">
                    成长日志
                  </h3>
                  <p className="mt-2 text-[length:var(--fs-body-sm)] text-[var(--ink-2)]">
                    {pulse ? `${pulse.total_records} 条笔记` : '还空着'}
                  </p>
                  <div className="mt-4 flex items-center text-[length:var(--fs-body-sm)] text-[var(--chestnut)] font-medium">
                    <span>{pulse && pulse.total_records > 0 ? '去回顾' : '去记录'}</span>
                    <ArrowRight className="ml-1 w-4 h-4 transition-transform group-hover:translate-x-0.5" />
                  </div>
                </PaperCard>
              </div>
            </Chapter>
          </div>
        </div>
      )}
    </main>
  )
}
