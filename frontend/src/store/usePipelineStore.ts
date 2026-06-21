import { create } from 'zustand'
import type { PipelineResponse, PipelineStatus } from '../types/pipeline'
import type { KGStats, KGExpansion, KGGraphData } from '../types/kg'
import type { GNNWeights } from '../types/gnn'

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
}

export const usePipelineStore = create<PipelineState>()((set) => ({
  ...DEFAULTS,
  setIdea:           (idea)           => set({ idea }),
  setTopK:           (topK)           => set({ topK }),
  setGNNMode:        (gnnMode)        => set({ gnnMode }),
  setStatus:         (status)         => set({ status }),
  setError:          (error)          => set({ error }),
  setPipelineResult: (pipelineResult) => set({ pipelineResult }),
  setKGStats:        (kgStats)        => set({ kgStats }),
  setKGExpansion:    (kgExpansion)    => set({ kgExpansion }),
  setKGGraphData:    (kgGraphData)    => set({ kgGraphData }),
  setGNNWeights:     (gnnWeights)     => set({ gnnWeights }),
  reset:             ()               => set(DEFAULTS),
}))
