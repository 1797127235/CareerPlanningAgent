import { ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface ReportActionsProps {
  actions: string[]
}

const CTA_ROUTES: Record<string, { path: string; label: string }> = {
  '简历': { path: '/profile', label: '完善画像' },
  '画像': { path: '/profile', label: '完善画像' },
  '诊断': { path: '/growth-log?tab=pursuits', label: '去求职追踪' },
  'JD': { path: '/growth-log?tab=pursuits', label: '去求职追踪' },
  '面试': { path: '/growth-log?tab=pursuits', label: '去求职追踪' },
  '项目': { path: '/growth-log?tab=projects', label: '去项目管理' },
  '图谱': { path: '/graph', label: '查看岗位图谱' },
}

function matchRoute(text: string): { path: string; label: string } | null {
  for (const [keyword, route] of Object.entries(CTA_ROUTES)) {
    if (text.includes(keyword)) return route
  }
  return null
}

export function ReportActions({ actions }: ReportActionsProps) {
  const navigate = useNavigate()
  if (!actions.length) return null

  return (
    <div className="glass-static p-6">
      <div className="relative z-[1]">
        <h3 className="text-[16px] font-semibold text-[var(--text-1)] mb-4">下一步行动</h3>
        <div className="space-y-3">
          {actions.map((action, i) => {
            const route = matchRoute(action)
            return (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-xl bg-white/25 hover:bg-white/40 transition-colors"
              >
                <span className="shrink-0 w-6 h-6 rounded-full bg-[var(--blue)]/10 flex items-center justify-center text-[12px] font-bold text-[var(--blue)]">
                  {i + 1}
                </span>
                <p className="flex-1 text-[13px] text-[var(--text-2)] leading-relaxed">{action}</p>
                {route && (
                  <button
                    onClick={() => navigate(route.path)}
                    className="shrink-0 btn-cta flex items-center gap-1 px-3 py-1 text-[11px] font-medium cursor-pointer"
                  >
                    {route.label}
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
