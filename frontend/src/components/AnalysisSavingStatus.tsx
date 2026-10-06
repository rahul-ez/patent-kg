import { usePipelineStore } from '../store/usePipelineStore'

export default function AnalysisSavingStatus() {
  const { pipelineResult, evaluationResult, improvementResult } = usePipelineStore()
  if (!pipelineResult) return null
  const outputs = [
    ['Analysis', pipelineResult], ['Evaluation', evaluationResult], ['Improvements', improvementResult],
  ] as const
  return (
    <section aria-label="Analysis saving status" role="status" className="saving-status">
      {outputs.map(([label, result]) => result && (
        <p key={label} data-state={result.persistence_status}>
          {label}: {result.persistence_status === 'persisted' ? 'Saved' : 'Not saved'}
          {result.persistence_message && ` — ${result.persistence_message}`}
        </p>
      ))}
      {pipelineResult.kg_status && pipelineResult.kg_status !== 'success' && <p>Graph expansion unavailable; displaying available retrieval results.</p>}
      {pipelineResult.gnn_status && pipelineResult.gnn_status !== 'success' && <p>GNN ranking unavailable; semantic fallback was used.</p>}
    </section>
  )
}
