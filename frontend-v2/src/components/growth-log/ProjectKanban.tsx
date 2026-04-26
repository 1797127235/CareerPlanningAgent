import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { rawFetch } from '@/api/client'
import { Plus, Trash2 } from 'lucide-react'

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
  { key: 'planning', label: '规划中', color: 'bg-[var(--text-3)]' },
  { key: 'in_progress', label: '进行中', color: 'bg-[var(--blue)]' },
  { key: 'completed', label: '已完成', color: 'bg-emerald-500' },
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
        <p className="text-[13px] text-[var(--text-3)]">
          共 {projects.length} 个项目
        </p>
        <button
          onClick={() => setShowAdd(true)}
          className="btn-cta flex items-center gap-1 px-3 py-1.5 text-[13px] font-medium cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          新增项目
        </button>
      </div>

      {/* Kanban */}
      {projects.length === 0 ? (
        <div className="py-16 text-center glass-static p-8">
          <div className="g-inner">
          <p className="text-[14px] text-[var(--text-2)] mb-3">还没有项目记录</p>
          <button
            onClick={() => setShowAdd(true)}
            className="text-[13px] font-semibold text-[var(--blue)] hover:text-[var(--blue-deep)] cursor-pointer"
          >
            创建你的第一个项目
          </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {grouped.map((stage) => (
            <div key={stage.key}>
              {/* Column header */}
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-2 h-2 rounded-full ${stage.color}`} />
                <span className="text-[13px] font-semibold text-[var(--text-1)]">
                  {stage.label}
                </span>
                <span className="text-[12px] text-[var(--text-3)] tabular-nums">
                  {stage.items.length}
                </span>
              </div>

              {/* Cards */}
              <div className="space-y-2 min-h-[80px]">
                {stage.items.length === 0 ? (
                  <div className="py-6 border border-dashed border-black/[0.06] rounded-[var(--radius-md)] text-center glass-static">
                    <span className="text-[12px] text-[var(--text-3)]">暂无</span>
                  </div>
                ) : (
                  stage.items.map((item, i) => (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03, duration: 0.2, ease }}
                      onClick={() => navigate(`/growth-log/projects/${item.id}`)}
                      className="relative group w-full text-left glass p-3 cursor-pointer"
                    >
                      <button
                        onClick={(e) => handleDelete(item.id, e)}
                        className="absolute top-2 right-2 p-1.5 rounded-md text-[var(--text-3)] opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 transition-all cursor-pointer z-10"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                      <p className="text-[14px] font-semibold text-[var(--text-1)] truncate pr-6">
                        {item.name}
                      </p>
                      {item.description && (
                        <p className="text-[12px] text-[var(--text-3)] truncate mt-0.5">
                          {item.description}
                        </p>
                      )}
                      {item.skills_used.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {item.skills_used.slice(0, 3).map((skill) => (
                            <span
                              key={skill}
                              className="chip px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-2)]"
                            >
                              {skill}
                            </span>
                          ))}
                          {item.skills_used.length > 3 && (
                            <span className="text-[10px] text-[var(--text-3)]">
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
        className="glass-static w-full max-w-[420px] mx-4 p-6"
      >
        <div className="g-inner">
        <h3 className="text-[18px] font-bold text-[var(--text-1)] mb-5">新建项目</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-semibold text-[var(--text-2)] mb-1.5">项目名 *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="如 Muduo 网络库"
              className="w-full px-3 py-2 rounded-lg border border-black/[0.06] text-[14px] text-[var(--text-1)] placeholder:text-[var(--text-3)] focus:outline-none focus:ring-2 focus:ring-[var(--blue)]/15 focus:border-[var(--blue)]/30 transition-all bg-white/60"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-[var(--text-2)] mb-1.5">简介</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="一句话描述这个项目"
              className="w-full px-3 py-2 rounded-lg border border-black/[0.06] text-[14px] text-[var(--text-1)] placeholder:text-[var(--text-3)] focus:outline-none focus:ring-2 focus:ring-[var(--blue)]/15 focus:border-[var(--blue)]/30 transition-all bg-white/60"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-[var(--text-2)] mb-1.5">技术栈</label>
            <input
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
              placeholder="用逗号分隔，如 C++, epoll, Reactor"
              className="w-full px-3 py-2 rounded-lg border border-black/[0.06] text-[14px] text-[var(--text-1)] placeholder:text-[var(--text-3)] focus:outline-none focus:ring-2 focus:ring-[var(--blue)]/15 focus:border-[var(--blue)]/30 transition-all bg-white/60"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-[var(--text-2)] mb-1.5">项目链接</label>
            <input
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="GitHub 仓库或项目演示地址"
              className="w-full px-3 py-2 rounded-lg border border-black/[0.06] text-[14px] text-[var(--text-1)] placeholder:text-[var(--text-3)] focus:outline-none focus:ring-2 focus:ring-[var(--blue)]/15 focus:border-[var(--blue)]/30 transition-all bg-white/60"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-[var(--text-2)] mb-2">状态</label>
            <div className="flex gap-2">
              {STAGES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStatus(s.key)}
                  className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
                    status === s.key
                      ? 'border-[var(--blue)]/40 bg-[var(--blue)]/[0.08] text-[var(--blue)]'
                      : 'border-black/[0.06] text-[var(--text-2)] hover:border-[var(--blue)]/30'
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
            className="px-4 py-2 rounded-lg text-[13px] font-medium text-[var(--text-2)] hover:bg-black/[0.04] transition-all cursor-pointer"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim() || createMut.isPending}
            className="px-5 py-2 rounded-lg bg-[var(--blue)] text-white text-[13px] font-bold hover:bg-[var(--blue-deep)] active:scale-[0.98] transition-all disabled:opacity-30 cursor-pointer"
          >
            {createMut.isPending ? '创建中...' : '创建'}
          </button>
        </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
