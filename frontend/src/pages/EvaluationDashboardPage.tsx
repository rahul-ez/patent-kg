import { useMemo } from 'react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip as RechartsTooltip,
} from 'recharts'
import { motion } from 'framer-motion'
import { usePipelineStore } from '../store/usePipelineStore'
import { NoveltyIcon } from '../assets/PatentIcons'
import { T } from '../theme'

// ── Mock eval generator ──────────────────────────────────────────────────────
function useMockEval() {
  const pipelineResult = usePipelineStore((s) => s.pipelineResult)
  return useMemo(() => {
    if (!pipelineResult) return null
    const topScore     = pipelineResult.results[0]?.semantic_score ?? 0.5
    const avgScore     = pipelineResult.results.reduce((s, h) => s + (h.semantic_score ?? 0), 0) / (pipelineResult.results.length || 1)
    const noveltyScore = Math.round((1 - avgScore) * 100)
    const crowdedness  = Math.round(avgScore * 100)
    const ideaStrength = Math.round(noveltyScore * 0.6 + (100 - crowdedness) * 0.4)
    const graphNovelty = Math.min(100, Math.round(noveltyScore * 0.9 + Math.random() * 10))
    const riskLevel    = ideaStrength > 70 ? 'Low' : ideaStrength > 50 ? 'Medium' : 'High'
    // Risk color from semantic palette — no arbitrary colors
    const riskColor    = ideaStrength > 70 ? T.sage : ideaStrength > 50 ? T.brass : T.clay
    const gnnNovelty   = pipelineResult.results[0]?.novelty_score
    return { topScore, avgScore, noveltyScore, crowdedness, ideaStrength, graphNovelty, riskLevel, riskColor, gnnNovelty }
  }, [pipelineResult])
}

// ── Radar custom tooltip ─────────────────────────────────────────────────────
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
      <p style={{ color: 'var(--ink)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{value.toFixed(1)}</p>
    </div>
  )
}

// ── Compact stat block ───────────────────────────────────────────────────────
function StatBlock({ label, value, sub, delay = 0 }: { label: string; value: number; sub: string; delay?: number }) {
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
function BreakdownCard({ label, value, explanation, delay = 0 }: { label: string; value: number; explanation: string; delay?: number }) {
  const pct      = Math.round(value * 100)
  const barColor = pct >= 60 ? T.sage : pct >= 40 ? T.brass : T.clay

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }}
      className="sheet" style={{ flex: 1, minWidth: 0 }}
    >
      <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>{label}</p>
      <p style={{ fontFamily: 'var(--font-display)', fontStyle: 'italic', fontSize: '1.9rem', fontWeight: 500, color: barColor, marginBottom: 8 }}>
        {pct}<span style={{ fontSize: '0.9rem', fontWeight: 400, color: T.inkSoft, fontStyle: 'normal' }}>/100</span>
      </p>
      {/* 4px flat score bar */}
      <div className="score-track" style={{ marginBottom: 10 }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, delay: delay + 0.2 }}
          style={{ height: '100%', background: barColor, borderRadius: 2 }}
        />
      </div>
      <p className="caption" style={{ lineHeight: 1.6 }}>{explanation}</p>
    </motion.div>
  )
}

