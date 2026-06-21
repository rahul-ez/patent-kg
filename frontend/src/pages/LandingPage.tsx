import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { PatentDocIcon, FAISSIcon, KGIcon, GNNIcon, NoveltyIcon, IdeaIcon } from '../assets/PatentIcons'
import { T } from '../theme'

const PIPELINE_STEPS = [
  { Icon: IdeaIcon,    title: 'NLP Processing',  sub: 'Gemini + spaCy'      },
  { Icon: FAISSIcon,   title: 'Embedding',        sub: 'PatentSBERTa'        },
  { Icon: FAISSIcon,   title: 'FAISS Search',     sub: '58k patents'         },
  { Icon: KGIcon,      title: 'Knowledge Graph',  sub: 'Neo4j'               },
  { Icon: GNNIcon,     title: 'GNN Re-ranking',   sub: 'GraphSAGE'           },
  { Icon: NoveltyIcon, title: 'Analysis',          sub: 'Scores + Insights'  },
]

const TECH_STACK = ['Python 3.13', 'Google Gemini', 'spaCy', 'FAISS', 'Neo4j', 'PyTorch Geometric', 'React']

const STATS = [
  { value: '58,428', label: 'PATENTS INDEXED' },
  { value: '768-dim', label: 'EMBEDDING SPACE' },
  { value: 'GraphSAGE', label: 'GNN ARCHITECTURE' },
  { value: '< 10s', label: 'FULL PIPELINE' },
]

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] },
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
      background: 'var(--paper)',
      fontFamily: 'var(--font-body)',
      position: 'relative',
      overflow: 'hidden',
    }}>

      {/* ── Faint patent-figure background illustration ─────────────────── */}
      <svg
        aria-hidden
        style={{
          position: 'fixed', top: '5%', right: '-8%',
          width: '55vw', maxWidth: 680, height: 'auto',
          opacity: 0.28, pointerEvents: 'none',
          color: T.line,
        }}
        viewBox="0 0 400 340" fill="none"
        stroke={T.line} strokeWidth="1" strokeLinecap="round"
      >
        {/* Idea node */}
        <circle cx="60" cy="170" r="28" className="stroke-draw" style={{ '--path-length': '176' } as React.CSSProperties} />
        <line x1="60" y1="142" x2="60" y2="130" className="stroke-draw" style={{ '--path-length': '12' } as React.CSSProperties} />
        <line x1="42" y1="152" x2="32" y2="142" className="stroke-draw" style={{ '--path-length': '14' } as React.CSSProperties} />
        <line x1="78" y1="152" x2="88" y2="142" className="stroke-draw" style={{ '--path-length': '14' } as React.CSSProperties} />
        {/* Arrow 1 */}
        <line x1="90" y1="170" x2="138" y2="170" className="stroke-draw" style={{ '--path-length': '48' } as React.CSSProperties} />
        <polyline points="128,162 138,170 128,178" className="stroke-draw" style={{ '--path-length': '24' } as React.CSSProperties} />
        {/* Search node */}
        <circle cx="168" cy="170" r="22" className="stroke-draw" style={{ '--path-length': '138' } as React.CSSProperties} />
        <circle cx="168" cy="170" r="10" className="stroke-draw" style={{ '--path-length': '63' } as React.CSSProperties} />
        {/* Arrow 2 */}
        <line x1="192" y1="170" x2="234" y2="170" className="stroke-draw" style={{ '--path-length': '42' } as React.CSSProperties} />
        <polyline points="224,162 234,170 224,178" className="stroke-draw" style={{ '--path-length': '24' } as React.CSSProperties} />
        {/* Graph cluster */}
        <circle cx="258" cy="150" r="12" className="stroke-draw" style={{ '--path-length': '75' } as React.CSSProperties} />
        <circle cx="280" cy="178" r="10" className="stroke-draw" style={{ '--path-length': '63' } as React.CSSProperties} />
        <circle cx="248" cy="192" r="9"  className="stroke-draw" style={{ '--path-length': '57' } as React.CSSProperties} />
        <line x1="258" y1="162" x2="274" y2="170" className="stroke-draw" style={{ '--path-length': '18' } as React.CSSProperties} />
        <line x1="258" y1="162" x2="250" y2="184" className="stroke-draw" style={{ '--path-length': '24' } as React.CSSProperties} />
        <line x1="274" y1="170" x2="252" y2="186" className="stroke-draw" style={{ '--path-length': '24' } as React.CSSProperties} />
        {/* Arrow 3 */}
        <line x1="296" y1="170" x2="334" y2="170" className="stroke-draw" style={{ '--path-length': '38' } as React.CSSProperties} />
        <polyline points="324,162 334,170 324,178" className="stroke-draw" style={{ '--path-length': '24' } as React.CSSProperties} />
        {/* Patent doc */}
        <rect x="336" y="148" width="40" height="50" rx="1" className="stroke-draw" style={{ '--path-length': '180' } as React.CSSProperties} />
        <polyline points="360,148 360,162 376,162" className="stroke-draw" style={{ '--path-length': '38' } as React.CSSProperties} />
        <line x1="342" y1="170" x2="370" y2="170" className="stroke-draw" style={{ '--path-length': '28' } as React.CSSProperties} />
        <line x1="342" y1="176" x2="370" y2="176" className="stroke-draw" style={{ '--path-length': '28' } as React.CSSProperties} />
        <line x1="342" y1="182" x2="362" y2="182" className="stroke-draw" style={{ '--path-length': '20' } as React.CSSProperties} />
      </svg>

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', minHeight: '62vh',
        padding: '80px 24px 48px', textAlign: 'center',
        position: 'relative', zIndex: 1,
      }}>

        {/* Classification tag */}
        <motion.div {...fadeUp(0.1)}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            border: `1px solid ${T.line}`,
            background: T.paperRaised,
            color: T.inkSoft,
            borderRadius: 'var(--radius)',
            padding: '4px 12px',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.72rem',
            letterSpacing: '0.06em',
            marginBottom: 32,
          }}>
            <PatentDocIcon size={13} color={T.inkSoft} animate={false} />
            PATENT INTELLIGENCE PLATFORM
          </span>
        </motion.div>

        {/* Hero h1 — Playfair, solid ink, no gradient */}
        <motion.h1 {...fadeUp(0.2)} style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(2.2rem, 5.5vw, 3.8rem)',
          fontWeight: 600,
          lineHeight: 1.08,
          letterSpacing: '-0.01em',
          color: 'var(--ink)',
          marginBottom: 20,
          maxWidth: 680,
        }}>
          Intelligent Patent<br />Feasibility Platform
        </motion.h1>

        {/* Subtitle */}
        <motion.p {...fadeUp(0.3)} style={{
          color: 'var(--ink-soft)',
          maxWidth: 520,
          fontSize: '1.05rem',
          lineHeight: 1.7,
          margin: '0 auto 36px',
        }}>
          Enter an innovation idea. Our AI pipeline extracts concepts, searches
          58,000+ patents, maps knowledge graphs, and ranks results using
          GraphSAGE GNN.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div {...fadeUp(0.4)} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
          <button
            id="cta-analyze"
            onClick={handleAnalyze}
            className="btn-primary"
            style={{ padding: '12px 28px', fontSize: '0.95rem' }}
          >
            Analyze an Idea →
          </button>
          <button
            id="cta-architecture"
            onClick={() => document.getElementById('architecture')?.scrollIntoView({ behavior: 'smooth' })}
            className="btn-secondary"
            style={{ padding: '12px 24px', fontSize: '0.95rem' }}
          >
            View Architecture
          </button>
        </motion.div>
      </section>

      {/* ── PIPELINE ARCHITECTURE ─────────────────────────────────────────── */}
      <section id="architecture" style={{
        padding: '56px 24px 40px', position: 'relative', zIndex: 1,
        maxWidth: 1100, margin: '0 auto',
      }}>
        <motion.div {...fadeUp(0.5)} style={{ marginBottom: 36, textAlign: 'center' }}>
          <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>
            System Architecture
          </p>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 600, color: 'var(--ink)' }}>
            How it works
          </h2>
        </motion.div>

        {/* Node-link pipeline diagram */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 0 }}>
          {PIPELINE_STEPS.map(({ Icon, title, sub }, i) => (
            <div key={title} style={{ display: 'flex', alignItems: 'center' }}>
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 + i * 0.08, duration: 0.4 }}
                style={{
                  background: T.paperRaised,
                  border: `1px solid ${T.line}`,
                  borderRadius: 'var(--radius)',
                  padding: '14px 12px',
                  textAlign: 'center',
                  width: 130,
                  flexShrink: 0,
                  cursor: 'default',
                  transition: 'border-color 120ms, transform 120ms',
                  boxShadow: '0 1px 2px rgba(35,39,31,0.06)',
                }}
                whileHover={{ borderColor: T.sage, y: -2 }}
              >
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 8 }}>
                  {/* animate=true: each step icon draws in as pipeline card mounts */}
                  <Icon size={20} color={T.sage} animate={true} />
                </div>
                <div style={{ fontWeight: 600, color: 'var(--ink)', fontSize: '0.8rem', marginBottom: 3, fontFamily: 'var(--font-body)' }}>
                  {title}
                </div>
                <div className="caption" style={{ fontSize: '0.7rem' }}>{sub}</div>
              </motion.div>

              {i < PIPELINE_STEPS.length - 1 && (
                <motion.div
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: 0.7 + i * 0.08 }}
                  style={{ padding: '0 4px', color: T.line, fontSize: '1rem', flexShrink: 0 }}
                >
                  —
                </motion.div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── STATS ROW ─────────────────────────────────────────────────────── */}
      <motion.section
        {...fadeUp(1.1)}
        style={{
          padding: '0 24px 56px',
          display: 'flex', justifyContent: 'center',
          gap: 48, flexWrap: 'wrap',
          position: 'relative', zIndex: 1,
        }}
      >
        {STATS.map((stat) => (
          <div key={stat.label} style={{ textAlign: 'center' }}>
            {/* Italic Playfair numerals — the one place display italics earn their keep */}
            <div className="stat-number" style={{ fontSize: '1.9rem', display: 'block' }}>
              {stat.value}
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.65rem',
              color: 'var(--ink-soft)', letterSpacing: '0.1em',
              textTransform: 'uppercase', marginTop: 4,
            }}>
              {stat.label}
            </div>
          </div>
        ))}
      </motion.section>

      {/* ── FOOTER — tech stack as plain mono text ────────────────────────── */}
      <footer style={{
        textAlign: 'center',
        padding: '20px 24px',
        borderTop: `1px solid ${T.line}`,
        position: 'relative', zIndex: 1,
      }}>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--ink-soft)', marginBottom: 6 }}>
          {TECH_STACK.join(' · ')}
        </p>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: T.line }}>
          Graph-Enhanced Patent Intelligence Platform · Demo Build 2026
        </p>
      </footer>
    </div>
  )
}
