import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { runPipeline } from '../api/pipeline'
import { usePipelineStore } from '../store/usePipelineStore'
import type { PipelineRequest } from '../types/pipeline'

export function usePipeline() {
  const navigate = useNavigate()
  const { setStatus, setError, setPipelineResult } = usePipelineStore()

  return useMutation({
    mutationFn: (req: PipelineRequest) => runPipeline(req),
    onMutate: () => {
      setStatus('running')
      setError(null)
      navigate('/pipeline')
    },
    onSuccess: (data) => {
      setPipelineResult(data)
      setStatus('complete')
      navigate('/results/nlp')
    },
    onError: (err: Error) => {
      setStatus('error')
      setError(err.message)
    },
  })
}
