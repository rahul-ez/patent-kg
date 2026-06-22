import { useMemo, useRef } from 'react'
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
import { Link } from 'react-router-dom'

// ── Score color — semantic palette ────────────────────────────────────────
function scoreColor(val: number): string {
  if (val >= 0.6) return 'var(--accent-sage)'
  if (val >= 0.4) return 'var(--accent-brass)'
  return 'var(--text-secondary)'
}

function ScoreCell({ value }: { value: number }) {
  return (
    <span style={{ color: scoreColor(value), fontWeight: 600 }}>
      {value.toFixed(4)}
    </span>
  )
}

// ── Delta glyph — mono signed numbers ─────────────────────────────────────
function DeltaGlyph({ delta }: { delta: number }) {
  if (delta > 0) return (
    <span className="rank-up" style={{ color: 'var(--accent-sage)' }}>
      ↑+{delta}
    </span>
  )
  if (delta < 0) return (
    <span className="rank-down" style={{ color: 'var(--accent-clay)' }}>
      ↓−{Math.abs(delta)}
    </span>
  )
  return <span className="rank-same" style={{ color: 'var(--text-tertiary)' }}>—</span>
}

// ── Recharts custom tooltip ───────────────────────────────────────────────
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-card)', border: `1px solid var(--border-hairline)`,
      borderRadius: 'var(--radius-card)', padding: '10px 14px', fontSize: '13px',
      boxShadow: 'var(--shadow-l2)',
    }}>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 6, fontFamily: 'var(--font-mono)' }}>ID: {label}</p>
      {payload.map((p: any) => (
        <div key={p.name} style={{ display: 'flex', gap: 8, marginBottom: 3 }}>
          <span style={{ color: 'var(--text-secondary)' }}>{p.name}:</span>
          <span style={{ color: p.fill, fontWeight: 700 }}>{Number(p.value).toFixed(4)}</span>
        </div>
      ))}
    </div>
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

  const chartData = useMemo(() =>
    rerankedHits.slice(0, 10).map((h) => ({
      id:       h.patent_id.slice(-8),
      Semantic: +(h.semantic_score ?? 0).toFixed(4),
      GNN:      +h.novelty_score.toFixed(4),
      Combined: +h.combined_score.toFixed(4),
    })),
  [rerankedHits])

  const biggestBoost = useMemo(() => {
    if (!rerankedHits.length) return null
    return rerankedHits.reduce((prev, cur) => cur.delta > prev.delta ? cur : prev, rerankedHits[0])
  }, [rerankedHits])

  const avgDelta = useMemo(() => {
    if (!rerankedHits.length) return '0.0'
    const total = rerankedHits.reduce((sum, h) => sum + Math.abs(h.delta), 0)
    return (total / rerankedHits.length).toFixed(1)
  }, [rerankedHits])

  if (!pipelineResult) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 20, textAlign: 'center', padding: 24 }}>
        <GNNIcon size={40} color={T.borderHairline} animate={false} />
        <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600 }}>No Case File Selected</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Please submit an innovation idea first to run GNN analysis.</p>
        <Link to="/analyze" className="btn-primary" style={{ textDecoration: 'none', marginTop: 4 }}>New Analysis →</Link>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 960, fontFamily: 'var(--font-body)' }}>

      {/* ─── Page Title Block ─── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
        style={{ marginBottom: 16 }}
      >
        <p className="caption" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>
          §04 — GRAPH-BASED RE-RANKING
        </p>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '44px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
          GNN Intelligence Layer
        </h1>
      </motion.div>

      {/* ─── Metadata Strip ─── */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.05 }}
        style={{
          height: 44,
          background: 'transparent',
          borderBottom: '1px solid var(--border-hairline)',
          display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
          padding: '0 0 12px 0',
          marginBottom: 40,
        }}
      >
        {/* Left cluster */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          {/* GNN Mode */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>GNN MODE</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>
              {activeMode === 'novelty' ? 'Novelty Scoring' : 'Graph Similarity'}
            </span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Patents Reranked */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>PATENTS RERANKED</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>{rerankedHits.length}</span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Avg Delta */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>AVG. DELTA</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>±{avgDelta} positions</span>
          </div>
        </div>

        {/* Right side: Ref number */}
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)', letterSpacing: '0.06em' }}>
          REF. {refNum.current}
        </div>
      </motion.div>

      {/* ─── Anchor Card (§1 Biggest GNN Boost) ─── */}
      {biggestBoost && biggestBoost.delta > 0 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.35 }}
          className="sheet-primary" style={{ marginBottom: 32 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <NoveltyIcon size={18} color={T.accentBrass} animate={false} />
            <h2 className="section-header" style={{ margin: 0 }}>
              <span className="section-clause-num">§1</span>Biggest GNN Boost
            </h2>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '15px', lineHeight: 1.7, margin: 0 }}>
            <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{biggestBoost.title}</strong>{' '}
            jumped{' '}
            <strong style={{ color: 'var(--accent-sage)', fontWeight: 700 }}>+{biggestBoost.delta} positions</strong>{' '}
            from FAISS rank #{biggestBoost.faiss_rank} to GNN rank #{biggestBoost.gnn_rank}.{' '}
            {biggestBoost.gnn_mode === 'novelty'
              ? 'Its high novelty score indicates structural uniqueness in the patent citation graph — GraphSAGE identified it as semantically similar but structurally distinct from the patent cluster centroid.'
              : 'Graph similarity analysis revealed strong structural connections to highly-cited patents, elevating its importance beyond raw semantic embedding similarity.'
            }
          </p>
        </motion.div>
      )}

      {/* ─── Sliders & Validation (§2 Scoring Weights) ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
        className="sheet-secondary" style={{ marginBottom: 32 }}
      >
        <h2 className="section-header" style={{ marginBottom: 16 }}>
          <span className="section-clause-num">§2</span>Scoring Weights
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 24, marginBottom: 16 }}>
          {/* Semantic Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <label style={{ fontSize: '13px', color: 'var(--accent-sage)', fontWeight: 600 }}>Semantic Weight (FAISS)</label>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)', fontWeight: 700 }}>
                {(gnnWeights.semantic * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range" min={0} max={1} step={0.05}
              value={gnnWeights.semantic}
              onChange={(e) => setGNNWeights({ ...gnnWeights, semantic: +e.target.value })}
              style={{ width: '100%', accentColor: T.accentSage, cursor: 'pointer' }}
            />
          </div>

          {/* GNN Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <label style={{ fontSize: '13px', color: 'var(--accent-brass)', fontWeight: 600 }}>GNN Weight (Novelty)</label>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)', fontWeight: 700 }}>
                {(gnnWeights.gnn * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range" min={0} max={1} step={0.05}
              value={gnnWeights.gnn}
              onChange={(e) => setGNNWeights({ ...gnnWeights, gnn: +e.target.value })}
              style={{ width: '100%', accentColor: T.accentBrass, cursor: 'pointer' }}
            />
          </div>
        </div>

        {/* Validation Status */}
        <div style={{ display: 'inline-block' }}>
          <span className="mono-tag" style={{ borderColor: sumOk ? 'var(--accent-sage)' : 'var(--accent-clay)', color: sumOk ? 'var(--accent-sage)' : 'var(--accent-clay)' }}>
            {sumOk
              ? `✓ ${Math.round(gnnWeights.semantic * 100)}% SEMANTIC + ${Math.round(gnnWeights.gnn * 100)}% GNN = 1.0`
              : `⚠ WEIGHTS SUM TO ${weightSum.toFixed(2)} (NOT 1.0)`
            }
          </span>
        </div>
      </motion.div>

      {/* No GNN Notice */}
      {!hasGNN && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="sheet-secondary" style={{ marginBottom: 32, borderLeft: `3px solid var(--accent-brass)` }}
        >
          <p style={{ color: 'var(--text-primary)', fontWeight: 600, marginBottom: 6 }}>GNN Scoring Unavailable</p>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13.5px', lineHeight: 1.65 }}>
            GNN scoring is unavailable — missing embeddings or novelty maps in the backend vector store. Live inference will default to FAISS semantic scores.
          </p>
        </motion.div>
      )}

      {/* ─── Score Distribution Chart (§3 Score Distribution) ─── */}
      {hasGNN && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="sheet-secondary" style={{ marginBottom: 32 }}
        >
          <h2 className="section-header" style={{ marginBottom: 16 }}>
            <span className="section-clause-num">§3</span>Score Distribution
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: 20 }}>
            Comparison of raw Semantic Similarity, GNN Novelty, and combined re-weighted scores across top retrieved candidates.
          </p>
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 4, right: 12, bottom: 20, left: -24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={T.borderHairline} vertical={false} />
                <XAxis
                  dataKey="id"
                  tick={{ fill: T.textSecondary, fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  interval={0}
                />
                <YAxis tick={{ fill: T.textSecondary, fontSize: 11, fontFamily: 'var(--font-mono)' }} domain={[0, 1]} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ color: T.textSecondary, fontSize: '12px', paddingTop: 10 }} />
                <Bar dataKey="Semantic" fill={T.accentSage}    radius={[2, 2, 0, 0]} maxBarSize={16} stroke={T.borderHairline} strokeWidth={0.5} />
                <Bar dataKey="GNN"      fill={T.accentBrass}   radius={[2, 2, 0, 0]} maxBarSize={16} stroke={T.borderHairline} strokeWidth={0.5} />
                <Bar dataKey="Combined" fill={T.textSecondary} radius={[2, 2, 0, 0]} maxBarSize={16} stroke={T.borderHairline} strokeWidth={0.5} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      )}

      {/* ─── Re-ranking Table (§4 Re-ranking Table) ─── */}
      {hasGNN && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
          style={{ marginBottom: 40 }}
        >
          <h2 className="section-header" style={{ marginBottom: 16 }}>
            <span className="section-clause-num">§4</span>Re-ranking Table
          </h2>
          
          <div className="sheet-technical" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: '13px', textAlign: 'right' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-hairline)', background: 'rgba(35, 39, 31, 0.03)' }}>
                    <th style={{ padding: '12px 14px', fontSize: '10.5px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', textAlign: 'center', width: 60 }}>Rank</th>
                    <th style={{ padding: '12px 14px', fontSize: '10.5px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', textAlign: 'left' }}>Patent Candidates</th>
                    <th style={{ padding: '12px 14px', fontSize: '10.5px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', width: 90 }}>Semantic</th>
                    <th style={{ padding: '12px 14px', fontSize: '10.5px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', width: 90 }}>GNN</th>
                    <th style={{ padding: '12px 14px', fontSize: '10.5px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', width: 90 }}>Combined</th>
                    <th style={{ padding: '12px 14px', fontSize: '10.5px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', width: 80, textAlign: 'center' }}>Δ Rank</th>
                  </tr>
                </thead>
                <tbody>
                  {rerankedHits.map((hit, idx) => (
                    <tr
                      key={hit.patent_id}
                      style={{
                        borderBottom: idx === rerankedHits.length - 1 ? 'none' : '1px solid var(--border-hairline)',
                        background: 'transparent',
                        transition: 'background 120ms',
                      }}
                    >
                      <td style={{ padding: '12px 14px', textAlign: 'center', fontWeight: 700, color: 'var(--accent-sage)' }}>#{hit.gnn_rank}</td>
                      <td style={{ padding: '12px 14px', textAlign: 'left', fontFamily: 'var(--font-body)' }}>
                        <a href={hit.url} target="_blank" rel="noopener noreferrer"
                          style={{
                            color: 'var(--text-primary)', fontWeight: 600, textDecoration: 'none',
                            display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical',
                            overflow: 'hidden', lineHeight: 1.4, fontSize: '14px',
                          }}>
                          {hit.title}
                        </a>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)' }}>{hit.patent_id}</span>
                      </td>
                      <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)' }}><ScoreCell value={hit.semantic_score ?? 0} /></td>
                      <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)' }}><ScoreCell value={hit.novelty_score} /></td>
                      <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)' }}><ScoreCell value={hit.combined_score} /></td>
                      <td style={{ padding: '12px 14px', textAlign: 'center', fontFamily: 'var(--font-mono)' }}><DeltaGlyph delta={hit.delta} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
