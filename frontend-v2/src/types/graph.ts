export type Zone = 'safe' | 'transition' | 'danger' | 'leverage'

export interface GraphNode {
  node_id: string
  label: string
  role_family: string
  zone: Zone
  replacement_pressure: number
  human_ai_leverage: number
  salary_p50?: number
  career_level: number
  must_skills?: string[]
  skill_count?: number
  degree?: number
  soft_skills?: Record<string, number>
  promotion_path?: Array<{ level: number; title: string }>
}

export interface GraphEdge {
  source: string
  target: string
  edge_type?: string
}

export interface GraphMapResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  node_count: number
  edge_count: number
}

export interface NodeDetail extends GraphNode {
  terrain?: Record<string, unknown>
  [key: string]: unknown
}

export interface EscapeRoute {
  target_node_id: string
  target_label: string
  gap_skills: string[]
  estimated_hours: number
  safety_gain: number
  target_zone?: string
  tag?: string
  salary_p50?: number
}

export interface EscapeRoutesResponse {
  node_id: string
  routes: EscapeRoute[]
}

export interface SearchResult {
  node_id: string
  label: string
  role_family: string
  zone: Zone
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
}

