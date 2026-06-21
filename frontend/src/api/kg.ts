import client from './client'
import type { KGStats, KGExpansion, KGGraphData } from '../types/kg'

export async function buildKG(patent_ids: string[]): Promise<KGStats> {
  const { data } = await client.post<KGStats>('/kg/build', { patent_ids })
  return data
}

export async function expandKG(patent_ids: string[], cpc_cap = 10): Promise<KGExpansion> {
  const { data } = await client.post<KGExpansion>('/kg/expand', { patent_ids, cpc_cap })
  return data
}

export async function getKGGraph(patent_ids: string[]): Promise<KGGraphData> {
  const { data } = await client.get<KGGraphData>('/kg/graph', {
    params: { patent_ids: patent_ids.join(',') },
  })
  return data
}
