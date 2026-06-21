import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { IdeaIcon, FAISSIcon, KGIcon, GNNIcon, NoveltyIcon, PatentDocIcon } from '../assets/PatentIcons'
import { T } from '../theme'

const STAGES = [
  { Icon: IdeaIcon,      name: 'NLP Processing',    description: 'Extracting keywords and entities with Gemini + spaCy' },
  { Icon: FAISSIcon,     name: 'Semantic Embedding', description: 'Encoding your idea with PatentSBERTa (768-dim)' },
  { Icon: FAISSIcon,     name: 'FAISS Retrieval',    description: 'Searching 58,428 indexed patents' },
  { Icon: GNNIcon,       name: 'GNN Re-ranking',     description: 'Re-ordering results using GraphSAGE novelty scores' },
  { Icon: KGIcon,        name: 'KG Analysis',        description: 'Building patent knowledge graph in Neo4j' },
  { Icon: NoveltyIcon,   name: 'Complete',           description: 'Results ready' },
]

type StageStatus = 'pending' | 'running' | 'done'

// Inline line-drawn checkmark SVG
function CheckGlyph() {
  return (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none"
      stroke={T.sage} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round"
    >
      <polyline points="3,8 7,12 13,4" />
    </svg>
  )
}

export default function PipelineProgressPage() {
  const navigate = useNavigate()
  const { idea, status, error } = usePipelineStore()
  const [currentStageIdx, setCurrentStageIdx] = useState(0)
  const [stageStatuses, setStageStatuses] = useState<StageStatus[]>(STAGES.map(() => 'pending'))

  useEffect(() => {
    if (status === 'complete') {
      setStageStatuses(STAGES.map(() => 'done'))
      setCurrentStageIdx(STAGES.length - 1)
      const t = setTimeout(() => navigate('/results/nlp'), 1000)
      return () => clearTimeout(t)
    }
    if (status === 'error') return

    const interval = setInterval(() => {
      setCurrentStageIdx(prev => {
        const next = Math.min(prev + 1, STAGES.length - 2)
        setStageStatuses(statuses => {
          const updated = [...statuses]
          updated[prev] = 'done'
          if (next < STAGES.length - 1) updated[next] = 'running'
          return updated
        })
        return next
      })
    }, 4000)

    setStageStatuses(s => { const u = [...s]; u[0] = 'running'; return u })
    return () => clearInterval(interval)
  }, [status, navigate])

  const truncatedIdea = idea.length > 90 ? idea.slice(0, 90) + '…' : idea

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--paper)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '40px 24px',
      fontFamily: 'var(--font-body)',
    }}>
      <div style={{ width: '100%', maxWidth: 540, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>

        {/* Minimal spinner (only when running) */}
        {status !== 'error' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ marginBottom: 24 }}>
            <div style={{
              width: 36, height: 36,
              border: `2px solid ${T.line}`,
              borderTopColor: T.sage,
              borderRadius: '50%',
              animation: 'spin 0.9s linear infinite',
            }} />
          </motion.div>
        )}

        {/* Title */}
        <motion.h1
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', fontWeight: 600, color: 'var(--ink)', marginBottom: 10, textAlign: 'center' }}
        >
          {status === 'error' ? 'Pipeline Error' : 'Running AI Pipeline'}
        </motion.h1>

        {/* Idea preview */}
        {idea && (
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.18 }}
            style={{ fontFamily: 'var(--font-mono)', color: T.inkSoft, fontSize: '0.82rem', maxWidth: 460, textAlign: 'center', lineHeight: 1.55, marginBottom: 32 }}
          >
            "{truncatedIdea}"
          </motion.p>
        )}

        {/* Error state */}
        <AnimatePresence>
          {status === 'error' && error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              style={{
                width: '100%', padding: '14px 18px', marginBottom: 20,
                background: 'var(--paper-raised)',
                border: `1px solid ${T.clay}`,
                borderLeft: `3px solid ${T.clay}`,
                borderRadius: 'var(--radius)',
                color: T.clay, fontSize: '0.88rem', lineHeight: 1.5,
              }}
            >
              <strong>Error: </strong>{error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Process strip — vertical */}
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 0 }}>
          {STAGES.map(({ Icon, name, description }, i) => {
            const stStatus = stageStatuses[i]
            const isRunning = stStatus === 'running'
            const isDone    = stStatus === 'done'
            const isPending = stStatus === 'pending'

            const borderColor = isRunning ? T.sage : isDone ? T.line : T.line
            const nameColor   = isRunning ? T.ink  : isDone ? T.sage : T.inkSoft

            return (
              <motion.div
                key={name}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.07, duration: 0.35 }}
                style={{
                  background: isRunning ? T.paperRaised : 'transparent',
                  border: `1px solid ${borderColor}`,
                  borderRadius: 'var(--radius)',
                  padding: '13px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  marginBottom: 6,
                  opacity: isPending ? 0.42 : 1,
                  transition: 'border-color 0.4s, background 0.4s, opacity 0.4s',
                  boxShadow: isRunning ? 'var(--shadow-sheet)' : 'none',
                }}
              >
                {/* Icon — draws in when stage activates (animate tied to isRunning/isDone mount) */}
                <div style={{ flexShrink: 0, color: isRunning ? T.sage : isDone ? T.sage : T.line }}>
                  {isDone
                    ? <CheckGlyph />
                    : <Icon size={16} color={isRunning ? T.sage : T.line} animate={isRunning} />
                  }
                </div>

                {/* Text */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, color: nameColor, fontSize: '0.86rem', marginBottom: 2, transition: 'color 0.4s' }}>
                    {name}
                  </div>
                  <div className="caption" style={{ fontSize: '0.74rem' }}>{description}</div>
                </div>

                {/* Running indicator — thin pulsing line */}
                {isRunning && (
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: T.sage, flexShrink: 0,
                    animation: 'pulse-dot 1.2s ease-in-out infinite',
                  }} />
                )}
              </motion.div>
            )
          })}
        </div>

        {/* Back to input if error */}
        {status === 'error' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} style={{ marginTop: 24 }}>
            <Link to="/analyze" className="btn-secondary" style={{ textDecoration: 'none', fontSize: '0.88rem' }}>
              ← Back to Input
            </Link>
          </motion.div>
        )}
      </div>

      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.4; transform: scale(0.7); }
        }
      `}</style>
    </div>
  )
}
