import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, BookOpen, Video, FileText, GraduationCap, ExternalLink, Filter } from 'lucide-react'
import { fetchNodeLearning } from '@/api/graph'
import type { LearningTopic } from '@/types/graph'

const TYPE_META: Record<string, { label: string; icon: typeof FileText; cls: string }> = {
  article: { label: '文章', icon: FileText, cls: 'bg-blue-50 text-blue-600' },
  video: { label: '视频', icon: Video, cls: 'bg-red-50 text-red-500' },
  course: { label: '课程', icon: GraduationCap, cls: 'bg-purple-50 text-purple-600' },
  book: { label: '书籍', icon: BookOpen, cls: 'bg-amber-50 text-amber-600' },
  official: { label: '官方文档', icon: FileText, cls: 'bg-green-50 text-green-600' },
  opensource: { label: '开源', icon: ExternalLink, cls: 'bg-slate-50 text-slate-600' },
}

export default function LearningPage() {
  const { nodeId } = useParams<{ nodeId: string }>()
  const navigate = useNavigate()
  const [topics, setTopics] = useState<LearningTopic[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!nodeId) return
    setLoading(true)
    fetchNodeLearning(nodeId, { type: typeFilter || undefined })
      .then(data => { setTopics(data.topics); setTotal(data.total) })
      .catch(() => { setTopics([]); setTotal(0) })
      .finally(() => setLoading(false))
  }, [nodeId, typeFilter])

  const filtered = search
    ? topics.filter(t =>
        t.title.toLowerCase().includes(search.toLowerCase()) ||
        t.description.toLowerCase().includes(search.toLowerCase())
      )
    : topics

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate(-1)}
          className="w-8 h-8 rounded-full bg-white border border-slate-200 flex items-center justify-center hover:bg-slate-50 cursor-pointer transition-colors"
        >
          <ArrowLeft className="w-4 h-4 text-slate-500" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-800">{nodeId} 学习路线</h1>
          <p className="text-sm text-slate-500">{total} 个话题</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-5">
        <div className="flex items-center gap-1.5 text-sm text-slate-500">
          <Filter className="w-3.5 h-3.5" />
        </div>
        <button
          onClick={() => setTypeFilter(null)}
          className={`text-xs px-2.5 py-1 rounded-lg border cursor-pointer transition-colors ${
            !typeFilter ? 'bg-[var(--blue)] text-white border-[var(--blue)]' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
          }`}
        >
          全部
        </button>
        {Object.entries(TYPE_META).map(([key, meta]) => (
          <button
            key={key}
            onClick={() => setTypeFilter(key === typeFilter ? null : key)}
            className={`text-xs px-2.5 py-1 rounded-lg border cursor-pointer transition-colors ${
              typeFilter === key ? 'bg-[var(--blue)] text-white border-[var(--blue)]' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}
          >
            {meta.label}
          </button>
        ))}

        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="搜索话题..."
          className="ml-auto text-sm px-3 py-1.5 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[var(--blue)]/20 focus:border-[var(--blue)] w-48"
        />
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-[var(--blue)] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20">
          <BookOpen className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-[14px] text-slate-500 mb-1">暂无学习资源</p>
          <p className="text-[12px] text-slate-400 mb-4">可以在学习路径中找到系统化的学习内容</p>
          <button
            onClick={() => navigate('/profile/learning')}
            className="px-4 py-2 text-[13px] font-medium bg-[var(--blue)] text-white rounded-lg hover:opacity-90 transition-opacity cursor-pointer"
          >
            查看学习路径
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(topic => (
            <div
              key={topic.topic_id}
              className="bg-white rounded-xl border border-slate-200 p-4 hover:border-slate-300 transition-colors"
            >
              <h3 className="text-sm font-semibold text-slate-800 mb-1">{topic.title}</h3>
              {topic.description && (
                <p className="text-xs text-slate-500 leading-relaxed mb-3 line-clamp-2">{topic.description}</p>
              )}
              <div className="flex flex-wrap gap-1.5">
                {topic.resources.map((r, i) => {
                  const meta = TYPE_META[r.type] || TYPE_META.article
                  const Icon = meta.icon
                  return (
                    <a
                      key={i}
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-1 rounded-md ${meta.cls} hover:opacity-80 transition-opacity max-w-[260px]`}
                      title={r.title}
                    >
                      <Icon className="w-3 h-3 shrink-0" />
                      <span className="truncate">{r.title}</span>
                    </a>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
