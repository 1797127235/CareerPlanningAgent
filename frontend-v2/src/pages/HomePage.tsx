import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  ArrowUpRight,
  Upload,
  PenLine,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'
import { useResumeUpload } from '@/hooks/useResumeUpload'
import { fetchReportList, type ReportListItem } from '@/api/report'
import { getActivityPulse, type ActivityPulseData } from '@/api/growthLog'
import Navbar from '@/components/shared/Navbar'

/* ── Design Tokens ── */
const t = {
  bg: '#F9F4EE',
  bgAlt: '#EDE8DF',
  ink: '#1F1F1F',
  inkSecondary: '#6B6560',
  inkMuted: '#9A9590',
  button: '#6B3E2E',
  buttonHover: '#5A3426',
  line: '#D9D4CC',
  accent: '#B85C38',
  accentHover: '#9A4A2E',
} as const

const serif = { fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }
const containerClass = 'mx-auto w-full max-w-[1440px] px-6 md:px-12'

/* ── helpers ── */
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

/* ── local hooks ── */
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

function useActivityPulseLocal(enabled: boolean) {
  const [pulse, setPulse] = useState<ActivityPulseData | null>(null)
  useEffect(() => {
    if (!enabled) return
    getActivityPulse()
      .then((data) => setPulse(data))
      .catch(() => setPulse(null))
  }, [enabled])
  return pulse
}

/* ── Hero ── */
function Hero({ hasProfile }: { hasProfile: boolean }) {
  const navigate = useNavigate()

  return (
    <section
      className="px-6 md:px-12"
      style={{
        background: t.bg,
        paddingTop: 'clamp(140px, 20vh, 220px)',
        paddingBottom: 'clamp(80px, 12vh, 120px)',
      }}
    >
      <div className={containerClass}>
        {/* Kicker with decorative rule */}
        <div className="flex items-center gap-3">
          <span className="inline-block h-px w-5" style={{ background: t.inkMuted }} />
          <p
            className="text-[10px] font-medium uppercase tracking-[0.28em]"
            style={{ ...sans, color: t.inkMuted }}
          >
            AI-Driven Career Planning
          </p>
        </div>

        <h1
          className="mt-10 font-semibold"
          style={{
            ...serif,
            color: t.ink,
            fontSize: 'clamp(44px, 5.8vw, 72px)',
            lineHeight: 1.15,
            letterSpacing: '0.01em',
            maxWidth: '800px',
          }}
        >
          让职业选择，
          <br />
          建立在<span style={{ color: t.accent }}>清晰判断</span>之上。
        </h1>

        <p
          className="mt-8 leading-[1.75]"
          style={{
            ...sans,
            color: t.inkSecondary,
            fontSize: '17px',
            maxWidth: '540px',
            letterSpacing: '0.01em',
          }}
        >
          CareerPlan 通过能力画像、岗位结构与成长路径分析，帮助你理解自己，并做出更可靠的职业决策。
        </p>

        <div className="mt-8 flex flex-wrap items-center gap-5">
          <button
            onClick={() => navigate(hasProfile ? '/profile' : '/login')}
            className="rounded-md px-6 py-2.5 text-[14px] font-medium text-white transition-colors duration-200"
            style={{ background: t.button, ...sans }}
            onMouseEnter={(e) => { e.currentTarget.style.background = t.buttonHover }}
            onMouseLeave={(e) => { e.currentTarget.style.background = t.button }}
          >
            开始分析
          </button>
          <button
            onClick={() => {
              const el = document.getElementById('capabilities')
              if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 80, behavior: 'smooth' })
            }}
            className="group inline-flex items-center gap-1.5 text-[14px] font-medium transition-colors duration-200"
            style={{ ...sans, color: t.inkSecondary }}
            onMouseEnter={(e) => { e.currentTarget.style.color = t.ink }}
            onMouseLeave={(e) => { e.currentTarget.style.color = t.inkSecondary }}
          >
            了解方法
            <ArrowRight size={14} strokeWidth={1.5} className="transition-transform duration-200 group-hover:translate-x-0.5" />
          </button>
        </div>
      </div>
    </section>
  )
}

