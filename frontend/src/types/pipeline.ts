export interface NLPResult {
  clean_text: string
  keywords: string[]
  entities: string[]
  source: string
}

export interface RetrievalHit {
  rank: number
  patent_id: string
  title: string
  abstract: string
  domain: string
  url: string
  source: 'faiss' | 'kg_family' | 'kg_cpc'
  faiss_rank?: number
  novelty_score?: number | null
  semantic_score: number | null
  graph_score: number | null
  combined_score: number | null
  gnn_mode?: string
  expansion_type?: 'family' | 'cpc_sibling' | null
}

export interface PipelineResponse {
  query_id: string
  query_text: string
  nlp_result: NLPResult
  model: string
  top_k: number
  results: RetrievalHit[]
  gnn_status?: string
  kg_status?: string
}

export interface PipelineRequest {
  idea: string
  top_k: number
  gnn_mode: string
}

export type PipelineStatus = 'idle' | 'running' | 'complete' | 'error'
