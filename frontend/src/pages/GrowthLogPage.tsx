/**
 * 成长档案页 — 时间轴 + 记录管理
 *
 * 顶部：GrowthDashboard（目标 + 分层技能覆盖率 + 匹配度曲线）
 * Tabs：
 *   - 时间轴：EventTimeline（自动+手动事件的叙事时间线，默认视图）
 *   - 项目：ProjectsSection（项目管理，带gap缺口关联）
 *   - 求职：PursuitsSection（求职追踪，不变）
 */
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Plus, FolderGit2, Mic2, Clock } from 'lucide-react'

import { GrowthDashboard } from '@/components/growth-log/GrowthDashboard'
import { EventTimeline } from '@/components/growth-log/EventTimeline'
import { ProjectsSection } from '@/components/growth-log/ProjectsSection'
import { PursuitsSection } from '@/components/growth-log/PursuitsSection'

type TabKey = 'timeline' | 'projects' | 'pursuits'

const TABS: { key: TabKey; label: string; Icon: typeof Clock }[] = [
  { key: 'timeline', label: '时间轴',  Icon: Clock },
  { key: 'projects', label: '项目',    Icon: FolderGit2 },
  { key: 'pursuits', label: '求职追踪', Icon: Mic2 },
]

export default function GrowthLogPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') as TabKey | null
  const [activeTab, setActiveTab] = useState<TabKey>(
    tabParam && TABS.some(t => t.key === tabParam) ? tabParam : 'timeline'
  )

  useEffect(() => {
    if (activeTab !== 'timeline') setSearchParams({ tab: activeTab }, { replace: true })
    else setSearchParams({}, { replace: true })
  }, [activeTab, setSearchParams])

  // Add menu dropdown state
  const [menuOpen, setMenuOpen] = useState(false)
  useEffect(() => {
    if (!menuOpen) return
    const close = () => setMenuOpen(false)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [menuOpen])

  return (
    <div className="max-w-[900px] mx-auto px-4 py-5 md:px-8">
      {/* ── Top: Growth Dashboard ── */}
      <div className="mb-5">
        <GrowthDashboard />
      </div>

      {/* ── Tab bar + add button ── */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-1">
          {TABS.map(t => {
            const active = activeTab === t.key
            return (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-[12px] font-medium transition-all cursor-pointer ${
                  active
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-500 hover:text-slate-800 hover:bg-white/50'
                }`}
              >
                <t.Icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            )
          })}
        </div>

        <div className="relative">
          <button
            onClick={e => { e.stopPropagation(); setMenuOpen(!menuOpen) }}
            className="flex items-center gap-1 px-3 py-2 bg-blue-600 text-white text-[11px] font-semibold rounded-lg hover:bg-blue-700 cursor-pointer transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> 记录
          </button>
          <AnimatePresence>
            {menuOpen && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.12 }}
                className="absolute right-0 top-full mt-1 w-40 bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden z-30"
                onClick={e => e.stopPropagation()}
              >
                <button
                  onClick={() => { setActiveTab('projects'); setMenuOpen(false) }}
                  className="w-full flex items-center gap-2 px-3.5 py-2.5 text-[11px] text-slate-800 hover:bg-slate-50 cursor-pointer font-medium"
                >
                  <FolderGit2 className="w-3.5 h-3.5 text-emerald-600" />
                  记录项目
                </button>
                <button
                  onClick={() => { setActiveTab('pursuits'); setMenuOpen(false) }}
                  className="w-full flex items-center gap-2 px-3.5 py-2.5 text-[11px] text-slate-800 hover:bg-slate-50 border-t border-slate-100 cursor-pointer font-medium"
                >
                  <Mic2 className="w-3.5 h-3.5 text-blue-600" />
                  岗位追踪
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Tab content ── */}
      {activeTab === 'timeline' && <EventTimeline />}
      {activeTab === 'projects' && <ProjectsSection />}
      {activeTab === 'pursuits' && <PursuitsSection />}
    </div>
  )
}
