import { useState, useEffect, useRef } from 'react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip as RechartsTooltip,
} from 'recharts'
import { motion, AnimatePresence } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { runEvaluation } from '../api/evaluate'
import { NoveltyIcon } from '../assets/PatentIcons'
import { T } from '../theme'
import type { EvaluationResult, IndiaFlag } from '../types/pipeline'
import { Link } from 'react-router-dom'

// ── Radar tooltip ────────────────────────────────────────────────────────────
function RadarTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const { subject, value } = payload[0].payload
  return (
    <div style={{
      background: 'var(--bg-card)', border: `1px solid var(--border-hairline)`,
      borderRadius: 'var(--radius-card)', padding: '8px 12px', fontSize: '13px',
      boxShadow: 'var(--shadow-l2)',
    }}>
      <p style={{ color: 'var(--accent-sage)', fontWeight: 600, marginBottom: 2 }}>{subject}</p>
      <p style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
        {value.toFixed(1)}
      </p>
    </div>
  )
}

// ── Score breakdown card ─────────────────────────────────────────────────────
function BreakdownCard({ label, value, explanation, delay = 0 }: {
  label: string; value: number; explanation: string; delay?: number
}) {
  const barColor = value >= 60 ? 'var(--accent-sage)' : value >= 40 ? 'var(--accent-brass)' : 'var(--accent-clay)'
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }}
      className="sheet-secondary" style={{ flex: 1, minWidth: 0 }}
    >
      <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8, color: 'var(--text-tertiary)' }}>{label}</p>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: '24px', fontWeight: 600, color: barColor, marginBottom: 8 }}>
        {Math.round(value)}<span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-secondary)', fontFamily: 'var(--font-body)' }}>/100</span>
      </p>
      <div className="score-track" style={{ marginBottom: 10 }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.7, delay: delay + 0.2 }}
          style={{ height: '100%', background: barColor, borderRadius: 2 }}
        />
      </div>
      <p style={{ fontFamily: 'var(--font-body)', fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
        {explanation}
      </p>
    </motion.div>
  )
}

// ── Spinner ──────────────────────────────────────────────────────────────────
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

// ── Skeleton block ────────────────────────────────────────────────────────────
function SkeletonBlock() {
  return (
    <div style={{
      flex: 1, minWidth: 110, padding: '14px 18px',
      background: 'var(--bg-card)', border: `1px solid var(--border-hairline)`,
      borderRadius: 'var(--radius-card)', animation: 'pulse 1.5s ease-in-out infinite',
    }}>
      <div style={{ width: 56, height: 32, background: 'var(--border-hairline)', borderRadius: 2, margin: '0 auto 10px' }} />
      <div style={{ width: '60%', height: 10, background: 'var(--border-hairline)', borderRadius: 2, margin: '0 auto 6px' }} />
      <div style={{ width: '40%', height: 8, background: 'var(--border-hairline)', borderRadius: 2, margin: '0 auto' }} />
    </div>
  )
}

// ── India flag chip ──────────────────────────────────────────────────────────
function IndiaFlagCard({ flag }: { flag: IndiaFlag }) {
  const [open, setOpen] = useState(false)
  const borderColor = flag.severity === 'HIGH' ? 'var(--accent-clay)' : flag.severity === 'MEDIUM' ? 'var(--accent-brass)' : 'var(--text-secondary)'
  return (
    <div
      onClick={() => setOpen(o => !o)}
      style={{
        cursor: 'pointer',
        border: `1px solid ${borderColor}`,
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: 'var(--radius-card)',
        background: 'var(--bg-card)',
        padding: '10px 14px',
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700, color: borderColor }}>
            §{flag.section}
          </span>
          <span style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--text-primary)' }}>{flag.title}</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: borderColor, fontWeight: 700 }}>
          {flag.severity} {open ? '▲' : '▼'}
        </span>
      </div>
      <AnimatePresence>
        {open && (
          <motion.p
            initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
            style={{ marginTop: 8, lineHeight: 1.65, overflow: 'hidden', color: 'var(--text-secondary)', fontSize: '13px', fontFamily: 'var(--font-body)' }}
          >
            {flag.explanation}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Non-obviousness sub-breakdown row ─────────────────────────────────────────
function NOSubRow({ label, score, weight, type = 'base', delay = 0 }: {
  label: string; score: number; weight: number; type?: string; delay?: number
}) {
  const color = score >= 0.65 ? 'var(--accent-sage)' : score >= 0.40 ? 'var(--accent-brass)' : 'var(--accent-clay)'
  const pct   = Math.round(score * 100)
  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay }}
      style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 7 }}
    >
      <span style={{ width: 180, fontSize: '13px', color: 'var(--text-secondary)', flexShrink: 0 }}>
        {label}
        {type === 'bonus' && <span style={{ marginLeft: 4, fontSize: '11px', color: 'var(--accent-brass)' }}>(bonus)</span>}
      </span>
      <div style={{ flex: 1, height: 6, background: 'var(--border-hairline)', borderRadius: 3, overflow: 'hidden' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, delay: delay + 0.1 }}
          style={{ height: '100%', background: color, borderRadius: 3 }}
        />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12.5px', width: 32, textAlign: 'right', color, fontWeight: 600 }}>
        {pct}%
      </span>
      <span className="caption" style={{ width: 48, textAlign: 'right', flexShrink: 0, color: 'var(--text-tertiary)' }}>
        {Math.round(weight * 100)}%
      </span>
    </motion.div>
  )
}

