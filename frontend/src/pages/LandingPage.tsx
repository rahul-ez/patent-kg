import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { PatentDocIcon } from '../assets/PatentIcons'
import { T } from '../theme'

const STATS = [
  { value: '58,428', label: 'PATENTS INDEXED' },
  { value: '768-dim', label: 'EMBEDDING SPACE' },
  { value: 'GraphSAGE', label: 'GNN ARCHITECTURE' },
  { value: '< 10s', label: 'FULL PIPELINE' },
]

const TECH_STACK = ['Python 3.13', 'Google Gemini', 'spaCy', 'FAISS', 'Neo4j', 'PyTorch Geometric', 'React']

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.45, delay, ease: [0.25, 1, 0.5, 1] },
})

export default function LandingPage() {
  const navigate = useNavigate()
  const { reset } = usePipelineStore()

  const handleAnalyze = () => {
    reset()
    navigate('/analyze')
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-page)',
      fontFamily: 'var(--font-body)',
      position: 'relative',
      overflow: 'hidden',
    }}>

      {/* ── Faint patent-figure background illustration ─────────────────── */}
      <svg
        aria-hidden
        style={{
          position: 'fixed', top: '10%', right: '-5%',
          width: '50vw', maxWidth: 640, height: 'auto',
          opacity: 0.20, pointerEvents: 'none',
          color: 'var(--border-hairline)',
        }}
        viewBox="0 0 400 340" fill="none"
        stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
      >
        <circle cx="60" cy="170" r="28" className="stroke-draw" style={{ '--path-length': '176' } as React.CSSProperties} />
        <line x1="60" y1="142" x2="60" y2="130" className="stroke-draw" style={{ '--path-length': '12' } as React.CSSProperties} />
        <line x1="42" y1="152" x2="32" y2="142" className="stroke-draw" style={{ '--path-length': '14' } as React.CSSProperties} />
        <line x1="78" y1="152" x2="88" y2="142" className="stroke-draw" style={{ '--path-length': '14' } as React.CSSProperties} />
        <line x1="90" y1="170" x2="138" y2="170" className="stroke-draw" style={{ '--path-length': '48' } as React.CSSProperties} />
        <polyline points="128,162 138,170 128,178" className="stroke-draw" style={{ '--path-length': '24' } as React.CSSProperties} />
        <circle cx="168" cy="170" r="22" className="stroke-draw" style={{ '--path-length': '138' } as React.CSSProperties} />
        <line x1="192" y1="170" x2="234" y2="170" className="stroke-draw" style={{ '--path-length': '42' } as React.CSSProperties} />
        <polyline points="224,162 234,170 224,178" className="stroke-draw" style={{ '--path-length': '24' } as React.CSSProperties} />
        <circle cx="258" cy="150" r="12" className="stroke-draw" style={{ '--path-length': '75' } as React.CSSProperties} />
        <circle cx="280" cy="178" r="10" className="stroke-draw" style={{ '--path-length': '63' } as React.CSSProperties} />
        <circle cx="248" cy="192" r="9"  className="stroke-draw" style={{ '--path-length': '57' } as React.CSSProperties} />
        <line x1="258" y1="162" x2="274" y2="170" className="stroke-draw" style={{ '--path-length': '18' } as React.CSSProperties} />
        <line x1="258" y1="162" x2="250" y2="184" className="stroke-draw" style={{ '--path-length': '24' } as React.CSSProperties} />
        <line x1="296" y1="170" x2="334" y2="170" className="stroke-draw" style={{ '--path-length': '38' } as React.CSSProperties} />
        <polyline points="324,162 334,170 324,178" className="stroke-draw" style={{ '--path-length': '24' } as React.CSSProperties} />
        <rect x="336" y="148" width="40" height="50" rx="1" className="stroke-draw" style={{ '--path-length': '180' } as React.CSSProperties} />
        <polyline points="360,148 360,162 376,162" className="stroke-draw" style={{ '--path-length': '38' } as React.CSSProperties} />
      </svg>

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', minHeight: '62vh',
        padding: '80px 24px 48px', textAlign: 'center',
        position: 'relative', zIndex: 1,
      }}>
        {/* Eyebrow */}
        <motion.div {...fadeUp(0.1)} style={{ marginBottom: 16 }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            fontWeight: 500,
            color: 'var(--accent-sage)',
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
          }}>
            RESEARCH-GRADE PATENT INTELLIGENCE
          </span>
        </motion.div>

        {/* Title */}
        <motion.h1 {...fadeUp(0.2)} style={{
          fontFamily: 'var(--font-display)',
          fontSize: '56px',
          fontWeight: 600,
          lineHeight: 1.05,
          letterSpacing: '-0.01em',
          color: 'var(--text-primary)',
          marginBottom: 20,
          maxWidth: 680,
        }}>
          Intelligent Patent Feasibility Platform
        </motion.h1>

        {/* Subtitle */}
        <motion.p {...fadeUp(0.3)} style={{
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-body)',
          maxWidth: 560,
          fontSize: '18px',
          lineHeight: 1.6,
          margin: '0 auto 36px',
        }}>
          Enter an innovation idea. The platform extracts technical concepts, retrieves SBERTa embeddings via FAISS, expands familial structures in Neo4j, and reranks results using live GraphSAGE GNN inference.
        </motion.p>

        {/* CTAs */}
        <motion.div {...fadeUp(0.4)} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
          <button
            id="cta-analyze"
            onClick={handleAnalyze}
            className="btn-primary"
            style={{ padding: '12px 28px', fontSize: '14px' }}
          >
            Analyze an idea
          </button>
          <button
            id="cta-architecture"
            onClick={() => document.getElementById('architecture')?.scrollIntoView({ behavior: 'smooth' })}
            className="btn-secondary"
            style={{ padding: '12px 24px', fontSize: '14px', borderWidth: '1px' }}
          >
            View architecture
          </button>
        </motion.div>
      </section>

      {/* ── PIPELINE ARCHITECTURE (Single Secondary Card containing one diagram) ─ */}
      <section id="architecture" style={{
        padding: '0 24px 56px', position: 'relative', zIndex: 1,
        maxWidth: 960, margin: '0 auto',
      }}>
        <motion.div {...fadeUp(0.5)} style={{ marginBottom: 28, textAlign: 'center' }}>
          <p className="caption" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>
            SYSTEM PIPELINE
          </p>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
            §1 Pipeline Diagram
          </h2>
        </motion.div>

        <motion.div {...fadeUp(0.6)} className="sheet-secondary" style={{ padding: '32px 24px' }}>
          {/* Responsive SVG Diagram */}
          <div style={{ width: '100%', overflowX: 'auto' }}>
            <svg viewBox="0 0 880 120" fill="none" style={{ minWidth: 800, width: '100%', height: 'auto' }}>
              {/* Connector Lines */}
              <line x1="100" y1="50" x2="180" y2="50" stroke={T.borderHairline} strokeWidth="1.5" strokeDasharray="3 3" />
              <line x1="220" y1="50" x2="310" y2="50" stroke={T.borderHairline} strokeWidth="1.5" />
              <line x1="350" y1="50" x2="440" y2="50" stroke={T.borderHairline} strokeWidth="1.5" />
              <line x1="480" y1="50" x2="570" y2="50" stroke={T.borderHairline} strokeWidth="1.5" />
              <line x1="610" y1="50" x2="700" y2="50" stroke={T.borderHairline} strokeWidth="1.5" />
              <line x1="740" y1="50" x2="820" y2="50" stroke={T.borderHairline} strokeWidth="1.5" strokeDasharray="3 3" />

              {/* Node 1: NLP */}
              <circle cx="90" cy="50" r="12" fill={T.bgCard} stroke={T.accentSage} strokeWidth="2" />
              <text x="90" y="82" textAnchor="middle" fill={T.textPrimary} fontSize="11" fontFamily="var(--font-mono)" fontWeight="600">NLP</text>
              <text x="90" y="96" textAnchor="middle" fill={T.textSecondary} fontSize="10" fontFamily="var(--font-body)">spaCy & Gemini</text>

              {/* Node 2: SBERTa */}
              <circle cx="200" cy="50" r="12" fill={T.bgCard} stroke={T.accentSage} strokeWidth="2" />
              <text x="200" y="82" textAnchor="middle" fill={T.textPrimary} fontSize="11" fontFamily="var(--font-mono)" fontWeight="600">EMBEDDING</text>
              <text x="200" y="96" textAnchor="middle" fill={T.textSecondary} fontSize="10" fontFamily="var(--font-body)">PatentSBERTa</text>

              {/* Node 3: FAISS */}
              <circle cx="330" cy="50" r="12" fill={T.bgCard} stroke={T.accentSage} strokeWidth="2" />
              <text x="330" y="82" textAnchor="middle" fill={T.textPrimary} fontSize="11" fontFamily="var(--font-mono)" fontWeight="600">RETRIEVAL</text>
              <text x="330" y="96" textAnchor="middle" fill={T.textSecondary} fontSize="10" fontFamily="var(--font-body)">FAISS Index</text>

              {/* Node 4: Neo4j */}
              <circle cx="460" cy="50" r="12" fill={T.bgCard} stroke={T.accentSage} strokeWidth="2" />
              <text x="460" y="82" textAnchor="middle" fill={T.textPrimary} fontSize="11" fontFamily="var(--font-mono)" fontWeight="600">GRAPH EXP.</text>
              <text x="460" y="96" textAnchor="middle" fill={T.textSecondary} fontSize="10" fontFamily="var(--font-body)">Neo4j Cypher</text>

              {/* Node 5: GNN */}
              <circle cx="590" cy="50" r="12" fill={T.bgCard} stroke={T.accentSage} strokeWidth="2" />
              <text x="590" y="82" textAnchor="middle" fill={T.textPrimary} fontSize="11" fontFamily="var(--font-mono)" fontWeight="600">GNN RE-RANK</text>
              <text x="590" y="96" textAnchor="middle" fill={T.textSecondary} fontSize="10" fontFamily="var(--font-body)">GraphSAGE Live</text>

              {/* Node 6: Eval */}
              <circle cx="720" cy="50" r="12" fill={T.bgCard} stroke={T.accentSage} strokeWidth="2" />
              <text x="720" y="82" textAnchor="middle" fill={T.textPrimary} fontSize="11" fontFamily="var(--font-mono)" fontWeight="600">EVALUATION</text>
              <text x="720" y="96" textAnchor="middle" fill={T.textSecondary} fontSize="10" fontFamily="var(--font-body)">Patentability Scorer</text>

              {/* Node 7: Agent */}
              <circle cx="830" cy="50" r="12" fill={T.bgCard} stroke={T.accentSage} strokeWidth="2" />
              <text x="830" y="82" textAnchor="middle" fill={T.textPrimary} fontSize="11" fontFamily="var(--font-mono)" fontWeight="600">IMPROVEMENT</text>
              <text x="830" y="96" textAnchor="middle" fill={T.textSecondary} fontSize="10" fontFamily="var(--font-body)">AI Reasoning Agent</text>
            </svg>
          </div>
        </motion.div>
      </section>

      {/* ── STATS ROW (Single Level-1-background strip pattern) ───────────────── */}
      <section style={{ maxWidth: 960, margin: '0 auto 64px', padding: '0 24px' }}>
        <motion.div
          {...fadeUp(0.7)}
          style={{
            background: 'var(--bg-structural)',
            borderBottom: '1px solid var(--border-hairline)',
            display: 'flex', justifyContent: 'space-around',
            padding: '24px 12px', flexWrap: 'wrap', gap: 24,
            boxShadow: 'var(--shadow-navbar)',
            borderRadius: 'var(--radius-card)',
          }}
        >
          {STATS.map((stat) => (
            <div key={stat.label} style={{ textAlign: 'center', minWidth: 140 }}>
              <div className="stat-number" style={{ fontSize: '32px', display: 'block', lineHeight: 1.1 }}>
                {stat.value}
              </div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10.5px',
                color: 'var(--text-secondary)', letterSpacing: '0.12em',
                textTransform: 'uppercase', marginTop: 6,
              }}>
                {stat.label}
              </div>
            </div>
          ))}
        </motion.div>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────────────────────── */}
      <footer style={{
        textAlign: 'center',
        padding: '32px 24px',
        borderTop: `1px solid var(--border-hairline)`,
        position: 'relative', zIndex: 1,
        background: 'var(--bg-structural)',
      }}>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: 8 }}>
          {TECH_STACK.join(' · ')}
        </p>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)' }}>
          Graph-Enhanced Patent Intelligence Platform · Docket Examiner V3 Build
        </p>
      </footer>
    </div>
  )
}
