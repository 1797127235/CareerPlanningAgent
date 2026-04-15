import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Block, BlockGrid } from '@/components/ui'
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
    title = `你回来了${profile?.name ? '，' + profile.name : ''}`
    subtitle = '你的画像、报告和成长日志都在等你。'
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

      <div className="max-w-[860px] mx-auto px-[var(--space-6)] md:px-[var(--space-7)] py-[var(--space-6)]">
        <section className="mb-[var(--space-5)]">
          <h1 className="text-[var(--text-2xl)] font-semibold text-[var(--ink-1)] tracking-tight">
            {title}
          </h1>
          <p className="mt-2 text-[var(--text-base)] text-[var(--ink-2)] max-w-[48ch]">
            {subtitle}
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-4">
            <button
              onClick={primaryAction}
              disabled={uploading}
              className="inline-flex items-center justify-center px-5 py-2.5 rounded-full bg-[var(--chestnut)] text-white text-[var(--text-base)] font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {primaryLabel}
            </button>
            <button
              onClick={secondaryAction}
              className="text-[var(--ink-2)] hover:text-[var(--ink-1)] underline underline-offset-4 transition-colors text-[var(--text-base)]"
            >
              {secondaryLabel}
            </button>
          </div>
          {uploadError && (
            <p className="mt-3 text-[var(--ember)] text-[var(--text-sm)]">{uploadError}</p>
          )}
        </section>

        {hasProfile && (
          <div className="space-y-[var(--space-5)]">
            <BlockGrid>
              <Block
                kicker="画像"
                title={profile?.name || '我的画像'}
                span={2}
              >
                <p className="text-[var(--text-sm)] text-[var(--ink-2)]">
                  已完成 {sectionsCompleted} / 6 个章节
                </p>
                <button
                  onClick={() => navigate('/profile')}
                  className="mt-4 inline-flex items-center text-[var(--text-sm)] text-[var(--chestnut)] font-medium hover:opacity-90"
                >
                  去查看 <ArrowRight className="ml-1 w-4 h-4" />
                </button>
              </Block>

              <Block
                kicker="报告"
                title="职业分析报告"
              >
                <p className="text-[var(--text-sm)] text-[var(--ink-2)]">
                  {report ? `上次生成于 ${formatRelativeTime(report.created_at)}` : '还没生成'}
                </p>
                <button
                  onClick={() => navigate('/report')}
                  className="mt-4 inline-flex items-center text-[var(--text-sm)] text-[var(--chestnut)] font-medium hover:opacity-90"
                >
                  {report ? '查看报告' : '去生成'} <ArrowRight className="ml-1 w-4 h-4" />
                </button>
              </Block>

              <Block
                kicker="成长"
                title="成长日志"
              >
                <p className="text-[var(--text-sm)] text-[var(--ink-2)]">
                  {pulse ? `${pulse.total_records} 条笔记` : '还空着'}
                </p>
                <button
                  onClick={() => navigate('/growth-log')}
                  className="mt-4 inline-flex items-center text-[var(--text-sm)] text-[var(--chestnut)] font-medium hover:opacity-90"
                >
                  {pulse && pulse.total_records > 0 ? '去回顾' : '去记录'} <ArrowRight className="ml-1 w-4 h-4" />
                </button>
              </Block>
            </BlockGrid>

            <div className="text-[var(--text-sm)] text-[var(--ink-2)] max-w-[68ch] space-y-2">
              <p>
                你上次更新档案是 {formatRelativeTime(profile?.updated_at)}。
                {report
                  ? `报告还留在 ${formatRelativeTime(report.created_at)} 那版 —— 如果最近有新经历，值得重新跑一次。`
                  : '报告还没有生成 —— 准备好了就去试试。'}
              </p>
              {pulse && pulse.current_streak_weeks > 0 ? (
                <p>成长日志里，你已连续记录了 {pulse.current_streak_weeks} 周。</p>
              ) : (
                <p>成长日志还是空白 —— 第一笔从哪里开始都可以。</p>
              )}
            </div>

            <p className="pt-[var(--space-5)] border-t border-[var(--line)] text-[var(--text-sm)] text-[var(--ink-3)] italic">
              档案只给自己看，但每一步都算数。
            </p>
          </div>
        )}
      </div>
    </main>
  )
}
