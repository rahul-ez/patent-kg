# Redesign Spec — Patent Intelligence Platform

This spec restyles the existing app only. No routes, state, hooks, API calls, or data flow change — every section below maps onto the components and pages already described in `frontend_context.md`. Treat this as a design handoff to whoever touches the Tailwind classes and component JSX.

---

## 1. Design Direction

**The problem with the current UI:** dark background, violet-to-cyan gradient text, glowing cards — this is the default "AI product" look right now. It reads as a demo, not as a research instrument. A patent researcher who lives in Lens.org, Espacenet, and USPTO Public PAIR will not trust a tool that looks like a crypto landing page.

**The new thesis:** design this like an instrument for examining prior art, not a SaaS marketing site. Patents are technical-legal documents with a specific visual vocabulary — line-drawing figures, numbered claims, classification codes, official stamps and seals, hairline rules on off-white paper. We borrow *that* vocabulary instead of the generic AI-product vocabulary. The platform should feel closer to a well-made archive or examiner's workbench than a startup pitch.

**Signature element:** every diagram, icon, and loading state in the product is drawn as a *technical line illustration* — thin, single-weight strokes that animate by drawing themselves in (`stroke-dasharray` reveal), the way a patent figure or a pen plotter would render a schematic. This replaces all the floating gradient orbs and glow effects. It's the one consistent, ownable visual idea running through the whole app.

---

## 2. Design Tokens

### Color

Soft, paper-toned, desaturated. No neon, no glow shadows.

| Token | Hex | Use |
|---|---|---|
| `paper` | `#F6F4EE` | page background |
| `paper-raised` | `#FBFAF6` | card surfaces, sits just above paper |
| `ink` | `#23271F` | primary text — warm near-black, not pure black |
| `ink-soft` | `#5B5F54` | secondary text, captions |
| `line` | `#DEDACE` | hairline borders, dividers |
| `sage` | `#5B7A66` | primary accent — actions, links, active states |
| `indigo` | `#3E4D72` | secondary accent — used sparingly for KG/graph context |
| `brass` | `#A47C3B` | tertiary accent — used only for "novelty" / scoring highlights |
| `clay` | `#B5654A` | risk / overlap warning state (replaces red) |

Rules:
- No glow box-shadows. Shadows are soft, short, and warm-grey (`0 1px 2px rgba(35,39,31,0.06)`), used only to lift a card slightly off the page.
- No gradient text. Headlines are solid `ink`, set in the display serif.
- Color carries *meaning* (sage = action/healthy, brass = score/novelty, clay = overlap/risk, indigo = graph/structural) rather than decoration. Don't introduce a fifth accent for variety.

### Type

| Role | Face | Notes |
|---|---|---|
| Display (h1, page titles, the gradient-text replacements) | **Playfair Display**, weights 500/600 | Italic numerals used for figure/stat callouts (e.g. *58,428* patents indexed) |
| Body | **Source Sans 3** (or Public Sans) | Regular/medium only. This is the workhorse — keep it quiet. |
| Data / technical (patent IDs, CPC codes, scores, query text) | **IBM Plex Mono** | Replaces JetBrains Mono. Slightly warmer, reads less "code editor." |

Type scale (desktop):
- Display XL — 56px / 1.05, Playfair 600 — landing hero only
- Display L — 36px / 1.1, Playfair 600 — page titles
- Display M — 24px / 1.2, Playfair 500 — section headers
- Body — 16px / 1.6, Source Sans 400
- Caption / label — 13px / 1.4, Source Sans 500, letter-spacing 0.02em, `ink-soft`
- Mono data — 14px, Plex Mono 400

Import:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;1,500&family=Source+Sans+3:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### Spacing, radius, borders

- Radius: 4px on cards and buttons, not 12px. Patents don't have rounded corners. Sharper, document-like.
- Borders: 1px solid `line`, not glow. Cards are defined by a hairline, not a shadow.
- Spacing scale: 8 / 16 / 24 / 40 / 64. Generous vertical rhythm between sections — minimal means *fewer* elements, each given more room, not smaller padding everywhere.

### Motion

- Page transitions: a single 200ms fade + 8px rise (keep Framer Motion, just shorten the distance and remove any scale/blur).
- The signature motion is the **stroke-draw reveal**: SVG icons and diagrams animate `stroke-dashoffset` from full to 0 over 600–900ms on mount, easing `cubic-bezier(0.4, 0, 0.2, 1)`. Use once per element, on entry — never looping, never ambient.
- No floating/orbiting background elements. No particle effects. No infinite pulsing glows.
- Hover states: a 1px border color shift (`line` → `sage`) and a 2px upward translate, 120ms. That's it.
- Respect `prefers-reduced-motion`: disable the stroke-draw and rise/fade, swap to instant opacity.

