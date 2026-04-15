/**
 * 项目页 — 全新实现
 * 卡片式布局 + 进度环 + 详情 Modal + 进展日志
 * 参考图谱页 Coverflow 卡片风格
 */
import { useState, useRef, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Plus, Check, Trash2, FolderGit2, ExternalLink, FileText, Sparkles, BookOpen } from 'lucide-react'
import type { ProjectRecord, ProjectLogEntry } from '@/api/growthLog'
import {
  listProjects, createProject, updateProject, deleteProject,
  listProjectLogs, createProjectLog,
} from '@/api/growthLog'

/* ── Helpers ── */

const STATUS = {
  planning:    { label: '计划中', color: '#8E8E93', bg: 'rgba(142,142,147,0.12)' },
  in_progress: { label: '进行中', color: '#2563EB', bg: 'rgba(37,99,235,0.10)'   },
  completed:   { label: '已完成', color: '#16A34A', bg: 'rgba(22,163,74,0.10)'   },
}

const SKILL_SUGGESTIONS = [
  'C++', 'Python', 'Java', 'Go', 'Rust', 'React', 'Vue.js', 'TypeScript',
  'Node.js', 'FastAPI', 'Spring Boot', 'Docker', 'Kubernetes', 'MySQL',
  'Redis', 'PostgreSQL', 'Linux', '网络编程', '多线程', '机器学习', 'LangChain',
]

