import { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { motion } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { useGNNRerank } from '../hooks/useGNNRerank'
import type { RankedHit } from '../types/gnn'
import { GNNIcon, NoveltyIcon } from '../assets/PatentIcons'
import { T } from '../theme'

// ── Score color — semantic palette ────────────────────────────────────────
function scoreColor(val: number): string {
  if (val >= 0.6) return T.sage
  if (val >= 0.4) return T.brass
  return T.inkSoft
}

function ScoreCell({ value }: { value: number }) {
  return (
    <span style={{ color: scoreColor(value), fontFamily: 'var(--font-mono)', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
      {value.toFixed(3)}
    </span>
  )
}

// ── Delta glyph — line-drawn arrows ───────────────────────────────────────
function DeltaGlyph({ delta }: { delta: number }) {
  if (delta > 0) return (
    <span className="rank-up" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
      ↑+{delta}
    </span>
  )
  if (delta < 0) return (
    <span className="rank-down" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
      ↓{Math.abs(delta)}
    </span>
  )
  return <span className="rank-same" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>—</span>
}

// ── Recharts custom tooltip ───────────────────────────────────────────────
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: T.paperRaised, border: `1px solid ${T.line}`,
      borderRadius: 'var(--radius)', padding: '10px 14px', fontSize: '0.78rem',
      boxShadow: 'var(--shadow-sheet)',
    }}>
      <p style={{ color: T.inkSoft, marginBottom: 6, fontFamily: 'var(--font-mono)' }}>{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} style={{ display: 'flex', gap: 8, marginBottom: 3 }}>
          <span style={{ color: T.inkSoft }}>{p.name}:</span>
          <span style={{ color: p.fill, fontWeight: 700 }}>{Number(p.value).toFixed(4)}</span>
        </div>
      ))}
    </div>
  )
}

