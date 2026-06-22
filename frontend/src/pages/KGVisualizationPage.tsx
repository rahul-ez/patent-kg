import { useEffect, useCallback, useState, useRef, useMemo } from 'react'
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
  patent:   { border: T.borderAnchor, bg: T.bgCard, color: T.textPrimary   },
  company:  { border: T.accentIndigo, bg: T.bgCard, color: T.accentIndigo },
  cpc:      { border: T.accentBrass,  bg: T.bgCard, color: T.accentBrass  },
  inventor: { border: T.accentSage,   bg: T.bgCard, color: T.accentSage   },
}

function getNodeStyle(nodeType: string) {
  return NODE_STYLE[nodeType] ?? { border: T.borderTechnical, bg: T.bgCard, color: T.textSecondary }
}

// ── Spinner ────────────────────────────────────────────────────────────────
function Spinner({ size = 24 }: { size?: number }) {
  return (
    <div style={{
      width: size, height: size,
      border: `2px solid var(--border-hairline)`,
      borderTopColor: 'var(--accent-sage)',
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
    }} />
  )
}

// ── KG stat strip items helper ──────────────────────────────────────────────
function StatStrip({ kgStats }: { kgStats: any }) {
  const nodeCount = Object.values(kgStats.nodes as Record<string, number>).reduce((a, b) => a + b, 0)
  const edgeCount = Object.values(kgStats.edges as Record<string, number>).reduce((a, b) => a + b, 0)
  return { nodeCount, edgeCount }
}

