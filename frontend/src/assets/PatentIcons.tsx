import { useLayoutEffect, useRef } from 'react'

/**
 * PatentIcons — 6 custom single-weight line SVGs
 *
 * Prop contract (shared):
 *   size?:    number   — px, width & height. Default 24.
 *   color?:   string   — stroke color. Default 'currentColor'.
 *   animate?: boolean  — stroke-draw reveal on mount. Default true.
 *                        Set false for static contexts (sidebar logo, section markers)
 *                        to avoid redrawing on every mount.
 *
 * Animation: strokeDashoffset 100% → 0 over 700ms cubic-bezier(0.4,0,0.2,1),
 * once on mount. Skipped automatically when prefers-reduced-motion is set.
 */

interface PatentIconProps {
  size?:    number
  color?:   string
  animate?: boolean
}

function useStrokeDraw(animate: boolean) {
  const ref = useRef<SVGSVGElement>(null)

  useLayoutEffect(() => {
    if (!animate) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const svg = ref.current
    if (!svg) return

    const paths = svg.querySelectorAll<SVGGeometryElement>('path, circle, line, polyline, rect, ellipse')
    paths.forEach((el) => {
      try {
        const len = el.getTotalLength()
        el.style.strokeDasharray  = String(len)
        el.style.strokeDashoffset = String(len)
        el.style.animation = `stroke-draw 700ms cubic-bezier(0.4,0,0.2,1) forwards`
      } catch {
        // getTotalLength not supported on this element — skip
      }
    })
  }, [animate])

  return ref
}

const STROKE = 1.5
const CAPS: React.SVGProps<SVGSVGElement> = {
  fill:           'none',
  strokeWidth:    STROKE,
  strokeLinecap:  'round',
  strokeLinejoin: 'round',
}

// ── Wireframe lightbulb — query / idea ──────────────────────────────────────
export function IdeaIcon({ size = 24, color = 'currentColor', animate = true }: PatentIconProps) {
  const ref = useStrokeDraw(animate)
  return (
    <svg ref={ref} width={size} height={size} viewBox="0 0 24 24" stroke={color} {...CAPS} aria-hidden>
      <circle cx="12" cy="9" r="5" />
      <line x1="12" y1="14" x2="12" y2="17" />
      <line x1="9"  y1="9"  x2="9"  y2="11" />
      <line x1="12" y1="4"  x2="12" y2="2"  />
      <line x1="7"  y1="5.5" x2="5.5" y2="4" />
      <line x1="17" y1="5.5" x2="18.5" y2="4" />
      <line x1="6"  y1="9"  x2="4"  y2="9"  />
      <line x1="18" y1="9"  x2="20" y2="9"  />
      <line x1="10" y1="17" x2="14" y2="17" />
      <line x1="10.5" y1="19.5" x2="13.5" y2="19.5" />
    </svg>
  )
}

// ── Concentric circles + crosshair — FAISS similarity sweep ─────────────────
export function FAISSIcon({ size = 24, color = 'currentColor', animate = true }: PatentIconProps) {
  const ref = useStrokeDraw(animate)
  return (
    <svg ref={ref} width={size} height={size} viewBox="0 0 24 24" stroke={color} {...CAPS} aria-hidden>
      <circle cx="12" cy="12" r="2"  />
      <circle cx="12" cy="12" r="5"  />
      <circle cx="12" cy="12" r="9"  />
      <line x1="12" y1="3"  x2="12" y2="1"  />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="3"  y1="12" x2="1"  y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
    </svg>
  )
}

// ── 3 nodes + 2 edges — knowledge graph ──────────────────────────────────────
export function KGIcon({ size = 24, color = 'currentColor', animate = true }: PatentIconProps) {
  const ref = useStrokeDraw(animate)
  return (
    <svg ref={ref} width={size} height={size} viewBox="0 0 24 24" stroke={color} {...CAPS} aria-hidden>
      <circle cx="12" cy="5"  r="2.5" />
      <circle cx="5"  cy="18" r="2.5" />
      <circle cx="19" cy="18" r="2.5" />
      <line x1="10.1" y1="7.1"  x2="6.8"  y2="15.9" />
      <line x1="13.9" y1="7.1"  x2="17.2" y2="15.9" />
      <line x1="7.5"  y1="18"   x2="16.5" y2="18"   />
    </svg>
  )
}

// ── Two stacked bars with displacement arrow — GNN re-rank ──────────────────
export function GNNIcon({ size = 24, color = 'currentColor', animate = true }: PatentIconProps) {
  const ref = useStrokeDraw(animate)
  return (
    <svg ref={ref} width={size} height={size} viewBox="0 0 24 24" stroke={color} {...CAPS} aria-hidden>
      {/* top bar — before */}
      <line x1="4" y1="8"  x2="16" y2="8"  />
      {/* bottom bar — after (shorter) */}
      <line x1="4" y1="15" x2="11" y2="15" />
      {/* displacement arrow */}
      <polyline points="14,18 17,15 14,12" />
      <line x1="17" y1="15" x2="20" y2="15" />
    </svg>
  )
}

// ── 6-point compass rosette — novelty score ───────────────────────────────────
export function NoveltyIcon({ size = 24, color = 'currentColor', animate = true }: PatentIconProps) {
  const ref = useStrokeDraw(animate)
  // Six points around a centre circle, connected to form a rosette
  const pts = Array.from({ length: 6 }, (_, i) => {
    const a = (i * 60 - 90) * (Math.PI / 180)
    return [12 + 8 * Math.cos(a), 12 + 8 * Math.sin(a)] as [number, number]
  })
  return (
    <svg ref={ref} width={size} height={size} viewBox="0 0 24 24" stroke={color} {...CAPS} aria-hidden>
      <circle cx="12" cy="12" r="2.5" />
      {pts.map(([x, y], i) => (
        <line key={i} x1="12" y1="12" x2={x} y2={y} />
      ))}
      {pts.map(([x, y], i) => {
        const [nx, ny] = pts[(i + 1) % 6]
        return <line key={`e${i}`} x1={x} y1={y} x2={nx} y2={ny} />
      })}
    </svg>
  )
}

// ── Rectangle with folded corner + 3 text lines — patent document / logo ────
export function PatentDocIcon({ size = 24, color = 'currentColor', animate = true }: PatentIconProps) {
  const ref = useStrokeDraw(animate)
  return (
    <svg ref={ref} width={size} height={size} viewBox="0 0 24 24" stroke={color} {...CAPS} aria-hidden>
      {/* Document outline with folded top-right corner */}
      <path d="M5 2 H16 L19 5 V22 H5 Z" />
      <polyline points="16,2 16,5 19,5" />
      {/* Three text lines */}
      <line x1="8" y1="9"  x2="16" y2="9"  />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="13" y2="17" />
    </svg>
  )
}
