import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchGraphMap } from '@/api/graph'
import { fetchProfile } from '@/api/profiles'
import { Block, BlockGrid, DataRow, Tooltip } from '@/components/ui'
import { GLOSSARY } from '@/lib/glossary'
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
const zoneMeta: Record<Zone, { label: string; title: string; intro: string; glossaryKey: keyof typeof GLOSSARY }> = {
  safe: {
    label: '安全区',
    title: '稳扎稳打',
    intro: '门槛明确，技能成熟，市场稳定。',
    glossaryKey: 'zone_safe',
  },
  leverage: {
    label: '杠杆区',
    title: '放大优势',
    intro: '人类价值与 AI 结合最紧密的方向。',
    glossaryKey: 'zone_leverage',
  },
  transition: {
    label: '过渡区',
    title: '变道加速',
    intro: '技能半衰期较短，学习节奏更快。',
    glossaryKey: 'zone_transition',
  },
  danger: {
    label: '危险区',
    title: '谨慎踏入',
    intro: '重复性高、标准化程度高的岗位。',
    glossaryKey: 'zone_danger',
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

/* ── Main Page ── */
export default function GraphPage() {
  const [isMock] = useState(() => new URLSearchParams(window.location.search).get('mock') === '1')
  const navigate = useNavigate()

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

  const nodes = useMemo(() => mapQ.data?.nodes ?? [], [mapQ.data?.nodes])
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
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-[var(--space-5)]">
        <p className="font-serif italic text-[var(--text-lg)] text-[var(--ink-2)]">正在绘制图谱…</p>
      </main>
    )
  }

  if (mapQ.error || nodes.length === 0) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-[var(--space-5)]">
        <div className="text-center max-w-md">
          <p className="text-[var(--text-lg)] text-[var(--ink-1)]">图谱加载失败</p>
          <p className="mt-2 text-[var(--text-base)] text-[var(--ink-3)]">{mapQ.error instanceof Error ? mapQ.error.message : '暂无数据'}</p>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <div className="max-w-[960px] mx-auto px-[var(--space-6)] md:px-[var(--space-7)] py-[var(--space-6)]">
        <section className="mb-[var(--space-5)]">
          <h1 className="text-[var(--text-2xl)] font-semibold text-[var(--ink-1)] tracking-tight">
            岗位图谱
          </h1>
          <p className="mt-2 text-[var(--text-base)] text-[var(--ink-2)] max-w-[58ch]">
            四个 zone 重新排列：安全区适合扎根，杠杆区适合放大优势，过渡区需要变道加速，危险区则提醒谨慎踏入。
          </p>
          {(fromNode || targetNode) && (
            <div className="mt-4 flex flex-wrap gap-3">
              {fromNode && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-pill)] border border-[var(--line)] bg-[var(--bg-card)] text-[var(--text-sm)] text-[var(--ink-1)]">
                  <span className="w-2 h-2 rounded-full bg-[var(--moss)]" />
                  你现在在这里 · {fromNode.label}
                </span>
              )}
              {targetNode && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-pill)] border border-[var(--line)] bg-[var(--bg-card)] text-[var(--text-sm)] text-[var(--ink-1)]">
                  <span className="w-2 h-2 rounded-full bg-[var(--chestnut)]" />
                  你想去那里 · {targetNode.label}
                </span>
              )}
            </div>
          )}
        </section>

        <BlockGrid>
          {zones.map((zone) => {
            const meta = zoneMeta[zone]
            const list = grouped[zone]
            if (list.length === 0) return null
            const isCurrentZone = fromNode?.zone === zone
            return (
              <Block
                key={zone}
                kicker={
                  <Tooltip content={GLOSSARY[meta.glossaryKey].desc} storageKey={meta.glossaryKey}>
                    <span>{meta.label}</span>
                  </Tooltip>
                }
                title={meta.title}
                accent={isCurrentZone}
              >
                <p className="text-[var(--text-sm)] text-[var(--ink-2)] mb-3">{meta.intro}</p>
                <div className="space-y-1">
                  {list.slice(0, 5).map((node) => (
                    <div
                      key={node.node_id}
                      onClick={() => navigate(`/role/${node.node_id}`)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') navigate(`/role/${node.node_id}`)
                      }}
                      role="button"
                      tabIndex={0}
                      className="cursor-pointer rounded-[var(--radius-sm)] hover:bg-[var(--bg-paper-2)] transition-colors"
                    >
                      <DataRow
                        label={node.label}
                        value={
                          <Tooltip content={GLOSSARY.p50.desc} storageKey="p50">
                            <span>{formatSalary(node.salary_p50)}</span>
                          </Tooltip>
                        }
                        hint={`${levelLabel(node.career_level)} · ${node.role_family}`}
                      />
                    </div>
                  ))}
                </div>
              </Block>
            )
          })}
        </BlockGrid>

        <p className="mt-[var(--space-6)] text-[var(--text-sm)] text-[var(--ink-3)] italic text-center">
          图谱会随市场变化而更新，但你的位置和目标，只由你自己定义。
        </p>
      </div>
    </main>
  )
}