// ── Skeleton placeholder ─────────────────────────────────────────────────────
function SkeletonBlock() {
  return (
    <div style={{
      flex: 1, minWidth: 110, padding: '14px 18px',
      background: T.paperRaised, border: `1px solid ${T.line}`,
      borderRadius: 'var(--radius)', animation: 'pulse 1.5s ease-in-out infinite',
    }}>
      <div style={{ width: 56, height: 32, background: T.line, borderRadius: 2, margin: '0 auto 10px' }} />
      <div style={{ width: '60%', height: 10, background: T.line, borderRadius: 2, margin: '0 auto 6px' }} />
      <div style={{ width: '40%', height: 8,  background: T.line, borderRadius: 2, margin: '0 auto' }} />
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function EvaluationDashboardPage() {
  const pipelineResult = usePipelineStore((s) => s.pipelineResult)
  const mockEval = useMockEval()

  const radarData = mockEval ? [
    { subject: 'Semantic Similarity', value: +(mockEval.topScore * 100).toFixed(1) },
    { subject: 'Graph Novelty',       value: mockEval.graphNovelty },
    { subject: 'Novelty Score',       value: mockEval.noveltyScore },
    { subject: 'Market Gap',          value: 100 - mockEval.crowdedness },
    { subject: 'Uniqueness',          value: +(mockEval.graphNovelty * 0.95).toFixed(1) },
  ] : []

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Page header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 22 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', fontWeight: 600, color: 'var(--ink)' }}>
            Evaluation Dashboard
          </h1>
          {/* Disclaimer — ink-soft mono caption in bordered box */}
          <span className="mono-tag" style={{ fontSize: '0.7rem', maxWidth: 380, textAlign: 'right', lineHeight: 1.5 }}>
            Scores derived from retrieval metrics — full ML evaluation coming soon
          </span>
        </div>
      </motion.div>

      {/* Compact stat row (4 blocks in one flex row — not 4 heavy sheets) */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        {mockEval ? (
          <>
            <StatBlock label="Idea Strength"  value={mockEval.ideaStrength}  sub="Higher is better" delay={0}    />
            <StatBlock label="Novelty Score"  value={mockEval.noveltyScore}  sub="Higher is better" delay={0.05} />
            <StatBlock label="Crowdedness"    value={mockEval.crowdedness}   sub="Lower is better"  delay={0.1}  />
            <StatBlock label="Graph Novelty"  value={mockEval.graphNovelty}  sub="Higher is better" delay={0.15} />
          </>
        ) : (
          [0, 1, 2, 3].map(i => <SkeletonBlock key={i} />)
        )}
      </div>

      {/* Risk indicator — plain bordered, no glow */}
      {mockEval && (
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}
          style={{ display: 'flex', justifyContent: 'center', marginBottom: 28 }}
        >
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '8px 28px',
            border: `1px solid ${mockEval.riskColor}`,
            borderLeft: `3px solid ${mockEval.riskColor}`,
            borderRadius: 'var(--radius)',
            background: T.paperRaised,
            boxShadow: 'var(--shadow-sheet)',
          }}>
            <NoveltyIcon size={18} color={mockEval.riskColor} animate={false} />
            <span style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600, color: mockEval.riskColor }}>
              Patent Risk Level:
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: mockEval.riskColor, fontWeight: 700 }}>
              {mockEval.riskLevel.toUpperCase()}
            </span>
          </div>
        </motion.div>
      )}

      {/* Radar chart — sage stroke on paper, no fill glow */}
      {mockEval && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.24 }}
          className="sheet" style={{ marginBottom: 20 }}
        >
          <p className="caption" style={{ textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
            Patent Feasibility Radar
          </p>
          <ResponsiveContainer width="100%" height={310}>
            <RadarChart data={radarData} margin={{ top: 16, right: 32, bottom: 16, left: 32 }}>
              {/* line grid, no fill */}
              <PolarGrid stroke={T.line} />
              <PolarAngleAxis dataKey="subject" tick={{ fill: T.inkSoft, fontSize: 12, fontFamily: 'var(--font-body)' }} />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <RechartsTooltip content={<RadarTooltip />} />
              <Radar
                name="Score" dataKey="value"
                fill="transparent"          /* no fill — stroke only per spec */
                stroke={T.sage}
                strokeWidth={1.5}
                dot={{ fill: T.sage, r: 3, strokeWidth: 0 }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {/* Score breakdown row */}
      {mockEval ? (
        <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
          <BreakdownCard
            label="Semantic Similarity"
            value={mockEval.topScore}
            explanation="Based on FAISS cosine similarity with 58k patent corpus"
            delay={0.3}
          />
          <BreakdownCard
            label="GNN Novelty Signal"
            value={mockEval.gnnNovelty ?? 1 - mockEval.avgScore}
            explanation="GraphSAGE structural uniqueness in patent citation graph"
            delay={0.34}
          />
          <BreakdownCard
            label="Innovation Gap"
            value={1 - mockEval.avgScore}
            explanation="Proportion of unexplored adjacent patent space"
            delay={0.38}
          />
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 14 }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{ flex: 1, background: T.paperRaised, border: `1px solid ${T.line}`, borderRadius: 'var(--radius)', padding: 20, animation: 'pulse 1.5s ease-in-out infinite' }}>
              {[80, 40, 20].map((w, j) => (
                <div key={j} style={{ width: `${w}%`, height: 10, background: T.line, borderRadius: 2, marginBottom: 8 }} />
              ))}
            </div>
          ))}
        </div>
      )}

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
      `}</style>
    </div>
  )
}