/* ── Capabilities (编号式 01/02/03) ── */
const capabilities = [
  {
    num: '01',
    title: '能力画像',
    desc: '我们识别你的经验、技能结构与潜在优势，构建你的数字化能力基线。',
    route: '/profile',
  },
  {
    num: '02',
    title: '岗位结构',
    desc: '我们分析岗位之间的关系、迁移空间与行业趋势，让你看清更多可能性。',
    route: '/graph',
  },
  {
    num: '03',
    title: '成长路径',
    desc: '我们把目标拆解为可执行的阶段性能力建设建议，陪伴你持续成长。',
    route: '/growth-log',
  },
]

function CapabilitiesSection() {
  const navigate = useNavigate()

  return (
    <section
      id="capabilities"
      className="px-6 md:px-12"
      style={{ background: t.bg }}
    >
      <div className={containerClass}>
        {capabilities.map((item) => (
          <button
            key={item.num}
            onClick={() => navigate(item.route)}
            className="group flex w-full items-start gap-5 py-8 text-left md:gap-8 md:py-10"
            style={{ borderTop: `1px solid ${t.line}` }}
          >
            <span
              className="mt-0.5 text-[24px] font-light transition-colors duration-200 md:text-[28px]"
              style={{ ...serif, color: t.inkMuted, minWidth: '40px' }}
            >
              {item.num}
            </span>
            <div className="min-w-0 flex-1">
              <h3
                className="text-[17px] font-semibold transition-colors duration-200 group-hover:text-[#B85C38] md:text-[18px]"
                style={{ ...sans, color: t.ink }}
              >
                {item.title}
              </h3>
              <p
                className="mt-2 text-[14px] leading-[1.65] md:text-[15px]"
                style={{ ...sans, color: t.inkSecondary }}
              >
                {item.desc}
              </p>
            </div>
            <ArrowUpRight
              size={18}
              strokeWidth={1.5}
              className="mt-1 shrink-0 transition-all duration-200 group-hover:translate-x-0.5 group-hover:text-[#B85C38]"
              style={{ color: t.inkMuted }}
            />
          </button>
        ))}
        {/* bottom border for last item */}
        <div style={{ borderTop: `1px solid ${t.line}` }} />
      </div>
    </section>
  )
}

