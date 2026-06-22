import client from './client'
import type { EvaluateRequest, EvaluationResult } from '../types/pipeline'

export async function runEvaluation(req: EvaluateRequest): Promise<EvaluationResult> {
  const { data } = await client.post<EvaluationResult>('/evaluate', req, { timeout: 300_000 })
  return data
}
