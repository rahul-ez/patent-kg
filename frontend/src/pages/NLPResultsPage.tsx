import { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { IdeaIcon, FAISSIcon } from '../assets/PatentIcons'
import { T } from '../theme'

export default function NLPResultsPage() {
  const navigate = useNavigate()
  const { pipelineResult } = usePipelineStore()
  const [queryOpen, setQueryOpen] = useState(false)

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
        <IdeaIcon size={40} color={T.borderHairline} animate={false} />
        <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600 }}>No Case File Selected</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Please submit an innovation idea first to generate case logs.</p>
        <Link to="/analyze" className="btn-primary" style={{ textDecoration: 'none', marginTop: 4 }}>New Analysis →</Link>
      </div>
    )
  }

  const { nlp_result, model } = pipelineResult
  const { clean_text, keywords, entities, source } = nlp_result
  const isGemini = source === 'gemini' || source?.toLowerCase().includes('gemini')

  return (
    <div style={{ maxWidth: 960, fontFamily: 'var(--font-body)' }}>

      {/* ─── Page Title Block ─── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
        style={{ marginBottom: 16 }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <div>
            <p className="caption" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>
              §01 — LANGUAGE PROCESSING
            </p>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '44px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
              NLP Analysis
            </h1>
          </div>
        </div>
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
          {/* Model */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>MODEL</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>{model || 'PatentSBERTa'}</span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />
          
          {/* Source */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>SOURCE</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>{isGemini ? 'Gemini LLM' : 'spaCy'}</span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />
          
          {/* Keywords count */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>KEYWORDS</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>{keywords?.length || 0}</span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />
          
          {/* Entities count */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>ENTITIES</span>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              color: (entities?.length || 0) === 0 ? 'var(--text-tertiary)' : 'var(--text-primary)'
            }}>
              {entities?.length || 0}
            </span>
          </div>
        </div>

        {/* Right side: Ref number */}
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)', letterSpacing: '0.06em' }}>
          REF. {refNum.current}
        </div>
      </motion.div>

      {/* ─── Anchor Card (§1 Preprocessed Text) ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.35 }}
        className="sheet-primary" style={{ marginBottom: 32 }}
      >
        <h2 className="section-header" style={{ marginBottom: 14 }}>
          <span className="section-clause-num">§1</span>Preprocessed Text
        </h2>
        <p style={{
          fontFamily: 'var(--font-display)',
          fontSize: '18px',
          fontWeight: 500,
          fontStyle: 'italic',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
          margin: 0,
        }}>
          {clean_text || 'No preprocessed text available in case log.'}
        </p>
      </motion.div>

      {/* ─── Keywords + Entities (65/35 Split Row) ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16, duration: 0.35 }}
        style={{ display: 'grid', gridTemplateColumns: '65% 35%', gap: 32, alignItems: 'start', marginBottom: 32 }}
      >
        {/* Keywords */}
        <div className="sheet-secondary">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <h2 className="section-header" style={{ margin: 0 }}>
              <span className="section-clause-num">§2</span>Extracted Keywords
            </h2>
            <span className="mono-tag">{keywords?.length || 0}</span>
          </div>
          {keywords && keywords.length > 0
            ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                {keywords.map((kw, i) => <span key={i} className="tag-keyword">{kw}</span>)}
              </div>
            : <p style={{ color: 'var(--text-secondary)', fontSize: '13px', fontStyle: 'italic' }}>No keywords extracted.</p>
          }
        </div>

        {/* Entities (or Empty State) */}
        {entities && entities.length > 0 ? (
          <div className="sheet-secondary">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <h2 className="section-header" style={{ margin: 0 }}>
                <span className="section-clause-num">§3</span>Named Entities
              </h2>
              <span className="mono-tag">{entities?.length || 0}</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              {entities.map((ent, i) => {
                const name = typeof ent === 'string' ? ent : ent?.text || ''
                const label = typeof ent === 'string' ? '' : ent?.label || ''
                return (
                  <span key={i} className="tag-entity" title={label}>
                    {name}{label && ` (${label})`}
                  </span>
                )
              })}
            </div>
          </div>
        ) : (
          <div style={{ padding: '20px 0' }}>
            <h2 className="section-header" style={{ marginBottom: 12 }}>
              <span className="section-clause-num">§3</span>Named Entities
            </h2>
            {/* Empty state: inline, italic, no card chrome */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-tertiary)', fontSize: '13px', fontStyle: 'italic' }}>
              <IdeaIcon size={14} color={T.textTertiary} animate={false} />
              No entities detected for this query.
            </div>
          </div>
        )}
      </motion.div>

      {/* ─── Technical Card: FAISS Query Text ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22, duration: 0.35 }}
        className="sheet-technical" style={{ marginBottom: 48, padding: 0, overflow: 'hidden' }}
      >
        <button
          onClick={() => setQueryOpen(o => !o)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '14px 16px', background: 'none', border: 'none', cursor: 'pointer', outline: 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)' }}>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 600, letterSpacing: '0.1em' }}>
              {queryOpen ? '▼' : '▶'} §4 FAISS QUERY TEXT
            </span>
          </div>
        </button>

        {queryOpen && (
          <div style={{ padding: '0 16px 16px 16px' }}>
            <pre style={{
              background: 'transparent',
              fontFamily: 'var(--font-mono)', fontSize: '13.5px',
              color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              lineHeight: 1.65, margin: 0,
            }}>
              {pipelineResult.query_text || 'No query text available.'}
            </pre>
          </div>
        )}
      </motion.div>

      {/* ─── CTA Banner ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.28, duration: 0.35 }}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
          padding: '24px 0 0 0',
          borderTop: `2px solid ${T.accentSage}`,
          marginBottom: 32,
        }}
      >
        <div>
          <p style={{ fontWeight: 600, fontSize: '16px', color: 'var(--text-primary)', marginBottom: 2 }}>Ready to explore semantic patent matches?</p>
          <p className="caption" style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{pipelineResult.results?.length || 0} patents retrieved and ranked</p>
        </div>
        <button onClick={() => navigate('/results/patents')} className="btn-primary" style={{ padding: '10px 24px' }}>
          View Patent Results →
        </button>
      </motion.div>
    </div>
  )
}
