import client from './client'
import type { PipelineResponse, EvaluationResult } from '../types/pipeline'
import type { ImprovementResponse } from '../types/improvement'

export interface SavedAnalysisRun {
  case_id: string
  run_id: string
  case_title: string
  idea_text: string
  top_k: number
  gnn_mode: string
  started_at: string
  pipeline_result: PipelineResponse | null
  evaluation_result: EvaluationResult | null
  improvement_result: ImprovementResponse | null
}

export async function getRun(caseId: string, runId: string): Promise<SavedAnalysisRun> {
  const { data } = await client.get<SavedAnalysisRun>(`/cases/${caseId}/runs/${runId}`)
  return data
}

export type CaseStatus = 'draft' | 'active' | 'archived'

export interface AnalysisRunSummary {
  run_id: string
  query_id?: string | null
  gnn_mode: string
  top_k: number
  run_status: string
  started_at: string
  completed_at?: string | null
}

export interface AnalysisCase {
  case_id: string
  title: string
  idea_text: string
  status: CaseStatus
  created_at: string
  updated_at: string
  runs: AnalysisRunSummary[]
}

export async function listCases(): Promise<AnalysisCase[]> {
  const { data } = await client.get<AnalysisCase[]>('/cases')
  return data
}

export async function createCase(title: string, ideaText: string): Promise<AnalysisCase> {
  const { data } = await client.post<AnalysisCase>('/cases', { title, idea_text: ideaText })
  return data
}

export async function deleteCase(caseId: string): Promise<void> {
  await client.delete(`/cases/${caseId}`)
}
