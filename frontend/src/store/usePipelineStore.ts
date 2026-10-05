import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { PipelineResponse, PipelineStatus, EvaluationResult } from '../types/pipeline'
import type { KGStats, KGExpansion, KGGraphData } from '../types/kg'
import type { GNNWeights } from '../types/gnn'
import type { ImprovementResponse } from '../types/improvement'
import type { SavedAnalysisRun } from '../api/cases'
import type { PipelineRequest } from '../types/pipeline'

interface PipelineState {
  requestId: string | null
  activeCaseId: string | null
  savedRun: { caseId: string; runId: string } | null
  restoreRun: (run: SavedAnalysisRun) => void
  selectCase: (caseId: string, idea: string) => void
  startAnalysis: (request: PipelineRequest) => string
  // Input
  idea: string
  topK: number
  gnnMode: string
  // Execution state
  status: PipelineStatus
  error: string | null
  // Results
  pipelineResult: PipelineResponse | null
  kgStats: KGStats | null
  kgExpansion: KGExpansion | null
  kgGraphData: KGGraphData | null
  gnnWeights: GNNWeights
  // Evaluation
  evaluationResult: EvaluationResult | null
  evalStatus: 'idle' | 'running' | 'complete' | 'error'
  evalError: string | null
  // Improvement
  improvementResult: ImprovementResponse | null
  improvementStatus: 'idle' | 'running' | 'complete' | 'error'
  improvementError: string | null
  // Actions
  setIdea: (idea: string) => void
  setTopK: (k: number) => void
  setGNNMode: (mode: string) => void
  setStatus: (status: PipelineStatus) => void
  setError: (error: string | null) => void
  setPipelineResult: (result: PipelineResponse) => void
  setKGStats: (stats: KGStats) => void
  setKGExpansion: (exp: KGExpansion) => void
  setKGGraphData: (data: KGGraphData) => void
  setGNNWeights: (w: GNNWeights) => void
  setEvaluationResult: (result: EvaluationResult) => void
  setEvalStatus: (status: 'idle' | 'running' | 'complete' | 'error') => void
  setEvalError: (error: string | null) => void
  setImprovementResult: (result: ImprovementResponse) => void
  setImprovementStatus: (status: 'idle' | 'running' | 'complete' | 'error') => void
  setImprovementError: (error: string | null) => void
  reset: () => void
}

const DEFAULTS = {
  requestId: null as string | null,
  activeCaseId: null as string | null,
  savedRun: null as { caseId: string; runId: string } | null,
  idea: '',
  topK: 10,
  gnnMode: 'novelty',
  status: 'idle' as PipelineStatus,
  error: null,
  pipelineResult: null,
  kgStats: null,
  kgExpansion: null,
  kgGraphData: null,
  // Matches the server-side reranker defaults. UI changes are preview-only.
  gnnWeights: { semantic: 0.7, gnn: 0.3 },
  evaluationResult: null,
  evalStatus: 'idle' as const,
  evalError: null,
  improvementResult: null,
  improvementStatus: 'idle' as const,
  improvementError: null,
}

export const usePipelineStore = create<PipelineState>()(
  persist(
    (set) => ({
      ...DEFAULTS,
      startAnalysis: (request) => {
        const requestId = crypto.randomUUID()
        set({ ...DEFAULTS, requestId, idea: request.idea, topK: request.top_k, gnnMode: request.gnn_mode, activeCaseId: request.case_id ?? null, status: 'running' })
        return requestId
      },
      selectCase: (caseId, idea) => set({ ...DEFAULTS, activeCaseId: caseId, idea }),
      restoreRun: (run) => set({
        ...DEFAULTS, activeCaseId: run.case_id, savedRun: { caseId: run.case_id, runId: run.run_id },
        idea: run.idea_text, topK: run.top_k, gnnMode: run.gnn_mode,
        pipelineResult: run.pipeline_result, status: run.pipeline_result ? 'complete' : 'idle',
        evaluationResult: run.evaluation_result, evalStatus: run.evaluation_result ? 'complete' : 'idle',
        improvementResult: run.improvement_result, improvementStatus: run.improvement_result ? 'complete' : 'idle',
      }),
      setIdea:             (idea)             => set({ idea }),
      setTopK:             (topK)             => set({ topK }),
      setGNNMode:          (gnnMode)          => set({ gnnMode }),
      setStatus:           (status)           => set({ status }),
      setError:            (error)            => set({ error }),
      setPipelineResult:   (pipelineResult)   => set({ pipelineResult,
        activeCaseId: pipelineResult.case_id ?? null,
        savedRun: pipelineResult.persistence_status === 'persisted' && pipelineResult.case_id && pipelineResult.run_id
          ? { caseId: pipelineResult.case_id, runId: pipelineResult.run_id } : null,
      }),
      setKGStats:          (kgStats)          => set({ kgStats }),
      setKGExpansion:      (kgExpansion)      => set({ kgExpansion }),
      setKGGraphData:      (kgGraphData)      => set({ kgGraphData }),
      setGNNWeights:       (gnnWeights)       => set({ gnnWeights }),
      setEvaluationResult: (evaluationResult) => set({ evaluationResult, evalStatus: 'complete' }),
      setEvalStatus:       (evalStatus)       => set({ evalStatus }),
      setEvalError:        (evalError)        => set({ evalError, evalStatus: 'error' }),
      setImprovementResult:(improvementResult)=> set({ improvementResult, improvementStatus: 'complete' }),
      setImprovementStatus:(improvementStatus)=> set({ improvementStatus }),
      setImprovementError: (improvementError) => set({ improvementError, improvementStatus: 'error' }),
      reset:               ()                 => set(DEFAULTS),
    }),
    {
      name: 'patent-intelligence-store',
      storage: createJSONStorage(() => localStorage),
      // Saved results are restored from MySQL; local storage keeps only a pointer.
      version: 1,
      migrate: () => ({}),
      partialize: (state) => ({
        idea:             state.idea,
        topK:             state.topK,
        gnnMode:          state.gnnMode,
        activeCaseId: state.activeCaseId,
        savedRun: state.savedRun,
      }),
    }
  )
)