// ── Expansion card ─────────────────────────────────────────────────────────
function ExpansionCard({ patent, accentColor }: { patent: PatentExpanded; accentColor: string }) {
  const abstract = patent.abstract ? patent.abstract.slice(0, 240) + (patent.abstract.length > 240 ? '…' : '') : 'No abstract available.'
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      className="sheet-sm"
      style={{ display: 'flex', flexDirection: 'column', gap: 6, borderLeft: `3px solid ${accentColor}`, marginBottom: 12 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {patent.domain && (
          <span className="tag-keyword" style={{ borderColor: 'var(--accent-indigo)', color: 'var(--accent-indigo)', margin: 0 }}>
            {patent.domain}
          </span>
        )}
      </div>
      <p style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '14.5px', lineHeight: 1.45 }}>{patent.title}</p>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)' }}>
        {patent.patent_id}{patent.publication_year ? ` · ${patent.publication_year}` : ''}
      </p>
      <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{abstract}</p>
      {patent.cited_by_patent_count && (
        <p className="caption" style={{ color: 'var(--text-tertiary)' }}>Cited by {patent.cited_by_patent_count} patents</p>
      )}
      {patent.url && (
        <a href={patent.url} target="_blank" rel="noopener noreferrer"
          style={{ fontSize: '13px', color: 'var(--accent-sage)', textDecoration: 'none', fontWeight: 600 }}>
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

  const patentIds = useMemo(() => {
    return pipelineResult?.results.map((r) => r.patent_id) ?? []
  }, [pipelineResult])

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

  // Reset local error when pipelineResult changes
  useEffect(() => {
    setGraphError(null)
  }, [pipelineResult])

  useEffect(() => {
    if (pipelineResult && !kgStats && !buildMutation.isPending && !buildMutation.isError) {
      buildMutation.mutate(patentIds)
    }
  }, [pipelineResult, kgStats, buildMutation.isPending, buildMutation.isError, patentIds])

  useEffect(() => {
    if (!kgStats) return
    if (!kgExpansion && !expandMutation.isPending && !expandMutation.isError) {
      expandMutation.mutate({ ids: patentIds })
    }
    if (!kgGraphData && !graphError) {
      getKGGraph(patentIds)
        .then((data) => setKGGraphData(data))
        .catch((err) => setGraphError(err?.message ?? 'Failed to load graph'))
    }
  }, [kgStats, kgExpansion, expandMutation.isPending, expandMutation.isError, kgGraphData, graphError, patentIds])

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
          border: `1.5px solid ${style.border}`,
          borderRadius: 'var(--radius-card)',
          color: style.color,
          fontSize: 11,
          fontFamily: 'var(--font-mono)',
          padding: '6px 10px',
          minWidth: 90,
          boxShadow: 'var(--shadow-l2)',
        },
      }
    })
    const rfEdges: Edge[] = kgGraphData.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      style: { stroke: T.borderHairline, strokeWidth: 1.5 },
      labelStyle: { fill: T.textSecondary, fontSize: 10, fontFamily: 'var(--font-mono)' },
    }))
    setNodes(rfNodes)
    setEdges(rfEdges)
  }, [kgGraphData]) // eslint-disable-line

  const buildStatus = buildMutation.isPending ? 'building' : buildMutation.isError ? 'error' : kgStats ? 'done' : 'idle'
  const { nodeCount, edgeCount } = kgStats ? StatStrip({ kgStats }) : { nodeCount: 0, edgeCount: 0 }

  if (!pipelineResult) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 20, textAlign: 'center', padding: 24 }}>
        <KGIcon size={40} color={T.borderHairline} animate={false} />
        <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600 }}>No Case File Selected</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Please submit an innovation idea first to construct the Knowledge Graph.</p>
        <Link to="/analyze" className="btn-primary" style={{ textDecoration: 'none', marginTop: 4 }}>New Analysis →</Link>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 960, fontFamily: 'var(--font-body)' }}>

      {/* ─── Page Title Block ─── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
        style={{ marginBottom: 16 }}
      >
        <p className="caption" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>
          §03 — KNOWLEDGE GRAPH EXPANSION
        </p>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '44px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
          Knowledge Graph
        </h1>
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
          {/* Nodes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>NODES</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>{nodeCount}</span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Edges */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>EDGES</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>{edgeCount}</span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Status */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>STATUS</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600, color: buildStatus === 'done' ? 'var(--accent-sage)' : 'var(--text-secondary)' }}>
              {buildStatus.toUpperCase()}
            </span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Expanded */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>EXPANDED</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>{kgExpansion?.total_added ?? 0}</span>
          </div>
        </div>

        {/* Right side: Ref number */}
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)', letterSpacing: '0.06em' }}>
          REF. {refNum.current}
        </div>
      </motion.div>

      {/* ─── Anchor Card (§1 Knowledge Graph Canvas) ─── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.99 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.35, delay: 0.1 }}
        className="sheet-primary"
        style={{ marginBottom: 24, padding: '32px' }}
      >
        <h2 className="section-header" style={{ marginBottom: 16 }}>
          <span className="section-clause-num">§1</span>Knowledge Graph Visualization
        </h2>

        <div style={{
          height: 520,
          border: '1.5px solid var(--border-anchor)',
          borderRadius: 'var(--radius-card)',
          overflow: 'hidden',
          background: 'var(--bg-page)',
          position: 'relative',
        }}>
          {kgGraphData === null ? (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 14, padding: 24 }}>
              {buildStatus === 'error' ? (
                <>
                  <KGIcon size={32} color="var(--accent-clay)" animate={false} />
                  <p style={{ color: 'var(--accent-clay)', fontSize: '14.5px', fontWeight: 600, margin: 0 }}>SUBGRAPH BUILD FAILED</p>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: 400, textAlign: 'center', lineHeight: 1.5, margin: 0 }}>
                    {(buildMutation.error as any)?.message ?? 'An error occurred while connecting to Neo4j database.'}
                  </p>
                </>
              ) : graphError ? (
                <>
                  <KGIcon size={32} color="var(--accent-clay)" animate={false} />
                  <p style={{ color: 'var(--accent-clay)', fontSize: '14.5px', fontWeight: 600, margin: 0 }}>GRAPH QUERY FAILED</p>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: 400, textAlign: 'center', lineHeight: 1.5, margin: 0 }}>
                    {graphError}
                  </p>
                </>
              ) : (
                <>
                  <Spinner size={32} />
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 500 }}>Building knowledge graph…</p>
                  <p className="caption" style={{ color: 'var(--text-tertiary)' }}>Connecting to Neo4j and ingesting {patentIds.length} patents</p>
                </>
              )}
            </div>
          ) : kgGraphData.nodes.length === 0 ? (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
              <KGIcon size={32} color={T.borderHairline} animate={false} />
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>No graph data available. Neo4j may not be running.</p>
            </div>
          ) : (
            <ReactFlow
              nodes={nodes} edges={edges}
              onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
              fitView fitViewOptions={{ padding: 0.2 }}
              attributionPosition="bottom-right"
            >
              {/* Light dot grid on var(--bg-page) */}
              <Background variant={BackgroundVariant.Dots} color={T.borderHairline} gap={20} size={1} />
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
        </div>
      </motion.div>

      {/* ─── Legend (§2 Graph Legend) ─── */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}
        style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 32, alignItems: 'center' }}
      >
        <span className="caption" style={{ color: 'var(--text-secondary)' }}>§2 LEGEND:</span>
        {Object.entries(NODE_STYLE).map(([type, { border }]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, border: `1.5px solid ${border}`, background: 'var(--bg-card)' }} />
            <span className="caption" style={{ textTransform: 'capitalize', color: 'var(--text-primary)', fontWeight: 600 }}>{type}</span>
          </div>
        ))}
      </motion.div>

      {/* Expansion loading status */}
      {expandMutation.isPending && !kgExpansion && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 18px', marginBottom: 24 }} className="sheet-secondary">
          <Spinner size={16} />
          <span style={{ color: 'var(--text-secondary)', fontSize: '13.5px' }}>Expanding via Knowledge Graph...</span>
        </div>
      )}

      {/* ─── Expansion Results (§3, §4, §5) ─── */}
      {kgExpansion && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          
          {/* §3 Expansion Summary */}
          <div className="sheet-secondary" style={{ marginBottom: 24 }}>
            <h2 className="section-header" style={{ marginBottom: 12 }}>
              <span className="section-clause-num">§3</span>Expansion Summary
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.7 }}>
              Found{' '}
              <strong style={{ color: 'var(--accent-indigo)', fontWeight: 600 }}>{kgExpansion.family.length} family members</strong>{' '}
              and{' '}
              <strong style={{ color: 'var(--accent-brass)', fontWeight: 600 }}>{kgExpansion.cpc_siblings.length} CPC siblings</strong>{' '}
              not in original FAISS top-K. A total of{' '}
              <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{kgExpansion.total_added} patents</strong> added to the docket.
            </p>
          </div>

          {/* §4 Family Members */}
          {kgExpansion.family.length > 0 && (
            <div className="sheet-secondary" style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyUnderline: 'space-between', justifyContent: 'space-between', marginBottom: 14 }}>
                <h2 className="section-header" style={{ margin: 0 }}>
                  <span className="section-clause-num">§4</span>Patent Family Members
                </h2>
                <span className="mono-tag">{kgExpansion.family.length}</span>
              </div>
              {familyOpen && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
                  {kgExpansion.family.map((p) => (
                    <ExpansionCard key={p.patent_id} patent={p} accentColor={T.accentIndigo} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* §5 CPC Technology Siblings */}
          {kgExpansion.cpc_siblings.length > 0 && (
            <div className="sheet-secondary" style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyUnderline: 'space-between', justifyContent: 'space-between', marginBottom: 14 }}>
                <h2 className="section-header" style={{ margin: 0 }}>
                  <span className="section-clause-num">§5</span>CPC Technology Siblings
                </h2>
                <span className="mono-tag">{kgExpansion.cpc_siblings.length}</span>
              </div>
              {siblingsOpen && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
                  {kgExpansion.cpc_siblings.map((p) => (
                    <ExpansionCard key={p.patent_id} patent={p} accentColor={T.accentBrass} />
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
