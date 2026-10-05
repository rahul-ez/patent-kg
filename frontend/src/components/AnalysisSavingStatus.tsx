import { usePipelineStore } from '../store/usePipelineStore'

export default function AnalysisSavingStatus() {
  const { pipelineResult, evaluationResult, improvementResult } = usePipelineStore()
  if (!pipelineResult) return null
  const outputs = [
    ['Analysis', pipelineResult], ['Evaluation', evaluationResult], ['Improvements', improvementResult],
  ] as const
  return (
    <section aria-label="Analysis saving status" role="status" style={{ marginBottom: 20, padding: '12px 16px', border: '1px solid var(--border-hairline)', borderRadius: 'var(--radius-card)' }}>
      {outputs.map(([label, result]) => result && (
        <p key={label} style={{ margin: '4px 0', fontSize: 13, color: result.persistence_status === 'persisted' ? 'var(--accent-sage)' : 'var(--accent-clay)' }}>
          {label}: {result.persistence_status === 'persisted' ? 'Saved to MySQL' : 'Not saved to MySQL'}
          {result.persistence_message && ` — ${result.persistence_message}`}
        </p>
      ))}
      {pipelineResult.kg_status && pipelineResult.kg_status !== 'success' && <p>Graph expansion unavailable; displaying available retrieval results.</p>}
      {pipelineResult.gnn_status && pipelineResult.gnn_status !== 'success' && <p>GNN ranking unavailable; semantic fallback was used.</p>}
    </section>
  )
}
