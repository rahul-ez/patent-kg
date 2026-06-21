import client from './client'
import type { PipelineRequest, PipelineResponse } from '../types/pipeline'

export async function runPipeline(req: PipelineRequest): Promise<PipelineResponse> {
  const { data } = await client.post<PipelineResponse>('/pipeline/run', req)
  return data
}
