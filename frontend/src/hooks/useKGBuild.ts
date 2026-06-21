import { useMutation } from '@tanstack/react-query'
import { buildKG } from '../api/kg'
import { usePipelineStore } from '../store/usePipelineStore'

export function useKGBuild() {
  const setKGStats = usePipelineStore((s) => s.setKGStats)
  return useMutation({
    mutationFn: (ids: string[]) => buildKG(ids),
    onSuccess: (data) => setKGStats(data),
  })
}
