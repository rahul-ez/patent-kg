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

// ── Radar tooltip ────────────────────────────────────────────────────────────
function RadarTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const { subject, value } = payload[0].payload
  return (
    <div style={{
      background: T.paperRaised, border: `1px solid ${T.line}`,
      borderRadius: 'var(--radius)', padding: '8px 12px', fontSize: '0.78rem',
      boxShadow: 'var(--shadow-sheet)',
    }}>
      <p style={{ color: T.sage, fontWeight: 600, marginBottom: 2 }}>{subject}</p>
      <p style={{ color: 'var(--ink)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
        {value.toFixed(1)}
      </p>
    </div>
  )
}

// ── Stat block ───────────────────────────────────────────────────────────────
function StatBlock({ label, value, sub, delay = 0 }: {
  label: string; value: number; sub: string; delay?: number
}) {
  const color = value >= 70 ? T.sage : value >= 50 ? T.brass : T.clay
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        padding: '14px 18px',
        background: T.paperRaised, border: `1px solid ${T.line}`,
        borderRadius: 'var(--radius)', boxShadow: 'var(--shadow-sheet)',
        flex: 1, minWidth: 110,
      }}
    >
      <p style={{ fontFamily: 'var(--font-display)', fontStyle: 'italic', fontSize: '2.2rem', fontWeight: 500, lineHeight: 1, color, marginBottom: 6 }}>
        {value}
      </p>
      <p style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--ink)', marginBottom: 2, textAlign: 'center' }}>{label}</p>
      <p className="caption" style={{ textAlign: 'center' }}>{sub}</p>
    </motion.div>
  )
}

// ── Score breakdown card ─────────────────────────────────────────────────────
function BreakdownCard({ label, value, explanation, delay = 0 }: {
  label: string; value: number; explanation: string; delay?: number
}) {
  const barColor = value >= 60 ? T.sage : value >= 40 ? T.brass : T.clay
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }}
      className="sheet" style={{ flex: 1, minWidth: 0 }}
    >
      <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>{label}</p>
      <p style={{ fontFamily: 'var(--font-display)', fontStyle: 'italic', fontSize: '1.9rem', fontWeight: 500, color: barColor, marginBottom: 8 }}>
        {Math.round(value)}<span style={{ fontSize: '0.9rem', fontWeight: 400, color: T.inkSoft, fontStyle: 'normal' }}>/100</span>
      </p>
      <div className="score-track" style={{ marginBottom: 10 }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.7, delay: delay + 0.2 }}
          style={{ height: '100%', background: barColor, borderRadius: 2 }}
        />
      </div>
      <p className="caption" style={{ lineHeight: 1.6 }}>{explanation}</p>
    </motion.div>
  )
}

// ── Skeleton block ────────────────────────────────────────────────────────────
function SkeletonBlock() {
  return (
    <div style={{
      flex: 1, minWidth: 110, padding: '14px 18px',
      background: T.paperRaised, border: `1px solid ${T.line}`,
      borderRadius: 'var(--radius)', animation: 'pulse 1.5s ease-in-out infinite',
    }}>
      <div style={{ width: 56, height: 32, background: T.line, borderRadius: 2, margin: '0 auto 10px' }} />
      <div style={{ width: '60%', height: 10, background: T.line, borderRadius: 2, margin: '0 auto 6px' }} />
      <div style={{ width: '40%', height: 8, background: T.line, borderRadius: 2, margin: '0 auto' }} />
    </div>
  )
}

// ── India flag chip ──────────────────────────────────────────────────────────
function IndiaFlagCard({ flag }: { flag: IndiaFlag }) {
  const [open, setOpen] = useState(false)
  const borderColor = flag.severity === 'HIGH' ? T.clay : flag.severity === 'MEDIUM' ? T.brass : T.inkSoft
  return (
    <div
      onClick={() => setOpen(o => !o)}
      style={{
        cursor: 'pointer',
        border: `1px solid ${borderColor}`,
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: 'var(--radius)',
        background: T.paperRaised,
        padding: '10px 14px',
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 700, color: borderColor }}>
            §{flag.section}
          </span>
          <span style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--ink)' }}>{flag.title}</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: borderColor, fontWeight: 700 }}>
          {flag.severity} {open ? '▲' : '▼'}
        </span>
      </div>
      <AnimatePresence>
        {open && (
          <motion.p
            initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
            className="caption"
            style={{ marginTop: 8, lineHeight: 1.65, overflow: 'hidden' }}
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
  const color = score >= 0.65 ? T.sage : score >= 0.40 ? T.brass : T.clay
  const pct   = Math.round(score * 100)
  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay }}
      style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 7 }}
    >
      <span style={{ width: 180, fontSize: '0.78rem', color: T.inkSoft, flexShrink: 0 }}>
        {label}
        {type === 'bonus' && <span style={{ marginLeft: 4, fontSize: '0.68rem', color: T.brass }}>(bonus)</span>}
      </span>
      <div style={{ flex: 1, height: 6, background: T.line, borderRadius: 3, overflow: 'hidden' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, delay: delay + 0.1 }}
          style={{ height: '100%', background: color, borderRadius: 3 }}
        />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem', width: 32, textAlign: 'right', color }}>
        {pct}
      </span>
      <span className="caption" style={{ width: 48, textAlign: 'right', flexShrink: 0 }}>
        {Math.round(weight * 100)}%
      </span>
    </motion.div>
  )
}