// ── Depth badge ───────────────────────────────────────────────────────────────
function DepthBadge({ level, confidence }: { level: string; confidence: number }) {
  const color = level === 'High' ? 'var(--accent-sage)' : level === 'Medium' ? 'var(--accent-brass)' : 'var(--accent-clay)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{
        padding: '2px 8px', borderRadius: 'var(--radius-control)',
        border: `1px solid ${color}`,
        fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600, color,
      }}>
        {level.toUpperCase()}
      </div>
      <span className="caption" style={{ color: 'var(--text-secondary)' }}>Confidence: {Math.round(confidence * 100)}%</span>
    </div>
  )
}

const EVAL_STEPS = [
  'Extracting concepts from your idea…',
  'Searching prior art for each concept…',
  'Computing combination difficulty…',
  'Analyzing motivation to combine…',
  'Scoring cross-domain novelty…',
  'Checking citation isolation…',
  'Estimating long-felt need…',
  'Detecting teaching-away signals…',
  'Running reconstruction difficulty test…',
  'Checking for unexpected effects…',
  'Scoring competitive landscape…',
  'Assessing claim breadth potential…',
  'Analyzing patent timing…',
  'Checking Indian Patent Act eligibility…',
  'Assessing technical depth…',
  'Computing final patentability score…',
]

