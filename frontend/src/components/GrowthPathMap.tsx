import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Check, Lock, MapPin, ArrowRight, BookOpen } from 'lucide-react'
import { rawFetch } from '@/api/client'

interface Topic {
  id: string
  title: string
  title_zh?: string
  subtopics: Array<{ id: string; completed: boolean }>
  completed: number
  total: number
}

interface PathData {
  role_id: string
  topics: Topic[]
  progress: { completed: number; total: number; pct: number }
}

interface GrowthPathMapProps {
  roleId: string
  roleLabel: string
}

type NodeStatus = 'completed' | 'current' | 'locked'

export function GrowthPathMap({ roleId, roleLabel }: GrowthPathMapProps) {
  const navigate = useNavigate()
  const [data, setData] = useState<PathData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchPath = useCallback(async () => {
    if (!roleId) return
    setLoading(true)
    try {
      setData(await rawFetch<PathData>(`/graph/learning-path/${roleId}`))
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [roleId])

  useEffect(() => { fetchPath() }, [fetchPath])

  if (loading) {
    return (
      <div className="animate-pulse space-y-3">
        <div className="h-3 bg-slate-100 rounded w-full" />
        <div className="h-20 bg-slate-100 rounded-xl" />
        <div className="h-12 bg-slate-50 rounded-xl" />
      </div>
    )
  }

  if (!data || data.topics.length === 0) {
    return <p className="text-[14px] text-slate-500 text-center py-4">该岗位暂无学习路径数据</p>
  }

  // Compute statuses
  const statuses: NodeStatus[] = []
  let prevDone = true
  for (const t of data.topics) {
    if (t.total > 0 && t.completed === t.total) {
      statuses.push('completed')
      prevDone = true
    } else if (prevDone || t.completed > 0) {
      statuses.push('current')
      prevDone = false
    } else {
      statuses.push('locked')
      prevDone = false
    }
  }

  const completedTopics = data.topics.filter((_, i) => statuses[i] === 'completed')
  const currentTopic = data.topics.find((_, i) => statuses[i] === 'current')
  const currentIdx = statuses.indexOf('current')
  const lockedCount = statuses.filter(s => s === 'locked').length
  // Show next 2 locked topics as "upcoming"
  const upcomingTopics = data.topics
    .map((t, i) => ({ ...t, status: statuses[i] }))
    .filter(t => t.status === 'locked')
    .slice(0, 2)

  const { progress } = data
  const currentPct = currentTopic && currentTopic.total > 0
    ? Math.round((currentTopic.completed / currentTopic.total) * 100)
    : 0

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <h3 className="text-[15px] font-bold text-slate-800">{roleLabel}</h3>
            <p className="text-[11px] text-slate-400">{data.topics.length} 个模块 · {progress.total} 个学习项</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/profile/learning')}
          className="text-[12px] font-semibold text-[var(--blue)] hover:text-blue-700 flex items-center gap-1 cursor-pointer transition-colors"
        >
          进入学习 <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Overall progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[12px] font-medium text-slate-600">
            {progress.pct > 0 ? `总进度 ${progress.pct}%` : '准备开始学习'}
          </span>
          <span className="text-[11px] text-slate-400 tabular-nums">{progress.completed}/{progress.total}</span>
        </div>
        <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-blue-400 to-emerald-400"
            initial={{ width: 0 }}
            animate={{ width: `${progress.pct}%` }}
            transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
          />
        </div>
      </div>

      {/* Completed section */}
      {completedTopics.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3"
        >
          <div className="flex items-center gap-2 mb-2">
            <Check className="w-3.5 h-3.5 text-emerald-600" />
            <span className="text-[12px] font-semibold text-emerald-700">已掌握 {completedTopics.length} 个模块</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {completedTopics.map(t => (
              <span key={t.id} className="text-[11px] text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-md">
                {t.title_zh || t.title}
              </span>
            ))}
          </div>
        </motion.div>
      )}

      {/* Current topic — prominent */}
      {currentTopic && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-xl border-2 border-blue-300 bg-blue-50/40 p-4 cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate('/profile/learning')}
        >
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="w-4 h-4 text-blue-600" />
            <span className="text-[13px] font-bold text-blue-700">当前学习</span>
          </div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[15px] font-bold text-slate-800">
              {currentTopic.title_zh || currentTopic.title}
            </span>
            <span className="text-[12px] font-medium text-blue-600 tabular-nums">
              {currentTopic.completed}/{currentTopic.total}
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-blue-100 overflow-hidden mb-3">
            <motion.div
              className="h-full rounded-full bg-blue-500"
              initial={{ width: 0 }}
              animate={{ width: `${currentPct}%` }}
              transition={{ duration: 0.6, delay: 0.3 }}
            />
          </div>
          <div className="flex items-center gap-1 text-[12px] font-semibold text-blue-600">
            继续学习 <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </motion.div>
      )}

      {/* Upcoming topics */}
      {upcomingTopics.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Lock className="w-3 h-3 text-slate-400" />
            <span className="text-[11px] font-semibold text-slate-400">接下来</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {upcomingTopics.map(t => (
              <span key={t.id} className="text-[11px] text-slate-400 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-md">
                {t.title_zh || t.title}
              </span>
            ))}
            {lockedCount > 2 && (
              <span className="text-[11px] text-slate-300 px-1">
                +{lockedCount - 2} 个模块
              </span>
            )}
          </div>
        </motion.div>
      )}

      {/* No progress yet — show first step CTA */}
      {completedTopics.length === 0 && !currentTopic && data.topics.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border-2 border-dashed border-blue-200 bg-blue-50/30 p-5 text-center cursor-pointer hover:border-blue-300 transition-colors"
          onClick={() => navigate('/profile/learning')}
        >
          <BookOpen className="w-6 h-6 text-blue-400 mx-auto mb-2" />
          <p className="text-[14px] font-semibold text-slate-700 mb-1">开始你的学习之旅</p>
          <p className="text-[12px] text-slate-400 mb-3">
            从「{data.topics[0].title_zh || data.topics[0].title}」开始，逐步掌握 {roleLabel} 所需技能
          </p>
          <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-blue-600">
            开始学习 <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </motion.div>
      )}
    </div>
  )
}
