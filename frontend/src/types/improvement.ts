export interface StrategyItem {
  strategy: string
  impact: 'high' | 'medium' | 'low'
  reason: string
}

export interface OverlappingPatentItem {
  patent_id: string
  title: string
  similarity: number
}

export interface ImprovementResponse {
  diagnosis: string[]
  weaknesses: string[]
  strategies: StrategyItem[]
  alternative_directions: string[]
  recommendations: string
  overlapping_patents: OverlappingPatentItem[]
}

export interface ImprovementRequest {
  idea: string
  pipeline_result?: any | null
  evaluation_result?: any | null
}
