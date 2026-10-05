import { useMutation } from '@tanstack/react-query'
import { expandKG } from '../api/kg'
import { usePipelineStore } from '../store/usePipelineStore'

export function useKGExpand() {
  const setKGExpansion = usePipelineStore((s) => s.setKGExpansion)
  return useMutation({
    onMutate: () => usePipelineStore.getState().pipelineResult,
    mutationFn: ({ ids, cap }: { ids: string[]; cap?: number }) =>
      expandKG(ids, cap),
    onSuccess: (data, _request, snapshot) => {
      if (usePipelineStore.getState().pipelineResult === snapshot) setKGExpansion(data)
    },
  })
}
