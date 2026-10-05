import { FormEvent, useEffect, useState } from 'react'
import { createCase, deleteCase, listCases, getRun, type AnalysisCase } from '../api/cases'
import { useNavigate } from 'react-router-dom'
import { usePipelineStore } from '../store/usePipelineStore'

export default function CaseHistoryPage() {
  const [cases, setCases] = useState<AnalysisCase[]>([])
  const [title, setTitle] = useState('')
  const [ideaText, setIdeaText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [opening, setOpening] = useState<string | null>(null)
  const navigate = useNavigate()
  const { restoreRun, selectCase } = usePipelineStore()
  const currentIdea = usePipelineStore((state) => state.idea)

  const refresh = async () => {
    setLoading(true)
    try {
      setCases(await listCases())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load saved analyses.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refresh() }, [])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!title.trim() || !ideaText.trim()) return
    try {
      await createCase(title.trim(), ideaText.trim())
      setTitle('')
      setIdeaText('')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create analysis case.')
    }
  }

  const remove = async (caseId: string) => {
    if (!window.confirm('Delete this case and all its saved analyses?')) return
    try {
      await deleteCase(caseId)
      if (usePipelineStore.getState().activeCaseId === caseId) usePipelineStore.getState().reset()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete analysis case.')
    }
  }

  const open = async (caseId: string, runId: string) => {
    setOpening(runId)
    try {
      const run = await getRun(caseId, runId)
      if (!run.pipeline_result) throw new Error('This run has no saved results.')
      restoreRun(run)
      navigate('/results/nlp')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not open analysis.')
    } finally {
      setOpening(null)
    }
  }

  return (
    <section style={{ maxWidth: 960, margin: '0 auto' }}>
      <p className="caption">Relational database</p>
      <h1 style={{ margin: '6px 0 10px' }}>Saved analysis cases</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 28 }}>
        Open a saved analysis or create another run in the same case. Saved results are loaded from MySQL.
      </p>

      <form onSubmit={submit} style={{ display: 'grid', gap: 10, padding: 20, background: 'var(--bg-card)', borderRadius: 'var(--radius-card)', marginBottom: 24 }}>
        <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Case title" aria-label="Case title" />
        <textarea value={ideaText} onChange={(event) => setIdeaText(event.target.value)} placeholder="Invention idea" aria-label="Invention idea" rows={4} />
        <div style={{ display: 'flex', gap: 10 }}>
          <button type="submit" className="btn-primary">Save draft</button>
          {currentIdea && <button type="button" onClick={() => setIdeaText(currentIdea)}>Use current idea</button>}
        </div>
      </form>

      {error && <div style={{ color: 'var(--accent-clay)', marginBottom: 16 }}><p>{error}</p><button type="button" onClick={() => void refresh()}>Retry loading history</button></div>}
      {loading ? <p>Loading saved cases…</p> : error && cases.length === 0 ? null : cases.length === 0 ? <p>No saved cases yet.</p> : (
        <div style={{ display: 'grid', gap: 12 }}>
          {cases.map((analysisCase) => (
            <article key={analysisCase.case_id} style={{ padding: 18, background: 'var(--bg-card)', borderRadius: 'var(--radius-card)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
                <div>
                  <h2 style={{ fontSize: 18, margin: 0 }}>{analysisCase.title}</h2>
                  <p style={{ color: 'var(--text-secondary)', margin: '8px 0' }}>{analysisCase.idea_text}</p>
                  <small>{analysisCase.status} · {analysisCase.runs.length} stored run{analysisCase.runs.length === 1 ? '' : 's'}</small>
                  <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
                    {analysisCase.runs.map(run => (
                      <button key={run.run_id} type="button" disabled={opening !== null} onClick={() => void open(analysisCase.case_id, run.run_id)}>
                        {opening === run.run_id ? 'Opening…' : `Open analysis · ${new Date(run.started_at).toLocaleString()}`}
                      </button>
                    ))}
                    <button type="button" onClick={() => { selectCase(analysisCase.case_id, analysisCase.idea_text); navigate('/analyze') }}>
                      {analysisCase.runs.length ? 'New run in this case' : 'Analyse this draft'}
                    </button>
                  </div>
                </div>
                <button type="button" onClick={() => void remove(analysisCase.case_id)}>Delete</button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