/* ── Dashboard (仅已登录且有档案时显示) ── */
function Dashboard({
  hasProfile,
  profile,
}: {
  hasProfile: boolean
  profile: ReturnType<typeof useProfileData>['profile']
}) {
  const navigate = useNavigate()
  const report = useReportMeta(hasProfile)
  const pulse = useActivityPulseLocal(hasProfile)

  const sectionsCompleted = [
    !!profile?.name,
    !!profile?.profile?.education?.school,
    ((profile?.profile?.internships?.length ?? 0) > 0) || ((profile?.profile?.projects?.length ?? 0) > 0),
    (profile?.profile?.skills?.length ?? 0) > 0,
    Object.keys((profile?.profile?.soft_skills as Record<string, unknown>) ?? {}).filter((k) => k !== '_version').length > 0,
    (profile?.career_goals?.length ?? 0) > 0,
  ].filter(Boolean).length

  if (!hasProfile) return null

  return (
    <section
      className="px-6 md:px-12"
      style={{ background: t.bg, paddingTop: '80px', paddingBottom: '80px' }}
    >
      <div className={containerClass}>
        <p
          className="text-[11px] font-medium uppercase tracking-[0.22em]"
          style={{ ...sans, color: t.inkMuted }}
        >
          Your Dashboard
        </p>

        <div className="mt-8 grid gap-10 md:grid-cols-3">
          <div>
            <h3 className="text-[16px] font-semibold" style={{ ...sans, color: t.ink }}>
              {profile?.name || '档案画像'}
            </h3>
            <p className="mt-2 text-[14px] leading-relaxed" style={{ ...sans, color: t.inkSecondary }}>
              完成度 {sectionsCompleted}/6 · 上次更新 {formatRelativeTime(profile?.updated_at)}
            </p>
            <button
              onClick={() => navigate('/profile')}
              className="group mt-4 inline-flex items-center gap-1 text-[14px] font-medium transition-colors duration-200"
              style={{ ...sans, color: t.button }}
              onMouseEnter={(e) => { e.currentTarget.style.color = t.buttonHover }}
              onMouseLeave={(e) => { e.currentTarget.style.color = t.button }}
            >
              查看
              <ArrowRight size={14} strokeWidth={1.5} className="transition-transform duration-200 group-hover:translate-x-0.5" />
            </button>
          </div>

          <div>
            <h3 className="text-[16px] font-semibold" style={{ ...sans, color: t.ink }}>
              职业分析报告
            </h3>
            <p className="mt-2 text-[14px] leading-relaxed" style={{ ...sans, color: t.inkSecondary }}>
              {report ? `上次生成于 ${formatRelativeTime(report.created_at)}` : '尚未生成'}
            </p>
            <button
              onClick={() => navigate('/report')}
              className="group mt-4 inline-flex items-center gap-1 text-[14px] font-medium transition-colors duration-200"
              style={{ ...sans, color: t.button }}
              onMouseEnter={(e) => { e.currentTarget.style.color = t.buttonHover }}
              onMouseLeave={(e) => { e.currentTarget.style.color = t.button }}
            >
              {report ? '查看' : '生成'}
              <ArrowRight size={14} strokeWidth={1.5} className="transition-transform duration-200 group-hover:translate-x-0.5" />
            </button>
          </div>

          <div>
            <h3 className="text-[16px] font-semibold" style={{ ...sans, color: t.ink }}>
              成长日志
            </h3>
            <p className="mt-2 text-[14px] leading-relaxed" style={{ ...sans, color: t.inkSecondary }}>
              {pulse ? `${pulse.total_records} 条笔记` : '暂无记录'}
              {pulse && pulse.current_streak_weeks > 0 && ` · 连续 ${pulse.current_streak_weeks} 周`}
            </p>
            <button
              onClick={() => navigate('/growth-log')}
              className="group mt-4 inline-flex items-center gap-1 text-[14px] font-medium transition-colors duration-200"
              style={{ ...sans, color: t.button }}
              onMouseEnter={(e) => { e.currentTarget.style.color = t.buttonHover }}
              onMouseLeave={(e) => { e.currentTarget.style.color = t.button }}
            >
              {pulse && pulse.total_records > 0 ? '回顾' : '记录'}
              <ArrowRight size={14} strokeWidth={1.5} className="transition-transform duration-200 group-hover:translate-x-0.5" />
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ── CTA Section (上传简历引导 + 路径图) ── */
function CTASection({ isAuthenticated }: { isAuthenticated: boolean }) {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { uploading, uploadStep, uploadError, triggerFileDialog, onFileSelected } =
    useResumeUpload(async () => { navigate('/profile') })

  const handleUploadClick = () => {
    if (isAuthenticated) {
      triggerFileDialog()
    } else {
      navigate('/login')
    }
  }

  return (
    <section
      className="px-6 md:px-12"
      style={{ background: t.bgAlt, paddingTop: '100px', paddingBottom: '100px' }}
    >
      <div className={containerClass}>
        <div className="grid items-center gap-12 md:grid-cols-2 md:gap-16">
          {/* Left — Copy */}
          <div>
            <h2
              className="font-semibold tracking-[-0.02em]"
              style={{
                ...serif,
                color: t.ink,
                fontSize: 'clamp(24px, 3vw, 32px)',
                lineHeight: 1.25,
              }}
            >
              更清晰的自我认知，
              <br />
              带来更长远的职业可能。
            </h2>
            <p
              className="mt-5 leading-[1.7]"
              style={{ ...sans, color: t.inkSecondary, fontSize: '15px', maxWidth: '440px' }}
            >
              从一份简历开始，CareerPlan 帮你整理线索，生成初始能力画像，开启你的职业探索。
            </p>

            <input ref={fileInputRef} type="file" accept=".pdf,.doc,.docx,.txt" className="hidden" onChange={onFileSelected} />

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button
                onClick={handleUploadClick}
                disabled={uploading}
                className="group inline-flex items-center gap-2 text-[14px] font-medium transition-colors duration-200 disabled:opacity-40"
                style={{ ...sans, color: t.accent }}
                onMouseEnter={(e) => { if (!uploading) e.currentTarget.style.color = t.accentHover }}
                onMouseLeave={(e) => { e.currentTarget.style.color = t.accent }}
              >
                {uploading ? `上传中（${uploadStep + 1}/4）…` : '上传简历'}
                <ArrowRight size={14} strokeWidth={1.5} className="transition-transform duration-200 group-hover:translate-x-0.5" />
              </button>

              {isAuthenticated && (
                <button
                  onClick={() => navigate('/profile')}
                  className="inline-flex items-center gap-2 rounded-md border px-5 py-2.5 text-[14px] font-medium transition-colors duration-200"
                  style={{ borderColor: t.line, color: t.ink, ...sans }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = t.bg }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                >
                  <PenLine size={14} strokeWidth={1.5} />
                  手动填写
                </button>
              )}
            </div>

            {uploadError && (
              <p className="mt-4 text-[13px]" style={{ ...sans, color: '#C45D3A' }}>
                {uploadError}
              </p>
            )}
          </div>

          {/* Right — Illustration */}
          <div className="flex items-center justify-center overflow-hidden">
            <img
              src="/cta-landscape.png"
              alt="职业旅程"
              className="w-full"
              style={{
                objectFit: 'cover',
                objectPosition: 'center 30%',
                height: 'clamp(280px, 36vw, 400px)',
              }}
            />
          </div>
        </div>
      </div>
    </section>
  )
}

/* ── Footer ── */
const footerColumns = [
  [
    { label: '能力画像', route: '/profile' },
    { label: '成长手札', route: '/growth-log' },
  ],
  [
    { label: '成长路径', route: '/growth-log' },
  ],
  [
    { label: '岗位图谱', route: '/graph' },
  ],
  [
    { label: '关于我们', route: '#' },
    { label: '隐私政策', route: '#' },
    { label: '使用条款', route: '#' },
  ],
]

function Footer() {
  const navigate = useNavigate()

  return (
    <footer
      className="px-6 py-14 md:px-12"
      style={{ background: t.bg, borderTop: `1px solid ${t.line}` }}
    >
      <div className={`${containerClass} grid gap-10 md:grid-cols-5`}>
        {/* Brand */}
        <div className="md:col-span-1">
          <p
            className="text-[16px] font-semibold tracking-tight"
            style={{ ...serif, color: t.ink }}
          >
            CareerPlan
          </p>
          <p
            className="mt-2 text-[13px] leading-relaxed"
            style={{ ...sans, color: t.inkMuted }}
          >
            AI 驱动的职业规划平台，让成长有迹可循。
          </p>
          <p
            className="mt-6 text-[12px]"
            style={{ ...sans, color: t.inkMuted }}
          >
            © {new Date().getFullYear()} CareerPlan
          </p>
        </div>

        {/* Link columns */}
        {footerColumns.map((col, idx) => (
          <div key={idx} className="flex flex-col gap-3">
            {col.map((item) => (
              <button
                key={item.label}
                onClick={() => item.route !== '#' && navigate(item.route)}
                className="text-left text-[14px] transition-colors duration-200"
                style={{ ...sans, color: t.inkSecondary }}
                onMouseEnter={(e) => { e.currentTarget.style.color = t.ink }}
                onMouseLeave={(e) => { e.currentTarget.style.color = t.inkSecondary }}
              >
                {item.label}
              </button>
            ))}
          </div>
        ))}
      </div>
    </footer>
  )
}

/* ── Page ── */
export default function HomePage() {
  const { isAuthenticated } = useAuth()
  const { profile } = useProfileData(isAuthenticated)

  const hasProfile = isAuthenticated && !!(
    profile?.profile?.skills?.length ||
    profile?.profile?.knowledge_areas?.length ||
    profile?.profile?.projects?.length ||
    profile?.profile?.internships?.length ||
    profile?.profile?.education?.school ||
    profile?.name
  )

  return (
    <div
      className="min-h-screen"
      style={{ background: t.bg, color: t.ink, position: 'relative', zIndex: 2 }}
    >
      <Navbar />
      <Hero hasProfile={hasProfile} />
      <CapabilitiesSection />
      <Dashboard hasProfile={hasProfile} profile={profile} />
      {!hasProfile && <CTASection isAuthenticated={isAuthenticated} />}
      <Footer />
    </div>
  )
}
