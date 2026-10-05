// Run with Node 24+: node --test tests/*.test.mjs
import test, { beforeEach } from 'node:test'
import assert from 'node:assert/strict'

const storage = new Map()
globalThis.localStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
  removeItem: key => storage.delete(key),
}
const { usePipelineStore: store } = await import('../src/store/usePipelineStore.ts')
const pipeline = { query_id: 'same-query', results: [], top_k: 5, nlp_result: {}, model: 'fixture', query_text: 'sensor', case_id: 'c1', run_id: 'r1', persistence_status: 'persisted' }
beforeEach(() => store.getState().reset())

test('beginning an analysis clears every old output but preserves its case', () => {
  store.setState({ pipelineResult: pipeline, evaluationResult: {}, improvementResult: {}, kgStats: {}, kgGraphData: {}, kgExpansion: {} })
  const token = store.getState().startAnalysis({ idea: 'Revised idea', top_k: 5, gnn_mode: 'novelty', case_id: 'c1' })
  assert.equal(store.getState().requestId, token)
  assert.equal(store.getState().activeCaseId, 'c1')
  assert.equal(store.getState().status, 'running')
  for (const field of ['pipelineResult', 'evaluationResult', 'improvementResult', 'kgStats', 'kgGraphData', 'kgExpansion', 'savedRun']) assert.equal(store.getState()[field], null)
})

test('switching cases invalidates an in-flight request token', () => {
  const token = store.getState().startAnalysis({ idea: 'Old', top_k: 5, gnn_mode: 'novelty' })
  store.getState().selectCase('c2', 'New')
  assert.notEqual(store.getState().requestId, token)
  assert.equal(store.getState().activeCaseId, 'c2')
})

test('unsaved analyses never leave a reload pointer', () => {
  store.getState().setPipelineResult({ ...pipeline, persistence_status: 'not_saved' })
  assert.equal(store.getState().savedRun, null)
})

test('local storage keeps identifiers and input, not result payloads', () => {
  store.getState().setPipelineResult(pipeline)
  const persisted = JSON.parse(storage.get('patent-intelligence-store')).state
  assert.deepEqual(persisted.savedRun, { caseId: 'c1', runId: 'r1' })
  assert.equal(persisted.pipelineResult, undefined)
  assert.equal(persisted.evaluationResult, undefined)
  assert.equal(persisted.improvementResult, undefined)
})

test('API restoration restores the full evaluation and improvement snapshot', () => {
  const evaluation = { patentability_score: 61, persistence_status: 'persisted' }
  const improvement = { recommendations: 'Full output', strategies: [], persistence_status: 'persisted' }
  store.getState().restoreRun({ case_id: 'c1', run_id: 'r1', idea_text: 'Original idea', top_k: 5, gnn_mode: 'novelty', pipeline_result: pipeline, evaluation_result: evaluation, improvement_result: improvement })
  assert.equal(store.getState().idea, 'Original idea')
  assert.equal(store.getState().evaluationResult, evaluation)
  assert.equal(store.getState().improvementResult, improvement)
  assert.equal(store.getState().evalStatus, 'complete')
  assert.equal(store.getState().improvementStatus, 'complete')
})

test('reset removes any saved pointer and stale result', () => {
  store.getState().setPipelineResult(pipeline)
  store.getState().reset()
  assert.equal(store.getState().savedRun, null)
  assert.equal(store.getState().pipelineResult, null)
})