// ── Depth badge ───────────────────────────────────────────────────────────────
function DepthBadge({ level, confidence }: { level: string; confidence: number }) {
  const color = level === 'High' ? T.sage : level === 'Medium' ? T.brass : T.clay
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{
        padding: '3px 10px', borderRadius: 12,
        background: color + '22', border: `1px solid ${color}`,
        fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 700, color,
      }}>
        {level.toUpperCase()}
      </div>
      <span className="caption">Confidence: {Math.round(confidence * 100)}%</span>
    </div>
  )
}

// ── Empty / no pipeline state ─────────────────────────────────────────────────
function EmptyState() {
  return (
    <div style={{ textAlign: 'center', padding: '60px 0', color: T.inkSoft }}>
      <p style={{ fontSize: '1rem', marginBottom: 8 }}>No pipeline result yet.</p>
      <p className="caption">Run the pipeline from the home page first, then come back here to evaluate.</p>
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

  // Cycle through step messages while loading
  useEffect(() => {
    if (isLoading) {
      setStepIdx(0)
      stepTimer.current = setInterval(() => {
        setStepIdx((i) => Math.min(i + 1, EVAL_STEPS.length - 1))
      }, runFast ? 2500 : 7000)
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
        pipeline_result: pipelineResult,   // reuse existing hits — no double pipeline run
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
    ? (eval_.risk === 'Low' ? T.sage : eval_.risk === 'Medium' ? T.brass : T.clay)
    : T.inkSoft

  const nob = eval_?.non_obviousness.breakdown

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 22 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', fontWeight: 600, color: 'var(--ink)' }}>
            Evaluation Dashboard
          </h1>
          {eval_ && (
            <span className="mono-tag" style={{ fontSize: '0.7rem' }}>
              {eval_.concept_count} concepts · {eval_.elapsed_seconds}s · {eval_.fast_mode ? 'fast mode' : 'full analysis'}
            </span>
          )}
        </div>
      </motion.div>

      {/* No pipeline result */}
      {!pipelineResult && <EmptyState />}

      {/* Evaluate button row */}
      {pipelineResult && !eval_ && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ marginBottom: 24 }}>
          <div className="sheet" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
            <div>
              <p style={{ fontWeight: 600, marginBottom: 4 }}>Ready to evaluate</p>
              <p className="caption">Pipeline has results for "{idea.slice(0, 80)}{idea.length > 80 ? '…' : ''}"</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={runFast}
                  onChange={e => setRunFast(e.target.checked)}
                  style={{ accentColor: T.sage }}
                />
                <span className="caption">Fast mode (skip deep Gemini analysis)</span>
              </label>
              <button
                onClick={handleEvaluate}
                disabled={isLoading}
                style={{
                  padding: '8px 22px', borderRadius: 'var(--radius)',
                  background: T.sage, color: '#fff', border: 'none',
                  fontWeight: 600, fontSize: '0.85rem', cursor: isLoading ? 'wait' : 'pointer',
                  opacity: isLoading ? 0.6 : 1,
                }}
              >
                {isLoading ? 'Evaluating…' : 'Run Evaluation'}
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Re-run bar (shown after first evaluation) */}
      {pipelineResult && eval_ && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={runFast}
                onChange={e => setRunFast(e.target.checked)}
                style={{ accentColor: T.sage }}
              />
              <span className="caption">Fast mode</span>
            </label>
            <button
              onClick={handleEvaluate}
              disabled={isLoading}
              style={{
                padding: '5px 16px', borderRadius: 'var(--radius)',
                background: 'transparent', color: T.sage,
                border: `1px solid ${T.sage}`, fontWeight: 600, fontSize: '0.8rem',
                cursor: isLoading ? 'wait' : 'pointer', opacity: isLoading ? 0.6 : 1,
              }}
            >
              {isLoading ? 'Re-evaluating…' : 'Re-run'}
            </button>
          </div>
        </motion.div>
      )}

      {/* Loading state */}
      {isLoading && !eval_ && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
            {[0, 1, 2, 3].map(i => <SkeletonBlock key={i} />)}
          </div>
          <div className="sheet" style={{ padding: 28 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <div style={{
                width: 10, height: 10, borderRadius: '50%',
                background: T.sage, animation: 'pulse 1.2s ease-in-out infinite',
                flexShrink: 0,
              }} />
              <p style={{ color: T.sage, fontWeight: 600 }}>
                Running patentability analysis…
              </p>
            </div>
            {/* Live step indicator */}
            <motion.p
              key={stepIdx}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="caption"
              style={{ fontFamily: 'var(--font-mono)', marginBottom: 14 }}
            >
              Step {stepIdx + 1} / {EVAL_STEPS.length} — {EVAL_STEPS[stepIdx]}
            </motion.p>
            {/* Progress bar */}
            <div style={{ height: 3, background: T.line, borderRadius: 2, overflow: 'hidden' }}>
              <motion.div
                animate={{ width: `${((stepIdx + 1) / EVAL_STEPS.length) * 100}%` }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                style={{ height: '100%', background: T.sage, borderRadius: 2 }}
              />
            </div>
            {!runFast && (
              <p className="caption" style={{ marginTop: 10 }}>
                Full mode: includes Gemini reconstruction test — expect 60–120 s total
              </p>
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {evalStatus === 'error' && evalError && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          style={{ marginBottom: 20, padding: '12px 18px', border: `1px solid ${T.clay}`, borderRadius: 'var(--radius)', background: T.paperRaised }}
        >
          <p style={{ color: T.clay, fontWeight: 600, marginBottom: 4 }}>Evaluation failed</p>
          <p className="caption">{evalError}</p>
        </motion.div>
      )}

      {/* ── Results ── */}
      {eval_ && (
        <>
          {/* Stat row */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
            <StatBlock label="Patentability"    value={eval_.patentability_score}    sub="Overall score"    delay={0}    />
            <StatBlock label="Novelty"          value={eval_.novelty.score}          sub="vs prior art"     delay={0.05} />
            <StatBlock label="Non-Obviousness"  value={eval_.non_obviousness.score}  sub="inventive step"  delay={0.1}  />
            <StatBlock label="Claim Breadth"    value={eval_.claim_breadth.score}    sub="scope potential"  delay={0.15} />
          </div>

          {/* Technical depth + Verdict row */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
            {/* Technical depth */}
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.18 }}
              className="sheet" style={{ flex: 1 }}
            >
              <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                Technical Depth
              </p>
              <DepthBadge level={eval_.technical_depth.level} confidence={eval_.technical_depth.confidence} />
              <p className="caption" style={{ marginTop: 8, lineHeight: 1.6 }}>
                {eval_.technical_depth.interpretation}
              </p>
            </motion.div>

            {/* Risk indicator */}
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
              className="sheet" style={{ flex: 2 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <NoveltyIcon size={18} color={riskColor} animate={false} />
                <span style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600, color: riskColor }}>
                  Patent Risk:
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: riskColor, fontWeight: 700 }}>
                  {eval_.risk.toUpperCase()}
                </span>
              </div>
              <p className="caption" style={{ lineHeight: 1.65 }}>{eval_.verdict}</p>
              {eval_.timing.recency_flag !== 'UNKNOWN' && (
                <p className="caption" style={{ marginTop: 6 }}>
                  Prior art window:{' '}
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: T.inkSoft }}>
                    {eval_.timing.recency_flag}
                  </span>
                  {eval_.timing.newest_year && ` (newest: ${eval_.timing.newest_year})`}
                </p>
              )}
            </motion.div>
          </div>

          {/* Radar */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.24 }}
            className="sheet" style={{ marginBottom: 20 }}
          >
            <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
              Patentability Radar
            </p>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData} margin={{ top: 16, right: 32, bottom: 16, left: 32 }}>
                <PolarGrid stroke={T.line} />
                <PolarAngleAxis dataKey="subject" tick={{ fill: T.inkSoft, fontSize: 12, fontFamily: 'var(--font-body)' }} />
                <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                <RechartsTooltip content={<RadarTooltip />} />
                <Radar
                  name="Score" dataKey="value"
                  fill="transparent"
                  stroke={T.sage}
                  strokeWidth={1.5}
                  dot={{ fill: T.sage, r: 3, strokeWidth: 0 }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* 5-dimension breakdown */}
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 20 }}>
            <BreakdownCard label="Novelty"           value={eval_.novelty.score}           explanation={eval_.novelty.interpretation}         delay={0.28} />
            <BreakdownCard label="Non-Obviousness"   value={eval_.non_obviousness.score}   explanation={eval_.non_obviousness.interpretation} delay={0.31} />
            <BreakdownCard label="Competitive Landscape" value={eval_.landscape.score_100} explanation={eval_.landscape.interpretation}       delay={0.34} />
            <BreakdownCard label="Claim Breadth"     value={eval_.claim_breadth.score}     explanation={eval_.claim_breadth.interpretation}   delay={0.37} />
            <BreakdownCard label="Timing"            value={eval_.timing.score}            explanation={eval_.timing.interpretation}          delay={0.40} />
          </div>

          {/* Non-obviousness sub-breakdown (collapsible) */}
          {nob && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.44 }}
              className="sheet" style={{ marginBottom: 20 }}
            >
              <button
                onClick={() => setShowNOBreak(o => !o)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                  display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center',
                }}
              >
                <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Non-Obviousness Sub-Factors
                </p>
                <span className="caption">{showNOBreak ? '▲ hide' : '▼ expand'}</span>
              </button>

              <AnimatePresence>
                {showNOBreak && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.25 }}
                    style={{ marginTop: 14, overflow: 'hidden' }}
                  >
                    <NOSubRow label="Combination Difficulty"  score={nob.combination_difficulty.score}  weight={nob.combination_difficulty.weight}  delay={0} />
                    <NOSubRow label="Motivation to Combine"   score={nob.motivation_to_combine.score}   weight={nob.motivation_to_combine.weight}   delay={0.03} />
                    <NOSubRow label="Cross-Domain Novelty"    score={nob.cross_domain_novelty.score}    weight={nob.cross_domain_novelty.weight}    delay={0.06} />
                    <NOSubRow label="Reconstruction Difficulty" score={nob.reconstruction.score}        weight={nob.reconstruction.weight}          delay={0.09} />
                    <NOSubRow label="Citation Isolation"      score={nob.citation_isolation.score}      weight={nob.citation_isolation.weight}      delay={0.12} />
                    <NOSubRow label="Long-Felt Need"          score={nob.long_felt_need.score}          weight={nob.long_felt_need.weight}          delay={0.15} />
                    <div style={{ borderTop: `1px solid ${T.line}`, margin: '8px 0' }} />
                    <NOSubRow label="Teaching Away (bonus)"   score={nob.teaching_away.score / 0.30}   weight={nob.teaching_away.weight}    type="bonus" delay={0.18} />
                    <NOSubRow label="Unexpected Effect (bonus)" score={nob.unexpected_effect.score / 0.15} weight={nob.unexpected_effect.weight} type="bonus" delay={0.21} />
                    {eval_.non_obviousness.fast_mode && (
                      <p className="caption" style={{ marginTop: 8, color: T.brass }}>
                        ⚡ Fast mode: motivation-to-combine and reconstruction scores are neutral placeholders.
                      </p>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* India eligibility */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.48 }}
            className="sheet" style={{ marginBottom: 20 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Indian Patent Act (Section 3) Eligibility
              </p>
              {eval_.india_eligibility.is_flagged ? (
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 700, color: T.clay }}>
                  FLAGGED
                </span>
              ) : (
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 700, color: T.sage }}>
                  CLEAR
                </span>
              )}
            </div>

            <p className="caption" style={{ marginBottom: eval_.india_eligibility.flags.length > 0 ? 12 : 0, lineHeight: 1.65 }}>
              {eval_.india_eligibility.summary}
            </p>

            {eval_.india_eligibility.flags.map((f, i) => (
              <IndiaFlagCard key={i} flag={f} />
            ))}

            {eval_.india_eligibility.safe_harbors.length > 0 && (
              <div style={{ marginTop: 10, padding: '10px 14px', background: T.sage + '11', borderRadius: 'var(--radius)', border: `1px solid ${T.sage}44` }}>
                <p style={{ fontWeight: 600, fontSize: '0.8rem', marginBottom: 6, color: T.sage }}>Claim Strategy Notes</p>
                {eval_.india_eligibility.safe_harbors.map((sh, i) => (
                  <div key={i} style={{ marginBottom: 6 }}>
                    <p style={{ fontWeight: 600, fontSize: '0.78rem', color: 'var(--ink)' }}>{sh.note}</p>
                    <p className="caption" style={{ lineHeight: 1.6 }}>{sh.detail}</p>
                  </div>
                ))}
              </div>
            )}
          </motion.div>

          {/* Concept list */}
          {eval_.concepts.length > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.52 }}
              className="sheet"
            >
              <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                Extracted Concepts ({eval_.concept_count})
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {eval_.concepts.map((c, i) => (
                  <div key={i} style={{
                    padding: '4px 12px', borderRadius: 12,
                    border: `1px solid ${T.line}`, background: T.paperRaised,
                  }}>
                    <span style={{ fontWeight: 600, fontSize: '0.78rem' }}>{c.label}</span>
                    {c.description && c.description !== c.label && (
                      <span className="caption" style={{ marginLeft: 6 }}>— {c.description.slice(0, 60)}</span>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </>
      )}

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
      `}</style>
    </div>
  )
}
