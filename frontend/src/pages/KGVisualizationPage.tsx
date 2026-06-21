import { useEffect, useCallback, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Node,
  type Edge,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { usePipelineStore } from '../store/usePipelineStore'
import { useKGBuild } from '../hooks/useKGBuild'
import { useKGExpand } from '../hooks/useKGExpand'
import { getKGGraph } from '../api/kg'
import type { PatentExpanded } from '../types/kg'
import { KGIcon } from '../assets/PatentIcons'
import { T } from '../theme'

// ── Node style map — uses T.* constants (no hex duplication) ───────────────
const NODE_STYLE: Record<string, { border: string; bg: string; color: string }> = {
  patent:   { border: T.ink,    bg: T.paperRaised, color: T.ink    },
  company:  { border: T.indigo, bg: T.paperRaised, color: T.indigo },
  cpc:      { border: T.brass,  bg: T.paperRaised, color: T.brass  },
  inventor: { border: T.sage,   bg: T.paperRaised, color: T.sage   },
}

function getNodeStyle(nodeType: string) {
  return NODE_STYLE[nodeType] ?? { border: T.inkSoft, bg: T.paperRaised, color: T.inkSoft }
}

// ── Spinner ────────────────────────────────────────────────────────────────
function Spinner({ size = 24 }: { size?: number }) {
  return (
    <div style={{
      width: size, height: size,
      border: `2px solid ${T.line}`,
      borderTopColor: T.sage,
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
    }} />
  )
}

// ── Status badge — mono-text, bordered, no glow ────────────────────────────
function StatusBadge({ status }: { status: 'building' | 'done' | 'error' | 'idle' }) {
  const map = {
    building: { border: T.sage,    color: T.sage,    label: 'Building'  },
    done:     { border: T.sage,    color: T.sage,    label: 'Complete'  },
    error:    { border: T.clay,    color: T.clay,    label: 'Error'     },
    idle:     { border: T.line,    color: T.inkSoft, label: 'Idle'      },
  }
  const s = map[status]
  return (
    <span style={{
      padding: '3px 10px', borderRadius: 'var(--radius)',
      border: `1px solid ${s.border}`, color: s.color,
      fontFamily: 'var(--font-mono)', fontSize: '0.72rem', letterSpacing: '0.04em',
    }}>
      {s.label}
    </span>
  )
}

// ── KG stat strip — mono counts in single thin bordered row ───────────────
function StatStrip({ kgStats }: { kgStats: any }) {
  const entries = [
    ...Object.entries(kgStats.nodes as Record<string, number>).map(([k, v]) => ({ label: k, value: v, type: 'node' })),
    ...Object.entries(kgStats.edges as Record<string, number>).map(([k, v]) => ({ label: k, value: v, type: 'edge' })),
  ]
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
      {entries.map(({ label, value, type }) => (
        <span key={`${type}-${label}`} className="mono-tag">
          {label} <strong style={{ fontWeight: 600, color: type === 'edge' ? T.indigo : T.ink }}>{value}</strong>
        </span>
      ))}
    </div>
  )
}

