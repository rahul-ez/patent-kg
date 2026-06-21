import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { usePipelineStore } from '../store/usePipelineStore'
import { IdeaIcon } from '../assets/PatentIcons'
import { T } from '../theme'

// ── Types ──────────────────────────────────────────────────────────────────
interface Overlap { patent_id: string; title: string; similarity: number; domain: string }
interface NovelDirection { direction: string; feasibility: 'High' | 'Medium' | 'Low' }

// ── Mock data generator ────────────────────────────────────────────────────
function useMockImprovements() {
  const pipelineResult = usePipelineStore((s) => s.pipelineResult)
  return useMemo(() => {
    if (!pipelineResult) return null
    const hits    = pipelineResult.results
    const topHits = hits.slice(0, 3)
    return {
      overlaps: topHits.map((h) => ({
        patent_id:  h.patent_id,
        title:      h.title,
        similarity: Math.round((h.semantic_score ?? 0) * 100),
        domain:     h.domain,
      })) as Overlap[],
      weakAreas: [
        'Insufficient differentiation in core algorithmic approach',
        `High overlap with existing patents in the ${hits[0]?.domain || 'target'} domain`,
        'Limited novelty in hardware interface layer',
      ],
      suggestions: [
        'Focus on a specific edge-case application that existing patents do not cover',
        'Combine the core concept with an emerging technology (e.g., edge computing, federated learning)',
        'Target a different geographic market or regulatory regime where IP space is less crowded',
        'Introduce a novel training data paradigm specific to your domain',
      ],
      novelDirections: [
        { direction: 'Privacy-preserving variant using differential privacy',  feasibility: 'High'   },
        { direction: 'On-device inference with quantized model weights',        feasibility: 'Medium' },
        { direction: 'Multi-modal fusion approach combining sensor modalities', feasibility: 'Medium' },
      ] as NovelDirection[],
      lessCrowdedSpaces: [
        'Emerging markets and low-resource environments',
        'Clinical trial monitoring and regulatory compliance automation',
        'Real-time adaptation with continual learning architectures',
      ],
    }
  }, [pipelineResult])
}

// ── Similarity badge ───────────────────────────────────────────────────────
function SimBadge({ pct }: { pct: number }) {
  const color = pct >= 70 ? T.clay : pct >= 50 ? T.brass : T.inkSoft
  return (
    <span className="mono-tag" style={{ borderColor: color, color }}>
      {pct}% match
    </span>
  )
}

// ── Feasibility badge ──────────────────────────────────────────────────────
function FeasBadge({ feasibility }: { feasibility: 'High' | 'Medium' | 'Low' }) {
  const map = {
    High:   { color: T.sage },
    Medium: { color: T.brass },
    Low:    { color: T.clay },
  }
  const { color } = map[feasibility]
  return (
    <span className="mono-tag" style={{ borderColor: color, color }}>
      {feasibility} Feasibility
    </span>
  )
}

