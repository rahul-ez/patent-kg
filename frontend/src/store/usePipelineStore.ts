import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { PipelineResponse, PipelineStatus, EvaluationResult } from '../types/pipeline'
import type { KGStats, KGExpansion, KGGraphData } from '../types/kg'
import type { GNNWeights } from '../types/gnn'
import type { ImprovementResponse } from '../types/improvement'

interface PipelineState {
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
  idea: '',
  topK: 10,
  gnnMode: 'novelty',
  status: 'idle' as PipelineStatus,
  error: null,
  pipelineResult: null,
  kgStats: null,
  kgExpansion: null,
  kgGraphData: null,
  gnnWeights: { semantic: 0.6, gnn: 0.4 },
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
      setIdea:             (idea)             => set({ idea }),
      setTopK:             (topK)             => set({ topK }),
      setGNNMode:          (gnnMode)          => set({ gnnMode }),
      setStatus:           (status)           => set({ status }),
      setError:            (error)            => set({ error }),
      setPipelineResult:   (pipelineResult)   => set({ pipelineResult }),
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
      // Only persist the results and inputs — not transient run state
      partialize: (state) => ({
        idea:             state.idea,
        topK:             state.topK,
        gnnMode:          state.gnnMode,
        pipelineResult:   state.pipelineResult,
        evaluationResult: state.evaluationResult,
        improvementResult:state.improvementResult,
      }),
    }
  )
)
