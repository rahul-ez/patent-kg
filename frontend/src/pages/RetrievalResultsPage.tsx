import { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import type { RetrievalHit } from '../types/pipeline'
import { FAISSIcon } from '../assets/PatentIcons'
import { T } from '../theme'

// ─── PatentCard (for ranks 2 to 100) ──────────────────────────────────────────
function PatentCard({ hit, idx }: { hit: RetrievalHit; idx: number }) {
  const [expanded, setExpanded] = useState(false)

  const score    = hit.semantic_score ?? 0
  const abstract = hit.abstract || ''
  const shortAbs = abstract.slice(0, 240)
  const isLong   = abstract.length > 240

  const hasGNN = hit.novelty_score != null || hit.combined_score != null

  // Score bar fill: sage for semantic baseline, brass if GNN elevated it
  const barColor = hasGNN && hit.combined_score !== undefined && hit.combined_score > score
    ? T.accentBrass : T.accentSage

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '32px 1fr', gap: 16, alignItems: 'start', marginBottom: 16 }}>
      {/* Rank number outside the card in the 32px gutter */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '18px',
        fontWeight: 600,
        color: 'var(--text-tertiary)',
        textAlign: 'right',
        marginTop: 18,
      }}>
        #{idx + 2}
      </div>

      <div className="sheet-secondary" style={{ position: 'relative' }}>
        {/* Title */}
        <h3 style={{
          fontFamily: 'var(--font-body)',
          fontWeight: 600,
          color: 'var(--text-primary)',
          fontSize: '16px',
          lineHeight: 1.45,
          marginBottom: 4,
          paddingRight: 12,
        }}>
          {hit.title || 'Untitled Patent'}
        </h3>

        {/* Patent ID */}
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: 10 }}>
          {hit.patent_id}
        </p>

        {/* Abstract */}
        <p style={{ color: 'var(--text-secondary)', fontSize: '13.5px', lineHeight: 1.6, marginBottom: 12 }}>
          {expanded ? abstract : shortAbs}
          {isLong && (
            <>
              {!expanded && '…'}
              {' '}
              <button
                onClick={() => setExpanded(e => !e)}
                style={{ background: 'none', border: 'none', color: 'var(--accent-sage)', fontSize: '13px', cursor: 'pointer', fontWeight: 600, padding: 0, fontFamily: 'inherit' }}
              >
                {expanded ? 'Show less' : 'Show more'}
              </button>
            </>
          )}
        </p>

        {/* Domain tag + external link */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14, flexWrap: 'wrap' }}>
          {hit.domain && (
            <span className="tag-keyword" style={{ borderColor: 'var(--accent-indigo)', color: 'var(--accent-indigo)' }}>
              {hit.domain}
            </span>
          )}
          {hit.url && (
            <a href={hit.url} target="_blank" rel="noopener noreferrer"
              style={{ color: 'var(--accent-sage)', fontSize: '13px', textDecoration: 'none', fontWeight: 600 }}
            >
              View on Lens.org ↗
            </a>
          )}
        </div>

        {/* Score bar */}
        <div className="score-track" style={{ marginBottom: 6 }}>
          <div
            className={barColor === T.accentSage ? 'score-fill-sage' : 'score-fill-brass'}
            style={{ width: `${Math.min(score * 100, 100)}%` }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)' }}>
          <span>Similarity Score</span>
          <span style={{ fontWeight: 600 }}>{score.toFixed(4)}</span>
        </div>

        {/* GNN scores */}
        {hasGNN && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10, borderTop: '1px solid var(--border-hairline)', paddingTop: 10 }}>
            <span className="mono-tag" style={{ borderColor: 'var(--accent-sage)', color: 'var(--accent-sage)' }}>
              SEMANTIC: {score.toFixed(4)}
            </span>
            {hit.novelty_score != null && (
              <span className="mono-tag" style={{ borderColor: 'var(--accent-brass)', color: 'var(--accent-brass)' }}>
                GNN NOVELTY: {hit.novelty_score.toFixed(4)}
              </span>
            )}
            {hit.combined_score != null && (
              <span className="mono-tag" style={{ borderColor: 'var(--text-secondary)', color: 'var(--text-secondary)' }}>
                COMBINED: {hit.combined_score.toFixed(4)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────
export default function RetrievalResultsPage() {
  const navigate = useNavigate()
  const { pipelineResult } = usePipelineStore()
  const [sortMode, setSortMode] = useState<'faiss' | 'gnn'>('faiss')
  const [topExpanded, setTopExpanded] = useState(false)

  // Ref number generation derived from query_id or current date
  const refNum = useRef('')
  if (pipelineResult && !refNum.current) {
    const d = new Date()
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hash = pipelineResult.query_id ? pipelineResult.query_id.slice(-4).toUpperCase() : 'TEMP'
    refNum.current = `PI-${yyyy}-${mm}${dd}-${hash}`
  }

  if (!pipelineResult) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 20, textAlign: 'center', padding: 24 }}>
        <FAISSIcon size={40} color={T.borderHairline} animate={false} />
        <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600 }}>No Case File Selected</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Please submit an innovation idea first to retrieve prior art.</p>
        <Link to="/analyze" className="btn-primary" style={{ textDecoration: 'none', marginTop: 4 }}>New Analysis →</Link>
      </div>
    )
  }

  const hits: RetrievalHit[] = pipelineResult.results ?? []
  const hasGNN = hits.some(h => h.novelty_score != null || h.combined_score != null)

  const sortedHits = [...hits].sort((a, b) => {
    if (sortMode === 'gnn') return (b.combined_score ?? b.semantic_score ?? 0) - (a.combined_score ?? a.semantic_score ?? 0)
    return (b.semantic_score ?? 0) - (a.semantic_score ?? 0)
  })

  const topHit = sortedHits[0]

  return (
    <div style={{ maxWidth: 960, fontFamily: 'var(--font-body)' }}>

      {/* ─── Page Title Block ─── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
        style={{ marginBottom: 16 }}
      >
        <p className="caption" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>
          §02 — SEMANTIC RETRIEVAL
        </p>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '44px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
          Patent Retrieval Results
        </h1>
      </motion.div>

      {/* ─── Metadata Strip ─── */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.05 }}
        style={{
          height: 44,
          background: 'transparent',
          borderBottom: '1px solid var(--border-hairline)',
          display: 'flex', alignItems: 'baseline', justifyUnderline: 'space-between', justifyContent: 'space-between',
          padding: '0 0 12px 0',
          marginBottom: 40,
        }}
      >
        {/* Left cluster */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          {/* Indexed Count */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>INDEXED COUNT</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>58,428</span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Top Score */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>TOP SCORE</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>
              {topHit && topHit.semantic_score !== null ? topHit.semantic_score.toFixed(4) : '—'}
            </span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Results Returned */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>RESULTS RETURNED</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>{hits.length}</span>
          </div>
        </div>

        {/* Right side: Ref number */}
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)', letterSpacing: '0.06em' }}>
          REF. {refNum.current}
        </div>
      </motion.div>

      {/* ─── Sort toggle (Segmented Pattern) ─── */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}
        style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}
      >
        <span className="caption" style={{ color: 'var(--text-secondary)' }}>SORT BY:</span>
        <div style={{
          display: 'flex',
          background: 'var(--bg-structural)',
          border: `1px solid var(--border-hairline)`,
          borderRadius: 'var(--radius-control)',
          overflow: 'hidden',
        }}>
          {[
            { value: 'faiss', label: 'FAISS Order' },
            { value: 'gnn', label: 'GNN Order' }
          ].map(opt => {
            const active = sortMode === opt.value
            const disabled = opt.value === 'gnn' && !hasGNN
            return (
              <button
                key={opt.value}
                id={`sort-${opt.value}`}
                onClick={() => setSortMode(opt.value as 'faiss' | 'gnn')}
                disabled={disabled}
                style={{
                  padding: '6px 12px',
                  border: 'none',
                  background: active ? 'var(--surface-ink)' : 'transparent',
                  color: active ? 'var(--text-on-dark)' : disabled ? 'var(--text-tertiary)' : 'var(--text-secondary)',
                  fontSize: '11.5px',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  transition: 'background 120ms, color 120ms',
                }}
              >
                {opt.label.toUpperCase()}{opt.value === 'gnn' && !hasGNN && ' (N/A)'}
              </button>
            )
          })}
        </div>
        {sortMode === 'gnn' && hasGNN && (
          <span className="mono-tag" style={{ borderColor: 'var(--accent-sage)', color: 'var(--accent-sage)' }}>
            RE-RANKED BY GRAPHSAGE LIVE INFERENCE
          </span>
        )}
      </motion.div>

      {/* ─── Anchor Card (§1 Primary Exhibit: Rank #1 Hit) ─── */}
      {topHit && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15, duration: 0.35 }}
          className="sheet-primary" style={{ marginBottom: 40 }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
            <h2 className="section-header" style={{ margin: 0 }}>
              <span className="section-clause-num">§1</span>Primary Exhibit
            </h2>
            <span className="mono-tag" style={{ borderColor: 'var(--accent-clay)', color: 'var(--accent-clay)' }}>
              RANK #1 HIT
            </span>
          </div>

          <h3 style={{
            fontFamily: 'var(--font-display)',
            fontSize: '22px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            lineHeight: 1.35,
            marginBottom: 6,
          }}>
            {topHit.title || 'Untitled Patent'}
          </h3>

          <p style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: 16 }}>
            {topHit.patent_id}
          </p>

          <p style={{
            fontFamily: 'var(--font-body)',
            fontSize: '15px',
            lineHeight: 1.65,
            color: 'var(--text-primary)',
            marginBottom: 16,
          }}>
            {topExpanded ? topHit.abstract : (topHit.abstract?.slice(0, 320) + (topHit.abstract && topHit.abstract.length > 320 ? '…' : ''))}
            {topHit.abstract && topHit.abstract.length > 320 && (
              <button
                onClick={() => setTopExpanded(e => !e)}
                style={{ background: 'none', border: 'none', color: 'var(--accent-sage)', fontSize: '13.5px', cursor: 'pointer', fontWeight: 600, marginLeft: 6, padding: 0 }}
              >
                {topExpanded ? 'Show less' : 'Show more'}
              </button>
            )}
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
            {topHit.domain && (
              <span className="tag-keyword" style={{ borderColor: 'var(--accent-indigo)', color: 'var(--accent-indigo)', padding: '3px 10px' }}>
                {topHit.domain}
              </span>
            )}
            {topHit.url && (
              <a href={topHit.url} target="_blank" rel="noopener noreferrer"
                style={{ color: 'var(--accent-sage)', fontSize: '13.5px', textDecoration: 'none', fontWeight: 600 }}
              >
                View on Lens.org ↗
              </a>
            )}
          </div>

          {/* Full Score Breakdown */}
          <div style={{ borderTop: '1px solid var(--border-hairline)', paddingTop: 20 }}>
            <p className="caption" style={{ color: 'var(--text-secondary)', marginBottom: 14 }}>Full Score Breakdown</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20 }}>
              {/* Semantic Score */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: '12.5px', color: 'var(--text-secondary)', fontWeight: 500 }}>Semantic Similarity</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600 }}>{topHit.semantic_score?.toFixed(4)}</span>
                </div>
                <div className="score-track">
                  <div className="score-fill-sage" style={{ width: `${(topHit.semantic_score ?? 0) * 100}%` }} />
                </div>
              </div>

              {/* GNN Novelty Score */}
              {topHit.novelty_score !== undefined && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: '12.5px', color: 'var(--text-secondary)', fontWeight: 500 }}>GNN Novelty</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600 }}>{topHit.novelty_score?.toFixed(4)}</span>
                  </div>
                  <div className="score-track">
                    <div className="score-fill-brass" style={{ width: `${(topHit.novelty_score ?? 0) * 100}%` }} />
                  </div>
                </div>
              )}

              {/* Combined Score */}
              {topHit.combined_score !== undefined && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: '12.5px', color: 'var(--text-secondary)', fontWeight: 500 }}>Combined Reranked</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600 }}>{topHit.combined_score?.toFixed(4)}</span>
                  </div>
                  <div className="score-track">
                    <div className="score-fill-sage" style={{ width: `${(topHit.combined_score ?? 0) * 100}%` }} />
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* ─── Remaining hits (§2 Prior Art Candidates) ─── */}
      {sortedHits.length > 1 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.35 }}
          style={{ marginBottom: 48 }}
        >
          <h2 className="section-header" style={{ marginBottom: 20 }}>
            <span className="section-clause-num">§2</span>Prior Art Candidates
          </h2>
          <div>
            {sortedHits.slice(1).map((hit, i) => (
              <PatentCard key={hit.patent_id || i} hit={hit} idx={i} />
            ))}
          </div>
        </motion.div>
      )}

      {/* Empty State */}
      {sortedHits.length === 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-tertiary)', fontSize: '13px', fontStyle: 'italic', padding: '32px 0' }}>
          <FAISSIcon size={14} color={T.textTertiary} animate={false} />
          No prior art candidates detected for this query.
        </div>
      )}

      {/* ─── CTA Banner ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.35 }}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
          padding: '24px 0 0 0',
          borderTop: `2px solid ${T.accentSage}`,
          marginBottom: 32,
        }}
      >
        <div>
          <p style={{ fontWeight: 600, fontSize: '16px', color: 'var(--text-primary)', marginBottom: 2 }}>Explore the Knowledge Graph</p>
          <p className="caption" style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Visualize patent family structures and shared CPC classifications</p>
        </div>
        <button onClick={() => navigate('/results/graph')} className="btn-primary" style={{ padding: '10px 24px' }}>
          Explore Knowledge Graph →
        </button>
      </motion.div>
    </div>
  )
}

