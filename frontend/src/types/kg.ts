export interface KGStats {
  nodes: Record<string, number>
  edges: Record<string, number>
}

export interface PatentExpanded {
  patent_id: string
  title: string
  abstract: string
  domain: string
  url: string
  expansion_type?: string
  cited_by_patent_count?: string
  publication_year?: string
}

export interface KGExpansion {
  family: PatentExpanded[]
  cpc_siblings: PatentExpanded[]
  total_added: number
}

export interface KGNodeData {
  label: string
  title: string
  nodeType: string
}

export interface KGNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: KGNodeData
}

export interface KGEdge {
  id: string
  source: string
  target: string
  label: string
  type: string
}

export interface KGGraphData {
  nodes: KGNode[]
  edges: KGEdge[]
}
