/**
 * 成长档案页 — 结构重做
 *
 * 改动：
 *   - 去掉双层导航（tab + filter），合并为一层
 *   - Tab 栏：全部 | 项目 | 求职追踪（时间轴=全部，不再单独做 tab）
 *   - 记录按钮保留
 */
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Plus, FolderGit2, Mic2 } from 'lucide-react'

import { EventTimeline } from '@/components/growth-log/EventTimeline'
import { ProjectsSection } from '@/components/growth-log/ProjectsSection'
import { PursuitsSection } from '@/components/growth-log/PursuitsSection'

type TabKey = 'all' | 'projects' | 'pursuits'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'all',      label: '全部记录' },
  { key: 'projects',  label: '项目' },
  { key: 'pursuits',  label: '求职追踪' },
]

export default function GrowthLogPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') as TabKey | null
  const [activeTab, setActiveTab] = useState<TabKey>(
    tabParam && TABS.some(t => t.key === tabParam) ? tabParam : 'all'
  )
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    if (activeTab !== 'all') setSearchParams({ tab: activeTab }, { replace: true })
    else setSearchParams({}, { replace: true })
  }, [activeTab, setSearchParams])

  useEffect(() => {
    if (!menuOpen) return
    const close = () => setMenuOpen(false)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [menuOpen])

  return (
    <div className="max-w-[900px] mx-auto px-4 py-5 md:px-8">

      {/* ── Tab bar + add button ── */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex gap-1">
          {TABS.map(t => {
            const active = activeTab === t.key
            return (
              <button key={t.key} onClick={() => setActiveTab(t.key)}
                className={`px-3.5 py-2 rounded-lg text-[12px] font-semibold transition-all cursor-pointer ${
                  active
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-700 hover:bg-white/50'
                }`}>
                {t.label}
              </button>
            )
          })}
        </div>

        <div className="relative">
          <button onClick={e => { e.stopPropagation(); setMenuOpen(!menuOpen) }}
            className="flex items-center gap-1 px-3 py-2 bg-slate-800 text-white text-[11px] font-bold rounded-lg hover:bg-slate-700 cursor-pointer transition-colors">
            <Plus className="w-3.5 h-3.5" /> 记录
          </button>
          <AnimatePresence>
            {menuOpen && (
              <motion.div
                initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.12 }}
                className="absolute right-0 top-full mt-1 w-40 bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden z-30"
                onClick={e => e.stopPropagation()}>
                <button onClick={() => { setActiveTab('projects'); setMenuOpen(false) }}
                  className="w-full flex items-center gap-2 px-3.5 py-2.5 text-[11px] text-slate-800 hover:bg-slate-50 cursor-pointer font-medium">
                  <FolderGit2 className="w-3.5 h-3.5 text-emerald-600" /> 记录项目
                </button>
                <button onClick={() => { setActiveTab('pursuits'); setMenuOpen(false) }}
                  className="w-full flex items-center gap-2 px-3.5 py-2.5 text-[11px] text-slate-800 hover:bg-slate-50 border-t border-slate-100 cursor-pointer font-medium">
                  <Mic2 className="w-3.5 h-3.5 text-blue-600" /> 岗位追踪
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Content ── */}
      {activeTab === 'all'       && <EventTimeline />}
      {activeTab === 'projects'  && <ProjectsSection />}
      {activeTab === 'pursuits'  && <PursuitsSection />}
    </div>
  )
}
