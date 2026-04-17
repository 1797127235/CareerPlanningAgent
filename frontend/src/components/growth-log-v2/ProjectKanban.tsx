import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { rawFetch } from '@/api/client'
import { Plus, X, Trash2 } from 'lucide-react'

const ease = [0.22, 1, 0.36, 1] as const

interface ProjectRecord {
  id: number
  name: string
  description: string
  skills_used: string[]
  status: string
  github_url: string | null
  created_at: string
}

const STAGES = [
  { key: 'planning', label: '规划中', color: 'bg-slate-400' },
  { key: 'in_progress', label: '进行中', color: 'bg-blue-400' },
  { key: 'completed', label: '已完成', color: 'bg-emerald-400' },
]

interface Props {
  projects: ProjectRecord[]
  onRefresh: () => void
}

export function ProjectKanban({ projects, onRefresh }: Props) {
  const navigate = useNavigate()
  const [showAdd, setShowAdd] = useState(false)

  const qc = useQueryClient()

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('确定删除这个项目？相关的进展记录也会一并删除。')) return
    await rawFetch(`/growth-log/projects/${id}`, { method: 'DELETE' })
    onRefresh()
    qc.invalidateQueries({ queryKey: ['growth-projects'] })
  }

  const grouped = STAGES.map(stage => ({
    ...stage,
    items: projects.filter(p => p.status === stage.key),
  }))

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-slate-400">
          共 {projects.length} 个项目
        </p>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[13px] font-medium text-blue-600 hover:bg-blue-50 transition-all duration-200 cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          新增项目
        </button>
      </div>

      {/* Kanban */}
      {projects.length === 0 ? (
        <div className="py-16 text-center">
          <p className="text-[14px] text-slate-400 mb-3">还没有项目记录</p>
          <button
            onClick={() => setShowAdd(true)}
            className="text-[13px] font-semibold text-blue-600 hover:text-blue-700 cursor-pointer"
          >
            创建你的第一个项目
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {grouped.map((stage) => (
            <div key={stage.key}>
              {/* Column header */}
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-2 h-2 rounded-full ${stage.color}`} />
                <span className="text-[13px] font-semibold text-slate-700">
                  {stage.label}
                </span>
                <span className="text-[12px] text-slate-400 tabular-nums">
                  {stage.items.length}
                </span>
              </div>

              {/* Cards */}
              <div className="space-y-2 min-h-[80px]">
                {stage.items.length === 0 ? (
                  <div className="py-6 border border-dashed border-slate-200 rounded-lg text-center">
                    <span className="text-[12px] text-slate-300">暂无</span>
                  </div>
                ) : (
                  stage.items.map((item, i) => (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03, duration: 0.2, ease }}
                      onClick={() => navigate(`/growth-log/projects/${item.id}`)}
                      className="relative group w-full text-left p-3 rounded-lg border border-slate-200/60 bg-white/70 hover:bg-white hover:border-slate-300/60 hover:-translate-y-px hover:shadow-sm transition-all duration-200 cursor-pointer"
                    >
                      <button
                        onClick={(e) => handleDelete(item.id, e)}
                        className="absolute top-2 right-2 p-1.5 rounded-md text-slate-300 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 transition-all cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                      <p className="text-[14px] font-semibold text-slate-700 truncate pr-6">
                        {item.name}
                      </p>
                      {item.description && (
                        <p className="text-[12px] text-slate-400 truncate mt-0.5">
                          {item.description}
                        </p>
                      )}
                      {item.skills_used.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {item.skills_used.slice(0, 3).map((skill) => (
                            <span
                              key={skill}
                              className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500"
                            >
                              {skill}
                            </span>
                          ))}
                          {item.skills_used.length > 3 && (
                            <span className="text-[10px] text-slate-400">
                              +{item.skills_used.length - 3}
                            </span>
                          )}
                        </div>
                      )}
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add project modal */}
      <AnimatePresence>
        {showAdd && (
          <AddProjectModal onClose={() => setShowAdd(false)} onRefresh={onRefresh} />
        )}
      </AnimatePresence>
    </div>
  )
}


/* ── Add Project Modal ── */

function AddProjectModal({
  onClose,
  onRefresh,
}: {
  onClose: () => void
  onRefresh: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [skills, setSkills] = useState('')
  const [githubUrl, setGithubUrl] = useState('')
  const [status, setStatus] = useState('planning')

  const qc = useQueryClient()

  const createMut = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      rawFetch('/growth-log/projects', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      onClose()
      onRefresh()
      qc.invalidateQueries({ queryKey: ['growth-projects'] })
    },
  })

  const handleSubmit = () => {
    if (!name.trim()) return
    createMut.mutate({
      name: name.trim(),
      description: description.trim(),
      skills_used: skills.split(/[,，、]/).map(s => s.trim()).filter(Boolean),
      github_url: githubUrl.trim() || null,
      status,
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.2, ease }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-xl border border-slate-200 shadow-lg w-full max-w-[420px] mx-4 p-6"
      >
        <h3 className="text-[18px] font-bold text-slate-800 mb-5">新建项目</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">项目名 *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="如 Muduo 网络库"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">简介</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="一句话描述这个项目"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">技术栈</label>
            <input
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
              placeholder="用逗号分隔，如 C++, epoll, Reactor"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">项目链接</label>
            <input
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="GitHub 仓库或项目演示地址"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-2">状态</label>
            <div className="flex gap-2">
              {STAGES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStatus(s.key)}
                  className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
                    status === s.key
                      ? 'border-blue-400 bg-blue-50 text-blue-700'
                      : 'border-slate-200 text-slate-500 hover:border-blue-300'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-[13px] font-medium text-slate-500 hover:bg-slate-50 transition-all cursor-pointer"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim() || createMut.isPending}
            className="px-5 py-2 rounded-lg bg-blue-600 text-white text-[13px] font-bold hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-30 cursor-pointer"
          >
            {createMut.isPending ? '创建中...' : '创建'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}
