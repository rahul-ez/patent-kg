import PageHeading from '../components/PageHeading'
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
    <section className="result-page cases-page">
      <PageHeading title="Saved cases" description="Reopen an analysis, revise an invention or keep several runs together in one case." />
      <details className="draft-composer">
        <summary>Create a case draft</summary>
        <form onSubmit={submit} className="draft-form">
          <div><label htmlFor="case-title">Case title</label><input id="case-title" value={title} onChange={event => setTitle(event.target.value)} placeholder="A name for this research" required /></div>
          <div><label htmlFor="case-idea">Invention description</label><textarea id="case-idea" value={ideaText} onChange={event => setIdeaText(event.target.value)} placeholder="Describe the mechanism and application" rows={4} required /></div>
          <div className="draft-actions"><button type="submit" className="btn-primary">Save draft</button>
            {currentIdea && <button type="button" className="text-button" onClick={() => setIdeaText(currentIdea)}>Use current idea</button>}
          </div>
        </form>
      </details>
      <div className="cases-list-heading"><h2>Your cases</h2><button className="text-button" type="button" disabled={loading} onClick={() => void refresh()}>Refresh</button></div>
      {error && <div className="error-notice" role="alert"><p>{error}</p><button type="button" className="text-button" onClick={() => void refresh()}>Retry loading history</button></div>}
      {loading ? <p role="status" className="empty-list">Loading saved cases…</p> : error && cases.length === 0 ? null : cases.length === 0 ? <p className="empty-list">No saved cases yet. Create a draft above or run a new analysis.</p> : (
        <div className="case-list">
          {cases.map(analysisCase => (
            <article key={analysisCase.case_id} className="case-row">
              <div className="case-row-heading"><h2>{analysisCase.title}</h2><button className="delete-button" type="button" onClick={() => void remove(analysisCase.case_id)}>Delete</button></div>
              <p className="case-description">{analysisCase.idea_text}</p>
              <p className="case-meta"><span>{analysisCase.status}</span><span>{analysisCase.runs.length} saved run{analysisCase.runs.length === 1 ? '' : 's'}</span></p>
              <div className="case-runs">
                {analysisCase.runs.map(run => <button key={run.run_id} className="run-link" type="button" disabled={opening !== null} onClick={() => void open(analysisCase.case_id, run.run_id)}>
                  <span>{opening === run.run_id ? 'Opening…' : 'Open analysis'}</span><time dateTime={run.started_at}>{new Date(run.started_at).toLocaleString()}</time>
                </button>)}
              </div>
              <button className="btn-secondary" type="button" onClick={() => { selectCase(analysisCase.case_id, analysisCase.idea_text); navigate('/analyze') }}>
                {analysisCase.runs.length ? 'New run in this case' : 'Analyze this draft'}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
