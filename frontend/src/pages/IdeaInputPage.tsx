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
  'Solid-state lithium battery electrolyte using sulfide-based ceramic composite for ultra-fast charging',
  'AI smart grid energy optimization using reinforcement learning for dynamic load balancing',
]

const TOP_K_OPTIONS = [5, 10, 25, 50, 100]

export default function IdeaInputPage() {
  const navigate = useNavigate()
  const { idea: storeIdea, topK, gnnMode, setIdea: setStoreIdea, setTopK, setGNNMode } = usePipelineStore()
  const [idea, setIdea] = useState(storeIdea || '')
  const [localTopK, setLocalTopK] = useState(topK)
  const [localGNNMode, setLocalGNNMode] = useState(gnnMode)
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
    <div style={{ minHeight: '100vh', background: 'var(--paper)', fontFamily: 'var(--font-body)' }}>
      <div style={{ maxWidth: 880, margin: '0 auto', padding: '32px 24px 60px', position: 'relative', zIndex: 1 }}>

        {/* Back link */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }} style={{ marginBottom: 36 }}>
          <Link
            to="/"
            style={{ color: 'var(--ink-soft)', textDecoration: 'none', fontSize: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: 6, transition: 'color 120ms' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--ink)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-soft)')}
          >
            ← Back
          </Link>
        </motion.div>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }} style={{ marginBottom: 32 }}>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 600, color: 'var(--ink)', marginBottom: 10 }}>
            Describe Your Innovation
          </h1>
          <p style={{ color: 'var(--ink-soft)', fontSize: '1rem', lineHeight: 1.65, maxWidth: 520 }}>
            Our AI pipeline will analyze prior art, extract knowledge graphs, and evaluate your
            idea's novelty against 58,000+ patents.
          </p>
        </motion.div>

        {/* Split layout */}
        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>

          {/* ── LEFT: Input ── */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
            style={{ flex: '2 1 360px', minWidth: 0 }}
          >
            {/* Textarea — document field styling */}
            <textarea
              id="idea-input"
              value={idea}
              onChange={e => setIdea(e.target.value)}
              maxLength={2000}
              placeholder="Describe your invention idea in plain English…"
              style={{
                width: '100%', minHeight: 190,
                background: 'var(--paper-raised)',
                border: `1px solid ${idea.length > 0 ? T.ink : T.line}`,
                borderRadius: 'var(--radius)',
                color: 'var(--ink)',
                fontSize: '0.95rem',
                padding: 16,
                resize: 'vertical',
                outline: 'none',
                fontFamily: 'var(--font-body)',
                lineHeight: 1.65,
                boxSizing: 'border-box',
                transition: 'border-color 120ms',
              }}
              onFocus={e => { e.currentTarget.style.borderColor = T.ink }}
              onBlur={e => { e.currentTarget.style.borderColor = idea.length > 0 ? T.ink : T.line }}
            />
            <div style={{ color: idea.length > 1800 ? T.clay : T.inkSoft, fontFamily: 'var(--font-mono)', fontSize: '0.72rem', textAlign: 'right', marginBottom: 20 }}>
              {idea.length} / 2000
            </div>

            {/* Controls row */}
            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', marginBottom: 20, flexWrap: 'wrap' }}>

              {/* Top-K select */}
              <div style={{ flex: 1, minWidth: 110 }}>
                <label className="caption" style={{ display: 'block', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                  Results
                </label>
                <select
                  id="top-k-select"
                  value={localTopK}
                  onChange={e => setLocalTopK(Number(e.target.value))}
                  style={{
                    width: '100%',
                    background: 'var(--paper-raised)',
                    border: `1px solid ${T.line}`,
                    borderRadius: 'var(--radius)',
                    color: 'var(--ink)',
                    fontSize: '0.9rem',
                    padding: '9px 12px',
                    outline: 'none',
                    cursor: 'pointer',
                    fontFamily: 'var(--font-body)',
                    transition: 'border-color 120ms',
                  }}
                  onFocus={e => (e.currentTarget.style.borderColor = T.ink)}
                  onBlur={e => (e.currentTarget.style.borderColor = T.line)}
                >
                  {TOP_K_OPTIONS.map(k => (
                    <option key={k} value={k} style={{ background: T.paperRaised }}>Top {k}</option>
                  ))}
                </select>
              </div>

              {/* GNN mode toggle — sharp segmented control */}
              <div style={{ flex: 2, minWidth: 220 }}>
                <label className="caption" style={{ display: 'block', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                  GNN Mode
                </label>
                <div style={{
                  display: 'flex',
                  background: 'var(--paper-raised)',
                  border: `1px solid ${T.line}`,
                  borderRadius: 'var(--radius)',
                  overflow: 'hidden',
                }}>
                  {[
                    { value: 'novelty',    label: 'Novelty Score'   },
                    { value: 'similarity', label: 'Graph Similarity' },
                  ].map(opt => {
                    const active = localGNNMode === opt.value
                    return (
                      <button
                        key={opt.value}
                        id={`gnn-mode-${opt.value}`}
                        onClick={() => setLocalGNNMode(opt.value)}
                        style={{
                          flex: 1, padding: '9px 8px',
                          border: 'none',
                          background: active ? T.ink : 'transparent',
                          color: active ? T.paper : T.inkSoft,
                          fontSize: '0.82rem',
                          fontWeight: active ? 600 : 400,
                          cursor: 'pointer',
                          transition: 'background 150ms, color 150ms',
                          fontFamily: 'var(--font-body)',
                        }}
                      >
                        {opt.label}
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* Submit button */}
            <button
              id="submit-idea"
              onClick={handleSubmit}
              disabled={isDisabled}
              className="btn-primary"
              style={{
                width: '100%', height: 50,
                fontSize: '1rem',
                opacity: isDisabled ? 0.45 : 1,
                cursor: isDisabled ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              }}
            >
              {mutation.isPending ? (
                <>
                  <div style={{
                    width: 16, height: 16,
                    border: `2px solid rgba(246,244,238,0.4)`,
                    borderTopColor: T.paper,
                    borderRadius: '50%',
                    animation: 'spin 0.7s linear infinite',
                  }} />
                  Analyzing…
                </>
              ) : 'Analyze Idea →'}
            </button>

            {/* Error */}
            {mutation.error && (
              <motion.div
                initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                style={{
                  marginTop: 14, padding: '12px 16px',
                  background: 'var(--paper-raised)',
                  border: `1px solid ${T.clay}`,
                  borderLeft: `3px solid ${T.clay}`,
                  borderRadius: 'var(--radius)',
                  color: T.clay, fontSize: '0.85rem', lineHeight: 1.5,
                }}
              >
                <strong>Pipeline Error:</strong>{' '}
                {mutation.error instanceof Error ? mutation.error.message : 'An unexpected error occurred.'}
              </motion.div>
            )}
          </motion.div>

          {/* ── RIGHT: Examples ── */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.32 }}
            className="sheet-sm"
            style={{ flex: '1 1 220px' }}
          >
            <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 14 }}>
              Try an Example
            </p>

            {/* Examples as bordered list with doc icon */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {EXAMPLES.map((ex, i) => {
                const active = idea === ex
                return (
                  <button
                    key={i}
                    onClick={() => setIdea(ex)}
                    style={{
                      background: active ? 'var(--paper)' : 'transparent',
                      border: `1px solid ${active ? T.ink : T.line}`,
                      borderRadius: 'var(--radius)',
                      padding: '9px 10px',
                      textAlign: 'left',
                      color: active ? T.ink : T.inkSoft,
                      fontSize: '0.78rem',
                      cursor: 'pointer',
                      width: '100%',
                      lineHeight: 1.5,
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 8,
                      transition: 'border-color 120ms, color 120ms',
                      fontFamily: 'var(--font-body)',
                    }}
                    onMouseEnter={e => {
                      if (!active) {
                        (e.currentTarget as HTMLButtonElement).style.borderColor = T.ink
                        ;(e.currentTarget as HTMLButtonElement).style.color = T.ink
                      }
                    }}
                    onMouseLeave={e => {
                      if (!active) {
                        (e.currentTarget as HTMLButtonElement).style.borderColor = T.line
                        ;(e.currentTarget as HTMLButtonElement).style.color = T.inkSoft
                      }
                    }}
                  >
                    <PatentDocIcon size={13} color={active ? T.sage : T.line} animate={false} style={{ flexShrink: 0, marginTop: 2 } as React.SVGProps<SVGSVGElement>} />
                    <span style={{
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>{ex}</span>
                  </button>
                )
              })}
            </div>

            {/* Tip */}
            <div style={{
              marginTop: 16, padding: '9px 12px',
              background: 'var(--paper)',
              border: `1px solid ${T.line}`,
              borderLeft: `2px solid ${T.sage}`,
              borderRadius: 'var(--radius)',
            }}>
              <p className="caption" style={{ color: T.sage, marginBottom: 3 }}>Tip</p>
              <p style={{ color: 'var(--ink-soft)', fontSize: '0.75rem', lineHeight: 1.55 }}>
                More technical detail = better results. Include materials, methods, or target application.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