function timeAgo(iso: string) {
  const d = new Date(iso), now = new Date()
  const days = Math.floor((now.getTime() - d.getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function fmtDate(iso: string | null) {
  if (!iso) return null
  const d = new Date(iso)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/* ── Progress Ring ── */
function ProgressRing({ count, status }: { count: number; status: string }) {
  const st = STATUS[status as keyof typeof STATUS] ?? STATUS.in_progress
  const r = 34
  const circ = 2 * Math.PI * r
  // max 7 logs for full ring
  const pct = status === 'completed' ? 1 : Math.min(count / 7, 1)
  const offset = circ * (1 - pct)

  return (
    <div className="relative w-[76px] h-[76px]">
      <svg width="76" height="76" viewBox="0 0 76 76" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="38" cy="38" r={r} fill="none" stroke="rgba(0,0,0,0.05)" strokeWidth="5" />
        <circle
          cx="38" cy="38" r={r} fill="none"
          stroke={st.color} strokeWidth="5" strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={pct > 0 ? offset : circ}
          style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.23,1,0.32,1)' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[20px] font-extrabold text-[#1a1a1a] leading-none">{count}</span>
        <span className="text-[9px] text-[#8E8E93] mt-0.5">条进展</span>
      </div>
    </div>
  )
}

/* ── Project Card ── */
function ProjectCard({ project, logCount, onClick }: {
  project: ProjectRecord
  logCount: number
  onClick: () => void
}) {
  const st = STATUS[project.status as keyof typeof STATUS] ?? STATUS.in_progress

  return (
    <motion.div
      layout
      onClick={onClick}
      className="relative cursor-pointer select-none"
      whileHover={{ y: -3 }}
      transition={{ duration: 0.15 }}
    >
      <div
        className="h-full rounded-[20px] p-5 flex flex-col gap-3"
        style={{
          background: 'rgba(255,255,255,0.58)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          border: '1px solid rgba(255,255,255,0.65)',
          boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
          transition: 'box-shadow 0.2s ease, background 0.2s ease',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 28px rgba(0,0,0,0.08)'; (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.72)' }}
        onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 12px rgba(0,0,0,0.04)'; (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.58)' }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="text-[15px] font-bold text-[#1a1a1a] truncate leading-snug">{project.name}</h3>
            <p className="text-[10px] mt-0.5" style={{ color: '#C7C7CC' }}>
              {fmtDate(project.started_at) ? `开始于 ${fmtDate(project.started_at)}` : timeAgo(project.created_at)}
            </p>
          </div>
          <span className="text-[10px] font-semibold px-2.5 py-1 rounded-[8px] shrink-0"
            style={{ background: st.bg, color: st.color }}>
            {st.label}
          </span>
        </div>

        {/* Progress ring */}
        <div className="flex justify-center py-1">
          <ProgressRing count={logCount} status={project.status} />
        </div>

        {/* Gap skill links (高亮显示，这个项目补了哪些缺口) */}
        {project.gap_skill_links && project.gap_skill_links.length > 0 && (
          <div className="flex flex-wrap gap-1.5 items-center">
            <span className="text-[9px] font-bold text-blue-600 uppercase tracking-wider">补缺口</span>
            {project.gap_skill_links.slice(0, 4).map(s => (
              <span
                key={s}
                className="text-[10px] font-semibold px-2 py-0.5 rounded-[5px]"
                style={{ background: 'rgba(37,99,235,0.08)', color: '#2563EB', border: '1px solid rgba(37,99,235,0.2)' }}
              >
                {s}
              </span>
            ))}
            {project.gap_skill_links.length > 4 && (
              <span className="text-[10px] text-blue-500">+{project.gap_skill_links.length - 4}</span>
            )}
          </div>
        )}

        {/* Skills used */}
        {project.skills_used.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 min-h-[20px]">
            {project.skills_used.slice(0, 5).map(s => (
              <span key={s} className="text-[10px] font-medium px-2 py-0.5 rounded-[5px]"
                style={{ background: 'rgba(0,0,0,0.04)', color: '#636366' }}>
                {s}
              </span>
            ))}
            {project.skills_used.length > 5 && (
              <span className="text-[10px] text-[#C7C7CC]">+{project.skills_used.length - 5}</span>
            )}
          </div>
        ) : (
          <div className="min-h-[20px]" />
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-1" style={{ borderTop: '1px solid rgba(0,0,0,0.05)' }}>
          <span className="text-[11px] font-semibold" style={{ color: '#2563EB' }}>查看详情</span>
          {project.github_url && (
            <ExternalLink className="w-3.5 h-3.5" style={{ color: '#C7C7CC' }} />
          )}
          {project.status === 'completed' && !project.github_url && (
            <span className="text-[10px] font-semibold" style={{ color: '#16A34A' }}>已完成</span>
          )}
        </div>
      </div>
    </motion.div>
  )
}


/* ── Log input (shared) ── */
function LogInput({ projectId, logType, placeholder, onAdded }: {
  projectId: number
  logType: 'progress' | 'note'
  placeholder: string
  onAdded: () => void
}) {
  const [val, setVal] = useState('')
  const [saving, setSaving] = useState(false)
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => { ref.current?.focus() }, [logType])

  async function submit() {
    if (!val.trim() || saving) return
    setSaving(true)
    try { await createProjectLog(projectId, val.trim(), logType); setVal(''); onAdded() }
    finally { setSaving(false) }
  }

  return (
    <div className="flex gap-2">
      <input ref={ref} value={val} onChange={e => setVal(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && submit()}
        placeholder={placeholder}
        className="flex-1 px-3 py-2.5 text-[12px] rounded-[10px] outline-none transition-all"
        style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.07)', color: '#1a1a1a' }}
        onFocus={e => { e.currentTarget.style.border = '1px solid rgba(37,99,235,0.4)'; e.currentTarget.style.background = '#fff' }}
        onBlur={e => { e.currentTarget.style.border = '1px solid rgba(0,0,0,0.07)'; e.currentTarget.style.background = 'rgba(0,0,0,0.04)' }}
      />
      <button onClick={submit} disabled={!val.trim() || saving}
        className="px-3 py-2.5 text-[11px] font-semibold text-white rounded-[10px] cursor-pointer shrink-0 transition-all"
        style={{ background: val.trim() ? '#2563EB' : 'rgba(37,99,235,0.3)' }}>
        {saving ? '...' : '记录'}
      </button>
    </div>
  )
}

/* ── Detail Modal ── */
type ModalTab = 'progress' | 'notes' | 'coach'

export function ProjectDetailModal({ project, onClose, onDeleted, onRefresh }: {
  project: ProjectRecord
  onClose: () => void
  onDeleted: () => void
  onRefresh: () => void
}) {
  const qc = useQueryClient()
  const [status, setStatus] = useState(project.status)
  const [savingStatus, setSavingStatus] = useState(false)
  const [activeTab, setActiveTab] = useState<ModalTab>('progress')

  const { data: logsData, refetch: refetchLogs } = useQuery({
    queryKey: ['project-logs', project.id],
    queryFn: () => listProjectLogs(project.id),
    staleTime: 30_000,
  })
  const allLogs: ProjectLogEntry[] = logsData?.logs ?? []
  const progressLogs = allLogs.filter(l => l.log_type === 'progress')
  const noteLogs = allLogs.filter(l => l.log_type === 'note')

  const handleStatusChange = async (s: string) => {
    setSavingStatus(true); setStatus(s)
    try { await updateProject(project.id, { status: s }); onRefresh() }
    finally { setSavingStatus(false) }
  }

  const handleDelete = async () => {
    if (!confirm(`删除「${project.name}」及所有记录？`)) return
    await deleteProject(project.id); onDeleted()
  }

  const handleLogAdded = () => { refetchLogs(); onRefresh() }

  const handleAskCoach = async () => {
    // Fetch career goal + gap skills from profile
    let goalLabel = ''
    let gapSkillsStr = ''
    try {
      const { fetchProfile } = await import('@/api/profiles')
      const profile = await fetchProfile()
      const goal = profile?.career_goals?.find(g => g.is_primary)
      if (goal) {
        goalLabel = goal.target_label || ''
        const gaps = goal.gap_skills || []
        if (gaps.length > 0) gapSkillsStr = gaps.slice(0, 8).join('、')
      }
    } catch { /* best effort */ }

    const progressSummary = progressLogs.slice(0, 5).map(l => `· ${l.content}`).join('\n')
    const notesSummary = noteLogs.slice(0, 3).map(l => `· ${l.content}`).join('\n')
    const skillsStr = project.skills_used.join('、') || '未填写'

    const msg = [
      `[项目规划请求]`,
      `项目名称：${project.name}`,
      project.description ? `项目描述：${project.description}` : '',
      `使用技能：${skillsStr}`,
      `项目状态：${STATUS[project.status as keyof typeof STATUS]?.label ?? project.status}`,
      goalLabel ? `目标岗位：${goalLabel}` : '',
      gapSkillsStr ? `当前技能缺口：${gapSkillsStr}` : '',
      '',
      progressLogs.length > 0
        ? `最近进展：\n${progressSummary}`
        : '进展：项目刚开始',
      notesSummary ? `\n知识笔记：\n${notesSummary}` : '',
      '',
      '请根据以上信息，帮我制定这个项目的具体里程碑规划。包括：每个阶段的目标、技术重点、以及这个项目能在面试中展示的核心亮点。不需要搜索 JD，直接基于我的目标岗位给出规划。',
    ].filter(Boolean).join('\n')

    const { sendToCoach } = await import('@/hooks/useCoachTrigger')
    sendToCoach(msg)
    onClose()
  }

  const st = STATUS[status as keyof typeof STATUS] ?? STATUS.in_progress

  const TABS: { key: ModalTab; label: string; Icon: typeof FileText; count?: number }[] = [
    { key: 'progress', label: '进展记录', Icon: FileText, count: progressLogs.length },
    { key: 'notes',    label: '知识笔记', Icon: BookOpen, count: noteLogs.length },
    { key: 'coach',    label: '问教练',   Icon: Sparkles },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div className="absolute inset-0" style={{ background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(8px)' }}
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 12 }}
        transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
        className="relative w-full max-w-[540px] min-h-[620px] max-h-[88vh] flex flex-col rounded-[22px] overflow-hidden"
        style={{
          background: 'rgba(248,250,255,0.88)',
          backdropFilter: 'blur(40px)',
          WebkitBackdropFilter: 'blur(40px)',
          border: '1px solid rgba(255,255,255,0.7)',
          boxShadow: '0 32px 80px rgba(0,0,0,0.14), 0 4px 16px rgba(0,0,0,0.06)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* ── Header ── */}
        <div className="px-6 pt-5 pb-4 shrink-0" style={{ background: 'linear-gradient(to bottom, rgba(37,99,235,0.03), transparent)', borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div className="flex items-start justify-between gap-2 mb-3">
            <div className="min-w-0 flex-1">
              <h2 className="text-[18px] font-extrabold text-[#1a1a1a] leading-tight truncate">{project.name}</h2>
              {project.description && (
                <p className="text-[11px] mt-1 leading-relaxed line-clamp-1" style={{ color: '#8E8E93' }}>{project.description}</p>
              )}
            </div>
            <button onClick={onClose} className="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer shrink-0"
              style={{ background: 'rgba(0,0,0,0.04)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.08)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.04)')}>
              <X className="w-3.5 h-3.5" style={{ color: '#8E8E93' }} />
            </button>
          </div>

          {/* Row 1: Status selector */}
          <div className="flex items-center gap-1.5 mb-2.5">
            {Object.entries(STATUS).map(([key, s]) => (
              <button key={key}
                onClick={() => !savingStatus && handleStatusChange(key)}
                className="px-3 py-1 text-[10px] font-semibold rounded-[20px] cursor-pointer transition-all"
                style={{
                  background: status === key ? s.bg : 'rgba(0,0,0,0.04)',
                  color: status === key ? s.color : '#C7C7CC',
                  border: status === key ? `1.5px solid ${s.color}22` : '1.5px solid transparent',
                }}>
                {s.label}
              </button>
            ))}
            {project.github_url && (
              <a href={project.github_url} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1 px-2.5 py-1 rounded-[20px] text-[10px] font-medium cursor-pointer ml-auto"
                style={{ color: '#2563EB', background: 'rgba(37,99,235,0.08)' }}
                onClick={e => e.stopPropagation()}>
                <ExternalLink className="w-2.5 h-2.5" /> GitHub
              </a>
            )}
          </div>

          {/* Row 2: Skills */}
          {project.skills_used.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {project.skills_used.map(s => (
                <span key={s} className="text-[10px] font-medium px-2 py-0.5 rounded-[5px]"
                  style={{ background: 'rgba(0,0,0,0.04)', color: '#636366' }}>{s}</span>
              ))}
            </div>
          )}
        </div>

        {/* ── Tabs ── */}
        <div className="flex shrink-0" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          {TABS.map(t => (
            <button key={t.key} onClick={() => setActiveTab(t.key)}
              className="flex-1 flex items-center justify-center gap-1.5 py-3 text-[11px] font-semibold cursor-pointer transition-all border-b-2"
              style={{
                color: activeTab === t.key ? '#2563EB' : '#C7C7CC',
                borderBottomColor: activeTab === t.key ? '#2563EB' : 'transparent',
                background: activeTab === t.key ? 'rgba(37,99,235,0.03)' : 'transparent',
              }}>
              <t.Icon className="w-3.5 h-3.5" />
              {t.label}
              {t.count != null && t.count > 0 && (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
                  style={{ background: 'rgba(37,99,235,0.1)', color: '#2563EB' }}>
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ── Tab content ── */}
        <div className="flex-1 overflow-y-auto px-5 py-4" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(0,0,0,0.08) transparent' }}>

          {/* 进展记录 */}
          {activeTab === 'progress' && (
            <div className="space-y-4">
              <LogInput projectId={project.id} logType="progress" placeholder="今天做了什么..." onAdded={handleLogAdded} />
              {progressLogs.length === 0 ? (
                <p className="text-center py-8 text-[11px]" style={{ color: '#C7C7CC' }}>回车记录今天的进展</p>
              ) : (
                <div className="relative pl-4">
                  <div className="absolute left-1.5 top-2 bottom-2 w-px" style={{ background: 'rgba(0,0,0,0.06)' }} />
                  {progressLogs.map(log => (
                    <div key={log.id} className="flex gap-3 py-2.5">
                      <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 -ml-4 relative z-10"
                        style={{ background: '#2563EB', boxShadow: '0 0 0 2px #fff' }} />
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] text-[#1a1a1a] leading-relaxed">{log.content}</p>
                        <p className="text-[9px] mt-0.5" style={{ color: '#C7C7CC' }}>{timeAgo(log.created_at)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 知识笔记 */}
          {activeTab === 'notes' && (
            <div className="space-y-4">
              <LogInput projectId={project.id} logType="note" placeholder="记录学到的知识、踩过的坑..." onAdded={handleLogAdded} />
              {noteLogs.length === 0 ? (
                <div className="py-8 text-center">
                  <BookOpen className="w-8 h-8 mx-auto mb-2" style={{ color: '#E5E5EA' }} />
                  <p className="text-[11px]" style={{ color: '#C7C7CC' }}>记录做这个项目学到的技术知识</p>
                  <p className="text-[10px] mt-1" style={{ color: '#E5E5EA' }}>比如：epoll LT 和 ET 的区别</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {noteLogs.map(log => (
                    <div key={log.id} className="px-3.5 py-3 rounded-[12px]"
                      style={{ background: 'rgba(124,58,237,0.05)', border: '1px solid rgba(124,58,237,0.1)' }}>
                      <p className="text-[12px] text-[#1a1a1a] leading-relaxed">{log.content}</p>
                      <p className="text-[9px] mt-1.5" style={{ color: '#C7C7CC' }}>{timeAgo(log.created_at)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 问教练 */}
          {activeTab === 'coach' && (
            <div className="py-2">
              {/* Context preview */}
              <div className="p-3.5 rounded-[14px] mb-4"
                style={{ background: 'linear-gradient(135deg, rgba(37,99,235,0.05), rgba(124,58,237,0.05))', border: '1px solid rgba(37,99,235,0.1)' }}>
                <p className="text-[10px] font-bold mb-2" style={{ color: '#2563EB' }}>教练会知道</p>
                <div className="space-y-1">
                  <p className="text-[11px]" style={{ color: '#374151' }}>· 项目：{project.name}（{st.label}）</p>
                  {project.skills_used.length > 0 && (
                    <p className="text-[11px]" style={{ color: '#374151' }}>· 技能：{project.skills_used.slice(0, 4).join('、')}</p>
                  )}
                  <p className="text-[11px]" style={{ color: '#374151' }}>· 进展：{progressLogs.length} 条记录</p>
                  {progressLogs.length > 0 && (
                    <p className="text-[11px] line-clamp-1" style={{ color: '#6B7280' }}>  最近：{progressLogs[0]?.content}</p>
                  )}
                </div>
              </div>

              <p className="text-[11px] leading-relaxed mb-4" style={{ color: '#6B7280' }}>
                教练会结合你的目标岗位和技能缺口，分析这个项目能为你带来什么竞争力，以及接下来应该重点做什么。
              </p>

              <button onClick={handleAskCoach}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-[14px] text-[13px] font-semibold text-white cursor-pointer"
                style={{ background: 'linear-gradient(135deg, #2563EB, #7C3AED)', boxShadow: '0 4px 16px rgba(37,99,235,0.3)' }}
                onMouseEnter={e => (e.currentTarget.style.opacity = '0.9')}
                onMouseLeave={e => (e.currentTarget.style.opacity = '1')}>
                <Sparkles className="w-4 h-4" />
                向教练寻求规划建议
              </button>

              <p className="text-[10px] text-center mt-2.5" style={{ color: '#C7C7CC' }}>
                教练面板会自动打开，关闭此窗口后继续对话
              </p>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="px-5 py-3.5 flex items-center justify-between shrink-0"
          style={{ borderTop: '1px solid rgba(0,0,0,0.06)', background: 'rgba(255,255,255,0.4)' }}>
          <button onClick={handleDelete}
            className="text-[10px] font-medium px-2.5 py-1.5 rounded-[7px] cursor-pointer transition-colors"
            style={{ color: '#EF4444' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(239,68,68,0.06)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
            删除
          </button>
          <button onClick={onClose}
            className="text-[11px] font-semibold px-4 py-1.5 rounded-[9px] text-white cursor-pointer"
            style={{ background: '#2563EB' }}>
            完成
          </button>
        </div>
      </motion.div>
    </div>
  )
}

/* ── Add Project Form ── */
export function AddProjectForm({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [techStack, setTechStack] = useState('')
  const [githubUrl, setGithubUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) { setError('项目名称不能为空'); return }
    setSaving(true); setError('')
    try {
      const skills = techStack.split(/[,，、\s]+/).map(s => s.trim()).filter(Boolean)
      await createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        skills_used: skills,
        github_url: githubUrl.trim() || undefined,
      })
      onSuccess()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally { setSaving(false) }
  }

  const inputCls = "w-full px-3.5 py-2.5 text-[13px] rounded-xl outline-none bg-slate-50 border border-slate-200 focus:border-blue-400 focus:bg-white transition-colors"

  return (
    <div className="bg-white rounded-2xl p-6 shadow-xl">
      <p className="text-[15px] font-bold text-slate-800 mb-5">新建项目</p>
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="项目名称 *"
          autoFocus
          className={inputCls + ' font-semibold'}
        />
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="项目介绍（做了什么、解决了什么问题）"
          rows={3}
          className={inputCls + ' resize-none'}
        />
        <input
          value={techStack}
          onChange={e => setTechStack(e.target.value)}
          placeholder="技术栈（用逗号分隔，如 React, Node.js, Redis）"
          className={inputCls}
        />
        <input
          value={githubUrl}
          onChange={e => setGithubUrl(e.target.value)}
          placeholder="项目链接（GitHub / 演示地址）"
          className={inputCls}
        />
        {error && <p className="text-[11px] text-red-500">{error}</p>}
        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={saving}
            className="flex-1 py-2.5 text-[13px] font-semibold text-white rounded-xl cursor-pointer transition-colors"
            style={{ background: saving ? 'rgba(37,99,235,0.5)' : '#2563EB' }}>
            {saving ? '创建中...' : '创建项目'}
          </button>
          <button type="button" onClick={onCancel}
            className="px-5 py-2.5 text-[13px] text-slate-500 rounded-xl cursor-pointer border border-slate-200 hover:bg-slate-50 transition-colors">
            取消
          </button>
        </div>
      </form>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Main Export
   ═══════════════════════════════════════════════════════════════ */

export function ProjectsSection() {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['growth-projects'],
    queryFn: listProjects,
    staleTime: 3 * 60_000,
  })

  // Fetch log counts for all projects
  const projects = data?.projects ?? []

  // We need log counts per project — use a separate query map
  const [logCounts, setLogCounts] = useState<Record<number, number>>({})

  useEffect(() => {
    if (projects.length === 0) return
    Promise.all(projects.map(p => listProjectLogs(p.id).then(r => [p.id, r.logs.length] as [number, number])))
      .then(pairs => setLogCounts(Object.fromEntries(pairs)))
  }, [data])

  const selected = projects.find(p => p.id === selectedId) ?? null

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['growth-projects'] })
    qc.invalidateQueries({ queryKey: ['growth-timeline'] })
    qc.invalidateQueries({ queryKey: ['growth-summary'] })
  }

  const handleSuccess = () => {
    setShowAdd(false)
    invalidate()
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-52 rounded-[20px] animate-pulse" style={{ background: 'rgba(255,255,255,0.4)' }} />
        ))}
      </div>
    )
  }

  return (
    <>
      <AnimatePresence>
        {showAdd && (
          <AddProjectForm onSuccess={handleSuccess} onCancel={() => setShowAdd(false)} />
        )}
      </AnimatePresence>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {projects.map(p => (
          <ProjectCard
            key={p.id}
            project={p}
            logCount={logCounts[p.id] ?? 0}
            onClick={() => setSelectedId(p.id)}
          />
        ))}
        {/* Add card — always in DOM, opacity-hidden while form is open */}
        <div
          onClick={() => { if (!showAdd) setShowAdd(true) }}
          className="rounded-[20px] flex flex-col items-center justify-center gap-2 min-h-[200px]"
          style={{
            background: 'rgba(255,255,255,0.3)',
            border: '2px dashed rgba(37,99,235,0.2)',
            opacity: showAdd ? 0 : 1,
            pointerEvents: showAdd ? 'none' : 'auto',
            cursor: showAdd ? 'default' : 'pointer',
            transition: 'opacity 0.15s, background 0.15s',
          }}
          onMouseEnter={e => { if (!showAdd) (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.5)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.3)' }}
        >
          <div className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(37,99,235,0.08)' }}>
            <Plus className="w-5 h-5" style={{ color: '#2563EB' }} />
          </div>
          <p className="text-[12px] font-semibold" style={{ color: '#2563EB' }}>添加项目</p>
        </div>
      </div>

      {/* Detail Modal */}
      <AnimatePresence>
        {selected && (
          <ProjectDetailModal
            project={selected}
            onClose={() => setSelectedId(null)}
            onDeleted={() => { setSelectedId(null); invalidate() }}
            onRefresh={() => { invalidate(); qc.invalidateQueries({ queryKey: ['project-logs', selected.id] }) }}
          />
        )}
      </AnimatePresence>
    </>
  )
}
