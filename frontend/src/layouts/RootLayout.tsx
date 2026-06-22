import { Outlet, useLocation, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { PatentDocIcon, KGIcon, IdeaIcon, FAISSIcon, GNNIcon, NoveltyIcon } from '../assets/PatentIcons'
import { T } from '../theme'

const NAV_ITEMS = [
  { path: '/results/nlp',          label: 'NLP Analysis',     Icon: IdeaIcon   },
  { path: '/results/patents',      label: 'Patent Retrieval', Icon: FAISSIcon  },
  { path: '/results/graph',        label: 'Knowledge Graph',  Icon: KGIcon     },
  { path: '/results/gnn',          label: 'GNN Re-ranking',   Icon: GNNIcon    },
  { path: '/results/evaluation',   label: 'Evaluation',       Icon: NoveltyIcon },
  { path: '/results/improvements', label: 'Improvements',     Icon: IdeaIcon   },
]

export default function RootLayout() {
  const location = useLocation()
  const { status, idea, reset } = usePipelineStore()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--bg-page)' }}>

      {/* ── Top Nav ───────────────────────────────────────────────────────── */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px', height: 52,
        background: 'var(--bg-structural)',
        borderBottom: '1px solid var(--border-hairline)',
        boxShadow: 'var(--shadow-navbar)',
        position: 'sticky', top: 0, zIndex: 50,
      }}>

        {/* Logo */}
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <PatentDocIcon size={18} color={T.textPrimary} animate={false} />
          <span style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: '16px',
            color: 'var(--text-primary)',
            letterSpacing: '-0.01em',
          }}>Patent Intelligence</span>
        </Link>

        {/* Status + CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {status === 'running' && (
            <span className="tag-status" style={{ borderColor: T.accentSage, color: T.accentSage }}>
              Running
            </span>
          )}
          {status === 'complete' && (
            <span className="tag-status" style={{ borderColor: T.accentSage, color: T.accentSage }}>
              Complete
            </span>
          )}
          {status === 'error' && (
            <span className="tag-status" style={{ borderColor: T.accentClay, color: T.accentClay }}>
              Error
            </span>
          )}
          <Link
            to="/analyze"
            onClick={reset}
            className="btn-primary"
            style={{ fontSize: '13px', padding: '6px 14px', height: '30px' }}
          >
            New Analysis
          </Link>
        </div>
      </nav>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* ── Sidebar ─────────────────────────────────────────────────────── */}
        <aside style={{
          width: 240, flexShrink: 0,
          background: 'var(--bg-structural)',
          boxShadow: 'var(--shadow-structural)',
          borderRight: 'none',
          padding: '24px 0',
          display: 'flex', flexDirection: 'column',
        }}>
          {/* Nav Header Title */}
          <p className="caption" style={{ padding: '0 20px', marginBottom: 8, color: 'var(--text-tertiary)' }}>
            Results
          </p>

          {/* Docket Tab — styled asymmetric tab protruding from sidebar edge */}
          {idea && (
            <div style={{
              margin: '0 16px 20px 16px',
              padding: '12px 14px',
              background: 'var(--bg-card)',
              borderLeft: `3px solid ${T.accentSage}`,
              borderRadius: `0 var(--radius-card) var(--radius-card) 0`,
              boxShadow: 'var(--shadow-l2)',
            }}>
              <p className="caption" style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginBottom: 2 }}>
                DOCKET
              </p>
              <p style={{
                fontFamily: 'var(--font-display)',
                fontStyle: 'italic',
                fontWeight: 500,
                fontSize: '13px',
                color: 'var(--text-primary)',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                lineHeight: 1.4
              }}>
                {idea}
              </p>
            </div>
          )}

          {/* Nav links */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {NAV_ITEMS.map(({ path, label, Icon }) => {
              const active = location.pathname === path
              return (
                <Link
                  key={path}
                  to={path}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    height: 40,
                    padding: '10px 20px',
                    textDecoration: 'none',
                    fontSize: '14px',
                    fontFamily: 'var(--font-body)',
                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontWeight: active ? 600 : 500,
                    boxShadow: active ? `inset 2px 0 0 ${T.accentSage}` : 'none',
                    background: active ? 'var(--bg-hover-tint)' : 'transparent',
                    transition: 'color 120ms, background-color 120ms',
                  }}
                  onMouseEnter={e => {
                    if (!active) {
                      e.currentTarget.style.background = 'var(--bg-hover-tint)'
                      e.currentTarget.style.color = 'var(--text-primary)'
                    }
                  }}
                  onMouseLeave={e => {
                    if (!active) {
                      e.currentTarget.style.background = 'transparent'
                      e.currentTarget.style.color = 'var(--text-secondary)'
                    }
                  }}
                >
                  <Icon size={14} color={active ? T.accentSage : T.textTertiary} animate={false} />
                  {label}
                </Link>
              )
            })}
          </div>
        </aside>

        {/* ── Main content ─────────────────────────────────────────────────── */}
        <main style={{ flex: 1, overflowY: 'auto', padding: '40px 48px', background: 'var(--bg-page)' }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