// ── GNN mode badge — mono bordered tag ────────────────────────────────────
function ModeBadge({ mode }: { mode: string }) {
  const isNovelty = mode === 'novelty'
  return (
    <span className="mono-tag" style={{ borderColor: isNovelty ? T.brass : T.sage, color: isNovelty ? T.brass : T.sage }}>
      {isNovelty ? 'Novelty Score' : 'Graph Similarity'}
    </span>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function GNNAnalysisPage() {
  const gnnWeights    = usePipelineStore((s) => s.gnnWeights)
  const setGNNWeights = usePipelineStore((s) => s.setGNNWeights)
  const pipelineResult = usePipelineStore((s) => s.pipelineResult)

  const rerankedHits: RankedHit[] = useGNNRerank()

  const hasGNN     = rerankedHits.length > 0
  const activeMode = rerankedHits[0]?.gnn_mode ?? 'novelty'
  const weightSum  = +(gnnWeights.semantic + gnnWeights.gnn).toFixed(4)
  const sumOk      = Math.abs(weightSum - 1.0) < 0.01

  const chartData = useMemo(() =>
    rerankedHits.slice(0, 12).map((h) => ({
      id:       h.patent_id.slice(-15),
      Semantic: +(h.semantic_score ?? 0).toFixed(4),
      GNN:      +h.novelty_score.toFixed(4),
      Combined: +h.combined_score.toFixed(4),
    })),
  [rerankedHits])

  const biggestBoost = useMemo(() => {
    if (!rerankedHits.length) return null
    return rerankedHits.reduce((prev, cur) => cur.delta > prev.delta ? cur : prev, rerankedHits[0])
  }, [rerankedHits])

  if (!pipelineResult) {
    return (
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 0' }}>
        <div className="sheet" style={{ padding: 48, textAlign: 'center' }}>
          <GNNIcon size={40} color={T.line} animate={false} />
          <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--ink)', fontWeight: 600, marginBottom: 8, marginTop: 16 }}>No Analysis Yet</h2>
          <p style={{ color: 'var(--ink-soft)' }}>Run a patent analysis to see GNN re-ranking results.</p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22 }}
      >
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', fontWeight: 600, color: 'var(--ink)' }}>
          GNN Intelligence Layer
        </h1>
        {hasGNN && <ModeBadge mode={activeMode} />}
      </motion.div>

      {/* Scoring weights panel */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
        className="sheet" style={{ marginBottom: 20 }}
      >
        <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>Scoring Weights</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>

          {/* Semantic slider — sage accent */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <label style={{ fontSize: '0.82rem', color: T.sage, fontWeight: 500 }}>Semantic Weight (FAISS)</label>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--ink)', fontWeight: 700 }}>
                {(gnnWeights.semantic * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range" min={0} max={1} step={0.05}
              value={gnnWeights.semantic}
              onChange={(e) => setGNNWeights({ ...gnnWeights, semantic: +e.target.value })}
              style={{ width: '100%', accentColor: T.sage, cursor: 'pointer' }}
            />
          </div>

          {/* GNN slider — brass accent */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <label style={{ fontSize: '0.82rem', color: T.brass, fontWeight: 500 }}>GNN Weight (Novelty)</label>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--ink)', fontWeight: 700 }}>
                {(gnnWeights.gnn * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range" min={0} max={1} step={0.05}
              value={gnnWeights.gnn}
              onChange={(e) => setGNNWeights({ ...gnnWeights, gnn: +e.target.value })}
              style={{ width: '100%', accentColor: T.brass, cursor: 'pointer' }}
            />
          </div>
        </div>

        {/* Weight sum indicator */}
        <div style={{ marginTop: 14 }}>
          <span className="mono-tag" style={{ borderColor: sumOk ? T.sage : T.clay, color: sumOk ? T.sage : T.clay }}>
            {sumOk
              ? `✓ ${Math.round(gnnWeights.semantic * 100)}% semantic + ${Math.round(gnnWeights.gnn * 100)}% GNN = 1.0`
              : `⚠ Weights sum to ${weightSum.toFixed(2)} (not 1.0)`
            }
          </span>
        </div>
      </motion.div>

      {/* No GNN notice */}
      {!hasGNN && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="sheet" style={{ marginBottom: 20, borderLeft: `2px solid ${T.brass}` }}
        >
          <p style={{ color: 'var(--ink)', fontWeight: 600, marginBottom: 6 }}>GNN Scoring Unavailable</p>
          <p style={{ color: 'var(--ink-soft)', fontSize: '0.87rem', lineHeight: 1.7 }}>
            GNN scoring is unavailable — missing{' '}
            <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--paper)', padding: '1px 5px', borderRadius: 'var(--radius)', color: T.sage }}>novelty_scores.json</code>
            {' '}or{' '}
            <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--paper)', padding: '1px 5px', borderRadius: 'var(--radius)', color: T.sage }}>node_embeddings.npy</code>
            {' '}in{' '}
            <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--paper)', padding: '1px 5px', borderRadius: 'var(--radius)', color: T.sage }}>backend/data/vector_store/</code>.
            Run the Colab training notebook to generate these files.
          </p>
        </motion.div>
      )}

      {/* Score distribution chart — sage/brass/ink flat fills, no gradients */}
      {hasGNN && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="sheet" style={{ marginBottom: 20 }}
        >
          <p style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--ink-soft)', marginBottom: 14 }}>
            Score Distribution Across Top Patents
          </p>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData} margin={{ top: 4, right: 12, bottom: 40, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={T.line} />
              <XAxis
                dataKey="id"
                tick={{ fill: T.inkSoft, fontSize: 10, fontFamily: 'var(--font-mono)' }}
                angle={-35} textAnchor="end" interval={0}
              />
              <YAxis tick={{ fill: T.inkSoft, fontSize: 11 }} domain={[0, 1]} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ color: T.inkSoft, fontSize: '0.78rem', paddingTop: 8 }} />
              {/* Flat fills from T.* constants — no gradients */}
              <Bar dataKey="Semantic" fill={T.sage}    radius={[3, 3, 0, 0]} maxBarSize={18} stroke={T.line} strokeWidth={0.5} />
              <Bar dataKey="GNN"      fill={T.brass}   radius={[3, 3, 0, 0]} maxBarSize={18} stroke={T.line} strokeWidth={0.5} />
              <Bar dataKey="Combined" fill={T.inkSoft} radius={[3, 3, 0, 0]} maxBarSize={18} stroke={T.line} strokeWidth={0.5} />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {/* Re-ranking table */}
      {hasGNN && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.14 }} style={{ marginBottom: 22 }}>
          {/* Table header */}
          <div style={{
            display: 'grid', gridTemplateColumns: '48px 1fr 88px 88px 88px 64px',
            background: T.paperRaised, borderRadius: 'var(--radius) var(--radius) 0 0',
            padding: '9px 14px',
            border: `1px solid ${T.line}`, borderBottom: 'none',
          }}>
            {['Rank', 'Patent', 'Semantic', 'GNN', 'Combined', 'Δ Rank'].map(h => (
              <span key={h} className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', textAlign: h === 'Patent' ? 'left' : 'right' }}>
                {h}
              </span>
            ))}
          </div>

          {rerankedHits.map((hit, idx) => (
            <motion.div
              key={hit.patent_id}
              initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.02 * idx }}
              style={{
                display: 'grid', gridTemplateColumns: '48px 1fr 88px 88px 88px 64px',
                padding: '11px 14px', fontSize: '0.82rem', alignItems: 'center',
                borderBottom: `1px solid ${T.line}`,
                border: `1px solid ${T.line}`,
                borderTop: 'none',
                background: idx % 2 === 0 ? T.paper : T.paperRaised,
                transition: 'background 120ms',
              }}
            >
              <span style={{ fontFamily: 'var(--font-mono)', color: T.sage, fontWeight: 700 }}>#{hit.gnn_rank}</span>

              <div style={{ overflow: 'hidden' }}>
                <a href={hit.url} target="_blank" rel="noopener noreferrer"
                  style={{
                    color: 'var(--ink)', fontWeight: 500, textDecoration: 'none',
                    display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                    overflow: 'hidden', lineHeight: 1.4, marginBottom: 2,
                  }}>
                  {hit.title}
                </a>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: T.inkSoft }}>{hit.patent_id}</span>
              </div>

              <div style={{ textAlign: 'right' }}><ScoreCell value={hit.semantic_score ?? 0} /></div>
              <div style={{ textAlign: 'right' }}><ScoreCell value={hit.novelty_score} /></div>
              <div style={{ textAlign: 'right' }}><ScoreCell value={hit.combined_score} /></div>
              <div style={{ textAlign: 'right' }}><DeltaGlyph delta={hit.delta} /></div>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Biggest boost callout */}
      {biggestBoost && biggestBoost.delta > 0 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="sheet" style={{ borderLeft: `2px solid ${T.brass}` }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <NoveltyIcon size={16} color={T.brass} animate={false} />
            <p style={{ color: 'var(--ink)', fontWeight: 700, fontSize: '0.93rem' }}>Biggest GNN Boost</p>
          </div>
          <p style={{ color: 'var(--ink-soft)', fontSize: '0.87rem', lineHeight: 1.7 }}>
            <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{biggestBoost.title}</span>{' '}
            jumped{' '}
            <span style={{ color: T.sage, fontWeight: 700 }}>+{biggestBoost.delta} positions</span>{' '}
            from FAISS rank #{biggestBoost.faiss_rank} to GNN rank #{biggestBoost.gnn_rank}.{' '}
            {biggestBoost.gnn_mode === 'novelty'
              ? 'Its high novelty score indicates structural uniqueness in the patent citation graph — GraphSAGE identified it as semantically similar but structurally distinct from the patent cluster centroid.'
              : 'Graph similarity analysis revealed strong structural connections to highly-cited patents, elevating its importance beyond raw semantic embedding similarity.'
            }
          </p>
        </motion.div>
      )}
    </div>
  )
}