---

## 3. Iconography

All icons are custom single-weight line SVGs (1.5px stroke, round joins, no fill) drawn in the same hand as the patent-figure motif — not Lucide's default icon set, even though Lucide stays in the dependency list as a fallback for anything not worth custom-drawing.

Build a small custom set for the recurring concepts, each as a simple technical glyph:
- **Idea / query** — a single lightbulb rendered as a wireframe (circle + filament lines), not solid
- **Semantic retrieval (FAISS)** — overlapping concentric circles with a crosshair, like a radar/similarity sweep
- **Knowledge graph** — three nodes and connecting lines, drawn in the exact node-link style the KG page already uses, just restyled
- **GNN re-rank** — two stacked bars with an arrow showing displacement (the delta concept)
- **Novelty score** — a six-pointed compass/rosette, evoking a patent office seal
- **Patent document** — a simple rectangle with a folded corner and three text lines, like a document icon on official forms

Use these consistently as section markers instead of decorative gradients. Each one only appears where it's semantically relevant — not as generic bullet decoration.

---

## 4. Layout & Component Patterns (shared across pages)

These replace the current `.card`, `.badge-keyword`, `.badge-entity`, `.btn-primary` etc. Functionality is identical — only the visual treatment changes.

**Card → "Sheet"**
- `paper-raised` background, 1px `line` border, 4px radius, 24px padding, soft 1px shadow.
- No `.card-hover` glow. Hover = border shifts to `sage`, shadow gets very slightly deeper (still no color glow).
- Cut any sheet that exists purely as a wrapper with no distinct content (the audit below flags candidates).

**Badges → "Tags"**
- Replace pill badges with small bordered rectangles (4px radius, not full pill) — keywords in `sage` outline, entities in `indigo` outline, both on transparent/`paper` background, text in matching ink color. No filled-background pills. This reads as classification labels (like CPC tags) rather than chat-UI chips.

**Buttons**
- Primary: solid `ink` background, `paper` text, 4px radius, no gradient. Hover: `sage`.
- Secondary: transparent background, 1px `ink` border, `ink` text. Hover: border + text shift to `sage`.
- Remove all gradient buttons.

**Top nav / sidebar**
- `paper-raised` background instead of near-black. Logo as a small line-drawn mark (e.g. the document-with-corner icon + wordmark in Playfair).
- Status badge: small mono-text label in a thin bordered rectangle (`Running` / `Complete` / `Error`), color via text + border only, never a filled glow chip.
- Sidebar nav links: current page indicated by a left-side 2px `sage` rule, not a background fill.

**Score bars / progress**
- Thin (4px) horizontal bars, `line`-colored track, `sage` or `brass` fill depending on context (semantic vs. novelty). No gradient fills.

---

## 5. Page-by-Page Notes

Only calling out what changes. Anything not mentioned keeps its current structure and data bindings.

### `LandingPage.tsx` (`/`)
- Drop the floating orbs and mesh background entirely — replace with a single, large, faint line-drawn patent-figure illustration (e.g., a schematic "idea → patent" diagram) positioned behind the hero text, very low contrast (`line` color stroke at 60% opacity), stroke-draws in on load.
- Hero h1 in Playfair, solid `ink`, no gradient.
- "Pipeline architecture" steps: keep the 6-step sequence (this is a real process, so numbering is justified), but render as a horizontal line-and-node diagram (your KG node-link visual language, reused) instead of 6 separate glowing cards with arrows between them. One diagram, not six slabs.
- Stats row (58,428 patents / 768-dim / GraphSAGE / <10s): keep, but set the numbers in italic Playfair, labels in mono caps underneath. This is the one place italic display numerals earn their keep.
- Tech-stack pill row: cut it from the redesign, or move it to a footer as plain mono text. It's implementation detail, not something a researcher needs on a landing page.

### `IdeaInputPage.tsx` (`/analyze`)
- Textarea styled like a document field: hairline border, `paper-raised` background, focus state = border shifts to `ink`, no glow ring.
- Example ideas: keep as a list, but style as a simple bordered list with the document icon, not buttons-as-cards.
- Top-K select and GNN-mode toggle: keep functionality, restyle the segmented control with sharp 4px corners and `ink` borders instead of the violet-gradient active state — active segment gets solid `ink` fill, `paper` text.

### `PipelineProgressPage.tsx` (`/pipeline`)
- Replace the 6 glowing stage cards with a single vertical or horizontal line diagram — a "process strip" — where the active stage's icon does the stroke-draw animation and completed stages show a solid checkmark glyph (also line-drawn). This is the clearest place to use the signature motion: each stage's icon draws itself in as it activates.
- Keep the existing `setInterval` simulation and store-driven completion/error logic untouched.

