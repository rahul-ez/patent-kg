import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import type { RetrievalHit } from '../types/pipeline'
import { FAISSIcon, KGIcon } from '../assets/PatentIcons'
import { T } from '../theme'

// ─── PatentCard ──────────────────────────────────────────────────────────────
function PatentCard({ hit, idx }: { hit: RetrievalHit; idx: number }) {
  const [expanded, setExpanded] = useState(false)

  const score    = hit.semantic_score ?? 0
  const abstract = hit.abstract || ''
  const shortAbs = abstract.slice(0, 280)
  const isLong   = abstract.length > 280

  const hasGNN = hit.novelty_score != null || hit.combined_score != null

  // Score bar fill: sage for semantic baseline, brass if GNN elevated it
  const barColor = hasGNN && hit.combined_score !== undefined && hit.combined_score > score
    ? T.brass : T.sage

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="sheet"
      style={{ padding: '18px 18px 14px', marginBottom: 10, position: 'relative', cursor: 'default' }}
      whileHover={{ borderColor: T.sage } as any}
    >
      {/* Rank watermark */}
      <div style={{
        position: 'absolute', top: 14, right: 16,
        fontFamily: 'var(--font-display)', fontStyle: 'italic',
        fontSize: '1.35rem', fontWeight: 500,
        color: T.line, lineHeight: 1, userSelect: 'none',
      }}>
        #{idx + 1}
      </div>

      {/* Title */}
      <h3 style={{ fontWeight: 600, color: 'var(--ink)', fontSize: '0.93rem', lineHeight: 1.45, marginBottom: 5, paddingRight: 44 }}>
        {hit.title || 'Untitled Patent'}
      </h3>

      {/* Patent ID — IBM Plex Mono */}
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: T.inkSoft, marginBottom: 10, letterSpacing: '0.03em' }}>
        {hit.patent_id}
      </p>

      {/* Abstract */}
      <p style={{ color: 'var(--ink-soft)', fontSize: '0.84rem', lineHeight: 1.65, marginBottom: 10 }}>
        {expanded ? abstract : shortAbs}
        {isLong && (
          <>
            {!expanded && '…'}
            {' '}
            <button
              onClick={() => setExpanded(e => !e)}
              style={{ background: 'none', border: 'none', color: T.sage, fontSize: '0.8rem', cursor: 'pointer', fontWeight: 500, padding: 0, fontFamily: 'inherit' }}
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          </>
        )}
      </p>

      {/* Domain tag + external link */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
        {hit.domain && <span className="tag-keyword" style={{ borderColor: T.indigo, color: T.indigo }}>{hit.domain}</span>}
        {hit.url && (
          <a href={hit.url} target="_blank" rel="noopener noreferrer"
            style={{ color: T.sage, fontSize: '0.75rem', textDecoration: 'none', fontWeight: 500, transition: 'color 120ms' }}
            onMouseEnter={e => (e.currentTarget.style.color = T.ink)}
            onMouseLeave={e => (e.currentTarget.style.color = T.sage)}
          >
            View on Lens.org ↗
          </a>
        )}
      </div>

      {/* Score bar — 4px thin, flat fill, no glow */}
      <div className="score-track" style={{ marginBottom: 5 }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(score * 100, 100)}%` }}
          transition={{ delay: idx * 0.04 + 0.25, duration: 0.6, ease: 'easeOut' }}
          className={barColor === T.sage ? 'score-fill-sage' : 'score-fill-brass'}
        />
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: T.inkSoft }}>
        Similarity: {score.toFixed(4)}
      </div>

      {/* GNN mono-text scores */}
      {hasGNN && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
          <span className="mono-tag" style={{ borderColor: T.sage, color: T.sage }}>
            Semantic: {score.toFixed(4)}
          </span>
          {hit.novelty_score != null && (
            <span className="mono-tag" style={{ borderColor: T.brass, color: T.brass }}>
              GNN Novelty: {hit.novelty_score.toFixed(4)}
            </span>
          )}
          {hit.combined_score != null && (
            <span className="mono-tag" style={{ borderColor: T.inkSoft, color: T.inkSoft }}>
              Combined: {hit.combined_score.toFixed(4)}
            </span>
          )}
        </div>
      )}
    </motion.div>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────
export default function RetrievalResultsPage() {
  const navigate = useNavigate()
  const { pipelineResult } = usePipelineStore()
  const [sortMode, setSortMode] = useState<'faiss' | 'gnn'>('faiss')

  if (!pipelineResult) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 20, textAlign: 'center', padding: 24 }}>
        <FAISSIcon size={40} color={T.line} animate={false} />
        <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--ink)', fontSize: '1.3rem', fontWeight: 600 }}>No Results Yet</h2>
        <p style={{ color: 'var(--ink-soft)', fontSize: '0.9rem' }}>Run an analysis first to see patent results.</p>
        <Link to="/analyze" className="btn-primary" style={{ textDecoration: 'none', marginTop: 4 }}>Analyze an Idea →</Link>
      </div>
    )
  }

  const hits: RetrievalHit[] = pipelineResult.results ?? []
  const topHit = hits[0]
  const hasGNN = hits.some(h => h.novelty_score != null || h.combined_score != null)

  const sortedHits = [...hits].sort((a, b) => {
    if (sortMode === 'gnn') return (b.combined_score ?? b.semantic_score ?? 0) - (a.combined_score ?? a.semantic_score ?? 0)
    return (b.semantic_score ?? 0) - (a.semantic_score ?? 0)
  })

  return (
    <div style={{ maxWidth: 960, fontFamily: 'var(--font-body)' }}>

      {/* ─── Header ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} style={{ marginBottom: 20 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', fontWeight: 600, color: 'var(--ink)', marginBottom: 4 }}>
          Patent Retrieval Results
        </h1>
        <p className="caption">
          Top {hits.length} patents ranked by semantic similarity{hasGNN ? ' + GNN novelty scoring' : ''}
        </p>
      </motion.div>

      {/* ─── Slim stat row (1 row, not 4 heavy sheets) ─── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08, duration: 0.35 }}
        style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}
      >
        {[
          { label: 'Patents Indexed', value: '58,428' },
          { label: 'Top Match Score', value: topHit && topHit.semantic_score !== null ? topHit.semantic_score.toFixed(4) : '—' },
          { label: 'Results',         value: String(hits.length) },
        ].map(m => (
          <div key={m.label} style={{
            display: 'flex', gap: 8, alignItems: 'baseline',
            padding: '8px 14px',
            background: T.paperRaised, border: `1px solid ${T.line}`,
            borderRadius: 'var(--radius)', boxShadow: 'var(--shadow-sheet)',
          }}>
            <span style={{ fontFamily: 'var(--font-display)', fontStyle: 'italic', fontSize: '1.1rem', color: 'var(--ink)' }}>{m.value}</span>
            <span className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: '0.65rem' }}>{m.label}</span>
          </div>
        ))}
      </motion.div>

      {/* ─── Sort toggle ─── */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}
        style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}
      >
        <span className="caption">Sort by:</span>
        <div style={{ display: 'flex', background: T.paperRaised, border: `1px solid ${T.line}`, borderRadius: 'var(--radius)', overflow: 'hidden' }}>
          {[{ value: 'faiss', label: 'FAISS Order' }, { value: 'gnn', label: 'GNN Order' }].map(opt => {
            const active   = sortMode === opt.value
            const disabled = opt.value === 'gnn' && !hasGNN
            return (
              <button
                key={opt.value}
                id={`sort-${opt.value}`}
                onClick={() => setSortMode(opt.value as 'faiss' | 'gnn')}
                disabled={disabled}
                style={{
                  padding: '7px 14px', border: 'none',
                  background: active ? T.ink : 'transparent',
                  color: active ? T.paper : disabled ? T.line : T.inkSoft,
                  fontSize: '0.82rem', fontWeight: active ? 600 : 400,
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  transition: 'all 150ms', fontFamily: 'inherit',
                }}
              >
                {opt.label}{opt.value === 'gnn' && !hasGNN && <span style={{ fontSize: '0.65rem', marginLeft: 4 }}>(N/A)</span>}
              </button>
            )
          })}
        </div>
        {sortMode === 'gnn' && hasGNN && (
          <span className="mono-tag" style={{ borderColor: T.sage, color: T.sage }}>Re-ranked by GraphSAGE</span>
        )}
      </motion.div>

      {/* ─── Patent cards ─── */}
      {sortedHits.length === 0
        ? <div style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--ink-soft)', fontSize: '0.9rem' }}>No patents found for this query.</div>
        : sortedHits.map((hit, i) => <PatentCard key={hit.patent_id || i} hit={hit} idx={i} />)
      }

      {/* ─── CTA ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.38, duration: 0.35 }}
        className="sheet"
        style={{ marginTop: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, borderLeft: `2px solid ${T.indigo}` }}
      >
        <div>
          <p style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--ink)', marginBottom: 2 }}>Explore the Knowledge Graph</p>
          <p className="caption">Visualize patent relationships and concept clusters in Neo4j</p>
        </div>
        <button onClick={() => navigate('/results/graph')} className="btn-primary" style={{ padding: '10px 24px' }}>
          Explore Knowledge Graph →
        </button>
      </motion.div>
    </div>
  )
}
