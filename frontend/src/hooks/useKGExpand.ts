import { useMutation } from '@tanstack/react-query'
import { expandKG } from '../api/kg'
import { usePipelineStore } from '../store/usePipelineStore'

export function useKGExpand() {
  const setKGExpansion = usePipelineStore((s) => s.setKGExpansion)
  return useMutation({
    mutationFn: ({ ids, cap }: { ids: string[]; cap?: number }) =>
      expandKG(ids, cap),
    onSuccess: (data) => setKGExpansion(data),
  })
}
