import { useMemo } from 'react'
import { usePipelineStore } from '../store/usePipelineStore'
import type { RankedHit } from '../types/gnn'

export function useGNNRerank(): RankedHit[] {
  const pipelineResult = usePipelineStore((s) => s.pipelineResult)
  const gnnWeights     = usePipelineStore((s) => s.gnnWeights)

  return useMemo(() => {
    if (!pipelineResult) return []
    const hits = pipelineResult.results
    const hasGNN = hits.some((h) => h.novelty_score != null)
    if (!hasGNN) return []

    const reranked = [...hits]
      .filter((h) => h.novelty_score != null)
      .map((h) => ({
        ...h,
        _combined: gnnWeights.semantic * (h.semantic_score ?? 0) + gnnWeights.gnn * (h.novelty_score ?? 0.5),
      }))
      .sort((a, b) => b._combined - a._combined)

    return reranked.map((h, i) => ({
      patent_id:     h.patent_id,
      title:         h.title,
      url:           h.url,
      domain:        h.domain,
      semantic_score: h.semantic_score,
      novelty_score: h.novelty_score ?? 0.5,
      combined_score:h._combined,
      faiss_rank:    h.faiss_rank ?? h.rank,
      gnn_rank:      i + 1,
      delta:         (h.faiss_rank ?? h.rank) - (i + 1),
      gnn_mode:      (h.gnn_mode ?? 'novelty') as 'novelty' | 'graph_sim',
    }))
  }, [pipelineResult, gnnWeights])
}
