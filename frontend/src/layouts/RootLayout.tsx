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
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--paper)' }}>

      {/* ── Top Nav ───────────────────────────────────────────────────────── */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px', height: 52,
        background: 'var(--paper-raised)',
        borderBottom: '1px solid var(--line)',
        position: 'sticky', top: 0, zIndex: 50,
      }}>

        {/* Logo */}
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
          {/* animate=false: re-mounts on every nav change, would redraw each time */}
          <PatentDocIcon size={18} color={T.ink} animate={false} />
          <span style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: '0.95rem',
            color: 'var(--ink)',
            letterSpacing: '0.01em',
          }}>Patent Intelligence</span>
        </Link>

        {/* Status + CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {status === 'running' && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.72rem',
              color: T.sage, border: `1px solid ${T.sage}`,
              padding: '2px 8px', borderRadius: 'var(--radius)',
              letterSpacing: '0.03em',
            }}>Running</span>
          )}
          {status === 'complete' && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.72rem',
              color: T.sage, border: `1px solid ${T.sage}`,
              padding: '2px 8px', borderRadius: 'var(--radius)',
            }}>Complete</span>
          )}
          {status === 'error' && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.72rem',
              color: T.clay, border: `1px solid ${T.clay}`,
              padding: '2px 8px', borderRadius: 'var(--radius)',
            }}>Error</span>
          )}
          <Link
            to="/analyze"
            onClick={reset}
            className="btn-primary"
            style={{ fontSize: '0.8rem', padding: '6px 14px', textDecoration: 'none' }}
          >
            New Analysis
          </Link>
        </div>
      </nav>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* ── Sidebar ─────────────────────────────────────────────────────── */}
        <aside style={{
          width: 200, flexShrink: 0,
          background: 'var(--paper-raised)',
          borderRight: '1px solid var(--line)',
          padding: '20px 0',
          display: 'flex', flexDirection: 'column', gap: 2,
        }}>
          <p className="caption" style={{ padding: '0 16px 10px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Results
          </p>

          {/* Idea preview */}
          {idea && (
            <div style={{
              margin: '0 12px 10px',
              padding: '8px 10px',
              background: 'var(--paper)',
              border: '1px solid var(--line)',
              borderRadius: 'var(--radius)',
            }}>
              <p className="caption" style={{ marginBottom: 2 }}>Your idea</p>
              <p style={{ fontSize: '0.72rem', color: 'var(--ink-soft)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {idea.slice(0, 60)}{idea.length > 60 ? '…' : ''}
              </p>
            </div>
          )}

          {/* Nav links */}
          {NAV_ITEMS.map(({ path, label, Icon }) => {
            const active = location.pathname === path
            return (
              <Link
                key={path}
                to={path}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '9px 16px',
                  textDecoration: 'none',
                  fontSize: '0.82rem',
                  fontFamily: 'var(--font-body)',
                  color: active ? 'var(--ink)' : 'var(--ink-soft)',
                  fontWeight: active ? 600 : 400,
                  borderLeft: active ? `2px solid ${T.sage}` : '2px solid transparent',
                  transition: 'color 120ms, border-color 120ms',
                  background: 'transparent',
                }}
                onMouseEnter={e => {
                  if (!active) (e.currentTarget as HTMLAnchorElement).style.color = 'var(--ink)'
                }}
                onMouseLeave={e => {
                  if (!active) (e.currentTarget as HTMLAnchorElement).style.color = 'var(--ink-soft)'
                }}
              >
                {/* animate=false: static sidebar icon, not re-drawn on each visit */}
                <Icon size={14} color={active ? T.sage : T.inkSoft} animate={false} />
                {label}
              </Link>
            )
          })}
        </aside>

        {/* ── Main content ─────────────────────────────────────────────────── */}
        <main style={{ flex: 1, overflowY: 'auto', padding: 32, background: 'var(--paper)' }}>
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
