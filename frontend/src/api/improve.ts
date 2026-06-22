import client from './client'
import type { ImprovementRequest, ImprovementResponse } from '../types/improvement'

export async function runImprovement(req: ImprovementRequest): Promise<ImprovementResponse> {
  const { data } = await client.post<ImprovementResponse>('/improve', req, { timeout: 300_000 })
  return data
}
