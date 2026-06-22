import { useEffect, useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { IdeaIcon, FAISSIcon, KGIcon, GNNIcon, NoveltyIcon } from '../assets/PatentIcons'
import { T } from '../theme'

const STAGES = [
  { Icon: IdeaIcon,      name: 'NLP Processing',    description: 'Extracting keywords and entities with Gemini + spaCy' },
  { Icon: FAISSIcon,     name: 'Semantic Embedding', description: 'Encoding idea with PatentSBERTa (768-dim)' },
  { Icon: FAISSIcon,     name: 'FAISS Retrieval',    description: 'Searching 58,428 indexed patents' },
  { Icon: GNNIcon,       name: 'GNN Re-ranking',     description: 'Re-ordering results using live GraphSAGE' },
  { Icon: KGIcon,        name: 'KG Analysis',        description: 'Building patent knowledge graph in Neo4j' },
  { Icon: NoveltyIcon,   name: 'Complete',           description: 'Case folder assembly ready' },
]

type StageStatus = 'pending' | 'running' | 'done'

function CheckGlyph() {
  return (
    <svg width={14} height={14} viewBox="0 0 16 16" fill="none"
      stroke={T.accentSage} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
    >
      <polyline points="3,8 7,12 13,4" />
    </svg>
  )
}

export default function PipelineProgressPage() {
  const navigate = useNavigate()
  const { idea, status, error, pipelineResult } = usePipelineStore()
  const [currentStageIdx, setCurrentStageIdx] = useState(0)
  const [stageStatuses, setStageStatuses] = useState<StageStatus[]>(STAGES.map(() => 'pending'))
  
  // Ref number generation derived from query_id or current date
  const refNum = useRef('')
  if (!refNum.current) {
    const d = new Date()
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hash = pipelineResult?.query_id ? pipelineResult.query_id.slice(-4).toUpperCase() : Math.random().toString(36).slice(-4).toUpperCase()
    refNum.current = `PI-${yyyy}-${mm}${dd}-${hash}`
  }

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
    }, 3000)

    setStageStatuses(s => { const u = [...s]; u[0] = 'running'; return u })
    return () => clearInterval(interval)
  }, [status, navigate])

  const truncatedIdea = idea.length > 90 ? idea.slice(0, 90) + '…' : idea

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-page)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '40px 24px',
      fontFamily: 'var(--font-body)',
    }}>
      <div style={{ width: '100%', maxWidth: 580, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>

        {/* Reference Number */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ marginBottom: 12 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)', letterSpacing: '0.06em' }}>
            REF. {refNum.current}
          </span>
        </motion.div>

        {/* Title */}
        <motion.h1
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          style={{ fontFamily: 'var(--font-display)', fontSize: '44px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8, textAlign: 'center' }}
        >
          {status === 'error' ? 'Intake Error' : 'Opening Examination Case File'}
        </motion.h1>

        {/* Idea Preview */}
        {idea && (
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}
            style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontSize: '13px', maxWidth: 460, textAlign: 'center', lineHeight: 1.5, marginBottom: 32 }}
          >
            "{truncatedIdea}"
          </motion.p>
        )}

        {/* Error box */}
        <AnimatePresence>
          {status === 'error' && error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className="sheet-technical"
              style={{ borderLeftColor: T.accentClay, color: T.accentClay, width: '100%', marginBottom: 20 }}
            >
              <div style={{ fontWeight: 600, marginBottom: 4, fontSize: '11px', fontFamily: 'var(--font-mono)' }}>EXAMINATION HALTED</div>
              <div style={{ fontFamily: 'var(--font-body)', fontSize: '13px' }}>{error}</div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Process Strip — Single Level-2 Card containing all stages */}
        <div className="sheet" style={{ width: '100%', padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: 16, position: 'relative' }}>
          
          {/* Connector Line behind stages */}
          <div style={{
            position: 'absolute',
            left: 31,
            top: 40,
            bottom: 40,
            width: 1,
            background: 'var(--border-hairline)',
            zIndex: 0,
          }} />

          {STAGES.map(({ Icon, name, description }, i) => {
            const stStatus = stageStatuses[i]
            const isRunning = stStatus === 'running'
            const isDone    = stStatus === 'done'
            const isPending = stStatus === 'pending'

            const nameColor   = isRunning ? 'var(--text-primary)' : isDone ? 'var(--accent-sage)' : 'var(--text-secondary)'
            const opacity     = isPending ? 0.45 : 1

            return (
              <motion.div
                key={name}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05, duration: 0.3 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  opacity: opacity,
                  position: 'relative',
                  zIndex: 1,
                }}
              >
                {/* Node circle */}
                <div style={{
                  width: 24,
                  height: 24,
                  borderRadius: '50%',
                  background: isDone ? 'transparent' : 'var(--bg-card)',
                  border: `1.5px solid ${isDone ? T.accentSage : isRunning ? T.accentSage : T.borderHairline}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  transition: 'border-color 0.3s',
                }}>
                  {isDone ? <CheckGlyph /> : <Icon size={12} color={isRunning ? T.accentSage : T.textTertiary} animate={isRunning} />}
                </div>

                {/* Stage Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{
                    fontWeight: 600,
                    color: nameColor,
                    fontSize: '14px',
                    fontFamily: 'var(--font-body)',
                  }}>
                    {name}
                  </span>
                  <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '12px', lineHeight: 1.4 }}>
                    {description}
                  </p>
                </div>

                {/* Status Indicator Tag */}
                <div style={{ flexShrink: 0 }}>
                  {isRunning && (
                    <span className="tag-status" style={{ borderColor: T.accentSage, color: T.accentSage, animation: 'pulse-dot 1.2s ease-in-out infinite' }}>
                      RUNNING
                    </span>
                  )}
                  {isDone && (
                    <span className="tag-status" style={{ borderColor: T.borderHairline, color: T.textTertiary }}>
                      DONE
                    </span>
                  )}
                  {isPending && (
                    <span className="tag-status" style={{ borderColor: T.borderHairline, color: T.textTertiary, opacity: 0.5 }}>
                      PENDING
                    </span>
                  )}
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* Back to desk if error */}
        {status === 'error' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} style={{ marginTop: 24 }}>
            <Link to="/analyze" className="btn-secondary" style={{ fontSize: '13px' }}>
              ← Return to Case Intake
            </Link>
          </motion.div>
        )}
      </div>

      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.4; }
        }
      `}</style>
    </div>
  )
}
