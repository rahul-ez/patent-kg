import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { usePipeline } from '../hooks/usePipeline'
import { usePipelineStore } from '../store/usePipelineStore'
import { PatentDocIcon } from '../assets/PatentIcons'
import { T } from '../theme'

const EXAMPLES = [
  'EEG seizure detection wearable with real-time neural signal processing and adaptive threshold calibration',
  'Autonomous drone navigation with LiDAR-based obstacle avoidance and swarm coordination protocols',
  'Federated learning framework for medical imaging with differential privacy and cross-silo aggregation',
  'Solid-state lithium battery electrolyte using sulfide-based composite for ultra-fast charging',
  'AI smart grid energy optimization using reinforcement learning for dynamic load balancing',
]

const TOP_K_OPTIONS = [5, 10, 25, 50, 100]

export default function IdeaInputPage() {
  const navigate = useNavigate()
  const { idea: storeIdea, topK, gnnMode, setIdea: setStoreIdea, setTopK, setGNNMode } = usePipelineStore()
  const [idea, setIdea] = useState(storeIdea || '')
  const [localTopK, setLocalTopK] = useState(topK)
  const [localGNNMode, setLocalGNNMode] = useState(gnnMode)
  const [isFocused, setIsFocused] = useState(false)
  const mutation = usePipeline()

  useEffect(() => { setStoreIdea(idea) }, [idea, setStoreIdea])

  const handleSubmit = () => {
    if (!idea.trim() || mutation.isPending) return
    setTopK(localTopK)
    setGNNMode(localGNNMode)
    mutation.mutate({ idea: idea.trim(), top_k: localTopK, gnn_mode: localGNNMode })
  }

  const isDisabled = !idea.trim() || mutation.isPending

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-page)', fontFamily: 'var(--font-body)' }}>
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 0 60px' }}>

        {/* Back Link */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }} style={{ marginBottom: 24 }}>
          <Link
            to="/"
            style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: 6, transition: 'color 120ms' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
          >
            ← Back to Desk
          </Link>
        </motion.div>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }} style={{ marginBottom: 32 }}>
          <p className="caption" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>
            §00 — CASE INTAKE
          </p>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '44px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 10 }}>
            New Analysis
          </h1>
        </motion.div>

        {/* Two-Column Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 32, alignItems: 'flex-start' }}>

          {/* ── LEFT: Case Intake Input ── */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 0 }}
          >
            {/* Textarea Wrapper for elevation feedback */}
            <div style={{
              background: 'var(--bg-card)',
              border: isFocused ? '1.5px solid var(--border-anchor)' : '1px solid var(--border-hairline)',
              borderRadius: 'var(--radius-card)',
              boxShadow: isFocused ? 'var(--shadow-l3), var(--shadow-l3-highlight)' : 'var(--shadow-l2)',
              transition: 'border-color 150ms, box-shadow 150ms',
              padding: 16,
              marginBottom: 16,
            }}>
              <textarea
                id="idea-input"
                value={idea}
                onChange={e => setIdea(e.target.value)}
                maxLength={2000}
                placeholder="Describe your invention idea in plain English to open a new examination case file…"
                style={{
                  width: '100%', minHeight: 180,
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-primary)',
                  fontSize: '16px',
                  resize: 'vertical',
                  outline: 'none',
                  fontFamily: 'var(--font-body)',
                  lineHeight: 1.65,
                  padding: 0,
                  boxSizing: 'border-box',
                }}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
              />
              <div style={{ color: idea.length > 1800 ? T.accentClay : T.textTertiary, fontFamily: 'var(--font-mono)', fontSize: '10.5px', textAlign: 'right', marginTop: 8 }}>
                {idea.length} / 2000
              </div>
            </div>

            {/* Compact Control Strip */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              background: 'var(--bg-structural)',
              border: '1px solid var(--border-hairline)',
              borderRadius: 'var(--radius-card)',
              marginBottom: 20,
              gap: 24,
            }}>
              {/* Top-K Select */}
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className="caption" style={{ color: 'var(--text-secondary)', flexShrink: 0 }}>
                  RESULTS:
                </span>
                <select
                  id="top-k-select"
                  value={localTopK}
                  onChange={e => setLocalTopK(Number(e.target.value))}
                  style={{
                    background: 'var(--bg-card)',
                    border: `1px solid var(--border-hairline)`,
                    borderRadius: 'var(--radius-control)',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                    padding: '6px 10px',
                    outline: 'none',
                    cursor: 'pointer',
                    fontFamily: 'var(--font-body)',
                  }}
                >
                  {TOP_K_OPTIONS.map(k => (
                    <option key={k} value={k}>Top {k}</option>
                  ))}
                </select>
              </div>

              {/* Segmented GNN Control */}
              <div style={{ flex: 2, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 12 }}>
                <span className="caption" style={{ color: 'var(--text-secondary)', flexShrink: 0 }}>
                  GNN MODE:
                </span>
                <div style={{
                  display: 'flex',
                  background: 'var(--bg-structural)',
                  border: `1px solid var(--border-hairline)`,
                  borderRadius: 'var(--radius-control)',
                  overflow: 'hidden',
                }}>
                  {[
                    { value: 'novelty',    label: 'Novelty'   },
                    { value: 'similarity', label: 'Similarity' },
                  ].map(opt => {
                    const active = localGNNMode === opt.value
                    return (
                      <button
                        key={opt.value}
                        id={`gnn-mode-${opt.value}`}
                        onClick={() => setLocalGNNMode(opt.value)}
                        style={{
                          padding: '6px 12px',
                          border: 'none',
                          background: active ? 'var(--surface-ink)' : 'transparent',
                          color: active ? 'var(--text-on-dark)' : 'var(--text-secondary)',
                          fontSize: '11.5px',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 600,
                          cursor: 'pointer',
                          transition: 'background 120ms, color 120ms',
                        }}
                      >
                        {opt.label.toUpperCase()}
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <button
              id="submit-idea"
              onClick={handleSubmit}
              disabled={isDisabled}
              className="btn-primary"
              style={{
                width: '100%', height: 48,
                fontSize: '14px',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              }}
            >
              {mutation.isPending ? 'Intaking Case File...' : 'Open Case File & Run Analysis →'}
            </button>

            {/* Error Message */}
            {mutation.error && (
              <motion.div
                initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                className="sheet-technical"
                style={{ borderLeftColor: T.accentClay, color: T.accentClay, marginTop: 14 }}
              >
                <div style={{ fontWeight: 600, marginBottom: 4, fontSize: '11px', fontFamily: 'var(--font-mono)' }}>ERROR INTAKE</div>
                <div style={{ fontFamily: 'var(--font-body)', fontSize: '13px' }}>
                  {mutation.error instanceof Error ? mutation.error.message : 'An unexpected pipeline error occurred.'}
                </div>
              </motion.div>
            )}
          </motion.div>

          {/* ── RIGHT: Examples Sidebar Card ── */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.32 }}
            className="sheet-secondary"
            style={{ padding: 20 }}
          >
            <h2 className="section-header" style={{ fontSize: '16px', marginBottom: 12 }}>
              <span className="section-clause-num">§1</span>Example Filings
            </h2>

            {/* Plain List Rows (No Card Chrome, background tint hover) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {EXAMPLES.map((ex, i) => {
                const active = idea === ex
                return (
                  <button
                    key={i}
                    onClick={() => setIdea(ex)}
                    style={{
                      background: active ? 'var(--bg-hover-tint)' : 'transparent',
                      border: 'none',
                      borderRadius: 'var(--radius-control)',
                      padding: '10px 12px',
                      textAlign: 'left',
                      color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                      fontSize: '13px',
                      cursor: 'pointer',
                      width: '100%',
                      lineHeight: 1.45,
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 8,
                      transition: 'background-color 120ms, color 120ms',
                      fontFamily: 'var(--font-body)',
                    }}
                    onMouseEnter={e => {
                      if (!active) e.currentTarget.style.background = 'var(--bg-hover-tint)'
                    }}
                    onMouseLeave={e => {
                      if (!active) e.currentTarget.style.background = 'transparent'
                    }}
                  >
                    <PatentDocIcon size={14} color={active ? T.accentSage : T.textTertiary} animate={false} style={{ flexShrink: 0, marginTop: 2 } as React.SVGProps<SVGSVGElement>} />
                    <span style={{
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>{ex}</span>
                  </button>
                )
              })}
            </div>

            {/* Intaking Guidelines Panel */}
            <div className="sheet-technical" style={{ borderLeftColor: T.accentSage, padding: '12px 14px', marginTop: 16 }}>
              <div className="caption" style={{ color: T.accentSage, marginBottom: 4 }}>INTAKE GUIDELINES</div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '12px', lineHeight: 1.5, fontFamily: 'var(--font-body)' }}>
                Provide technical mechanisms, algorithms, and application contexts. Vague inputs increase semantic retrieval overlap warnings.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
