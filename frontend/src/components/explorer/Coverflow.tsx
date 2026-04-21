import { useState, useCallback, useEffect, useRef, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Search, X, ChevronLeft, ChevronRight, ArrowUp, Repeat2, ArrowRight, CheckCircle2, MapPin, Target } from 'lucide-react'
import { searchGraphNodes, fetchEscapeRoutes, setCareerGoal, addCareerGoal, fetchNodeIntro } from '@/api/graph'
import type { GraphNode, GraphEdge, EscapeRoute, SearchResult } from '@/types/graph'
import { dispatchCoachTrigger } from '@/hooks/useCoachTrigger'

/* ── Helpers ── */

const ZONE_LABEL: Record<string, string> = { safe: '安全区', transition: '过渡区', danger: '危险区', leverage: '杠杆区' }
const ZONE_CLS: Record<string, string> = {
  safe: 'bg-green-100 text-green-700',
  transition: 'bg-amber-100 text-amber-700',
  danger: 'bg-red-100 text-red-700',
  leverage: 'bg-blue-100 text-blue-700',
}
const ZONE_STRIP: Record<string, string> = {
  safe: 'from-green-500 to-green-400',
  transition: 'from-amber-500 to-amber-400',
  danger: 'from-red-500 to-red-400',
  leverage: 'from-blue-500 to-blue-400',
}
const ZONE_DOT: Record<string, string> = { safe: '#22c55e', transition: '#f59e0b', danger: '#ef4444', leverage: '#3b82f6' }
const DEFAULT_ZONE = 'transition'

const ROLE_FAMILY_LABEL: Record<string, string> = {
  software_development: '软件开发',
  algorithm_ai: '算法/AI',
  data_engineering: '数据工程',
  data_analysis: '数据分析',
  devops_infra: '运维/安全/基础设施',
  management: '架构/管理',
  quality_assurance: '质量保障',
}

const TAG_CLS: Record<string, string> = {
  '最快': 'bg-blue-50 text-blue-600 border-blue-200',
  '最稳': 'bg-green-50 text-green-600 border-green-200',
  '高薪': 'bg-amber-50 text-amber-600 border-amber-200',
  '备选': 'bg-slate-50 text-slate-500 border-slate-200',
}


// Normalize with sqrt scaling + floor for balanced radar shape.
// Linear min-max creates near-zero spikes when data is skewed (e.g. degree 4-21).
// sqrt compresses high end, expands low end → visually balanced.
const _norm = (v: number, min: number, max: number) => {
  const linear = Math.max(0, Math.min(1, (v - min) / (max - min)))
  return Math.round(15 + Math.sqrt(linear) * 75) // range: 15-90
}

function computeAbilities(n: GraphNode) {
  return {
    'AI安全度': Math.max(0, 100 - (n.replacement_pressure ?? 50)),
    '人机杠杆': n.human_ai_leverage ?? 50,
    // skill_count range: 24-290 (from roadmap data)
    '技能广度': _norm(n.skill_count ?? 80, 24, 290),
    // degree range: 4-21 (from graph edges)
    '转型灵活度': _norm(n.degree ?? 6, 4, 21),
  }
}

function getSafety(n: GraphNode): number {
  return Math.max(0, 100 - (n.replacement_pressure ?? 50))
}

/* ── Radar Canvas ── */

function drawRadar(canvas: HTMLCanvasElement, abilities: Record<string, number>, size: number, animate = false, target?: Record<string, number>) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const cx = canvas.width / 2, cy = canvas.height / 2
  const keys = Object.keys(abilities), vals = Object.values(abilities), n = keys.length, r = size

  function render(progress: number) {
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    // Grid
    for (let ring = 1; ring <= 4; ring++) {
      const rr = r * ring / 4
      ctx.beginPath()
      for (let i = 0; i <= n; i++) {
        const a = (i / n) * Math.PI * 2 - Math.PI / 2
        i === 0 ? ctx.moveTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr) : ctx.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr)
      }
      ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5; ctx.stroke()
    }
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 - Math.PI / 2
      ctx.beginPath(); ctx.moveTo(cx, cy)
      ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r)
      ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5; ctx.stroke()
    }
    // Data
    const ease = 1 - Math.pow(1 - progress, 3)
    ctx.beginPath()
    for (let i = 0; i <= n; i++) {
      const idx = i % n, a = (idx / n) * Math.PI * 2 - Math.PI / 2
      const v = vals[idx] / 100 * r * ease
      i === 0 ? ctx.moveTo(cx + Math.cos(a) * v, cy + Math.sin(a) * v) : ctx.lineTo(cx + Math.cos(a) * v, cy + Math.sin(a) * v)
    }
    ctx.fillStyle = `rgba(99,102,241,${0.12 * ease})`; ctx.fill()
    ctx.strokeStyle = '#6366f1'; ctx.lineWidth = 1.5; ctx.globalAlpha = ease; ctx.stroke(); ctx.globalAlpha = 1
    // Dots + labels
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 - Math.PI / 2, v = vals[i] / 100 * r * ease
      ctx.beginPath(); ctx.arc(cx + Math.cos(a) * v, cy + Math.sin(a) * v, 2.5, 0, Math.PI * 2)
      ctx.fillStyle = '#6366f1'; ctx.globalAlpha = ease; ctx.fill(); ctx.globalAlpha = 1
      if (progress > 0.4) {
        const la = Math.min(1, (progress - 0.4) / 0.3)
        const lx = cx + Math.cos(a) * (r + 14), ly = cy + Math.sin(a) * (r + 14)
        ctx.font = "500 9px 'Commissioner','Noto Sans SC',sans-serif"
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
        ctx.fillStyle = `rgba(100,116,139,${la})`; ctx.fillText(keys[i], lx, ly)
      }
    }
    // Target overlay (dashed amber)
    if (target) {
      const tvals = Object.values(target)
      ctx.beginPath()
      for (let i = 0; i <= n; i++) {
        const idx = i % n, a = (idx / n) * Math.PI * 2 - Math.PI / 2
        const v = tvals[idx] / 100 * r * ease
        i === 0 ? ctx.moveTo(cx + Math.cos(a) * v, cy + Math.sin(a) * v) : ctx.lineTo(cx + Math.cos(a) * v, cy + Math.sin(a) * v)
      }
      ctx.setLineDash([4, 3])
      ctx.strokeStyle = '#f59e0b'
      ctx.lineWidth = 1.5
      ctx.globalAlpha = 0.8 * ease
      ctx.stroke()
      ctx.setLineDash([])
      ctx.globalAlpha = 1
    }
  }

  if (!animate) { render(1); return }
  const start = performance.now()
  function frame(now: number) {
    const p = Math.min((now - start) / 600, 1)
    render(p)
    if (p < 1) requestAnimationFrame(frame)
  }
  requestAnimationFrame(frame)
}

