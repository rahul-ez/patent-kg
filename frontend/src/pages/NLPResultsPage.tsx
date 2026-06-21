import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { IdeaIcon, FAISSIcon } from '../assets/PatentIcons'
import { T } from '../theme'

export default function NLPResultsPage() {
  const navigate = useNavigate()
  const { pipelineResult } = usePipelineStore()
  const [queryOpen, setQueryOpen] = useState(false)

  if (!pipelineResult) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 20, textAlign: 'center', padding: 24 }}>
        <IdeaIcon size={40} color={T.line} animate={false} />
        <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--ink)', fontSize: '1.3rem', fontWeight: 600 }}>No Results Yet</h2>
        <p style={{ color: 'var(--ink-soft)', fontSize: '0.9rem' }}>Run an analysis first to see NLP results.</p>
        <Link to="/analyze" className="btn-primary" style={{ textDecoration: 'none', marginTop: 4 }}>Analyze an Idea →</Link>
      </div>
    )
  }

  const { nlp_result, model } = pipelineResult
  const { clean_text, keywords, entities, source } = nlp_result
  const isGemini = source === 'gemini' || source?.toLowerCase().includes('gemini')

  return (
    <div style={{ maxWidth: 960, fontFamily: 'var(--font-body)' }}>

      {/* ─── Page Header ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
        style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 28, flexWrap: 'wrap', gap: 12 }}
      >
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', fontWeight: 600, color: 'var(--ink)', marginBottom: 8 }}>
            NLP Analysis
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {/* Source badge — mono-text bordered tag */}
            <span className="mono-tag">{isGemini ? 'Gemini LLM' : 'spaCy Fallback'}</span>
            <span className="mono-tag">source: {source || 'unknown'}</span>
          </div>
        </div>

        {/* Slim stat strip */}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {[
            { label: 'Model',    value: model || 'PatentSBERTa' },
            { label: 'Keywords', value: String(keywords?.length || 0) },
            { label: 'Entities', value: String(entities?.length || 0) },
          ].map(pill => (
            <div key={pill.label} className="sheet-sm" style={{ textAlign: 'center', padding: '8px 14px' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '1.05rem', color: 'var(--ink)' }}>{pill.value}</div>
              <div className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.65rem' }}>{pill.label}</div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* ─── Preprocessed Text ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08, duration: 0.35 }}
        className="sheet" style={{ marginBottom: 16 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <IdeaIcon size={16} color={T.sage} animate={false} />
          <h2 className="section-header" style={{ margin: 0 }}>Preprocessed Text</h2>
        </div>
        <div style={{
          background: 'var(--paper)', border: `1px solid ${T.line}`,
          borderRadius: 'var(--radius)', padding: 14,
          fontFamily: 'var(--font-body)', fontSize: '0.9rem',
          color: 'var(--ink-soft)', lineHeight: 1.75, fontStyle: 'italic',
        }}>
          {clean_text || 'No preprocessed text available.'}
        </div>
      </motion.div>

      {/* ─── Keywords + Entities ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15, duration: 0.35 }}
        style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(270px, 1fr))', gap: 16, marginBottom: 16 }}
      >
        {/* Keywords */}
        <div className="sheet">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <h2 className="section-header" style={{ margin: 0 }}>Extracted Keywords</h2>
            <span className="mono-tag">{keywords?.length || 0}</span>
          </div>
          {keywords && keywords.length > 0
            ? <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                {keywords.map((kw, i) => <span key={i} className="tag-keyword">{kw}</span>)}
              </div>
            : <p style={{ color: 'var(--ink-soft)', fontSize: '0.85rem', fontStyle: 'italic' }}>No keywords extracted.</p>
          }
        </div>

        {/* Entities */}
        <div className="sheet">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <h2 className="section-header" style={{ margin: 0, borderLeftColor: 'var(--indigo)' }}>Named Entities</h2>
            <span className="mono-tag">{entities?.length || 0}</span>
          </div>
          {entities && entities.length > 0
            ? <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                {entities.map((ent, i) => <span key={i} className="tag-entity">{ent}</span>)}
              </div>
            : <p style={{ color: 'var(--ink-soft)', fontSize: '0.85rem', fontStyle: 'italic' }}>No entities found.</p>
          }
        </div>
      </motion.div>

      {/* ─── FAISS Query (collapsible) ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22, duration: 0.35 }}
        className="sheet" style={{ marginBottom: 28, padding: 0, overflow: 'hidden' }}
      >
        <button
          onClick={() => setQueryOpen(o => !o)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '14px 20px', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FAISSIcon size={15} color={T.sage} animate={false} />
            <h2 className="section-header" style={{ margin: 0 }}>FAISS Query Text</h2>
          </div>
          <span className="caption" style={{ transition: 'transform 0.2s', display: 'inline-block', transform: queryOpen ? 'rotate(180deg)' : 'none' }}>▼</span>
        </button>

        {queryOpen && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }} style={{ padding: '0 20px 20px' }}>
            <pre style={{
              background: 'var(--paper)', border: `1px solid ${T.line}`,
              borderRadius: 'var(--radius)', padding: 14,
              fontFamily: 'var(--font-mono)', fontSize: '0.8rem',
              color: 'var(--ink-soft)', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              lineHeight: 1.6, margin: 0,
            }}>
              {pipelineResult.query_text || 'No query text available.'}
            </pre>
          </motion.div>
        )}
      </motion.div>

      {/* ─── CTA ─── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.35 }}
        className="sheet"
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, borderLeft: `2px solid ${T.sage}` }}
      >
        <div>
          <p style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--ink)', marginBottom: 2 }}>Ready to explore patent matches?</p>
          <p className="caption">{pipelineResult.results?.length || 0} patents retrieved and ranked</p>
        </div>
        <button onClick={() => navigate('/results/patents')} className="btn-primary" style={{ padding: '10px 24px' }}>
          View Patent Results →
        </button>
      </motion.div>
    </div>
  )
}
