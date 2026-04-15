import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, useScroll, useTransform, useSpring } from 'framer-motion'
import { fetchGraphMap } from '@/api/graph'
import { fetchProfile } from '@/api/profiles'
import { Kicker, Chapter, PaperCard } from '@/components/editorial'
import type { GraphNode, Zone } from '@/types/graph'
import type { ProfileData } from '@/types/profile'

/* ── Mocks ── */
const mockNodes: GraphNode[] = [
  { node_id: 'fe-junior', label: '前端开发实习生', role_family: '前端', zone: 'safe', replacement_pressure: 0.2, human_ai_leverage: 0.3, salary_p50: 8000, career_level: 1, must_skills: ['HTML', 'CSS', 'JavaScript'] },
  { node_id: 'fe-mid', label: '前端开发工程师', role_family: '前端', zone: 'safe', replacement_pressure: 0.3, human_ai_leverage: 0.4, salary_p50: 18000, career_level: 2, must_skills: ['React', 'TypeScript', 'Webpack'] },
  { node_id: 'fe-senior', label: '高级前端工程师', role_family: '前端', zone: 'leverage', replacement_pressure: 0.4, human_ai_leverage: 0.7, salary_p50: 32000, career_level: 3, must_skills: ['Performance', 'Architecture', 'Leadership'] },
  { node_id: 'fe-staff', label: '前端架构师', role_family: '前端', zone: 'leverage', replacement_pressure: 0.5, human_ai_leverage: 0.8, salary_p50: 50000, career_level: 4, must_skills: ['System Design', 'Cross-team', 'Strategy'] },
  { node_id: 'be-junior', label: '后端开发实习生', role_family: '后端', zone: 'transition', replacement_pressure: 0.4, human_ai_leverage: 0.3, salary_p50: 8500, career_level: 1, must_skills: ['Java', 'SQL', 'Spring'] },
  { node_id: 'be-mid', label: '后端开发工程师', role_family: '后端', zone: 'transition', replacement_pressure: 0.5, human_ai_leverage: 0.4, salary_p50: 19000, career_level: 2, must_skills: ['Redis', 'Kafka', 'Microservices'] },
  { node_id: 'pm-junior', label: '产品助理', role_family: '产品', zone: 'danger', replacement_pressure: 0.7, human_ai_leverage: 0.2, salary_p50: 7000, career_level: 1, must_skills: ['Axure', 'Communication', 'Documentation'] },
  { node_id: 'pm-mid', label: '产品经理', role_family: '产品', zone: 'danger', replacement_pressure: 0.8, human_ai_leverage: 0.3, salary_p50: 16000, career_level: 2, must_skills: ['Data Analysis', 'User Research', 'Roadmap'] },
]

const mockProfile: ProfileData = {
  id: 1,
  name: '林小北',
  source: 'resume',
  created_at: '2024-09-01T10:00:00Z',
  updated_at: '2025-01-15T08:30:00Z',
  profile: {},
  quality: {},
  graph_position: {
    from_node_id: 'fe-junior',
    from_node_label: '前端开发实习生',
    target_node_id: 'fe-senior',
    target_label: '高级前端工程师',
    target_zone: 'leverage',
    gap_skills: ['Performance', 'Architecture'],
    total_hours: 1200,
    safety_gain: 0.35,
    salary_p50: 32000,
  },
}

/* ── Helpers ── */
const zoneMeta: Record<Zone, { numeral: string; label: string; title: string; intro: string }> = {
  safe: {
    numeral: 'I',
    label: '安全区',
    title: '稳扎稳打',
    intro: '这些岗位门槛相对明确，技能体系成熟，市场需求稳定。如果你刚入行或希望稳步积累，这里是最好的起点。',
  },
  leverage: {
    numeral: 'II',
    label: '杠杆区',
    title: '放大优势',
    intro: '人类独特价值与 AI 工具结合得最紧密的方向。这里的岗位更看重判断力、架构思维和影响力，回报率也更高。',
  },
  transition: {
    numeral: 'III',
    label: '过渡区',
    title: '变道加速',
    intro: '技能半衰期较短，或行业正在剧烈重组。选择这里意味着更快的学习节奏，但也可能带来更大的不确定性。',
  },
  danger: {
    numeral: 'IV',
    label: '危险区',
    title: '谨慎踏入',
    intro: '重复性高、标准化程度高的岗位正面临最大替代压力。如果已经身处其中，建议尽早向相邻 zone 迁移。',
  },
}

