import { Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { MotionConfig } from 'framer-motion'
import RootLayout from './layouts/RootLayout'

const LandingPage             = lazy(() => import('./pages/LandingPage'))
const IdeaInputPage           = lazy(() => import('./pages/IdeaInputPage'))
const PipelineProgressPage    = lazy(() => import('./pages/PipelineProgressPage'))
const NLPResultsPage          = lazy(() => import('./pages/NLPResultsPage'))
const RetrievalResultsPage    = lazy(() => import('./pages/RetrievalResultsPage'))
const KGVisualizationPage     = lazy(() => import('./pages/KGVisualizationPage'))
const GNNAnalysisPage         = lazy(() => import('./pages/GNNAnalysisPage'))
const EvaluationDashboardPage = lazy(() => import('./pages/EvaluationDashboardPage'))
const ImprovementAgentPage    = lazy(() => import('./pages/ImprovementAgentPage'))
const CaseHistoryPage         = lazy(() => import('./pages/CaseHistoryPage'))

function LoadingFallback() {
  return (
    <div className="route-loading" role="status">
      <span className="loading-spinner" aria-hidden="true" /><span>Opening workspace…</span>
    </div>
  )
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/"         element={<LandingPage />} />
        <Route path="/analyze"  element={<IdeaInputPage />} />
        <Route path="/pipeline" element={<PipelineProgressPage />} />
        <Route element={<RootLayout />}>
          <Route path="/results/nlp"          element={<NLPResultsPage />} />
          <Route path="/results/patents"      element={<RetrievalResultsPage />} />
          <Route path="/results/graph"        element={<KGVisualizationPage />} />
          <Route path="/results/gnn"          element={<GNNAnalysisPage />} />
          <Route path="/results/evaluation"   element={<EvaluationDashboardPage />} />
          <Route path="/results/improvements" element={<ImprovementAgentPage />} />
          <Route path="/results/cases"        element={<CaseHistoryPage />} />
        </Route>
      </Routes>
    </Suspense>
    </MotionConfig>
  )
}