// ── Main page ────────────────────────────────────────────────────────────────
export default function EvaluationDashboardPage() {
  const idea           = usePipelineStore((s) => s.idea)
  const topK           = usePipelineStore((s) => s.topK)
  const gnnMode        = usePipelineStore((s) => s.gnnMode)
  const pipelineResult = usePipelineStore((s) => s.pipelineResult)
  const evalResult     = usePipelineStore((s) => s.evaluationResult)
  const evalStatus     = usePipelineStore((s) => s.evalStatus)
  const evalError      = usePipelineStore((s) => s.evalError)
  const setEvalResult  = usePipelineStore((s) => s.setEvaluationResult)
  const setEvalStatus  = usePipelineStore((s) => s.setEvalStatus)
  const setEvalError   = usePipelineStore((s) => s.setEvalError)

  const [runFast, setRunFast]         = useState(false)
  const [showNOBreak, setShowNOBreak] = useState(false)
  const [stepIdx, setStepIdx]         = useState(0)
  const stepTimer                     = useRef<ReturnType<typeof setInterval> | null>(null)

  const isLoading = evalStatus === 'running'

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

  // Cycle through step messages while loading
  useEffect(() => {
    if (isLoading) {
      setStepIdx(0)
      stepTimer.current = setInterval(() => {
        setStepIdx((i) => Math.min(i + 1, EVAL_STEPS.length - 1))
      }, runFast ? 1500 : 4500)
    } else {
      if (stepTimer.current) clearInterval(stepTimer.current)
    }
    return () => { if (stepTimer.current) clearInterval(stepTimer.current) }
  }, [isLoading, runFast])

  async function handleEvaluate() {
    if (!idea.trim()) return
    setEvalStatus('running')
    try {
      const result = await runEvaluation({
        idea,
        top_k: topK,
        gnn_mode: gnnMode,
        run_fast: runFast,
        n_reconstruction_samples: runFast ? 3 : 5,
        pipeline_result: pipelineResult,
      })
      setEvalResult(result)
    } catch (err: any) {
      setEvalError(err?.message ?? 'Evaluation failed')
    }
  }

  const eval_ = evalResult

  // Radar data — 5 real dimensions
  const radarData = eval_ ? [
    { subject: 'Novelty',          value: eval_.novelty.score },
    { subject: 'Non-Obviousness',  value: eval_.non_obviousness.score },
    { subject: 'Landscape',        value: eval_.landscape.score_100 },
    { subject: 'Claim Breadth',    value: eval_.claim_breadth.score },
    { subject: 'Timing',           value: eval_.timing.score },
  ] : []

  const riskColor = eval_
    ? (eval_.risk === 'Low' ? 'var(--accent-sage)' : eval_.risk === 'Medium' ? 'var(--accent-brass)' : 'var(--accent-clay)')
    : 'var(--text-tertiary)'

  const nob = eval_?.non_obviousness.breakdown

  const topDimensionScore = eval_ ? Math.max(
    eval_.novelty.score,
    eval_.non_obviousness.score,
    eval_.landscape.score_100,
    eval_.claim_breadth.score,
    eval_.timing.score
  ) : 0

  if (!pipelineResult) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 20, textAlign: 'center', padding: 24 }}>
        <NoveltyIcon size={40} color={T.borderHairline} animate={false} />
        <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600 }}>No Case File Selected</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Please submit an innovation idea first to run evaluation.</p>
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
          §05 — PATENT EVALUATION
        </p>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '44px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
          Evaluation Dashboard
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
          {/* Avg Score */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>AVG. SCORE</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>
              {eval_ ? `${eval_.patentability_score}/100` : '—'}
            </span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Top Score */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>TOP SCORE</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' }}>
              {eval_ ? `${Math.round(topDimensionScore)}/100` : '—'}
            </span>
          </div>
          <div style={{ height: 26, width: 1, background: 'var(--border-hairline)' }} />

          {/* Risk Level */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="caption" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>RISK LEVEL</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: riskColor, fontWeight: 600 }}>
              {eval_ ? eval_.risk.toUpperCase() : '—'}
            </span>
          </div>
        </div>

        {/* Right side: Ref number */}
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)', letterSpacing: '0.06em' }}>
          REF. {refNum.current}
        </div>
      </motion.div>

      {/* Evaluate Trigger Card */}
      {!eval_ && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ marginBottom: 32 }}>
          <div className="sheet-secondary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
            <div>
              <p style={{ fontWeight: 600, marginBottom: 4, color: 'var(--text-primary)' }}>Case Evaluation Pending</p>
              <p className="caption" style={{ color: 'var(--text-secondary)' }}>Assess claim novelty, non-obviousness, and landscape density.</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={runFast}
                  onChange={e => setRunFast(e.target.checked)}
                  style={{ accentColor: T.accentSage }}
                />
                <span className="caption" style={{ color: 'var(--text-secondary)' }}>Fast mode (skip deep LLM synthesis)</span>
              </label>
              <button
                onClick={handleEvaluate}
                disabled={isLoading}
                className="btn-primary"
              >
                {isLoading ? 'Evaluating…' : 'Run Evaluation'}
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Re-run controls (post-evaluation) */}
      {eval_ && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={runFast}
                onChange={e => setRunFast(e.target.checked)}
                style={{ accentColor: T.accentSage }}
              />
              <span className="caption" style={{ color: 'var(--text-secondary)' }}>Fast mode</span>
            </label>
            <button
              onClick={handleEvaluate}
              disabled={isLoading}
              className="btn-secondary"
              style={{ padding: '6px 14px' }}
            >
              {isLoading ? 'Re-evaluating…' : 'Re-run Evaluation'}
            </button>
          </div>
        </motion.div>
      )}

      {/* Loading state skeletons */}
      {isLoading && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
            {[0, 1, 2, 3].map(i => <SkeletonBlock key={i} />)}
          </div>
          <div className="sheet-secondary" style={{ padding: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <Spinner size={16} />
              <p style={{ color: 'var(--accent-sage)', fontWeight: 600, margin: 0 }}>
                Running patentability analysis…
              </p>
            </div>
            <motion.p
              key={stepIdx}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              style={{ fontFamily: 'var(--font-mono)', fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: 12 }}
            >
              STEP {stepIdx + 1} / {EVAL_STEPS.length} — {EVAL_STEPS[stepIdx]}
            </motion.p>
            {/* Progress bar */}
            <div style={{ height: 3, background: 'var(--border-hairline)', borderRadius: 2, overflow: 'hidden' }}>
              <motion.div
                animate={{ width: `${((stepIdx + 1) / EVAL_STEPS.length) * 100}%` }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                style={{ height: '100%', background: 'var(--accent-sage)', borderRadius: 2 }}
              />
            </div>
            {!runFast && (
              <p className="caption" style={{ marginTop: 10, color: 'var(--text-tertiary)' }}>
                Full analysis includes reconstruction trials — can take up to 45 seconds.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Error state */}
      {evalStatus === 'error' && evalError && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="sheet-technical" style={{ marginBottom: 32, borderLeftColor: 'var(--accent-clay)', color: 'var(--accent-clay)' }}
        >
          <p style={{ fontWeight: 600, marginBottom: 4 }}>EVALUATION EXCEPTION</p>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px' }}>{evalError}</p>
        </motion.div>
      )}

      {/* ─── Evaluation results ─── */}
      {eval_ && !isLoading && (
        <>
          {/* ─── Anchor Card (§1 Radar Chart) ─── */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="sheet-primary" style={{ marginBottom: 24 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 className="section-header" style={{ margin: 0 }}>
                <span className="section-clause-num">§1</span>Patentability Radar
              </h2>
              <span className="tag-status" style={{ borderColor: riskColor, color: riskColor }}>
                RISK: {eval_.risk.toUpperCase()}
              </span>
            </div>

            {/* Centered flow container for Radar */}
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <div style={{ width: '100%', maxWidth: 440, height: 320 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData} margin={{ top: 16, right: 32, bottom: 16, left: 32 }}>
                    <PolarGrid stroke="var(--border-hairline)" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: T.textSecondary, fontSize: 11, fontFamily: 'var(--font-mono)' }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                    <RechartsTooltip content={<RadarTooltip />} />
                    <Radar
                      name="Score" dataKey="value"
                      fill="transparent"
                      stroke={T.accentSage}
                      strokeWidth={1.5}
                      dot={{ fill: T.accentSage, r: 3, strokeWidth: 0 }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Verdict statement */}
            <div style={{ marginTop: 24, borderTop: '1px solid var(--border-hairline)', paddingTop: 16 }}>
              <p style={{ fontSize: '14.5px', lineHeight: 1.65, color: 'var(--text-primary)', margin: 0 }}>
                <strong style={{ fontWeight: 600 }}>Examiner Verdict:</strong> {eval_.verdict}
              </p>
            </div>
          </motion.div>

          {/* 5-dimension breakdown card list (Grid layout of 3 columns) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 24 }}>
            <BreakdownCard label="Novelty"           value={eval_.novelty.score}           explanation={eval_.novelty.interpretation}         delay={0.15} />
            <BreakdownCard label="Non-Obviousness"   value={eval_.non_obviousness.score}   explanation={eval_.non_obviousness.interpretation} delay={0.18} />
            <BreakdownCard label="Landscape Room"    value={eval_.landscape.score_100}     explanation={eval_.landscape.interpretation}       delay={0.21} />
            <BreakdownCard label="Claim Breadth"     value={eval_.claim_breadth.score}     explanation={eval_.claim_breadth.interpretation}   delay={0.24} />
            <BreakdownCard label="Timing Window"     value={eval_.timing.score}            explanation={eval_.timing.interpretation}          delay={0.27} />
          </div>

          {/* ─── §2 Technical Depth ─── */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="sheet-secondary" style={{ marginBottom: 24 }}
          >
            <h2 className="section-header" style={{ marginBottom: 14 }}>
              <span className="section-clause-num">§2</span>Technical Depth
            </h2>
            <div style={{ marginBottom: 12 }}>
              <DepthBadge level={eval_.technical_depth.level} confidence={eval_.technical_depth.confidence} />
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13.5px', lineHeight: 1.6, margin: 0 }}>
              {eval_.technical_depth.interpretation}
            </p>
          </motion.div>

          {/* ─── §3 India Patent Act Eligibility ─── */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
            className="sheet-secondary" style={{ marginBottom: 24 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h2 className="section-header" style={{ margin: 0 }}>
                <span className="section-clause-num">§3</span>Indian Patent Act eligibility
              </h2>
              <span className="tag-status" style={{
                borderColor: eval_.india_eligibility.is_flagged ? 'var(--accent-clay)' : 'var(--accent-sage)',
                color: eval_.india_eligibility.is_flagged ? 'var(--accent-clay)' : 'var(--accent-sage)'
              }}>
                {eval_.india_eligibility.is_flagged ? 'FLAGGED' : 'CLEAR'}
              </span>
            </div>

            <p style={{ color: 'var(--text-secondary)', fontSize: '13.5px', lineHeight: 1.65, marginBottom: 16 }}>
              {eval_.india_eligibility.summary}
            </p>

            {eval_.india_eligibility.flags.map((f, i) => (
              <IndiaFlagCard key={i} flag={f} />
            ))}

            {eval_.india_eligibility.safe_harbors.length > 0 && (
              <div style={{ marginTop: 14, padding: '12px 14px', background: 'var(--bg-inset)', borderRadius: 'var(--radius-card)', border: `1px solid var(--border-hairline)` }}>
                <p style={{ fontWeight: 600, fontSize: '13px', marginBottom: 8, color: 'var(--accent-sage)' }}>Claim Strategy Notes</p>
                {eval_.india_eligibility.safe_harbors.map((sh, i) => (
                  <div key={i} style={{ marginBottom: 8 }}>
                    <p style={{ fontWeight: 600, fontSize: '12.5px', color: 'var(--text-primary)', margin: 0 }}>{sh.note}</p>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '12px', lineHeight: 1.5, margin: '2px 0 0 0' }}>{sh.detail}</p>
                  </div>
                ))}
              </div>
            )}
          </motion.div>

          {/* ─── §4 Non-Obviousness Sub-Factors (Collapsible) ─── */}
          {nob && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
              className="sheet-secondary" style={{ marginBottom: 24 }}
            >
              <button
                onClick={() => setShowNOBreak(o => !o)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                  display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center',
                }}
              >
                <h2 className="section-header" style={{ margin: 0 }}>
                  <span className="section-clause-num">§4</span>Non-Obviousness Sub-Factors
                </h2>
                <span className="caption" style={{ color: 'var(--text-secondary)' }}>{showNOBreak ? '▲ hide' : '▼ expand'}</span>
              </button>

              <AnimatePresence>
                {showNOBreak && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.25 }}
                    style={{ marginTop: 16, overflow: 'hidden' }}
                  >
                    <NOSubRow label="Combination Difficulty"  score={nob.combination_difficulty.score}  weight={nob.combination_difficulty.weight}  delay={0} />
                    <NOSubRow label="Motivation to Combine"   score={nob.motivation_to_combine.score}   weight={nob.motivation_to_combine.weight}   delay={0.03} />
                    <NOSubRow label="Cross-Domain Novelty"    score={nob.cross_domain_novelty.score}    weight={nob.cross_domain_novelty.weight}    delay={0.06} />
                    <NOSubRow label="Reconstruction Difficulty" score={nob.reconstruction.score}        weight={nob.reconstruction.weight}          delay={0.09} />
                    <NOSubRow label="Citation Isolation"      score={nob.citation_isolation.score}      weight={nob.citation_isolation.weight}      delay={0.12} />
                    <NOSubRow label="Long-Felt Need"          score={nob.long_felt_need.score}          weight={nob.long_felt_need.weight}          delay={0.15} />
                    <div style={{ borderTop: `1px solid var(--border-hairline)`, margin: '12px 0' }} />
                    <NOSubRow label="Teaching Away (bonus)"   score={nob.teaching_away.score / 0.30}   weight={nob.teaching_away.weight}    type="bonus" delay={0.18} />
                    <NOSubRow label="Unexpected Effect (bonus)" score={nob.unexpected_effect.score / 0.15} weight={nob.unexpected_effect.weight} type="bonus" delay={0.21} />
                    {eval_.non_obviousness.fast_mode && (
                      <p className="caption" style={{ marginTop: 10, color: 'var(--accent-brass)' }}>
                        ⚡ Fast mode active: combination difficulty and reconstruction scores are fallback metrics.
                      </p>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* ─── §5 Extracted Concepts ─── */}
          {eval_.concepts.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}
              className="sheet-secondary" style={{ marginBottom: 32 }}
            >
              <h2 className="section-header" style={{ marginBottom: 14 }}>
                <span className="section-clause-num">§5</span>Extracted Concepts
              </h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {eval_.concepts.map((c, i) => (
                  <div key={i} style={{
                    padding: '4px 12px', borderRadius: 'var(--radius-control)',
                    border: `1px solid var(--border-hairline)`, background: 'var(--bg-card)',
                    display: 'flex', alignItems: 'baseline', gap: 8,
                  }}>
                    <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>{c.label}</span>
                    {c.description && c.description !== c.label && (
                      <span className="caption" style={{ color: 'var(--text-secondary)' }}>— {c.description.slice(0, 80)}</span>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ─── Legal Disclaimer (Technical treatment) ─── */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
            className="sheet-technical" style={{ padding: '12px 16px', textAlign: 'center', marginBottom: 40 }}
          >
            <span style={{ fontSize: '11px', letterSpacing: '0.08em', color: 'var(--text-secondary)', fontWeight: 600 }}>
              SCORES DERIVED FROM RETRIEVAL METRICS — NOT A LEGAL OPINION
            </span>
          </motion.div>
        </>
      )}
    </div>
  )
}
