import { Outlet, useLocation, Link } from 'react-router-dom'
import { usePipelineStore } from '../store/usePipelineStore'
import { KGIcon, IdeaIcon, FAISSIcon, GNNIcon, NoveltyIcon } from '../assets/PatentIcons'
import { useEffect, useState } from 'react'
import { getRun } from '../api/cases'
import AnalysisSavingStatus from '../components/AnalysisSavingStatus'
import AppHeader from '../components/AppHeader'

const NAV_ITEMS = [
  { path: '/results/nlp', label: 'Concepts', Icon: IdeaIcon },
  { path: '/results/patents', label: 'Related patents', Icon: FAISSIcon },
  { path: '/results/graph', label: 'Patent relationships', Icon: KGIcon },
  { path: '/results/gnn', label: 'Ranking', Icon: GNNIcon },
  { path: '/results/evaluation', label: 'Evaluation', Icon: NoveltyIcon },
  { path: '/results/improvements', label: 'Improvements', Icon: IdeaIcon },
]

export default function RootLayout() {
  const location = useLocation()
  const { status, idea, reset, savedRun, pipelineResult, restoreRun } = usePipelineStore()
  const [restoreError, setRestoreError] = useState<string | null>(null)
  useEffect(() => { window.scrollTo({ top: 0, left: 0, behavior: 'instant' }) }, [location.pathname])
  useEffect(() => {
    if (!savedRun || pipelineResult) return
    let ignore = false
    setRestoreError(null)
    getRun(savedRun.caseId, savedRun.runId)
      .then(run => { if (!ignore) restoreRun(run) })
      .catch(error => { if (!ignore) setRestoreError(error.message ?? 'Could not restore saved analysis.') })
    return () => { ignore = true }
  }, [savedRun?.caseId, savedRun?.runId, Boolean(pipelineResult), restoreRun])

  return (
    <div className="workspace-shell">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <AppHeader>
        {status !== 'idle' && <span className={'workspace-status status-' + status}>{status === 'running' ? 'Analyzing' : status === 'complete' ? 'Analysis complete' : 'Analysis failed'}</span>}
        <Link to="/analyze" onClick={reset} className="btn-primary">New analysis</Link>
      </AppHeader>
      <div className="workspace-body">
        <aside className="workspace-sidebar">
          {idea && <div className="analysis-context"><span>Current invention</span><p title={idea}>{idea}</p></div>}
          <nav className="results-nav" aria-label="Analysis views">
            {NAV_ITEMS.map(({ path, label, Icon }) => (
              <Link key={path} to={path} className={location.pathname === path ? 'active' : ''} aria-current={location.pathname === path ? 'page' : undefined}>
                <Icon size={17} animate={false} /><span>{label}</span>
              </Link>
            ))}
          </nav>
          <Link to="/results/cases" className={'saved-cases-link' + (location.pathname === '/results/cases' ? ' active' : '')} aria-current={location.pathname === '/results/cases' ? 'page' : undefined}>Saved cases</Link>
          <p className="sidebar-note">Compare the evidence.<br />Scores are research guidance.</p>
        </aside>
        <main id="main-content" className="workspace-main">
          <AnalysisSavingStatus />
          {savedRun && !pipelineResult ? (
            <section role="status" className="restore-status">
              {restoreError ? <><p>{restoreError}</p><Link to="/results/cases" onClick={reset} className="text-link">Open saved cases</Link></> : <p>Restoring saved analysis…</p>}
            </section>
          ) : <Outlet />}
        </main>
      </div>
    </div>
  )
}