// ── Section header ─────────────────────────────────────────────────────────
function SectionHeader({ title, accentColor = T.sage, count }: { title: string; accentColor?: string; count?: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
      <h2 style={{
        fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600, color: 'var(--ink)',
        borderLeft: `2px solid ${accentColor}`, paddingLeft: 10, margin: 0,
      }}>
        {title}
      </h2>
      {count !== undefined && (
        <span className="mono-tag">{count}</span>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function ImprovementAgentPage() {
  const pipelineResult = usePipelineStore((s) => s.pipelineResult)
  const data = useMockImprovements()

  if (!pipelineResult || !data) {
    return (
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '40px 0' }}>
        <div className="sheet" style={{ padding: 48, textAlign: 'center' }}>
          <IdeaIcon size={40} color={T.line} animate={false} />
          <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--ink)', fontWeight: 600, marginBottom: 8, marginTop: 16 }}>No Analysis Yet</h2>
          <p style={{ color: 'var(--ink-soft)', marginBottom: 24 }}>Run a patent analysis to generate improvement suggestions.</p>
          <Link to="/analyze" className="btn-primary" style={{ textDecoration: 'none' }}>Start Analysis →</Link>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>

      {/* Page header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 28 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', fontWeight: 600, color: 'var(--ink)', marginBottom: 8 }}>
          AI Improvement Agent
        </h1>
        <p style={{ color: 'var(--ink-soft)', fontSize: '0.9rem', marginBottom: 10 }}>
          Analyzing patent landscape to identify gaps and suggest novel directions for your idea.
        </p>
        {/* Disclaimer — mono caption in bordered box */}
        <span className="mono-tag" style={{ fontSize: '0.7rem' }}>
          Analysis derived from retrieval patterns — LLM agent integration coming soon
        </span>
      </motion.div>

      {/* ── Section 1: Overlaps — clay left rule ──────────────────────────── */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} style={{ marginBottom: 28 }}>
        <SectionHeader title="Overlap Detected" accentColor={T.clay} count={data.overlaps.length} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data.overlaps.map((ov, idx) => (
            <motion.div
              key={ov.patent_id}
              initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.08 + idx * 0.04 }}
              className="sheet-sm"
              style={{ borderLeft: `2px solid ${T.clay}` }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: T.inkSoft }}>{ov.patent_id}</span>
                <SimBadge pct={ov.similarity} />
                {ov.domain && <span className="tag-keyword" style={{ borderColor: T.indigo, color: T.indigo }}>{ov.domain}</span>}
              </div>
              <p style={{ color: 'var(--ink)', fontWeight: 500, fontSize: '0.88rem', lineHeight: 1.5 }}>{ov.title}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ── Section 2: Weak Areas — brass left rule ───────────────────────── */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.14 }} style={{ marginBottom: 28 }}>
        <SectionHeader title="Identified Weak Areas" accentColor={T.brass} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data.weakAreas.map((area, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.17 + idx * 0.04 }}
              className="sheet-sm"
              style={{ borderLeft: `2px solid ${T.brass}` }}
            >
              <p style={{ color: 'var(--ink-soft)', fontSize: '0.87rem', lineHeight: 1.6 }}>{area}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ── Section 3: Suggestions — sage left rule ───────────────────────── */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.21 }} style={{ marginBottom: 28 }}>
        <SectionHeader title="Suggested Modifications" accentColor={T.sage} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data.suggestions.map((sug, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.24 + idx * 0.04 }}
              className="sheet-sm"
              style={{ borderLeft: `2px solid ${T.sage}`, display: 'flex', gap: 14, alignItems: 'flex-start' }}
            >
              <span style={{ fontFamily: 'var(--font-display)', fontStyle: 'italic', fontWeight: 600, fontSize: '1.1rem', color: T.sage, lineHeight: 1.2, flexShrink: 0, width: 22 }}>
                {idx + 1}
              </span>
              <p style={{ color: 'var(--ink)', fontSize: '0.88rem', lineHeight: 1.65 }}>{sug}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ── Section 4: Novel Directions — sage left rule ──────────────────── */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} style={{ marginBottom: 28 }}>
        <SectionHeader title="Novel Directions to Explore" accentColor={T.sage} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
          {data.novelDirections.map((nd, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.33 + idx * 0.05 }}
              className="sheet-sm"
              style={{ borderLeft: `2px solid ${T.sage}`, display: 'flex', flexDirection: 'column', gap: 10 }}
            >
              <p style={{ fontWeight: 600, color: 'var(--ink)', fontSize: '0.88rem', lineHeight: 1.5, flex: 1 }}>
                {nd.direction}
              </p>
              <FeasBadge feasibility={nd.feasibility} />
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ── Section 5: Less Crowded Spaces — sage left rule ──────────────── */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.37 }} style={{ marginBottom: 28 }}>
        <SectionHeader title="Less Crowded Innovation Spaces" accentColor={T.sage} />
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {data.lessCrowdedSpaces.map((space, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.4 + idx * 0.05 }}
              className="tag-keyword"
              style={{ padding: '6px 12px', fontSize: '0.84rem' }}
            >
              {space}
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ── Coming Soon footer — plain bordered mono note ─────────────────── */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.44 }}
        style={{
          padding: '16px 20px',
          background: T.paperRaised,
          border: `1px solid ${T.line}`,
          borderRadius: 'var(--radius)',
          marginBottom: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <IdeaIcon size={14} color={T.inkSoft} animate={false} />
          <p style={{ color: 'var(--ink)', fontWeight: 600, fontSize: '0.88rem' }}>Full AI Improvement Agent</p>
          <span className="mono-tag">Coming Soon</span>
        </div>
        <p className="caption" style={{ lineHeight: 1.7, maxWidth: 640 }}>
          The complete improvement pipeline uses an LLM agent that reads the top patents,
          identifies specific claim gaps, and generates targeted modification suggestions.
          This requires the Gemini improvement module to be activated.
          Generated text will be visually distinguished with a thin{' '}
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: T.inkSoft }}>
            AI-generated analysis
          </span>{' '}
          label so it is never confused with computed retrieval / KG / GNN results.
        </p>
      </motion.div>
    </div>
  )
}