function levelLabel(level: number) {
  if (level >= 4) return '专家'
  if (level >= 3) return '资深'
  if (level >= 2) return '中级'
  return '初级'
}

function formatSalary(n?: number) {
  if (n == null) return '—'
  return `¥${Math.round(n / 1000)}K`
}

/* ── Components ── */
function RoleCard({
  node,
  isFrom,
  isTarget,
  onClick,
}: {
  node: GraphNode
  isFrom?: boolean
  isTarget?: boolean
  onClick: () => void
}) {
  return (
    <div
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onClick()
      }}
      role="button"
      tabIndex={0}
      className="relative shrink-0 w-[280px] md:w-[320px] cursor-pointer group"
      style={{ scrollSnapAlign: 'start' }}
    >
      <PaperCard className="h-full transition-transform duration-200 group-hover:-translate-y-1">
        {(isFrom || isTarget) && (
          <div className={`absolute -top-2 left-4 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${isTarget ? 'bg-[var(--chestnut)] text-white' : 'bg-[var(--moss)] text-white'}`}>
            {isTarget ? '你想去那里' : '你现在在这里'}
          </div>
        )}
        <div className="flex items-start justify-between gap-3 mb-3">
          <h3 className="font-display font-medium text-[length:var(--fs-body-lg)] leading-[var(--lh-display)] text-[var(--ink-1)] max-w-[20ch]">
            {node.label}
          </h3>
          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-[var(--bg-paper-2)] text-[var(--ink-3)] border border-[var(--line)]">
            {levelLabel(node.career_level)}
          </span>
        </div>
        <p className="text-[length:var(--fs-body-sm)] text-[var(--ink-3)] mb-2">{node.role_family}</p>
        <p className="font-serif italic text-[length:var(--fs-body)] text-[var(--chestnut)] mb-3">
          {formatSalary(node.salary_p50)}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {(node.must_skills || []).slice(0, 3).map((s) => (
            <span key={s} className="px-2 py-0.5 rounded-full border border-[var(--line)] text-[11px] text-[var(--ink-2)]">
              {s}
            </span>
          ))}
        </div>
      </PaperCard>
    </div>
  )
}

function Carousel({
  nodes,
  fromNodeId,
  targetNodeId,
}: {
  nodes: GraphNode[]
  fromNodeId?: string
  targetNodeId?: string
}) {
  const navigate = useNavigate()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault()
        el.scrollLeft += e.deltaY
      }
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [])

  return (
    <div
      ref={ref}
      className="flex gap-4 overflow-x-auto pb-4"
      style={{ scrollSnapType: 'x mandatory', scrollbarWidth: 'none', msOverflowStyle: 'none' }}
    >
      {nodes.map((n) => (
        <RoleCard
          key={n.node_id}
          node={n}
          isFrom={n.node_id === fromNodeId}
          isTarget={n.node_id === targetNodeId}
          onClick={() => navigate(`/role/${n.node_id}`)}
        />
      ))}
    </div>
  )
}

function PositionCards({
  fromNode,
  targetNode,
}: {
  fromNode?: GraphNode
  targetNode?: GraphNode
}) {
  if (!fromNode && !targetNode) return null
  return (
    <div className="mt-8 flex flex-wrap gap-4">
      {fromNode && (
        <div className="px-4 py-3 rounded-lg border border-[var(--line)] bg-[var(--bg-card)]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--moss)] mb-1">你现在在这里</p>
          <p className="font-display font-medium text-[length:var(--fs-body)] text-[var(--ink-1)]">{fromNode.label}</p>
        </div>
      )}
      {targetNode && (
        <div className="px-4 py-3 rounded-lg border border-[var(--line)] bg-[var(--bg-card)]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--chestnut)] mb-1">你想去那里</p>
          <p className="font-display font-medium text-[length:var(--fs-body)] text-[var(--ink-1)]">{targetNode.label}</p>
        </div>
      )}
    </div>
  )
}

