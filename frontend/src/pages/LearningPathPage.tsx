import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, ChevronDown, Check, ExternalLink,
  BookOpen, Video, FileText, GraduationCap, CheckCircle2,
  Rocket, ArrowRight,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'
import { rawFetch } from '@/api/client'

interface ConfirmResult {
  ok: boolean
  skill: string
  level: string
  match_pct: number
  gap_remaining: number
}

const TYPE_META: Record<string, { label: string; icon: typeof FileText; cls: string }> = {
  article: { label: '文章', icon: FileText, cls: 'bg-blue-50 text-blue-600' },
  video:   { label: '视频', icon: Video, cls: 'bg-red-50 text-red-500' },
  course:  { label: '课程', icon: GraduationCap, cls: 'bg-purple-50 text-purple-600' },
  book:    { label: '书籍', icon: BookOpen, cls: 'bg-amber-50 text-amber-600' },
  official:{ label: '官方', icon: FileText, cls: 'bg-green-50 text-green-600' },
}

interface Subtopic {
  id: string
  title: string
  description: string
  resources: Array<{ type: string; title: string; url: string }>
  completed: boolean
}

interface Topic {
  id: string
  title: string
  title_zh?: string
  description: string
  subtopics: Subtopic[]
  completed: number
  total: number
}

interface LearningPathData {
  role_id: string
  topics: Topic[]
  progress: { completed: number; total: number; pct: number }
}

const ROADMAP_SLUGS: Record<string, string> = {
  backend:'backend', frontend:'frontend', 'full-stack':'full-stack', devops:'devops',
  android:'android', ios:'ios', flutter:'flutter', 'react-native':'react-native',
  'ai-engineer':'ai-engineer', 'machine-learning':'mlops', mlops:'mlops',
  'data-engineer':'data-engineer', 'data-analyst':'data-analyst',
  'software-architect':'software-architect', 'engineering-manager':'engineering-manager',
  'game-developer':'game-developer', qa:'qa', 'cyber-security':'cyber-security',
  cpp:'cpp', rust:'rust', python:'python', java:'java', golang:'golang',
  kotlin:'kotlin', php:'php', react:'react', vue:'vue', angular:'angular',
  nodejs:'nodejs', kubernetes:'kubernetes', linux:'linux', docker:'docker',
  'postgresql-dba':'postgresql-dba',
}