// ── Expansion card — Sheet treatment ──────────────────────────────────────
function ExpansionCard({ patent, accentColor }: { patent: PatentExpanded; accentColor: string }) {
  const abstract = patent.abstract ? patent.abstract.slice(0, 280) + (patent.abstract.length > 280 ? '…' : '') : 'No abstract available.'
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      className="sheet-sm"
      style={{ display: 'flex', flexDirection: 'column', gap: 6, borderLeft: `2px solid ${accentColor}` }}
      whileHover={{ borderColor: T.sage } as any}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        {patent.domain && <span className="tag-keyword" style={{ borderColor: T.indigo, color: T.indigo }}>{patent.domain}</span>}
      </div>
      <p style={{ fontWeight: 600, color: 'var(--ink)', fontSize: '0.88rem', lineHeight: 1.45 }}>{patent.title}</p>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: T.inkSoft }}>
        {patent.patent_id}{patent.publication_year ? ` · ${patent.publication_year}` : ''}
      </p>
      <p style={{ fontSize: '0.82rem', color: 'var(--ink-soft)', lineHeight: 1.6 }}>{abstract}</p>
      {patent.cited_by_patent_count && (
        <p className="caption">Cited by {patent.cited_by_patent_count} patents</p>
      )}
      {patent.url && (
        <a href={patent.url} target="_blank" rel="noopener noreferrer"
          style={{ fontSize: '0.75rem', color: T.sage, textDecoration: 'none' }}>
          View on Lens.org →
        </a>
      )}
    </motion.div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function KGVisualizationPage() {
  const pipelineResult  = usePipelineStore((s) => s.pipelineResult)
  const kgStats         = usePipelineStore((s) => s.kgStats)
  const kgExpansion     = usePipelineStore((s) => s.kgExpansion)
  const kgGraphData     = usePipelineStore((s) => s.kgGraphData)
  const setKGGraphData  = usePipelineStore((s) => s.setKGGraphData)

  const buildMutation  = useKGBuild()
  const expandMutation = useKGExpand()

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const [familyOpen,   setFamilyOpen]   = useState(true)
  const [siblingsOpen, setSiblingsOpen] = useState(true)
  const [graphError,   setGraphError]   = useState<string | null>(null)

  const patentIds = pipelineResult?.results.map((r) => r.patent_id) ?? []

  useEffect(() => {
    if (pipelineResult && !kgStats && !buildMutation.isPending) {
      buildMutation.mutate(patentIds)
    }
  }, [pipelineResult, kgStats]) // eslint-disable-line

  useEffect(() => {
    if (!kgStats) return
    if (!kgExpansion && !expandMutation.isPending) expandMutation.mutate({ ids: patentIds })
    if (!kgGraphData) {
      getKGGraph(patentIds)
        .then((data) => setKGGraphData(data))
        .catch((err) => setGraphError(err?.message ?? 'Failed to load graph'))
    }
  }, [kgStats]) // eslint-disable-line

  useEffect(() => {
    if (!kgGraphData) return
    const rfNodes: Node[] = kgGraphData.nodes.map((n) => {
      const style = getNodeStyle(n.data.nodeType)
      return {
        id: n.id,
        position: n.position,
        data: { label: n.data.label.slice(0, 20) },
        style: {
          background: style.bg,
          border: `1px solid ${style.border}`,
          borderRadius: 'var(--radius)',
          color: style.color,
          fontSize: 11,
          fontFamily: 'var(--font-mono)',
          padding: '5px 9px',
          minWidth: 80,
          boxShadow: 'var(--shadow-sheet)',
        },
      }
    })
    const rfEdges: Edge[] = kgGraphData.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      style: { stroke: T.line, strokeWidth: 1.5 },
      labelStyle: { fill: T.inkSoft, fontSize: 10, fontFamily: 'var(--font-mono)' },
    }))
    setNodes(rfNodes)
    setEdges(rfEdges)
  }, [kgGraphData]) // eslint-disable-line

  const buildStatus: 'building' | 'done' | 'error' | 'idle' =
    buildMutation.isPending ? 'building'
    : buildMutation.isError  ? 'error'
    : kgStats ? 'done'
    : 'idle'

  if (!pipelineResult) {
    return (
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 0' }}>
        <div className="sheet" style={{ padding: 48, textAlign: 'center' }}>
          <KGIcon size={40} color={T.line} animate={false} />
          <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--ink)', fontWeight: 600, marginBottom: 8, marginTop: 16 }}>No Analysis Yet</h2>
          <p style={{ color: 'var(--ink-soft)', marginBottom: 24 }}>Run a patent analysis to build and explore the knowledge graph.</p>
          <Link to="/analyze" className="btn-primary" style={{ textDecoration: 'none' }}>Start Analysis →</Link>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}
      >
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', fontWeight: 600, color: 'var(--ink)' }}>
          Knowledge Graph
        </h1>
        <StatusBadge status={buildStatus} />
      </motion.div>

      {/* KG stat strip */}
      {kgStats && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <StatStrip kgStats={kgStats} />
        </motion.div>
      )}

      {/* ReactFlow Canvas — light background, line-colored dot grid */}
      <motion.div
        initial={{ opacity: 0, scale: 0.99 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.3 }}
        style={{
          height: 480, border: `1px solid ${T.line}`, borderRadius: 'var(--radius)',
          overflow: 'hidden', marginBottom: 24,
          background: T.paper, position: 'relative',
          boxShadow: 'var(--shadow-sheet)',
        }}
      >
        {kgGraphData === null ? (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 14 }}>
            {graphError ? (
              <>
                <KGIcon size={32} color={T.line} animate={false} />
                <p style={{ color: T.inkSoft }}>No graph data available. Neo4j may not be running.</p>
              </>
            ) : (
              <>
                <Spinner size={32} />
                <p style={{ color: T.inkSoft, fontSize: '0.9rem' }}>Building knowledge graph…</p>
                <p className="caption">Connecting to Neo4j and ingesting {patentIds.length} patents</p>
              </>
            )}
          </div>
        ) : kgGraphData.nodes.length === 0 ? (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
            <KGIcon size={32} color={T.line} animate={false} />
            <p style={{ color: T.inkSoft }}>No graph data available. Neo4j may not be running.</p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes} edges={edges}
            onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
            fitView fitViewOptions={{ padding: 0.2 }}
            attributionPosition="bottom-right"
          >
            {/* Light dot grid — T.line-colored on T.paper background */}
            <Background variant={BackgroundVariant.Dots} color={T.line} gap={20} size={1} />
            <Controls />
            <MiniMap
              nodeColor={(n) => {
                const nodeType = (n as any).data?._nodeType ?? 'patent'
                return getNodeStyle(nodeType).border
              }}
              maskColor="rgba(246,244,238,0.85)"
            />
          </ReactFlow>
        )}
      </motion.div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        {Object.entries(NODE_STYLE).map(([type, { border }]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 8, height: 8, borderRadius: 1, border: `1.5px solid ${border}` }} />
            <span className="caption" style={{ textTransform: 'capitalize' }}>{type}</span>
          </div>
        ))}
      </div>

      {/* Expansion loading */}
      {expandMutation.isPending && !kgExpansion && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 18px', marginBottom: 16 }} className="sheet-sm">
          <Spinner size={16} />
          <span style={{ color: 'var(--ink-soft)', fontSize: '0.88rem' }}>Expanding via knowledge graph…</span>
        </div>
      )}

      {/* KG Expansion results */}
      {kgExpansion && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <p style={{ color: 'var(--ink-soft)', marginBottom: 18, fontSize: '0.9rem', lineHeight: 1.7 }}>
            Found{' '}
            <span style={{ color: T.indigo, fontWeight: 600 }}>{kgExpansion.family.length} family members</span>{' '}
            and{' '}
            <span style={{ color: T.brass, fontWeight: 600 }}>{kgExpansion.cpc_siblings.length} CPC siblings</span>{' '}
            not in original FAISS top-K.{' '}
            <span style={{ fontWeight: 600 }}>{kgExpansion.total_added} patents added.</span>
          </p>

          {/* Family Members */}
          {kgExpansion.family.length > 0 && (
            <div style={{ marginBottom: 22 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <h3 className="section-header" style={{ margin: 0 }}>Patent Family Members ({kgExpansion.family.length})</h3>
                <button onClick={() => setFamilyOpen(o => !o)} className="btn-secondary" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
                  {familyOpen ? 'Collapse ▲' : 'Expand ▼'}
                </button>
              </div>
              {familyOpen && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {kgExpansion.family.map((p) => (
                    <ExpansionCard key={p.patent_id} patent={p} accentColor={T.indigo} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* CPC Siblings */}
          {kgExpansion.cpc_siblings.length > 0 && (
            <div style={{ marginBottom: 22 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <h3 className="section-header" style={{ margin: 0, borderLeftColor: T.brass }}>CPC Technology Siblings ({kgExpansion.cpc_siblings.length})</h3>
                <button onClick={() => setSiblingsOpen(o => !o)} className="btn-secondary" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
                  {siblingsOpen ? 'Collapse ▲' : 'Expand ▼'}
                </button>
              </div>
              {siblingsOpen && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {kgExpansion.cpc_siblings.map((p) => (
                    <ExpansionCard key={p.patent_id} patent={p} accentColor={T.brass} />
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>
      )}
    </div>
  )
}
