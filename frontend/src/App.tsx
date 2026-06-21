import { Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
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

function LoadingFallback() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: '#080d18' }}>
      <div style={{ width: 32, height: 32, border: '2px solid #6366f1', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
    </div>
  )
}

export default function App() {
  return (
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
        </Route>
      </Routes>
    </Suspense>
  )
}
