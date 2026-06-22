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

// ── Evaluation types ──────────────────────────────────────────────────────────

export interface EvalDimensionScore {
  score: number
  interpretation: string
  [key: string]: unknown
}

export interface NonObviousnessBreakdown {
  combination_difficulty: EvalDimensionScore & { weight: number }
  motivation_to_combine:  EvalDimensionScore & { weight: number }
  cross_domain_novelty:   EvalDimensionScore & { weight: number }
  reconstruction:         EvalDimensionScore & { weight: number }
  citation_isolation:     EvalDimensionScore & { weight: number }
  long_felt_need:         EvalDimensionScore & { weight: number }
  teaching_away:          EvalDimensionScore & { weight: number; type: string }
  unexpected_effect:      EvalDimensionScore & { weight: number; type: string }
  landscape:              EvalDimensionScore & { weight: number; type: string }
}

export interface IndiaFlag {
  section:     string
  title:       string
  severity:    'HIGH' | 'MEDIUM' | 'LOW'
  explanation: string
  matched_kw?: string[]
}

export interface IndiaSafeHarbor {
  note:   string
  detail: string
}

export interface EvaluationResult {
  patentability_score: number
  patentability_raw:   number
  verdict:             string
  risk:                'Low' | 'Medium' | 'High'
  confidence:          number

  novelty: {
    score:              number
    semantic_novelty:   number
    gnn_novelty:        number | null
    gnn_mode:           string | null
    blend:              { semantic: number; gnn: number }
    top_semantic_score: number
    n_hits_used:        number
    interpretation:     string
  }

  non_obviousness: {
    score:                  number
    score_raw:              number
    breakdown:              NonObviousnessBreakdown
    weighted_contributions: Record<string, number>
    interpretation:         string
    elapsed_seconds:        number
    fast_mode:              boolean
  }

  landscape: {
    score:                  number
    score_100:              number
    density:                number
    active_ratio:           number
    assignee_concentration: number
    interpretation:         string
  }

  claim_breadth: {
    score:                number
    avg_cpc_depth:        number | null
    unique_section_ratio: number | null
    total_cpc_codes:      number
    interpretation:       string
  }

  timing: {
    score:        number
    newest_year:  number | null
    oldest_year:  number | null
    year_spread:  number | null
    recency_flag: 'ACTIVE' | 'CLEARING' | 'LEGACY' | 'UNKNOWN'
    interpretation: string
  }

  india_eligibility: {
    flags:        IndiaFlag[]
    safe_harbors: IndiaSafeHarbor[]
    is_flagged:   boolean
    summary:      string
  }

  technical_depth: {
    level:                'Low' | 'Medium' | 'High'
    confidence:           number
    quantitative_hits:    number
    entity_count:         number
    word_count:           number
    interpretation:       string
  }

  weights:       Record<string, number>
  contributions: Record<string, number>
  concept_count: number
  concepts:      Array<{ label: string; description: string }>
  elapsed_seconds: number
  fast_mode:     boolean
}

export interface EvaluateRequest {
  idea:                    string
  top_k:                   number
  gnn_mode:                string
  run_fast:                boolean
  n_reconstruction_samples: number
  pipeline_result?:        PipelineResponse | null
}
