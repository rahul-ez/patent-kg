import { useEffect, useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { usePipelineStore } from '../store/usePipelineStore'
import AppHeader from '../components/AppHeader'

const STAGES = [
  { name: 'Analyze the invention', description: 'Extract concepts, find related patents and review graph-based ranking.' },
  { name: 'Prepare the results', description: 'Confirm the available results, fallback warnings and saving status.' },
]
type StageStatus = 'pending' | 'running' | 'done'

export default function PipelineProgressPage() {
  const navigate = useNavigate()
  const { idea, status, error, pipelineResult } = usePipelineStore()
  const [stageStatuses, setStageStatuses] = useState<StageStatus[]>(STAGES.map(() => 'pending'))
  const refNum = useRef('')
  if (!refNum.current) {
    const d = new Date()
    const hash = pipelineResult?.query_id ? pipelineResult.query_id.slice(-4).toUpperCase() : Math.random().toString(36).slice(-4).toUpperCase()
    refNum.current = 'PI-' + d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0') + '-' + hash
  }
  useEffect(() => {
    if (status === 'complete') {
      setStageStatuses(STAGES.map(() => 'done'))
      const t = setTimeout(() => navigate('/results/nlp'), 1000)
      return () => clearTimeout(t)
    }
    setStageStatuses(status === 'running' ? ['running', 'pending'] : ['pending', 'pending'])
  }, [status, navigate])
  return (
    <div className="standalone-page">
      <AppHeader />
      <main id="main-content" className="progress-main">
        <header className="page-heading">
          <h1>{status === 'error' ? 'Analysis could not finish' : status === 'complete' ? 'Your results are ready' : status === 'running' ? 'Analyzing your invention' : 'Ready to analyze'}</h1>
          <p>{status === 'running' ? 'The server is processing your request. This page will open the results when it finishes.' : status === 'error' ? 'Your description is retained. Review the error and return to try again.' : 'Review the request below.'}</p>
        </header>
        {idea && <blockquote className="progress-description">{idea}</blockquote>}
        <p className="request-reference">Request reference: {refNum.current}</p>
        {status === 'error' && error && <div className="error-notice" role="alert"><p>{error}</p></div>}
        <ol className="request-stages" aria-label="Analysis progress" aria-live="polite">
          {STAGES.map(({ name, description }, i) => <li key={name} className={'stage-' + stageStatuses[i]}>
            <span className="stage-indicator" aria-hidden="true">{stageStatuses[i] === 'running' ? <span className="loading-spinner" /> : stageStatuses[i] === 'done' ? '✓' : i + 1}</span>
            <div><h2>{name}</h2><p>{description}</p></div>
            <span className="stage-status">{status === 'error' ? i === 0 ? 'Failed' : 'Not started' : stageStatuses[i] === 'done' ? 'Complete' : stageStatuses[i] === 'running' ? 'In progress' : 'Waiting'}</span>
          </li>)}
        </ol>
        {status === 'running' && <p className="advisory-note">Detailed server-stage progress is not available; this is not a percentage estimate.</p>}
        {(status === 'error' || status === 'idle') && <Link to="/analyze" className="btn-secondary">Edit description</Link>}
      </main>
    </div>
  )
}
