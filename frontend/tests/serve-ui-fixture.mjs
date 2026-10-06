// Isolated visual QA: no real backend, credentials, database or persistent writes.
// npm run build && node tests/serve-ui-fixture.mjs -> http://127.0.0.1:5181
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { dirname, extname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const dist = resolve(dirname(fileURLToPath(import.meta.url)), '../dist')
const now = '2026-10-06T08:00:00Z'
const idea = 'UI verification fixture: an adaptive wearable EEG sensor identifies seizure patterns and alerts a caregiver.'
const titles = ['Adaptive neural-signal monitoring wearable', 'Low-power anomaly detection for biomedical signals', 'Sensor calibration and caregiver alert system']
const hits = titles.map((title, index) => ({
  rank: index + 1, patent_id: `UI-FIXTURE-${index + 1}`, title,
  abstract: 'Synthetic UI test data, not a real patent. A wearable sensing system processes neural signals, adapts its detection threshold and communicates alerts to a caregiver. Signal calibration and low-power processing support continuous monitoring.',
  domain: 'Medical devices', jurisdiction: 'US', publication_year: 2023 - index,
  legal_status: 'ACTIVE', family_size: 3, cites_patent_count: 8, cited_by_patent_count: 12,
  url: '', source: index === 2 ? 'kg_cpc' : 'faiss', faiss_rank: index + 1,
  semantic_score: .82 - index * .11, graph_score: .61 + index * .06,
  novelty_score: .39 - index * .06, combined_score: .70 - index * .05,
  expansion_type: index === 2 ? 'cpc_sibling' : null,
  related_publications: index === 0 ? [{ patent_id: 'UI-FIXTURE-1-A', url: '', domain: 'Medical devices', jurisdiction: 'WO', source: 'faiss', semantic_score: .79, combined_score: .69 }] : [],
}))
const pipeline = (request = {}) => ({
  query_id: 'ui-verification-0001', query_text: request.idea ?? idea,
  nlp_result: { clean_text: request.idea ?? idea, keywords: ['EEG', 'adaptive threshold', 'wearable sensor', 'caregiver alert'], entities: [{ text: 'EEG', label: 'TECHNOLOGY' }, { text: 'wearable sensor', label: 'DEVICE' }], source: 'UI fixture' },
  model: 'UI verification fixture', top_k: request.top_k ?? 10, results: hits,
  gnn_status: 'success', kg_status: 'success', case_id: request.case_id ?? 'fixture-case', run_id: 'fixture-run', persistence_status: 'persisted', indexed_count: 58428, canonical_count: 39102,
})
const dimension = (score, interpretation) => ({ score, interpretation })
const breakdown = Object.fromEntries(['combination_difficulty', 'motivation_to_combine', 'cross_domain_novelty', 'reconstruction', 'citation_isolation', 'long_felt_need', 'teaching_away', 'unexpected_effect', 'landscape'].map((name, index) => [name, { ...dimension(.55 + index * .025, 'Synthetic factor explanation for layout verification.'), weight: .1, type: index > 5 ? 'bonus' : 'base' }]))
const evaluation = {
  persistence_status: 'persisted', patentability_score: 64, patentability_raw: .64, verdict: 'Further investigation recommended', risk: 'Medium', confidence: .78,
  novelty: { score: 52, semantic_novelty: .48, gnn_novelty: .61, gnn_mode: 'novelty', blend: { semantic: .7, gnn: .3 }, top_semantic_score: .82, n_hits_used: 3, interpretation: 'Synthetic UI test: the adaptive calibration mechanism warrants closer comparison.' },
  non_obviousness: { score: 68, score_raw: .68, breakdown, weighted_contributions: {}, interpretation: 'Synthetic UI test: review how the sensing and alert mechanisms interact.', elapsed_seconds: 1.2, fast_mode: false },
  landscape: { score: .63, score_100: 63, density: .45, active_ratio: .7, assignee_concentration: .3, interpretation: 'Several related approaches appear in the test set.' },
  claim_breadth: { ...dimension(71, 'Review specific sensor calibration and processing limitations.'), avg_cpc_depth: 5, unique_section_ratio: .4, total_cpc_codes: 7 },
  timing: { ...dimension(65, 'Recent activity appears in the test set.'), newest_year: 2023, oldest_year: 2019, year_spread: 4, recency_flag: 'ACTIVE' },
  india_eligibility: { flags: [{ section: '3(k)', title: 'Computer program considerations', severity: 'MEDIUM', explanation: 'Synthetic explanation: distinguish a technical hardware effect from an algorithm alone.' }], safe_harbors: [{ note: 'Technical sensor integration', detail: 'Describe the physical sensing and processing arrangement.' }], is_flagged: true, summary: 'Eligibility flags are research guidance, not legal advice.' },
  technical_depth: { level: 'Medium', confidence: .76, quantitative_hits: 2, entity_count: 2, word_count: 22, interpretation: 'Add measurable power and signal-processing specifications.' },
  weights: { novelty: .3, non_obviousness: .3, landscape: .15, claim_breadth: .15, timing: .1 }, contributions: {}, concept_count: 2,
  concepts: [{ label: 'Adaptive signal calibration', description: 'Adjust the detection threshold to observed signal quality.' }, { label: 'Caregiver alerts', description: 'Communicate a detected event to a remote caregiver.' }], elapsed_seconds: 2.4, fast_mode: false,
}
const improvement = {
  persistence_status: 'persisted', diagnosis: ['Adaptive calibration is the main differentiating mechanism.'], weaknesses: ['Specify how calibration responds to motion artefacts.', 'Provide a measurable latency and battery-life target.'],
  strategies: [{ strategy: 'Define the calibration mechanism', impact: 'high', reason: 'Separate the adaptive process from generic monitoring.' }, { strategy: 'Add a low-power operating mode', impact: 'medium', reason: 'Make the implementation constraints concrete.' }],
  alternative_directions: ['Motion-aware calibration using a secondary inertial sensor.', 'Event-triggered communication that reduces wireless power consumption.'], recommendations: 'Synthetic UI fixture: refine the mechanism and compare each change with relevant publications.',
  overlapping_patents: hits.slice(0, 2).map(hit => ({ patent_id: hit.patent_id, title: hit.title, similarity: hit.semantic_score })),
}
const cases = [{ case_id: 'fixture-case', title: 'UI verification · adaptive EEG wearable', idea_text: idea, status: 'active', created_at: now, updated_at: now, runs: [{ run_id: 'fixture-run', query_id: 'ui-verification-0001', gnn_mode: 'novelty', top_k: 10, run_status: 'complete', started_at: now, completed_at: now }] }]
const graph = {
  nodes: [
    { id: 'UI-FIXTURE-1', type: 'default', position: { x: 240, y: 130 }, data: { label: 'Adaptive monitoring', title: titles[0], nodeType: 'patent' } },
    { id: 'company-1', type: 'default', position: { x: 0, y: 30 }, data: { label: 'Example research group', title: 'Synthetic assignee', nodeType: 'company' } },
    { id: 'cpc-1', type: 'default', position: { x: 500, y: 30 }, data: { label: 'A61B 5/00', title: 'Diagnostic measurement', nodeType: 'cpc' } },
    { id: 'inventor-1', type: 'default', position: { x: 0, y: 230 }, data: { label: 'Example inventor', title: 'Synthetic inventor', nodeType: 'inventor' } },
    { id: 'UI-FIXTURE-3', type: 'default', position: { x: 500, y: 230 }, data: { label: 'Sensor calibration', title: titles[2], nodeType: 'patent' } },
  ],
  edges: [
    { id: 'e1', source: 'UI-FIXTURE-1', target: 'company-1', label: 'ASSIGNED_TO', type: 'default' },
    { id: 'e2', source: 'UI-FIXTURE-1', target: 'cpc-1', label: 'CLASSIFIED_AS', type: 'default' },
    { id: 'e3', source: 'UI-FIXTURE-1', target: 'inventor-1', label: 'INVENTED_BY', type: 'default' },
    { id: 'e4', source: 'UI-FIXTURE-3', target: 'cpc-1', label: 'CLASSIFIED_AS', type: 'default' },
  ],
}
let savedPipeline = pipeline()
const requests = []
const send = (response, value, status = 200) => { response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); response.end(JSON.stringify(value)) }
const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, 'http://127.0.0.1:5181')
    if (url.pathname === '/__fixture/requests') return send(response, requests)
    if (url.pathname.startsWith('/api/')) {
      let raw = ''
      for await (const chunk of request) raw += chunk
      const body = raw ? JSON.parse(raw) : {}
      requests.push({ method: request.method, path: url.pathname, body })
      if (url.pathname === '/api/pipeline/run') {
        await new Promise(resolveDelay => setTimeout(resolveDelay, 800))
        if (body.idea?.includes('UI failure test')) return send(response, { detail: 'Synthetic verification failure. No live service was called.' }, 503)
        savedPipeline = pipeline(body)
        if (body.idea?.includes('UI fallback test')) savedPipeline = { ...savedPipeline, persistence_status: 'unavailable', persistence_message: 'Synthetic test: storage unavailable.', kg_status: 'unavailable', gnn_status: 'skipped', results: [] }
        return send(response, savedPipeline)
      }
      if (url.pathname === '/api/evaluate') return send(response, evaluation)
      if (url.pathname === '/api/improve') return send(response, improvement)
      if (url.pathname === '/api/kg/stats') return send(response, { nodes: { Patent: 3, Company: 1, CPC: 1, Inventor: 1 }, edges: { CLASSIFIED_AS: 2, ASSIGNED_TO: 1, INVENTED_BY: 1 } })
      if (url.pathname === '/api/kg/graph') return send(response, graph)
      if (url.pathname === '/api/kg/expand') return send(response, { family: [{ ...hits[0], patent_id: 'UI-FIXTURE-1-A' }], cpc_siblings: [hits[2]], total_added: 2 })
      if (url.pathname === '/api/cases' && request.method === 'GET') return send(response, cases)
      if (url.pathname === '/api/cases' && request.method === 'POST') {
        const draft = { case_id: `fixture-draft-${cases.length}`, title: body.title, idea_text: body.idea_text, status: 'draft', created_at: now, updated_at: now, runs: [] }
        cases.push(draft)
        return send(response, draft, 201)
      }
      if (/^\/api\/cases\/[^/]+\/runs\/[^/]+$/.test(url.pathname)) return send(response, { case_id: 'fixture-case', run_id: 'fixture-run', case_title: cases[0].title, idea_text: savedPipeline.query_text, top_k: savedPipeline.top_k, gnn_mode: 'novelty', started_at: now, pipeline_result: savedPipeline, evaluation_result: evaluation, improvement_result: improvement })
      if (request.method === 'DELETE' && /^\/api\/cases\/[^/]+$/.test(url.pathname)) {
        const index = cases.findIndex(item => item.case_id === url.pathname.split('/').at(-1))
        if (index >= 0) cases.splice(index, 1)
        return send(response, {})
      }
      return send(response, { detail: 'Unsupported fixture API route' }, 404)
    }
    const pathname = decodeURIComponent(url.pathname)
    const file = extname(pathname) ? resolve(dist, `.${pathname}`) : resolve(dist, 'index.html')
    if (!file.startsWith(dist + sep)) return send(response, { detail: 'Invalid asset path' }, 403)
    const contents = await readFile(file)
    const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png' }[extname(file)] ?? 'application/octet-stream'
    response.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'no-store' })
    response.end(contents)
  } catch (error) {
    send(response, { detail: error.message }, 500)
  }
})
server.listen(5181, '127.0.0.1', () => console.log('UI fixture only: http://127.0.0.1:5181 — no real backend requests'))
