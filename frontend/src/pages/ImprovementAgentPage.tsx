import PageHeading from '../components/PageHeading'
import EmptyAnalysis from '../components/EmptyAnalysis'
import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { runImprovement } from '../api/improve'
import { IdeaIcon } from '../assets/PatentIcons'

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
    if (pipelineResult && !improvementResult && improvementStatus === 'idle' && usePipelineStore.getState().improvementStatus === 'idle') {
      const fetchImprovement = async () => {
        setImprovementStatus('running')
        try {
          const res = await runImprovement({
            idea,
            pipeline_result: pipelineResult,
            evaluation_result: evaluationResult,
            run_id: pipelineResult.run_id,
          })
          if (usePipelineStore.getState().pipelineResult === pipelineResult) setImprovementResult(res)
        } catch (err: any) {
          if (usePipelineStore.getState().pipelineResult === pipelineResult) setImprovementError(err?.message ?? 'Failed to load improvement analysis')
        }
      }
      fetchImprovement()
    }
  }, [pipelineResult, improvementResult, improvementStatus]) // eslint-disable-line

  if (!pipelineResult) return <EmptyAnalysis />

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
    <div className="result-page">

      <PageHeading title="Refine your invention" description="Review overlaps, weaknesses and possible changes grounded in the retrieved evidence." />

      {/* ─── Metadata Strip ─── */}
      <motion.div
        initial={false} animate={{ opacity: 1 }} transition={{ delay: 0.05 }}
        className="result-metadata"
        style={{
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
            <span className="caption" style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>Overlaps</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>
              {improvementResult ? overlaps.length : '—'}
            </span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Weak Areas */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>Weak areas</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>
              {improvementResult ? weakAreas.length : '—'}
            </span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Novel Directions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>Alternative directions</span>
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
            <motion.div initial={false} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.35 }}
              className="sheet-primary" style={{ marginBottom: 32 }}
            >
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
                <h2 className="section-header" style={{ margin: 0 }}>
                  Closest prior-art match
                </h2>
                <span style={{ fontFamily: 'var(--font-body)', fontSize: '16px', fontWeight: 500, color: 'var(--text-secondary)' }}>
                  {topSimPct}% similarity
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
            <motion.div initial={false} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.35 }}
              className="sheet-primary" style={{ borderLeft: '4px solid var(--accent-sage)', marginBottom: 32 }}
            >
              <h2 className="section-header" style={{ marginBottom: 16 }}>
                Research recommendations
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
            <motion.div initial={false} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
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
            <motion.div initial={false} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
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
                        <span className="mono-tag" style={{ borderColor: impactColor, color: impactColor, fontWeight: 500, fontSize: '12px' }}>
                          {item.impact.toLowerCase()} impact
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
            <motion.div initial={false} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
              className="sheet-secondary" style={{ borderLeft: '3px solid var(--accent-sage)', marginBottom: 24 }}
            >
              <h2 className="section-header" style={{ marginBottom: 16 }}>
                <span className="section-clause-num">§4</span>Novel Directions to Explore
              </h2>
              <ul className="direction-list">
                {directions.map((dir, idx) => <li key={idx}>{dir}</li>)}
              </ul>
            </motion.div>
          )}

          {/* ─── §5 Examiner Recommendations Commentary (if overlaps card was shown) ─── */}
          {hasOverlaps && recommendations && (
            <motion.div initial={false} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
              className="sheet-secondary" style={{ borderLeft: '3px solid var(--accent-sage)', marginBottom: 32 }}
            >
              <h2 className="section-header" style={{ marginBottom: 14 }}>
                Research recommendations
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.65, margin: 0 }}>
                {recommendations}
              </p>
            </motion.div>
          )}

          {/* ─── Active Status Footer Note (Technical Card style) ─── */}
          <motion.div initial={false} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
            className="sheet-technical" style={{ padding: '16px 20px', marginBottom: 40 }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <IdeaIcon size={14} color="var(--text-secondary)" animate={false} />
              <p style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '13.5px', margin: 0 }}>About these suggestions</p>
            </div>
            <p className="caption" style={{ lineHeight: 1.7, maxWidth: 680, textTransform: 'none', letterSpacing: 'normal', color: 'var(--text-secondary)', fontSize: '12px' }}>
              The improvement pipeline compares retrieved prior art and evaluation scores. Commentary uses the configured Gemini model when available, with a local fallback. Suggestions are exploratory, not a legal opinion.
            </p>
          </motion.div>
        </>
      )}
    </div>
  )
}
