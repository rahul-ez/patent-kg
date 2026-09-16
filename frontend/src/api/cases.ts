import client from './client'

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