/* ── Props ── */

interface ProfileOption {
  id: number
  name: string
}

interface CoverflowProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  initialNodeId?: string
  profileId?: number
  fromNodeId?: string
  targetNodeId?: string
  profiles?: ProfileOption[]
  activeProfileId?: number | null
  onProfileChange?: (id: number) => void
  careerGoals?: import('@/types/profile').CareerGoal[]
  onGoalSet?: () => void
}

const ZONE_FILTERS = [
  { key: null,         label: '全部' },
  { key: 'safe',       label: '安全区' },
  { key: 'leverage',   label: '杠杆区' },
  { key: 'transition', label: '过渡区' },
  { key: 'danger',     label: '危险区' },
] as const

export function Coverflow({ nodes, edges: _edges, initialNodeId, profileId, fromNodeId, targetNodeId, careerGoals, profiles, activeProfileId, onProfileChange, onGoalSet }: CoverflowProps) {
  // Zone filter
  const [zoneFilter, setZoneFilter] = useState<string | null>(null)

  // Sort: entry-level first (lower career_level), then by AI safety descending
  const sortedNodes = useMemo(() =>
    [...nodes].sort((a, b) => {
      const levelDiff = (a.career_level ?? 3) - (b.career_level ?? 3)
      if (levelDiff !== 0) return levelDiff
      return getSafety(b) - getSafety(a)
    }),
    [nodes],
  )

  const filteredNodes = useMemo(() =>
    zoneFilter ? sortedNodes.filter(n => n.zone === zoneFilter) : sortedNodes,
    [sortedNodes, zoneFilter],
  )

  // Compute target index from initialNodeId (use filteredNodes)
  const targetIdx = useMemo(() => {
    if (!initialNodeId) return -1
    const idx = filteredNodes.findIndex(n => n.node_id === initialNodeId)
    return idx >= 0 ? idx : -1
  }, [initialNodeId, filteredNodes])

  const [currentIdx, setCurrentIdx] = useState(targetIdx >= 0 ? targetIdx : 0)
  const [flipped, setFlipped] = useState(false)

  // Reset currentIdx when zone filter changes, but skip on initial mount
  // (initial mount must preserve targetIdx from initialNodeId)
  const zoneFilterMounted = useRef(false)
  useEffect(() => {
    if (!zoneFilterMounted.current) { zoneFilterMounted.current = true; return }
    setCurrentIdx(0)
    setFlipped(false)
  }, [zoneFilter])

  // Focus-in entrance: blur → sharp, scale 0.92 → 1, with floating label
  const hasInitialTarget = targetIdx >= 0
  const [focusPhase, setFocusPhase] = useState<'blur' | 'reveal' | 'done'>(hasInitialTarget ? 'blur' : 'done')

  useEffect(() => {
    if (!hasInitialTarget) return
    const t1 = setTimeout(() => setFocusPhase('reveal'), 150)
    const t2 = setTimeout(() => setFocusPhase('done'), 1600)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [hasInitialTarget])

  const [routesCache, setRoutesCache] = useState<Map<string, EscapeRoute[]>>(new Map())
  const [routesLoading, setRoutesLoading] = useState(false)
  const [compareData, setCompareData] = useState<{ from: GraphNode; to: GraphNode; routes: EscapeRoute } | null>(null)

  // Node intro cache — use a ref to track fetched nodes (avoids introCache as dep)
  const [introCache, setIntroCache] = useState<Map<string, string>>(new Map())
  const introFetchedRef = useRef<Set<string>>(new Set())

  // Detail modal state
  const [detailNode, setDetailNode] = useState<GraphNode | null>(null)

  // Search (with IME composition guard for Chinese input)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchOpen, setSearchOpen] = useState(false)
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isComposing = useRef(false)
  const searchRef = useRef<HTMLDivElement>(null)

  const currentNode = filteredNodes[currentIdx] ?? null
  const nodeMap = useMemo(() => new Map(nodes.map(n => [n.node_id, n])), [nodes])

  // Fetch escape routes for center card
  useEffect(() => {
    if (!currentNode) return
    const id = currentNode.node_id
    if (routesCache.has(id)) return
    setRoutesLoading(true)
    fetchEscapeRoutes(id)
      .then(data => setRoutesCache(prev => new Map(prev).set(id, data.routes)))
      .catch(() => setRoutesCache(prev => new Map(prev).set(id, [])))
      .finally(() => setRoutesLoading(false))
  }, [currentNode, routesCache])

  // Fetch node intro for center card — ref guards against retry after failure
  useEffect(() => {
    if (!currentNode) return
    const id = currentNode.node_id
    if (introFetchedRef.current.has(id)) return
    introFetchedRef.current.add(id)
    fetchNodeIntro(id)
      .then(data => setIntroCache(prev => new Map(prev).set(id, data.intro)))
      .catch(() => setIntroCache(prev => new Map(prev).set(id, '')))
  }, [currentNode])

  const currentRoutes = currentNode ? (routesCache.get(currentNode.node_id) ?? []) : []

  // Navigation
  const navigate = useCallback((idx: number) => {
    if (filteredNodes.length === 0) return
    setCurrentIdx(Math.max(0, Math.min(filteredNodes.length - 1, idx)))
    setFlipped(false)
    setDetailNode(null)
  }, [filteredNodes.length])

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT') return
      if (e.key === 'ArrowLeft') navigate(currentIdx - 1)
      if (e.key === 'ArrowRight') navigate(currentIdx + 1)
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [currentIdx, navigate])

  // Search — fires API call, skipped during IME composition
  const doSearch = useCallback((q: string) => {
    if (searchTimer.current) clearTimeout(searchTimer.current)
    if (q.length < 1) { setSearchResults([]); setSearchOpen(false); return }
    searchTimer.current = setTimeout(async () => {
      try {
        const data = await searchGraphNodes(q)
        setSearchResults(data.results)
        setSearchOpen(true)
      } catch { setSearchResults([]) }
    }, 250)
  }, [])

  const handleSearchChange = useCallback((q: string) => {
    setSearchQuery(q)
    // Don't fire API during IME composition (Chinese/Japanese input)
    if (!isComposing.current) doSearch(q)
  }, [doSearch])

  const handleCompositionEnd = useCallback((e: React.CompositionEvent<HTMLInputElement>) => {
    isComposing.current = false
    const q = e.currentTarget.value
    setSearchQuery(q)
    doSearch(q)
  }, [doSearch])

  const handleSearchSelect = useCallback((nodeId: string) => {
    // If filtered, try within filtered first; else clear filter then jump
    const idx = filteredNodes.findIndex(n => n.node_id === nodeId)
    if (idx >= 0) {
      navigate(idx)
    } else {
      setZoneFilter(null)
      const fullIdx = sortedNodes.findIndex(n => n.node_id === nodeId)
      if (fullIdx >= 0) setTimeout(() => navigate(fullIdx), 0)
    }
    setSearchQuery(''); setSearchResults([]); setSearchOpen(false)
  }, [filteredNodes, sortedNodes, navigate])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setSearchOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Goal setting state (lives alongside compareData)
  type GoalPhase = 'idle' | 'confirming' | 'saving' | 'done'
  const [goalPhase, setGoalPhase] = useState<GoalPhase>('idle')
  const [goalError, setGoalError] = useState<string | null>(null)
  const routerNavigate = useNavigate()

  // Direct goal setting (from card front, bypasses escape-route compare flow)
  const [directGoalNode, setDirectGoalNode] = useState<GraphNode | null>(null)
  type DirectGoalPhase = 'confirm' | 'saving' | 'done'
  const [directGoalPhase, setDirectGoalPhase] = useState<DirectGoalPhase>('confirm')
  const [directGoalError, setDirectGoalError] = useState<string | null>(null)

  const openDirectGoal = useCallback((node: GraphNode, e: React.MouseEvent) => {
    e.stopPropagation()
    setDirectGoalNode(node)
    setDirectGoalPhase('confirm')
    setDirectGoalError(null)
  }, [])

  const handleSetDirectGoal = useCallback(async () => {
    if (!directGoalNode || !profileId) return
    setDirectGoalPhase('saving')
    setDirectGoalError(null)
    try {
      // 若该节点已是某个方向，则只更新主目标；否则新增方向
      const alreadyGoal = careerGoals?.some(g => g.target_node_id === directGoalNode.node_id)
      if (alreadyGoal) {
        const existing = careerGoals?.find(g => g.target_node_id === directGoalNode.node_id)
        if (existing && !existing.is_primary) {
          // 已有此方向但不是主目标 → 设为主目标（通过更新主目标接口）
          await setCareerGoal({
            profile_id: profileId,
            target_node_id: directGoalNode.node_id,
            target_label: directGoalNode.label,
            target_zone: directGoalNode.zone ?? DEFAULT_ZONE,
            gap_skills: existing.gap_skills ?? [],
            estimated_hours: existing.total_hours ?? 0,
            safety_gain: existing.safety_gain ?? 0,
            salary_p50: directGoalNode.salary_p50 ?? 0,
          })
        }
      } else if (careerGoals && careerGoals.length > 0) {
        // 已有其他方向 → 新增这个方向（不覆盖）
        await addCareerGoal({
          target_node_id: directGoalNode.node_id,
          target_label: directGoalNode.label,
          target_zone: directGoalNode.zone ?? DEFAULT_ZONE,
          gap_skills: [],
          estimated_hours: 0,
          safety_gain: 0,
          salary_p50: directGoalNode.salary_p50 ?? 0,
          set_as_primary: false,
        })
      } else {
        // 首次设目标 → 更新主目标
        await setCareerGoal({
          profile_id: profileId,
          target_node_id: directGoalNode.node_id,
          target_label: directGoalNode.label,
          target_zone: directGoalNode.zone ?? DEFAULT_ZONE,
          gap_skills: [],
          estimated_hours: 0,
          safety_gain: 0,
          salary_p50: directGoalNode.salary_p50 ?? 0,
        })
      }
      setDirectGoalPhase('done')
      onGoalSet?.()
    } catch (err) {
      setDirectGoalError(err instanceof Error ? err.message : '设定失败，请稍后重试')
      setDirectGoalPhase('confirm')
    }
  }, [directGoalNode, profileId, careerGoals, onGoalSet])

  // Reset goal state whenever compare overlay changes
  const handleShowCompare = useCallback((route: EscapeRoute) => {
    setGoalPhase('idle')
    setGoalError(null)
    if (!currentNode) return
    const toNode = nodeMap.get(route.target_node_id)
    if (toNode) setCompareData({ from: currentNode, to: toNode, routes: route })
  }, [currentNode, nodeMap])

  const handleSetGoal = useCallback(async () => {
    if (!compareData || !profileId) return
    setGoalPhase('saving')
    setGoalError(null)
    try {
      await setCareerGoal({
        profile_id: profileId,
        target_node_id: compareData.routes.target_node_id,
        target_label: compareData.routes.target_label ?? compareData.to.label,
        target_zone: compareData.routes.target_zone ?? compareData.to.zone,
        gap_skills: compareData.routes.gap_skills,
        estimated_hours: compareData.routes.estimated_hours ?? 0,
        safety_gain: compareData.routes.safety_gain ?? 0,
        salary_p50: compareData.to.salary_p50 ?? 0,
      })
      setGoalPhase('done')
      onGoalSet?.()
      // Notify coach
      dispatchCoachTrigger('goal-set', compareData.to.label ?? '未知岗位')
    } catch (err) {
      setGoalError(err instanceof Error ? err.message : '设定失败，请稍后重试')
      setGoalPhase('confirming')
    }
  }, [compareData, profileId, onGoalSet])

  // Compare
  const showCompare = handleShowCompare

  const jumpToNode = useCallback((nodeId: string) => {
    const idx = filteredNodes.findIndex(n => n.node_id === nodeId)
    if (idx >= 0) {
      navigate(idx)
    } else {
      setZoneFilter(null)
      const fullIdx = sortedNodes.findIndex(n => n.node_id === nodeId)
      if (fullIdx >= 0) setTimeout(() => navigate(fullIdx), 0)
    }
    setCompareData(null)
  }, [filteredNodes, sortedNodes, navigate])

  // Jump to "my position" (fromNodeId)
  const jumpToMyPosition = useCallback(() => {
    if (!fromNodeId) return
    jumpToNode(fromNodeId)
  }, [fromNodeId, jumpToNode])

  // Jump to target node
  const jumpToTarget = useCallback(() => {
    if (!targetNodeId) return
    jumpToNode(targetNodeId)
  }, [targetNodeId, jumpToNode])

  // Radar refs
  const radarRef = useRef<HTMLCanvasElement>(null)
  const prevNodeRef = useRef<string | null>(null)
  const gapRadarRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!radarRef.current || !currentNode) return
    const isNew = prevNodeRef.current !== currentNode.node_id
    prevNodeRef.current = currentNode.node_id
    const abilities = computeAbilities(currentNode)
    setTimeout(() => {
      if (radarRef.current) drawRadar(radarRef.current, abilities, 62, isNew)
    }, isNew ? 200 : 0)
  }, [currentNode])

  useEffect(() => {
    if (goalPhase !== 'done' || !compareData || !gapRadarRef.current) return
    const current = computeAbilities(compareData.from)
    const tgt = computeAbilities(compareData.to)
    const t = setTimeout(() => {
      if (gapRadarRef.current) drawRadar(gapRadarRef.current, current, 54, true, tgt)
    }, 80)
    return () => clearTimeout(t)
  }, [goalPhase, compareData])

  // Career level ladder
  const maxLevel = useMemo(() => Math.max(...nodes.map(n => n.career_level), 5), [nodes])

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* ── Top toolbar: zone filters + search + profile selector ── */}
      <div className="absolute top-4 left-4 right-4 z-30 flex items-start gap-3">
        {/* Left: zone filter pills */}
        <div className="flex items-center gap-1.5 flex-wrap shrink-0 max-w-[40%]">
          {ZONE_FILTERS.map(f => (
            <button
              key={String(f.key)}
              onClick={() => setZoneFilter(f.key)}
              className={`px-3 py-1.5 rounded-full text-[12px] font-semibold transition-all cursor-pointer ${
                zoneFilter === f.key
                  ? 'bg-[var(--blue)] text-white shadow-sm'
                  : 'bg-white/60 backdrop-blur-sm border border-white/50 text-slate-600 hover:bg-white/80'
              }`}
            >
              {f.label}
              {f.key === null && <span className="ml-1 text-slate-400 font-normal">{filteredNodes.length}</span>}
            </button>
          ))}
          {fromNodeId && (
            <button
              onClick={jumpToMyPosition}
              title="回到我的位置"
              className="flex items-center gap-1 px-3 py-1.5 rounded-full text-[12px] font-semibold bg-white/60 backdrop-blur-sm border border-white/50 text-slate-600 hover:bg-white/80 transition-all cursor-pointer"
            >
              <MapPin className="w-3.5 h-3.5 text-[var(--blue)]" />
              我的位置
            </button>
          )}
          {targetNodeId && (
            <button
              onClick={jumpToTarget}
              title="跳到目标岗位"
              className="flex items-center gap-1 px-3 py-1.5 rounded-full text-[12px] font-semibold bg-amber-50/80 backdrop-blur-sm border border-amber-200/60 text-amber-700 hover:bg-amber-100/80 transition-all cursor-pointer"
            >
              <Target className="w-3.5 h-3.5" />
              目标岗位
            </button>
          )}
        </div>

        {/* Center: search */}
        <div className="flex-1 flex justify-center min-w-0">
          <div ref={searchRef} className="relative w-full max-w-[360px]">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => handleSearchChange(e.target.value)}
              onCompositionStart={() => { isComposing.current = true }}
              onCompositionEnd={handleCompositionEnd}
              placeholder="搜索岗位..."
              className="w-full pl-10 pr-10 py-3 rounded-[20px] text-[13px] font-medium text-[var(--text-1)] bg-white/[0.38] backdrop-blur-[24px] backdrop-saturate-[140%] border-[1.5px] border-white/50 outline-none transition-all focus:bg-white/60 focus:border-[var(--blue)]/30 focus:shadow-[0_8px_32px_rgba(37,99,235,.10)] placeholder:text-[var(--text-3)]"
              style={{ fontFamily: "var(--font-sans)", boxShadow: '0 4px 20px rgba(0,0,0,.05)' }}
            />
            {searchQuery && (
              <button onClick={() => { setSearchQuery(''); setSearchResults([]); setSearchOpen(false) }}
                className="absolute right-4 top-1/2 -translate-y-1/2 cursor-pointer">
                <X className="w-4 h-4 text-slate-400 hover:text-slate-600" />
              </button>
            )}
            {searchOpen && searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-white/80 backdrop-blur-xl border-[1.5px] border-white/60 rounded-[20px] max-h-60 overflow-y-auto z-40"
                style={{ boxShadow: '0 8px 32px rgba(99,102,241,.10)' }}>
                {searchResults.map(r => (
                  <button key={r.node_id} onClick={() => handleSearchSelect(r.node_id)}
                    className="w-full text-left px-5 py-3 hover:bg-[var(--blue)]/[0.06] transition-colors flex items-center gap-2.5 cursor-pointer first:rounded-t-[20px] last:rounded-b-[20px]">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: ZONE_DOT[r.zone] ?? ZONE_DOT[DEFAULT_ZONE] }} />
                    <span className="text-[13px] font-semibold text-slate-800">{r.label}</span>
                    <span className="text-[11px] text-slate-400 ml-auto">{r.role_family}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: profile selector — only when multiple profiles */}
        {profiles && profiles.length > 1 && onProfileChange && (
          <div className="flex items-center gap-1.5 bg-white/70 backdrop-blur-sm border border-white/60 rounded-full px-3 py-1.5 shrink-0">
            <span className="text-[11px] text-slate-400 shrink-0">画像</span>
            <select
              value={activeProfileId ?? ''}
              onChange={e => onProfileChange(Number(e.target.value))}
              className="text-[12px] font-semibold text-slate-800 bg-transparent border-none outline-none cursor-pointer max-w-[120px]"
            >
              {profiles.map(p => (
                <option key={p.id} value={p.id}>{p.name || `画像 ${p.id}`}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* ── Coverflow Area ── */}
      <div
        className="flex-1 relative flex items-center justify-center overflow-hidden"
        style={{
          perspective: '1200px',
          filter: focusPhase === 'blur' ? 'blur(6px)' : 'blur(0px)',
          transform: focusPhase === 'blur' ? 'scale(0.92)' : 'scale(1)',
          opacity: focusPhase === 'blur' ? 0.3 : 1,
          transition: 'filter 0.6s ease-out, transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.5s ease-out',
        }}
      >
        {/* Nav arrows */}
        <button onClick={() => navigate(currentIdx - 1)} disabled={currentIdx === 0}
          className="absolute left-[max(16px,calc(50%-280px))] z-20 w-11 h-11 rounded-full bg-white/40 backdrop-blur-[10px] border-[1.5px] border-white/45 flex items-center justify-center cursor-pointer hover:border-[var(--blue)]/30 hover:text-[var(--blue)] transition-all disabled:opacity-30 disabled:cursor-default text-[var(--text-2)]">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <button onClick={() => navigate(currentIdx + 1)} disabled={currentIdx >= filteredNodes.length - 1}
          className="absolute right-[max(16px,calc(50%-280px))] z-20 w-11 h-11 rounded-full bg-white/40 backdrop-blur-[10px] border-[1.5px] border-white/45 flex items-center justify-center cursor-pointer hover:border-[var(--blue)]/30 hover:text-[var(--blue)] transition-all disabled:opacity-30 disabled:cursor-default text-[var(--text-2)]">
          <ChevronRight className="w-5 h-5" />
        </button>

        {/* Cards */}
        {filteredNodes.map((node, i) => {
          const offset = i - currentIdx
          const isCenter = offset === 0
          const abs = Math.abs(offset)
          const isMyPosition = node.node_id === fromNodeId
          const isMyTarget = node.node_id === targetNodeId
          if (abs > 3) return null

          const tx = offset * 220
          const scale = isCenter ? 1 : 0.75
          const ry = isCenter ? 0 : offset < 0 ? 35 : -35
          const opacity = abs > 2 ? 0 : isCenter ? 1 : 0.6
          const zIndex = 100 - abs * 10
          const isFlipped = isCenter && flipped
          const isLocateTarget = isCenter && focusPhase === 'reveal' && node.node_id === initialNodeId

          return (
            <div
              key={node.node_id}
              onClick={() => isCenter ? setFlipped(f => !f) : navigate(i)}
              className="absolute w-[380px] h-[460px] cursor-pointer"
              style={{
                transform: `translateX(${tx}px) scale(${scale}) rotateY(${ry}deg)${isFlipped ? ' rotateY(180deg)' : ''}`,
                opacity,
                zIndex,
                transition: 'all .5s cubic-bezier(.23,1,.32,1)',
                transformStyle: 'preserve-3d',
                pointerEvents: abs > 2 ? 'none' : 'auto',
              }}
            >
              {/* Locate label */}
              {isLocateTarget && (
                <div
                  className="absolute -top-10 left-1/2 -translate-x-1/2 z-10 px-4 py-1.5 rounded-full bg-[var(--blue)] text-white text-[12px] font-bold whitespace-nowrap shadow-lg"
                  style={{
                    animation: 'locateLabel 1.4s ease-out forwards',
                  }}
                >
                  📍 你的当前定位
                </div>
              )}

              {/* ── FRONT ── */}
              <div
                className="absolute inset-0 rounded-[20px] bg-white/[0.38] backdrop-blur-[24px] backdrop-saturate-[140%] border-[1.5px] border-white/[0.35] border-t-white/70 border-l-white/55 overflow-hidden p-6 flex flex-col"
                style={{
                  backfaceVisibility: 'hidden',
                  boxShadow: isLocateTarget
                    ? '0 0 40px rgba(99,102,241,0.3), 0 16px 48px rgba(37,99,235,.18)'
                    : isCenter ? '0 16px 48px rgba(37,99,235,.14)' : '0 8px 32px rgba(37,99,235,.08)',
                  borderColor: isLocateTarget ? 'rgba(99,102,241,0.4)' : undefined,
                  transition: 'box-shadow 0.6s ease-out, border-color 0.6s ease-out',
                }}
              >
                <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${ZONE_STRIP[node.zone] ?? ZONE_STRIP[DEFAULT_ZONE]}`} />

                <div className="flex justify-between items-start mb-2 mt-1">
                  <div className="flex-1 min-w-0 mr-2">
                    <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
                      <div className="text-[20px] font-extrabold tracking-tight text-[var(--text-1)]">{node.label}</div>
                      {isMyPosition && (
                        <span className="flex items-center gap-0.5 text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-100 text-blue-700">
                          <MapPin className="w-2.5 h-2.5" />当前
                        </span>
                      )}
                      {isMyTarget && (
                        <span className="flex items-center gap-0.5 text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-100 text-amber-700">
                          <Target className="w-2.5 h-2.5" />目标
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[12px] text-slate-500">{ROLE_FAMILY_LABEL[node.role_family] ?? node.role_family}</span>
                    </div>
                  </div>
                  <span className={`text-[10px] font-bold px-2.5 py-1 rounded-md shrink-0 ${ZONE_CLS[node.zone] ?? ZONE_CLS[DEFAULT_ZONE]}`}>{ZONE_LABEL[node.zone] ?? node.zone}</span>
                </div>

                <div className="flex justify-center mb-2 mt-1">
                  <canvas ref={isCenter ? radarRef : undefined} width={200} height={200} />
                </div>

                {/* Must skills tags — center card only */}
                {isCenter && node.must_skills && node.must_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {node.must_skills.slice(0, 4).map(s => (
                      <span key={s} className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200">{s}</span>
                    ))}
                  </div>
                )}

                {isCenter && node.contextual_narrative && (
                  <Link
                    to={`/explore?left=${node.node_id}`}
                    className="text-[11px] text-slate-500 hover:text-blue-600 mb-2 inline-block"
                  >
                    跟别的方向对比看看 →
                  </Link>
                )}

                {isCenter ? (
                  <div className="flex items-center justify-between mt-auto pt-1 gap-2">
                    <button
                      onClick={e => { e.stopPropagation(); setDetailNode(node) }}
                      className="text-[11px] font-semibold text-slate-500 hover:text-[var(--blue)] bg-slate-50 hover:bg-blue-50 px-2.5 py-1 rounded-lg cursor-pointer transition-colors"
                    >
                      详情
                    </button>
                    <span className="text-[11px] text-slate-400 flex-1 text-center">点击翻转看路径</span>
                    {profileId && (
                      <button
                        onClick={e => openDirectGoal(node, e)}
                        className="text-[11px] font-bold text-[var(--blue)] bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-lg cursor-pointer transition-colors"
                      >
                        {careerGoals?.some(g => g.target_node_id === node.node_id && g.is_primary)
                          ? '主方向'
                          : careerGoals?.some(g => g.target_node_id === node.node_id)
                          ? '设为主方向'
                          : careerGoals && careerGoals.length > 0
                          ? '加入方向'
                          : '设为目标'}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-[11px] text-slate-400 mt-auto">点击卡片翻转查看路径</div>
                )}
              </div>

              {/* ── BACK ── */}
              <div
                className="absolute inset-0 rounded-[20px] bg-white/[0.38] backdrop-blur-[24px] backdrop-saturate-[140%] border-[1.5px] border-white/[0.35] border-t-white/70 border-l-white/55 overflow-y-auto p-6"
                style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)', boxShadow: isCenter ? '0 16px 48px rgba(37,99,235,.14)' : '0 8px 32px rgba(37,99,235,.08)' }}
              >
                <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${ZONE_STRIP[node.zone] ?? ZONE_STRIP[DEFAULT_ZONE]}`} />

                {/* Promo ladder */}
                <div className="mb-5 mt-1">
                  <div className="text-[13px] font-bold text-slate-500 flex items-center gap-1.5 mb-3">
                    <ArrowUp className="w-3.5 h-3.5" /> 常见发展路径（参考）
                  </div>
                  <div className="flex items-center gap-1.5">
                    {Array.from({ length: maxLevel }, (_, lv) => {
                      const lvNum = lv + 1
                      const isCurrent = lvNum === node.career_level
                      return (
                        <div key={lv} className={`flex-1 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold transition-all ${
                          isCurrent ? 'bg-[var(--blue)] text-white ring-2 ring-[var(--blue)]/30 scale-110' :
                          lvNum < node.career_level ? 'bg-[var(--blue)]/10 text-[var(--blue)]' : 'bg-slate-100 text-slate-400'
                        }`}>
                          L{lvNum}
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Escape routes */}
                <div>
                  <div className="text-[13px] font-bold text-slate-500 flex items-center gap-1.5 mb-3">
                    <Repeat2 className="w-3.5 h-3.5" /> 可转换岗位
                  </div>
                  {routesLoading && isCenter ? (
                    <div className="text-[12px] text-slate-400 py-4 text-center">加载中...</div>
                  ) : currentRoutes.length > 0 && isCenter ? (
                    <div className="space-y-2">
                      {currentRoutes.map(route => {
                        const tag = route.tag || ''
                        const tagCls = TAG_CLS[tag] ?? 'bg-slate-50 text-slate-400 border-slate-200'
                        return (
                          <div key={route.target_node_id}
                            onClick={e => { e.stopPropagation(); showCompare(route) }}
                            className="flex items-center gap-2.5 p-2.5 rounded-xl cursor-pointer border border-transparent hover:bg-[var(--blue)]/[0.06] hover:border-[var(--blue)]/20 transition-all">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5 mb-0.5">
                                {tag && (
                                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${tagCls}`}>{tag}</span>
                                )}
                                <span className="text-[13px] font-semibold text-slate-800 truncate">{route.target_label}</span>
                              </div>
                              <div className="text-[10px] text-slate-400 truncate">
                                补{route.gap_skills.length > 0 ? `：${route.gap_skills.slice(0, 3).join('、')}${route.gap_skills.length > 3 ? '…' : ''}` : '：无需补充'}
                              </div>
                            </div>
                            <div className="flex flex-col items-end gap-0.5 shrink-0">
                              <span className={`text-[11px] font-bold ${(route.safety_gain ?? 0) >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                                {(route.safety_gain ?? 0) >= 0 ? '+' : ''}{route.safety_gain ?? 0}%
                              </span>
                              <span className="text-[9px] text-slate-400">安全增益</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  ) : isCenter ? (
                    <div className="text-[12px] text-slate-400 py-4 text-center">暂无转换路径</div>
                  ) : null}
                </div>

                <div className="text-center text-[11px] text-slate-400 mt-4">点击翻转回正面</div>
              </div>

            </div>
          )
        })}
      </div>

      {/* ── Bottom: counter + mini nav ── */}
      <div className="flex items-center justify-center gap-3 pb-5">
        <button onClick={() => navigate(currentIdx - 1)} disabled={currentIdx === 0}
          className="w-7 h-7 rounded-full bg-white/70 backdrop-blur border border-white/50 flex items-center justify-center text-slate-400 hover:text-[var(--blue)] transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-default"
          style={{ boxShadow: '0 2px 8px rgba(0,0,0,.04)' }}>
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
        <div className="bg-white/70 backdrop-blur border border-white/50 rounded-full px-4 py-1.5 text-[12px] font-semibold text-slate-600 tabular-nums"
          style={{ boxShadow: '0 2px 8px rgba(0,0,0,.04)' }}>
          <span className="text-[var(--blue)]">{currentIdx + 1}</span>
          <span className="text-slate-300 mx-1">/</span>
          <span>{filteredNodes.length}</span>
          {zoneFilter && <span className="text-slate-400 ml-1 font-normal">· {ZONE_LABEL[zoneFilter]}</span>}
        </div>
        <button onClick={() => navigate(currentIdx + 1)} disabled={currentIdx >= filteredNodes.length - 1}
          className="w-7 h-7 rounded-full bg-white/70 backdrop-blur border border-white/50 flex items-center justify-center text-slate-400 hover:text-[var(--blue)] transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-default"
          style={{ boxShadow: '0 2px 8px rgba(0,0,0,.04)' }}>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* ── Detail Modal ── */}
      {detailNode && (() => {
        const ab = computeAbilities(detailNode)
        const intro = introCache.get(detailNode.node_id)
        return (
          <div className="fixed inset-0 bg-slate-900/30 backdrop-blur-sm z-50 flex items-center justify-center p-6"
            onClick={() => setDetailNode(null)}>
            <div className="bg-white/95 backdrop-blur-xl max-w-[420px] w-full rounded-2xl shadow-2xl p-6 relative"
              onClick={e => e.stopPropagation()}
              style={{ animation: 'popoverIn .2s ease-out' }}>
              <button onClick={() => setDetailNode(null)}
                className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1.5 rounded-full hover:bg-slate-100 cursor-pointer transition-colors">
                <X className="w-4 h-4" />
              </button>

              {/* Header */}
              <div className="flex items-center gap-2 mb-4">
                <h3 className="text-lg font-extrabold text-slate-800">{detailNode.label}</h3>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${ZONE_CLS[detailNode.zone] ?? ZONE_CLS[DEFAULT_ZONE]}`}>
                  {ZONE_LABEL[detailNode.zone] ?? detailNode.zone}
                </span>
              </div>

              {/* Intro */}
              {intro ? (
                <p className="text-[13px] text-slate-600 leading-relaxed mb-4">{intro}</p>
              ) : (
                <p className="text-[12px] text-slate-400 italic mb-4">暂无介绍</p>
              )}

              {/* Stats */}
              <div className="flex items-center gap-4 mb-4 pb-4 border-b border-slate-100">
                {detailNode.salary_p50 != null && (
                  <div>
                    <div className="text-[18px] font-black text-emerald-600">{(detailNode.salary_p50 / 1000).toFixed(0)}K</div>
                    <div className="text-[10px] text-slate-400">月薪 P50</div>
                  </div>
                )}
                <div>
                  <div className="text-[18px] font-black text-[var(--blue)]">L{detailNode.career_level}</div>
                  <div className="text-[10px] text-slate-400">职级</div>
                </div>
                <div>
                  <div className="text-[18px] font-black text-slate-700">{ROLE_FAMILY_LABEL[detailNode.role_family] ?? detailNode.role_family}</div>
                  <div className="text-[10px] text-slate-400">方向</div>
                </div>
              </div>

              {/* Abilities */}
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 mb-4">
                {Object.entries(ab).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between">
                    <span className="text-[12px] text-slate-500">{k}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                        <div className={`h-full rounded-full ${v >= 70 ? 'bg-emerald-500' : v >= 40 ? 'bg-amber-400' : 'bg-red-400'}`}
                          style={{ width: `${v}%` }} />
                      </div>
                      <span className={`text-[11px] font-bold w-6 text-right ${v >= 70 ? 'text-emerald-600' : v >= 40 ? 'text-amber-600' : 'text-red-500'}`}>{v}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Skills */}
              {detailNode.must_skills && detailNode.must_skills.length > 0 && (
                <div className="mb-4">
                  <div className="text-[11px] font-semibold text-slate-400 mb-1.5">核心技能</div>
                  <div className="flex flex-wrap gap-1.5">
                    {detailNode.must_skills.map(s => (
                      <span key={s} className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200">{s}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Promotion Path */}
              {detailNode.promotion_path && detailNode.promotion_path.length > 0 && (
                <div className="mb-4">
                  <div className="text-[11px] font-semibold text-slate-400 mb-1.5">晋升路径</div>
                  <div className="flex items-center gap-0.5 overflow-x-auto pb-1">
                    {detailNode.promotion_path.map((p, i) => (
                      <div key={p.level} className="flex items-center shrink-0">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${p.level === detailNode.career_level ? 'bg-blue-100 text-blue-700 font-bold border border-blue-300' : 'bg-slate-50 text-slate-500'}`}>
                          L{p.level} {p.title}
                        </span>
                        {i < detailNode.promotion_path!.length - 1 && (
                          <span className="text-slate-300 text-[10px] mx-0.5">→</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Soft Skills */}
              {detailNode.soft_skills && Object.keys(detailNode.soft_skills).length > 0 && (() => {
                const DIM_ZH: Record<string, string> = { communication: '沟通', learning: '学习', resilience: '抗压', innovation: '创新', collaboration: '协作' }
                const DIM_ORDER = ['communication', 'learning', 'resilience', 'innovation', 'collaboration']
                return (
                  <div className="mb-4">
                    <div className="text-[11px] font-semibold text-slate-400 mb-1.5">软技能要求</div>
                    <div className="flex gap-2 flex-wrap">
                      {DIM_ORDER.filter(d => detailNode.soft_skills?.[d] != null).map(d => {
                        const v = detailNode.soft_skills![d]
                        const color = v >= 4 ? 'bg-blue-100 text-blue-700 border-blue-200' : v >= 3 ? 'bg-slate-100 text-slate-600 border-slate-200' : 'bg-slate-50 text-slate-400 border-slate-100'
                        return (
                          <span key={d} className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border ${color}`}>
                            {DIM_ZH[d] ?? d} {'★'.repeat(v)}
                          </span>
                        )
                      })}
                    </div>
                  </div>
                )
              })()}

              {/* Role detail page link */}
              <button
                onClick={() => { setDetailNode(null); routerNavigate(`/roles/${detailNode.node_id}`) }}
                className="w-full text-center text-[12px] font-semibold text-white bg-[var(--blue)] hover:brightness-110 py-2.5 rounded-xl cursor-pointer transition-all flex items-center justify-center gap-1.5"
              >
                查看完整岗位介绍
              </button>

            </div>
          </div>
        )
      })()}

      {/* ── Compare Overlay ── */}
      {compareData && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-50 flex items-center justify-center p-6"
          onClick={() => setCompareData(null)}>
          <div className="glass-static max-w-[480px] w-full p-6 sm:p-8 rounded-[24px] shadow-2xl relative"
            onClick={e => e.stopPropagation()}>
            <button onClick={() => setCompareData(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-2 rounded-full hover:bg-white/50 cursor-pointer transition-colors">
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-8 mt-2 relative z-10">
              <h3 className="text-[18px] font-extrabold text-slate-800">{compareData.from.label}</h3>
              <span className="text-[var(--blue)] text-[20px] font-extrabold">→</span>
              <h3 className="text-[18px] font-extrabold text-slate-800">{compareData.to.label}</h3>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-6 relative z-10">
              <div className="bg-white/20 p-4 rounded-2xl border border-white/30 flex flex-col items-center justify-center text-center shadow-sm">
                <div className="text-[11px] font-bold text-slate-500 mb-1">技能差距</div>
                <div className="text-[30px] font-black text-[var(--blue)] leading-none mb-1 drop-shadow-sm">
                  {compareData.routes.gap_skills.length}
                </div>
                <div className="text-[10px] text-slate-400 font-semibold">项</div>
              </div>

              <div className="bg-white/20 p-4 rounded-2xl border border-white/30 flex flex-col items-center justify-center text-center shadow-sm">
                <div className="text-[11px] font-bold text-slate-500 mb-1">安全增益</div>
                <div className={`text-[24px] font-black leading-none mb-1 drop-shadow-sm ${compareData.routes.safety_gain >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {compareData.routes.safety_gain >= 0 ? '+' : ''}{compareData.routes.safety_gain}%
                </div>
                <div className="text-[10px] text-slate-400 font-semibold">
                  {compareData.routes.safety_gain >= 0 ? '风险降低' : '风险上升'}
                </div>
              </div>

              <div className="bg-white/20 p-4 rounded-2xl border border-white/30 flex flex-col items-center justify-center text-center shadow-sm">
                <div className="text-[11px] font-bold text-slate-500 mb-1">学习时长</div>
                <div className="text-[24px] font-black text-violet-600 leading-none mb-1 drop-shadow-sm">
                  {compareData.routes.estimated_hours > 0 ? compareData.routes.estimated_hours : '–'}
                </div>
                <div className="text-[10px] text-slate-400 font-semibold">小时</div>
              </div>
            </div>


            {compareData.routes.gap_skills.length > 0 && (
              <div className="mb-8 relative z-10">
                <h4 className="text-[14px] font-bold text-slate-700 mb-4 flex items-center gap-2">
                  核心补充技能
                </h4>
                <div className="flex flex-wrap gap-2.5">
                  {compareData.routes.gap_skills.map(s => (
                    <span key={s} className="text-[13px] bg-white/30 text-[var(--blue-deep)] border border-white/40 px-3 py-1.5 rounded-xl font-bold shadow-sm">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* ── Goal setting CTA ── */}
            {goalPhase === 'done' ? (
              /* Gap Preview */
              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <p className="text-[13px] font-bold text-emerald-700">
                    目标已锁定：{compareData.routes.target_label ?? compareData.to.label}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-5">
                  {/* Dual radar */}
                  <div className="flex flex-col items-center">
                    <canvas ref={gapRadarRef} width={180} height={180} />
                    <div className="flex items-center gap-3 mt-1.5 text-[10px] text-slate-500">
                      <span className="flex items-center gap-1">
                        <span className="w-4 h-[2px] bg-indigo-500 inline-block rounded" />当前
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-4 inline-block" style={{ borderBottom: '2px dashed #f59e0b' }} />目标
                      </span>
                    </div>
                  </div>

                  {/* Gap skills */}
                  <div>
                    <p className="text-[11px] font-bold text-slate-500 mb-2 uppercase tracking-wide">能力差距</p>
                    <div className="flex flex-wrap gap-1.5">
                      {compareData.routes.gap_skills.slice(0, 5).map(s => (
                        <span key={s} className="text-[10px] bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-md font-semibold">{s}</span>
                      ))}
                      {compareData.routes.gap_skills.length > 5 && (
                        <span className="text-[10px] text-slate-400 self-center">+{compareData.routes.gap_skills.length - 5}</span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 mt-3">
                      需补 <span className="font-bold text-slate-700">{compareData.routes.gap_skills.length}</span> 项
                      {compareData.routes.estimated_hours > 0 && (
                        <> · 约 <span className="font-bold text-slate-700">{compareData.routes.estimated_hours}h</span></>
                      )}
                    </p>
                  </div>
                </div>

                {/* CTAs */}
                <div className="space-y-2">
                  <button
                    onClick={() => routerNavigate('/growth-log')}
                    className="w-full bg-[var(--blue)] text-white py-3 rounded-xl text-[13px] font-bold cursor-pointer transition-all shadow-md shadow-blue-500/20 flex items-center justify-center gap-2 hover:opacity-90"
                  >
                    去成长档案追踪
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => routerNavigate('/profile')}
                      className="py-2.5 rounded-xl text-[12px] font-medium text-slate-600 bg-white/60 border border-slate-200 cursor-pointer hover:bg-white/80 transition-all"
                    >
                      查看能力画像
                    </button>
                    <button
                      onClick={() => setCompareData(null)}
                      className="py-2.5 rounded-xl text-[12px] font-medium text-slate-500 bg-white/40 border border-slate-200 cursor-pointer hover:bg-white/60 transition-all"
                    >
                      继续探索
                    </button>
                  </div>
                </div>
              </div>
            ) : goalPhase === 'confirming' ? (
              /* Confirm step */
              <div className="relative z-10 space-y-3">
                {goalError && (
                  <p className="text-[12px] text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{goalError}</p>
                )}
                <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
                  <p className="text-[12.5px] font-semibold text-amber-800 mb-0.5">确认设定目标？</p>
                  <p className="text-[11.5px] text-amber-700">设定后不可更改，请确认选择「{compareData.routes.target_label ?? compareData.to.label}」作为职业目标。</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => { setGoalPhase('idle'); setGoalError(null) }}
                    className="flex-1 py-3 rounded-xl text-[13px] font-medium text-slate-600 bg-white/60 border border-slate-200 cursor-pointer hover:bg-white/80 transition-all"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSetGoal}
                    className="flex-1 py-3 rounded-xl text-[13px] font-bold text-white bg-[var(--blue)] cursor-pointer hover:opacity-90 transition-all shadow-md shadow-blue-500/20"
                  >
                    确认锁定目标
                  </button>
                </div>
              </div>
            ) : (
              /* Idle state: navigate + set goal */
              <div className="relative z-10 flex gap-2">
                <button
                  onClick={() => jumpToNode(compareData.to.node_id)}
                  className="flex-1 py-3.5 rounded-xl text-[13px] font-medium text-slate-600 bg-white/60 border border-slate-200 cursor-pointer hover:bg-white/80 transition-all flex items-center justify-center gap-1.5"
                >
                  前往查看
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
                {!profileId ? (
                  <button
                    disabled
                    className="flex-1 py-3.5 rounded-xl text-[13px] font-medium text-slate-400 bg-slate-100 border border-slate-200 flex items-center justify-center cursor-not-allowed"
                  >
                    先建立画像
                  </button>
                ) : (
                  <button
                    onClick={() => setGoalPhase('confirming')}
                    className="flex-1 py-3.5 rounded-xl text-[13px] font-bold text-white bg-[var(--blue)] cursor-pointer hover:opacity-90 transition-all shadow-md shadow-blue-500/20 flex items-center justify-center gap-1.5"
                  >
                    设为目标
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Direct Goal Overlay ── */}
      {directGoalNode && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-50 flex items-center justify-center p-6"
          onClick={() => { if (directGoalPhase !== 'saving') setDirectGoalNode(null) }}>
          <div className="glass-static max-w-[380px] w-full p-6 sm:p-8 rounded-[24px] shadow-2xl relative"
            onClick={e => e.stopPropagation()}>

            {directGoalPhase !== 'done' && (
              <button onClick={() => setDirectGoalNode(null)}
                className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-2 rounded-full hover:bg-white/50 cursor-pointer transition-colors">
                <X className="w-5 h-5" />
              </button>
            )}

            {directGoalPhase === 'done' ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2.5 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <div>
                    <p className="text-[13px] font-bold text-emerald-800">目标已设定</p>
                    <p className="text-[11.5px] text-emerald-700 mt-0.5">{directGoalNode.label}</p>
                  </div>
                </div>
                <button
                  onClick={() => routerNavigate('/growth-log')}
                  className="w-full bg-[var(--blue)] text-white py-3.5 rounded-xl text-[14px] font-bold cursor-pointer transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 hover:opacity-90"
                >
                  去成长档案追踪
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setDirectGoalNode(null)}
                  className="w-full py-3 rounded-xl text-[13px] font-medium text-slate-500 bg-white/40 border border-slate-200 cursor-pointer hover:bg-white/60 transition-all"
                >
                  稍后再说
                </button>
              </div>
            ) : (
              <div className="space-y-5">
                <div>
                  <h3 className="text-[18px] font-extrabold text-slate-800 mb-1">设定职业目标</h3>
                  <p className="text-[12px] text-slate-500">可随时更改目标</p>
                </div>

                <div className="bg-white/40 rounded-2xl p-4 border border-white/50">
                  <div className="text-[18px] font-extrabold text-slate-800">{directGoalNode.label}</div>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${ZONE_CLS[directGoalNode.zone] ?? ZONE_CLS[DEFAULT_ZONE]}`}>
                      {ZONE_LABEL[directGoalNode.zone] ?? directGoalNode.zone}
                    </span>
                    {directGoalNode.role_family && (
                      <span className="text-[11px] text-slate-400">{ROLE_FAMILY_LABEL[directGoalNode.role_family] ?? directGoalNode.role_family}</span>
                    )}
                  </div>
                </div>

                <p className="text-[12px] text-slate-500 bg-slate-50 rounded-xl px-4 py-3">
                  设定后，成长档案会按此目标追踪你的项目和求职进展。投递 JD 时粘贴到求职追踪做诊断，即可看到真实能力差距。
                </p>

                {directGoalError && (
                  <p className="text-[12px] text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{directGoalError}</p>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => setDirectGoalNode(null)}
                    disabled={directGoalPhase === 'saving'}
                    className="flex-1 py-3 rounded-xl text-[13px] font-medium text-slate-600 bg-white/60 border border-slate-200 cursor-pointer hover:bg-white/80 transition-all disabled:opacity-50"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSetDirectGoal}
                    disabled={directGoalPhase === 'saving'}
                    className="flex-1 py-3 rounded-xl text-[13px] font-bold text-white bg-[var(--blue)] cursor-pointer hover:opacity-90 transition-all shadow-md shadow-blue-500/20 disabled:opacity-60"
                  >
                    {directGoalPhase === 'saving' ? '设定中...' : '确认设定'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  )
}
