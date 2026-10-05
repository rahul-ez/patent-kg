import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { runPipeline } from '../api/pipeline'
import { usePipelineStore } from '../store/usePipelineStore'
import type { PipelineRequest } from '../types/pipeline'

export function usePipeline() {
  const navigate = useNavigate()
  const { setStatus, setError, setPipelineResult, startAnalysis } = usePipelineStore()

  return useMutation({
    mutationFn: (req: PipelineRequest) => runPipeline(req),
    onMutate: (request) => {
      const requestId = startAnalysis(request)
      navigate('/pipeline')
      return requestId
    },
    onSuccess: (data, _request, requestId) => {
      if (usePipelineStore.getState().requestId !== requestId) return
      setPipelineResult(data)
      setStatus('complete')
      navigate('/results/nlp')
    },
    onError: (err: Error, _request, requestId) => {
      if (usePipelineStore.getState().requestId !== requestId) return
      setStatus('error')
      setError(err.message)
    },
  })
}
