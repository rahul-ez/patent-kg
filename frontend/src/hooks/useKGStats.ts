import { useMutation } from '@tanstack/react-query'
import { getKGStats } from '../api/kg'
import { usePipelineStore } from '../store/usePipelineStore'

export function useKGStats() {
  const setKGStats = usePipelineStore((s) => s.setKGStats)
  return useMutation({
    onMutate: () => usePipelineStore.getState().pipelineResult,
    mutationFn: (ids: string[]) => getKGStats(ids),
    onSuccess: (data, _ids, snapshot) => {
      if (usePipelineStore.getState().pipelineResult === snapshot) setKGStats(data)
    },
  })
}
