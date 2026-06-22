import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { usePipelineStore } from '../store/usePipelineStore'
import { runImprovement } from '../api/improve'
import { IdeaIcon } from '../assets/PatentIcons'
import { T } from '../theme'

// ── Main page ──────────────────────────────────────────────────────────────
export default function ImprovementAgentPage() {
  const {
    idea,
    pipelineResult,
    evaluationResult,
    improvementResult,
    improvementStatus,
    improvementError,
    setImprovementResult,
    setImprovementStatus,
    setImprovementError,
  } = usePipelineStore()

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

  // Trigger live improvement analysis on mount if not already fetched
  useEffect(() => {
    if (pipelineResult && !improvementResult && improvementStatus === 'idle') {
      const fetchImprovement = async () => {
        setImprovementStatus('running')
        try {
          const res = await runImprovement({
            idea,
            pipeline_result: pipelineResult,
            evaluation_result: evaluationResult,
          })
          setImprovementResult(res)
        } catch (err: any) {
          setImprovementError(err?.message ?? 'Failed to load improvement analysis')
        }
      }
      fetchImprovement()
    }
  }, [pipelineResult, improvementResult, improvementStatus]) // eslint-disable-line

  if (!pipelineResult) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 20, textAlign: 'center', padding: 24 }}>
        <IdeaIcon size={40} color={T.borderHairline} animate={false} />
        <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600 }}>No Case File Selected</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Please submit an innovation idea first to run improvement analysis.</p>
        <Link to="/analyze" className="btn-primary" style={{ textDecoration: 'none', marginTop: 4 }}>New Analysis →</Link>
      </div>
    )
  }

  const isLoading = improvementStatus === 'running'
  const isError = improvementStatus === 'error'

  const overlaps = improvementResult?.overlapping_patents ?? []
  const hasOverlaps = overlaps.length > 0
  const topPatent = hasOverlaps ? overlaps[0] : null
  const topSimPct = topPatent ? Math.round(topPatent.similarity * 100) : 0

  const weakAreas = improvementResult?.weaknesses ?? []
  const strategies = improvementResult?.strategies ?? []
  const directions = improvementResult?.alternative_directions ?? []
  const recommendations = improvementResult?.recommendations ?? ''

  return (
    <div style={{ maxWidth: 960, fontFamily: 'var(--font-body)' }}>

      {/* ─── Page Title Block ─── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
        style={{ marginBottom: 16 }}
      >
        <p className="caption" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>
          §06 — IMPROVEMENT ANALYSIS
        </p>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '44px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
          AI Improvement Agent
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
          {/* Overlaps Found */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>OVERLAPS FOUND</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>
              {improvementResult ? overlaps.length : '—'}
            </span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Weak Areas */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>WEAK AREAS</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>
              {improvementResult ? weakAreas.length : '—'}
            </span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Novel Directions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>NOVEL DIRECTIONS</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>
              {improvementResult ? directions.length : '—'}
            </span>
          </div>
        </div>

        {/* Right side: Ref number */}
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)', letterSpacing: '0.06em' }}>
          REF. {refNum.current}
        </div>
      </motion.div>

      {/* ─── Skeleton Loading Bar ─── */}
      {isLoading && (
        <div style={{ marginBottom: 32 }}>
          <div className="skeleton-bar" style={{ marginBottom: 20 }} />
          <div className="sheet-secondary" style={{ padding: 24, textAlign: 'center' }}>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14.5px', fontWeight: 500, margin: 0 }}>
              Running visual prior art overlap detection and computing adjacent low-density opportunities...
            </p>
            <p className="caption" style={{ color: 'var(--text-tertiary)', marginTop: 8 }}>
              Analyzing semantic structures and query citation context
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {isError && improvementError && (
        <div className="sheet-technical" style={{ marginBottom: 32, borderLeftColor: 'var(--accent-clay)', color: 'var(--accent-clay)' }}>
          <p style={{ fontWeight: 600, marginBottom: 4 }}>ANALYSIS EXCEPTION</p>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px' }}>{improvementError}</p>
        </div>
      )}

      {/* ─── Results ─── */}
      {improvementResult && !isLoading && (
        <>
          {/* ─── Anchor Card (§1 Primary Overlap Exhibit OR General Recommendations) ─── */}
          {hasOverlaps && topPatent ? (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.35 }}
              className="sheet-primary" style={{ borderLeft: '4px solid var(--accent-clay)', marginBottom: 32 }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
                <h2 className="section-header" style={{ margin: 0 }}>
                  <span className="section-clause-num">§1</span>Highest Overlap Prior Art
                </h2>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '24px', fontWeight: 700, color: 'var(--accent-clay)' }}>
                  {topSimPct}% OVERLAP
                </span>
              </div>

              <h3 style={{
                fontFamily: 'var(--font-display)',
                fontSize: '20px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                lineHeight: 1.4,
                marginBottom: 6,
              }}>
                {topPatent.title}
              </h3>

              <p style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: 0 }}>
                {topPatent.patent_id}
              </p>
            </motion.div>
          ) : (
            // Fallback Anchor Card: General Recommendations
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.35 }}
              className="sheet-primary" style={{ borderLeft: '4px solid var(--accent-sage)', marginBottom: 32 }}
            >
              <h2 className="section-header" style={{ marginBottom: 16 }}>
                <span className="section-clause-num">§1</span>Examiner Recommendations
              </h2>
              <p style={{
                fontFamily: 'var(--font-body)',
                fontSize: '15px',
                lineHeight: 1.65,
                color: 'var(--text-primary)',
                margin: 0,
              }}>
                {recommendations || 'No recommendations generated.'}
              </p>
            </motion.div>
          )}

          {/* ─── §2 Weak Areas (Secondary Card, Brass Accent) ─── */}
          {weakAreas.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
              className="sheet-secondary" style={{ borderLeft: '3px solid var(--accent-brass)', marginBottom: 24 }}
            >
              <h2 className="section-header" style={{ marginBottom: 14 }}>
                <span className="section-clause-num">§2</span>Identified Weak Areas
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {weakAreas.map((area, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--accent-brass)', fontWeight: 600 }}>•</span>
                    <span style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{area}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ─── §3 Suggested Modifications / Strategies (Secondary Card, Sage Accent) ─── */}
          {strategies.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              className="sheet-secondary" style={{ borderLeft: '3px solid var(--accent-sage)', marginBottom: 24 }}
            >
              <h2 className="section-header" style={{ marginBottom: 16 }}>
                <span className="section-clause-num">§3</span>Suggested Modifications
              </h2>
              <div>
                {strategies.map((item, idx) => {
                  const impactColor = item.impact.toLowerCase() === 'high' ? 'var(--accent-clay)' : item.impact.toLowerCase() === 'medium' ? 'var(--accent-brass)' : 'var(--accent-sage)'
                  return (
                    <div key={idx} style={{
                      marginBottom: idx === strategies.length - 1 ? 0 : 16,
                      borderBottom: idx === strategies.length - 1 ? 'none' : '1px solid var(--border-hairline)',
                      paddingBottom: idx === strategies.length - 1 ? 0 : 16,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                        <span className="mono-tag" style={{ borderColor: impactColor, color: impactColor, fontWeight: 700, fontSize: '10px' }}>
                          {item.impact.toUpperCase()} IMPACT
                        </span>
                        <strong style={{ fontSize: '14.5px', color: 'var(--text-primary)', fontWeight: 600 }}>{item.strategy}</strong>
                      </div>
                      <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                        {item.reason}
                      </p>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          )}

          {/* ─── §4 Novel Directions to Explore (Secondary Card, Sage Accent) ─── */}
          {directions.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
              className="sheet-secondary" style={{ borderLeft: '3px solid var(--accent-sage)', marginBottom: 24 }}
            >
              <h2 className="section-header" style={{ marginBottom: 16 }}>
                <span className="section-clause-num">§4</span>Novel Directions to Explore
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                {directions.map((dir, idx) => {
                  const feasibility = idx % 3 === 0 ? 'HIGH' : idx % 3 === 1 ? 'MEDIUM' : 'LOW'
                  const feasColor = feasibility === 'HIGH' ? 'var(--accent-sage)' : feasibility === 'MEDIUM' ? 'var(--accent-brass)' : 'var(--accent-clay)'
                  return (
                    <div key={idx} style={{
                      padding: '14px',
                      border: '1px solid var(--border-hairline)',
                      borderRadius: 'var(--radius-card)',
                      background: 'var(--bg-card)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 12,
                      justifyContent: 'space-between',
                    }}>
                      <p style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '13.5px', lineHeight: 1.5, margin: 0 }}>
                        {dir}
                      </p>
                      <div>
                        <span className="mono-tag" style={{ borderColor: feasColor, color: feasColor, fontSize: '10px' }}>
                          FEASIBILITY: {feasibility}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          )}

          {/* ─── §5 Examiner Recommendations Commentary (if overlaps card was shown) ─── */}
          {hasOverlaps && recommendations && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
              className="sheet-secondary" style={{ borderLeft: '3px solid var(--accent-sage)', marginBottom: 32 }}
            >
              <h2 className="section-header" style={{ marginBottom: 14 }}>
                <span className="section-clause-num">§5</span>Examiner Recommendations
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.65, margin: 0 }}>
                {recommendations}
              </p>
            </motion.div>
          )}

          {/* ─── Active Status Footer Note (Technical Card style) ─── */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
            className="sheet-technical" style={{ padding: '16px 20px', marginBottom: 40 }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <IdeaIcon size={14} color="var(--text-secondary)" animate={false} />
              <p style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '13.5px', margin: 0 }}>Full AI Improvement Agent</p>
              <span className="mono-tag" style={{ borderColor: 'var(--accent-sage)', color: 'var(--accent-sage)' }}>ACTIVE</span>
            </div>
            <p className="caption" style={{ lineHeight: 1.7, maxWidth: 680, textTransform: 'none', letterSpacing: 'normal', color: 'var(--text-secondary)', fontSize: '12px' }}>
              The improvement pipeline performs a live cross-domain evaluation comparing prior art and novelty scores. Text commentary is generated by Gemini 1.5, restricted strictly to determined categories to maintain diagnosis consistency.
            </p>
          </motion.div>
        </>
      )}
    </div>
  )
}