/* ── Main Page ── */
export default function GraphPage() {
  const [isMock] = useState(() => new URLSearchParams(window.location.search).get('mock') === '1')
  const containerRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ container: containerRef })
  const rawProgress = useTransform(scrollYProgress, [0, 1], [0, 1])
  const progress = useSpring(rawProgress, { stiffness: 100, damping: 30, restDelta: 0.001 })

  const mapQ = useQuery({
    queryKey: ['graph-map'],
    queryFn: fetchGraphMap,
    initialData: isMock ? { nodes: mockNodes, edges: [], node_count: mockNodes.length, edge_count: 0 } : undefined,
  })

  const profileQ = useQuery({
    queryKey: ['profile'],
    queryFn: fetchProfile,
    enabled: !isMock,
    initialData: isMock ? mockProfile : undefined,
  })

  const nodes = mapQ.data?.nodes || []
  const gp = profileQ.data?.graph_position
  const fromNodeId = gp?.from_node_id
  const targetNodeId = gp?.target_node_id !== gp?.from_node_id ? gp?.target_node_id : undefined

  const fromNode = useMemo(() => nodes.find((n) => n.node_id === fromNodeId), [nodes, fromNodeId])
  const targetNode = useMemo(() => nodes.find((n) => n.node_id === targetNodeId), [nodes, targetNodeId])

  const grouped = useMemo(() => {
    const groups: Record<Zone, GraphNode[]> = { safe: [], leverage: [], transition: [], danger: [] }
    nodes.forEach((n) => {
      groups[n.zone]?.push(n)
    })
    ;(Object.keys(groups) as Zone[]).forEach((z) => {
      groups[z].sort((a, b) => (b.salary_p50 || 0) - (a.salary_p50 || 0))
    })
    return groups
  }, [nodes])

  const zones: Zone[] = ['safe', 'leverage', 'transition', 'danger']

  if (mapQ.isLoading) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <p className="font-serif italic text-[length:var(--fs-body-lg)] text-[var(--ink-2)]">正在绘制图谱…</p>
      </main>
    )
  }

  if (mapQ.error || nodes.length === 0) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <p className="font-sans text-[length:var(--fs-body-lg)] text-[var(--ink-1)]">图谱加载失败</p>
          <p className="mt-2 text-[length:var(--fs-body)] text-[var(--ink-3)]">{mapQ.error instanceof Error ? mapQ.error.message : '暂无数据'}</p>
        </div>
      </main>
    )
  }

  return (
    <main
      ref={containerRef}
      className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)] overflow-y-auto"
    >
      {/* Progress bar */}
      <div className="fixed top-0 left-0 right-0 h-1 bg-[var(--line)]/30 z-50">
        <motion.div
          className="h-full bg-[var(--chestnut)]"
          style={{ scaleX: progress, transformOrigin: '0%' }}
        />
      </div>

      <div className="max-w-[720px] mx-auto px-6 md:px-12 lg:px-20 pb-32">
        {/* Prologue */}
        <section className="pt-16 md:pt-24 pb-8">
          <Kicker>EDITORIAL · 本期图谱</Kicker>
          <h1 className="font-display font-medium text-[length:var(--fs-display-xl)] leading-[var(--lh-display)] tracking-tight text-[var(--ink-1)] max-w-[18ch]">
            你的岗位图谱
          </h1>
          <p className="mt-6 font-sans text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[58ch]">
            我们把市场上的岗位按四个 zone 重新排列：安全区适合扎根，杠杆区适合放大优势，过渡区需要变道加速，危险区则提醒谨慎踏入。
          </p>
          <PositionCards fromNode={fromNode} targetNode={targetNode} />
        </section>

        {/* Chapters */}
        {zones.map((zone) => {
          const meta = zoneMeta[zone]
          const list = grouped[zone]
          if (list.length === 0) return null
          return (
            <Chapter key={zone} numeral={meta.numeral} label={meta.label} title={meta.title} intro={meta.intro}>
              <Carousel nodes={list} fromNodeId={fromNodeId} targetNodeId={targetNodeId} />
            </Chapter>
          )
        })}

        {/* Epilogue */}
        <section className="relative py-16 md:py-24 text-center">
          <div className="max-w-[58ch] mx-auto">
            <p className="font-sans text-[length:var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] italic">
              图谱会随市场变化而更新，但你的位置和目标，只由你自己定义。
            </p>
            <p className="mt-6 font-mono text-[length:var(--fs-caption)] text-[var(--ink-3)]">
              generated at {new Date().toLocaleDateString('zh-CN')}
            </p>
          </div>
        </section>
      </div>
    </main>
  )
}