export default function LearningPathPage() {
  const navigate = useNavigate()
  const { token } = useAuth()
  const { profile, loadProfile } = useProfileData(token)

  const [data, setData] = useState<LearningPathData | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null)
  const [expandedSub, setExpandedSub] = useState<string | null>(null)
  const [togglingId, setTogglingId] = useState<string | null>(null)
  const [confirmSkill, setConfirmSkill] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [toast, setToast] = useState<{ skill: string; matchPct: number; gapRemaining: number } | null>(null)

  const goalRoleId = profile?.graph_position?.target_node_id
  const goalLabel = profile?.graph_position?.target_label
  const slug = goalRoleId ? ROADMAP_SLUGS[goalRoleId] || goalRoleId : null

  const fetchPath = useCallback(async () => {
    if (!goalRoleId) return
    setLoading(true)
    try {
      const result = await rawFetch<LearningPathData>(
        `/graph/learning-path/${goalRoleId}`
      )
      setData(result)
      const first = result.topics.find(t => t.completed < t.total)
      if (first) setExpandedTopic(first.id)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [goalRoleId])

  useEffect(() => { fetchPath() }, [fetchPath])

  async function toggleComplete(subtopicId: string, currentlyDone: boolean) {
    if (!goalRoleId || togglingId) return
    setTogglingId(subtopicId)
    try {
      await rawFetch('/graph/learning-path/progress', {
        method: 'POST',
        body: JSON.stringify({
          role_id: goalRoleId,
          subtopic_id: subtopicId,
          completed: !currentlyDone,
        }),
      })
      setData(prev => {
        if (!prev) return prev
        let totalDone = 0
        let totalAll = 0
        const topics = prev.topics.map(t => {
          const subs = t.subtopics.map(s => {
            const done = s.id === subtopicId ? !currentlyDone : s.completed
            if (done) totalDone++
            totalAll++
            return { ...s, completed: done }
          })
          const newCompleted = subs.filter(s => s.completed).length
          // Check if this topic just became fully complete (only for topics with 2+ subtopics)
          if (!currentlyDone && newCompleted === subs.length && subs.length >= 2 && t.completed < subs.length) {
            setTimeout(() => setConfirmSkill(t.title_zh || t.title), 300)
          }
          return { ...t, subtopics: subs, completed: newCompleted }
        })
        return {
          ...prev, topics,
          progress: { completed: totalDone, total: totalAll, pct: totalAll ? Math.round(totalDone / totalAll * 100) : 0 },
        }
      })
    } finally {
      setTogglingId(null)
    }
  }

  async function handleConfirmSkill() {
    if (!confirmSkill) return
    setConfirming(true)
    try {
      const result = await rawFetch<ConfirmResult>('/graph/learning-path/confirm-skill', {
        method: 'POST',
        body: JSON.stringify({ skill_name: confirmSkill, level: 'familiar' }),
      })
      // Show toast with match info
      setToast({
        skill: confirmSkill,
        matchPct: result.match_pct,
        gapRemaining: result.gap_remaining,
      })
      setTimeout(() => setToast(null), 4000)
      // Refresh profile data (skills updated) and learning path
      loadProfile()
      fetchPath()
    } finally {
      setConfirming(false)
      setConfirmSkill(null)
    }
  }

  if (!goalRoleId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-[15px] text-slate-500 mb-4">请先设定目标岗位</p>
          <button onClick={() => navigate('/profile')} className="btn-cta px-5 py-2 text-[13px] font-semibold cursor-pointer">
            前往画像页
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-200 rounded w-1/3" />
          <div className="h-2 bg-slate-200 rounded w-full" />
          {[1, 2, 3].map(i => <div key={i} className="h-16 bg-slate-200/60 rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (!data || data.topics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <BookOpen className="w-10 h-10 text-slate-300" />
        <p className="text-[15px] text-slate-500">该岗位暂无学习路径数据</p>
        <div className="flex gap-2">
          <button onClick={() => navigate('/graph')} className="px-4 py-2 text-[13px] font-medium bg-[var(--blue)] text-white rounded-lg hover:opacity-90 transition-opacity cursor-pointer">
            浏览岗位图谱
          </button>
          <button onClick={() => navigate('/profile')} className="px-4 py-2 text-[13px] font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer">
            换个目标
          </button>
        </div>
      </div>
    )
  }

  const { progress } = data

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 pb-16">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate('/profile')}
          className="w-8 h-8 rounded-full bg-white border border-slate-200 flex items-center justify-center hover:bg-slate-50 cursor-pointer transition-colors"
        >
          <ArrowLeft className="w-4 h-4 text-slate-500" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-[18px] font-bold text-slate-800 truncate">{goalLabel} 学习路径</h1>
          <p className="text-[12px] text-slate-400">{data.topics.length} 个模块 · {progress.total} 个学习项</p>
        </div>
        {slug && (
          <a
            href={`https://roadmap.sh/${slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-[12px] font-medium text-[var(--blue)] hover:text-blue-700 transition-colors shrink-0"
          >
            查看路线图
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>

      {/* Progress */}
      <div className="glass-static p-5 mb-6">
        <div className="g-inner">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[13px] font-semibold text-slate-700">
              {progress.pct > 0 ? `已完成 ${progress.pct}%` : '开始你的学习之旅'}
            </span>
            <span className="text-[12px] text-slate-400 tabular-nums">{progress.completed}/{progress.total}</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden bg-slate-100">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-blue-400 to-blue-600"
              initial={{ width: 0 }}
              animate={{ width: `${progress.pct}%` }}
              transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
            />
          </div>

          {/* 100% Completion CTA */}
          {progress.pct === 100 && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <div className="flex items-center gap-2 mb-3">
                <Rocket className="w-4 h-4 text-emerald-500" />
                <p className="text-[13px] font-bold text-emerald-700">学习路径已全部完成！</p>
              </div>
              <p className="text-[12px] text-slate-500 mb-3">你已经具备了关键技能基础，下一步可以开始投递或模拟面试。</p>
              <div className="flex gap-2">
                <button
                  onClick={() => navigate('/applications')}
                  className="flex items-center gap-1.5 px-4 py-2 bg-[var(--blue)] text-white text-[12px] font-semibold rounded-lg hover:opacity-90 transition-opacity cursor-pointer"
                >
                  开始投递 <ArrowRight className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => navigate('/growth-log')}
                  className="px-4 py-2 text-[12px] font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  查看成长档案
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Topics */}
      <div className="space-y-3">
        {data.topics.map(topic => {
          const isExpanded = expandedTopic === topic.id
          const allDone = topic.total > 0 && topic.completed === topic.total

          return (
            <div key={topic.id} className="glass overflow-visible">
              <div className="g-inner">
                <button
                  onClick={() => setExpandedTopic(isExpanded ? null : topic.id)}
                  className="w-full flex items-center gap-3 p-4 text-left cursor-pointer"
                >
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                    allDone ? 'bg-emerald-50 border border-emerald-200' : 'bg-slate-50 border border-slate-200'
                  }`}>
                    {allDone
                      ? <Check className="w-3.5 h-3.5 text-emerald-600" />
                      : <span className="text-[10px] font-bold text-slate-400">{topic.completed}/{topic.total}</span>
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className={`text-[14px] font-semibold ${allDone ? 'text-emerald-700' : 'text-slate-800'}`}>
                      {topic.title_zh || topic.title}
                    </span>
                    {topic.total > 0 && (
                      <div className="h-1 rounded-full bg-slate-100 mt-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${allDone ? 'bg-emerald-400' : 'bg-blue-400'}`}
                          style={{ width: `${topic.total ? (topic.completed / topic.total) * 100 : 0}%` }}
                        />
                      </div>
                    )}
                  </div>
                  <ChevronDown className={`w-4 h-4 text-slate-400 shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                </button>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 pb-4 space-y-1">
                        {topic.description && (
                          <p className="text-[12px] text-slate-400 leading-relaxed mb-3 pl-10">{topic.description}</p>
                        )}
                        {topic.subtopics.map(sub => {
                          const subOpen = expandedSub === sub.id
                          return (
                            <div key={sub.id}>
                              <div className="flex items-center gap-2.5 py-2 pl-2 rounded-lg hover:bg-white/30 transition-colors">
                                <button
                                  onClick={() => toggleComplete(sub.id, sub.completed)}
                                  disabled={togglingId === sub.id}
                                  className={`w-5 h-5 rounded-md border flex items-center justify-center shrink-0 cursor-pointer transition-colors ${
                                    sub.completed ? 'bg-emerald-500 border-emerald-500' : 'border-slate-300 hover:border-blue-400'
                                  } ${togglingId === sub.id ? 'opacity-50' : ''}`}
                                >
                                  {sub.completed && <Check className="w-3 h-3 text-white" />}
                                </button>
                                <button
                                  onClick={() => setExpandedSub(subOpen ? null : sub.id)}
                                  className={`flex-1 text-left text-[13px] cursor-pointer transition-colors ${
                                    sub.completed ? 'text-slate-400 line-through' : 'text-slate-700 hover:text-slate-900'
                                  }`}
                                >
                                  {sub.title}
                                </button>
                                {(sub.description || sub.resources.length > 0) && (
                                  <ChevronDown className={`w-3.5 h-3.5 text-slate-300 transition-transform ${subOpen ? 'rotate-180' : ''}`} />
                                )}
                              </div>

                              <AnimatePresence>
                                {subOpen && (
                                  <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="overflow-hidden"
                                  >
                                    <div className="pl-10 pr-2 pb-3">
                                      {sub.description && (
                                        <p className="text-[12px] text-slate-500 leading-relaxed mb-2">{sub.description}</p>
                                      )}
                                      {sub.resources.length > 0 && (
                                        <div className="flex flex-wrap gap-1.5">
                                          {sub.resources.map((r, i) => {
                                            const meta = TYPE_META[r.type] || TYPE_META.article
                                            const Icon = meta.icon
                                            return (
                                              <a
                                                key={i}
                                                href={r.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-1 rounded-md ${meta.cls} hover:opacity-80 transition-opacity max-w-[240px]`}
                                                title={r.title}
                                              >
                                                <Icon className="w-3 h-3 shrink-0" />
                                                <span className="truncate">{r.title}</span>
                                              </a>
                                            )
                                          })}
                                        </div>
                                      )}
                                    </div>
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </div>
                          )
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          )
        })}
      </div>

      {/* Success toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 40, x: 0 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
            className="fixed bottom-6 right-6 z-[1000] glass-static shadow-xl max-w-xs"
          >
            <div className="g-inner flex items-start gap-3 p-4">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600" />
              </div>
              <div>
                <p className="text-[13px] font-semibold text-slate-800">
                  「{toast.skill}」已加入画像
                </p>
                <p className="text-[12px] text-slate-500 mt-0.5">
                  目标匹配度 {toast.matchPct}% · 差距技能还剩 {toast.gapRemaining} 项
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Skill mastery confirmation modal */}
      {confirmSkill && (
        <div className="fixed inset-0 bg-slate-900/30 backdrop-blur-sm z-[999] flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full" onClick={e => e.stopPropagation()}>
            <div className="w-12 h-12 rounded-xl bg-emerald-50 flex items-center justify-center mx-auto mb-4">
              <Check className="w-6 h-6 text-emerald-600" />
            </div>
            <h3 className="text-[16px] font-bold text-slate-800 text-center mb-1">
              你已完成「{confirmSkill}」全部学习内容
            </h3>
            <p className="text-[13px] text-slate-500 text-center mb-5">
              确认掌握后，该技能将加入你的画像，差距分析会自动更新
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmSkill(null)}
                className="flex-1 py-2.5 text-[13px] font-medium text-slate-500 hover:text-slate-700 transition-colors cursor-pointer"
              >
                还没掌握
              </button>
              <button
                onClick={handleConfirmSkill}
                disabled={confirming}
                className="flex-[2] py-2.5 rounded-xl text-[13px] font-bold text-white bg-emerald-500 hover:bg-emerald-600 transition-colors cursor-pointer disabled:opacity-50"
              >
                {confirming ? '更新中...' : '确认掌握'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
