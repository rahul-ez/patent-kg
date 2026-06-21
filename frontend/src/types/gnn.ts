export type GNNMode = 'novelty' | 'graph_sim'

export interface GNNWeights {
  semantic: number
  gnn: number
}

export interface RankedHit {
  patent_id: string
  title: string
  url: string
  domain: string
  semantic_score: number | null
  novelty_score: number
  combined_score: number
  faiss_rank: number
  gnn_rank: number
  delta: number
  gnn_mode: GNNMode
}