### `NLPResultsPage.tsx` (`/results/nlp`)
- Source badge (Gemini vs spaCy): plain mono-text tag, bordered, not filled.
- Keywords/entities: tags per §4, not pills.
- FAISS query text block: keep as a mono `<pre>` block but on `paper-raised` with a hairline border — drop the cyan-glow monospace treatment.

### `RetrievalResultsPage.tsx` (`/results/patents`)
- Metric cards at top: reduce to the ones that matter (indexed count, top score, result count) in one slim stat row — not separate heavy sheets each.
- Patent cards: this page's content is genuinely list-like (ranked results), so keep the card-per-patent pattern, but apply the Sheet treatment, score bars per §4, and replace gradient score chips with mono-text scores.

### `KGVisualizationPage.tsx` (`/results/graph`)
- This is the most "diagram-native" page already — keep ReactFlow, but restyle node colors to the token palette (patent = `ink`/`paper-raised` fill with `ink` border, company = `indigo`, cpc = `brass`, inventor = `sage`) and switch the background from dark dots to a faint `line`-colored dot grid on `paper`.
- KG stat strip: mono-text counts in a single thin bordered row, not separate pill badges.

### `GNNAnalysisPage.tsx` (`/results/gnn`)
- Sliders: restyle track/thumb to `line`/`ink`, remove the blue/purple slider theming — use `sage` for semantic, `brass` for GNN/novelty consistently (this pairing should now hold everywhere novelty appears, including the future novelty-score feature).
- Recharts bars: same two-color logic, flat fills, no gradients, thin 1px outline matching the Sheet border style for visual consistency with the rest of the page.
- Re-ranking table: keep the grid, swap rank-up/down/same colors to `sage`/`clay`/`ink-soft` with a simple line-drawn arrow glyph instead of colored triangle characters.

### `EvaluationDashboardPage.tsx` (`/results/evaluation`) — and future novelty/LLM analysis
- Radar chart: restyle to `sage` stroke on `paper`, no fill glow.
- The 4 metric cards can likely consolidate to one row of compact stat blocks rather than 4 large separate sheets — apply the "cut slabs that don't earn their space" rule here specifically, since this page currently has the most cards-for-cards'-sake.
- This is the natural home for the upcoming novelty score: render it as the compass/rosette icon next to a Plex Mono numeric score in `brass`, consistent with the GNN page's novelty color.
- Keep the "scores derived from retrieval metrics" disclaimer — set it in `ink-soft` mono caption, bordered box, not a colored badge. When LLM analysis replaces the mock, this is also where a "source: LLM analysis" vs "derived metric" mono tag should live, so users can tell generated commentary from computed scores.

### `ImprovementAgentPage.tsx` (`/results/improvements`) — and future LLM analysis
- Five sections are fine conceptually (overlap, weak areas, suggestions, novel directions, less-crowded spaces) since each is a distinct analytical category — but tone down the visual differentiation: same Sheet style throughout, distinguished by a small left-edge color rule (`clay` for overlap, `brass` for weak areas, `sage` for suggestions/novel directions/less-crowded) rather than full background-color treatments per section.
- "Coming Soon" footer: plain bordered note in mono caption, not a card.
- When the real LLM analysis lands, keep this same section structure — it's a reasonable place for generated reasoning to live, just make sure generated text is visually distinguished (e.g., a thin `ink-soft` left border + small "AI-generated analysis" mono label) so it's never confused with the computed retrieval/KG/GNN results elsewhere on the page.

---

## 6. What Is Not Changing

- Routing, Zustand store shape, TanStack Query hooks, Axios client, API contracts — untouched.
- Recharts, ReactFlow, Framer Motion stay as the underlying libraries; only their visual configuration (colors, stroke widths, shadows, easing) changes.
- Data flow described in `frontend_context.md` is unaffected. This spec is purely about color, type, iconography, card treatment, and motion.

---

## 7. Quick Reference — CSS Variables

```css
:root {
  --paper: #F6F4EE;
  --paper-raised: #FBFAF6;
  --ink: #23271F;
  --ink-soft: #5B5F54;
  --line: #DEDACE;
  --sage: #5B7A66;
  --indigo: #3E4D72;
  --brass: #A47C3B;
  --clay: #B5654A;

  --font-display: 'Playfair Display', serif;
  --font-body: 'Source Sans 3', sans-serif;
  --font-mono: 'IBM Plex Mono', monospace;

  --radius: 4px;
  --shadow-sheet: 0 1px 2px rgba(35, 39, 31, 0.06);
}
```
