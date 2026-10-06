import { useState, useEffect, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { usePipeline } from '../hooks/usePipeline'
import { usePipelineStore } from '../store/usePipelineStore'
import AppHeader from '../components/AppHeader'

const EXAMPLES = [
  { label: 'Seizure-detection wearable', text: 'EEG seizure detection wearable with real-time neural signal processing and adaptive threshold calibration' },
  { label: 'Autonomous drone navigation', text: 'Autonomous drone navigation with LiDAR-based obstacle avoidance and swarm coordination protocols' },
  { label: 'Private medical-image learning', text: 'Federated learning framework for medical imaging with differential privacy and cross-silo aggregation' },
  { label: 'Fast-charging solid-state battery', text: 'Solid-state lithium battery electrolyte using sulfide-based composite for ultra-fast charging' },
  { label: 'Adaptive smart-grid control', text: 'AI smart grid energy optimization using reinforcement learning for dynamic load balancing' },
]
const TOP_K_OPTIONS = [5, 10, 25, 50, 100]

export default function IdeaInputPage() {
  const { idea: storeIdea, topK, gnnMode, activeCaseId, setIdea: setStoreIdea, setTopK, setGNNMode } = usePipelineStore()
  const [idea, setIdea] = useState(storeIdea || '')
  const [localTopK, setLocalTopK] = useState(topK)
  const [localGNNMode, setLocalGNNMode] = useState(gnnMode)
  const mutation = usePipeline()
  useEffect(() => { setStoreIdea(idea) }, [idea, setStoreIdea])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!idea.trim() || mutation.isPending) return
    setTopK(localTopK)
    setGNNMode(localGNNMode)
    mutation.mutate({ idea: idea.trim(), top_k: localTopK, gnn_mode: localGNNMode, case_id: activeCaseId ?? undefined })
  }

  return (
    <div className="standalone-page">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <AppHeader />
      <main id="main-content" className="intake-main">
        <div className="breadcrumb"><Link to="/">Workspace</Link><span aria-hidden="true">/</span><span>New analysis</span></div>
        <header className="page-heading">
          <h1>{activeCaseId ? 'New run in saved case' : 'Describe your invention'}</h1>
          <p>Find related patents by describing how your idea works, not just what it is called.</p>
        </header>
        <div className="intake-layout">
          <form onSubmit={handleSubmit} className="intake-form" aria-label="Invention analysis">
            {activeCaseId && <p className="inline-notice">This analysis will be added to your selected case.</p>}
            <div className="field-heading"><label htmlFor="idea-input">Invention description</label><span>A few clear sentences</span></div>
            <p id="idea-help" className="field-help">Include the mechanism, its application and what makes it different.</p>
            <div className="invention-editor">
              <textarea id="idea-input" name="idea" value={idea} onChange={e => setIdea(e.target.value)} maxLength={2000}
                aria-describedby="idea-help idea-count" placeholder="For example: A wearable EEG sensor detects early seizure patterns using adaptive thresholds and alerts a caregiver in real time." />
              <div id="idea-count" className={'editor-count' + (idea.length > 1800 ? ' near-limit' : '')}>{idea.length.toLocaleString()} / 2,000 characters</div>
            </div>
            <div className="search-settings">
              <div className="result-count-setting">
                <label htmlFor="top-k-select">Initial matches</label>
                <select id="top-k-select" value={localTopK} onChange={e => setLocalTopK(Number(e.target.value))}>
                  {TOP_K_OPTIONS.map(k => <option key={k} value={k}>Top {k}</option>)}
                </select>
                <p className="field-help">Related publications may be grouped in the results.</p>
              </div>
              <fieldset className="ranking-setting">
                <legend>Graph ranking</legend>
                <div className="segmented-control">
                  {[{ value: 'novelty', label: 'Novelty' }, { value: 'similarity', label: 'Similarity' }].map(opt => (
                    <label key={opt.value} className={localGNNMode === opt.value ? 'selected' : ''}>
                      <input type="radio" id={'gnn-mode-' + opt.value} name="gnn-mode" value={opt.value} checked={localGNNMode === opt.value} onChange={() => setLocalGNNMode(opt.value)} />
                      <span>{opt.label}</span>
                    </label>
                  ))}
                </div>
                <p className="field-help">{localGNNMode === 'novelty' ? 'Prioritize structurally distinct candidates.' : 'Prioritize candidates with similar graph relationships.'}</p>
              </fieldset>
            </div>
            <div className="form-submit-row">
              <button id="submit-idea" type="submit" disabled={!idea.trim() || mutation.isPending} className="btn-primary">
                {mutation.isPending ? 'Starting analysis…' : 'Run analysis'}
              </button>
              <p>Review matches before requesting an evaluation.</p>
            </div>
            {mutation.error && <div className="error-notice" role="alert"><strong>Analysis could not start</strong><p>{mutation.error instanceof Error ? mutation.error.message : 'An unexpected pipeline error occurred.'}</p></div>}
            <p className="advisory-note">Research guidance, not a legal opinion or a guarantee of patentability.</p>
          </form>
          <aside className="intake-guide" aria-label="Writing guidance and examples">
            <h2>What to include</h2>
            <dl className="writing-guidance">
              <div><dt>Mechanism</dt><dd>How does it work? Name the key components or process.</dd></div>
              <div><dt>Application</dt><dd>What problem does it solve, and where is it used?</dd></div>
              <div><dt>Difference</dt><dd>What changes compared with an existing approach?</dd></div>
            </dl>
            <div className="example-heading"><h2>Try an example</h2><p>Select one to fill the description.</p></div>
            <ul className="example-list">
              {EXAMPLES.map(example => <li key={example.label}><button type="button" onClick={() => setIdea(example.text)} aria-pressed={idea === example.text} title={example.text}>
                <span>{example.label}</span><span aria-hidden="true">+</span>
              </button></li>)}
            </ul>
          </aside>
        </div>
      </main>
    </div>
  )
}
