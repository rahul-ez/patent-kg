# Patent Intelligence Platform — Redesign Specification V3
## "The Examiner's Docket" — Implementation-Ready Design System

Scope: visual system only. No routing, store, hooks, API, or data-flow changes. This document supersedes the V1 token spec and incorporates the V2 critique findings as concrete, implementable rules.

---

## 1. Design Direction

**Thesis:** The application is a live patent examination case file, not a dashboard. Every analysis run is a docket: it has a reference number, numbered sections (like claims), a primary exhibit per stage, and supporting technical exhibits filed alongside it. The user is not "viewing results" — they are working a case file at an examiner's desk.

This governs every structural decision below:
- Each analysis gets a generated **Reference Number** (`PI-YYYY-MMDD-X`, client-generated from the existing query timestamp/ID, no backend change required) displayed persistently near the page title.
- Each page's primary content block is treated as the **Exhibit** for that pipeline stage — exactly one per page, visually dominant.
- Section headers are **numbered clauses** (`§1`, `§2`, `§3`), not generic headers.
- Raw/technical data (FAISS queries, JSON, graph metadata) is filed as a **Technical Exhibit** — visually distinct, terminal-styled, subordinate to the narrative content.
- Empty results are recorded, not boxed — a docket notes "none found," it doesn't draw an empty exhibit frame.

---

## 2. Design Tokens

### 2.1 Color

```css
:root {
  /* Surfaces */
  --bg-page:        #F6F4EE;  /* Level 0 — page background */
  --bg-structural:  #EDE9DF;  /* Level 1 — sidebar, navbar */
  --bg-card:        #FBFAF6;  /* Level 2/3 — card surfaces */
  --bg-inset:       #EFEAE0;  /* Level -1 — recessed technical panels */
  --bg-hover-tint:  rgba(91, 122, 102, 0.06); /* sage at 6% — hover/active tint */

  /* Borders */
  --border-hairline:  #DEDACE; /* standard card border, dividers */
  --border-anchor:     #23271F; /* primary/anchor card border, used at 100% but only 1.5px */
  --border-technical:  #8A8C7E; /* technical panel left marker */

  /* Text */
  --text-primary:   #23271F;  /* ink — headings, primary body */
  --text-secondary: #5B5F54;  /* ink-soft — supporting body, captions */
  --text-tertiary:  #8A8C7E;  /* ink-dim — metadata labels, disabled, placeholders */
  --text-on-dark:   #F6F4EE;  /* for solid-ink buttons/badges */

  /* Accents — semantic, not decorative */
  --accent-sage:    #5B7A66;  /* primary action, semantic score, "up", active nav */
  --accent-indigo:  #3E4D72;  /* graph/structural context (KG nodes, entities) */
  --accent-brass:   #A47C3B;  /* novelty/score/technical-data signal */
  --accent-clay:    #B5654A;  /* risk, overlap, "down", error */

  /* Solid-ink surfaces (buttons, primary CTA) */
  --surface-ink:        #23271F;
  --surface-ink-hover:  #5B7A66; /* solid-ink buttons hover to sage, not lighten */
}
```

Usage rule: `--bg-card` is used for both Level 2 and Level 3 surfaces — they are differentiated by **border weight + shadow + padding**, not by a different fill color. `--bg-inset` is reserved exclusively for technical/recessed panels — never used for a standard card.

### 2.2 Typography

```css
:root {
  --font-display: 'Playfair Display', serif;
  --font-body:    'Source Sans 3', sans-serif;
  --font-mono:    'IBM Plex Mono', monospace;
}
```

| Role | Font | Size | Weight | Line-height | Letter-spacing | Case |
|---|---|---|---|---|---|---|
| Page title (h1) | Playfair Display | 44px | 600 | 1.05 | -0.01em | Sentence |
| Page eyebrow/kicker | IBM Plex Mono | 11px | 500 | 1.2 | 0.14em | UPPERCASE |
| Section title (§N) | Playfair Display | 20px | 600 | 1.2 | 0 | Sentence |
| Section number (§N) | IBM Plex Mono | 13px | 600 | 1.2 | 0.04em | — |
| Subsection title | Source Sans 3 | 13px | 600 | 1.3 | 0.06em | UPPERCASE |
| Body text | Source Sans 3 | 16px | 400 | 1.6 | 0 | Sentence |
| Body — emphasis/quote | Playfair Display | 18px | 500 italic | 1.5 | 0 | Sentence |
| Metadata label | IBM Plex Mono | 10.5px | 500 | 1.2 | 0.12em | UPPERCASE |
| Metadata value | IBM Plex Mono | 13px | 500 | 1.3 | 0 | — |
| Mono technical text | IBM Plex Mono | 13.5px | 400 | 1.65 | 0 | — |
| Caption / footnote | Source Sans 3 | 12.5px | 500 | 1.4 | 0.01em | Sentence |
| Status label | IBM Plex Mono | 10.5px | 600 | 1.2 | 0.1em | UPPERCASE |
| Button label | Source Sans 3 | 14px | 600 | 1.2 | 0.01em | Sentence |

Font import (replaces existing):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;1,500&family=Source+Sans+3:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

### 2.3 Elevation System (5 levels)

```css
:root {
  --radius-card:    4px;
  --radius-inset:   3px;
  --radius-control: 4px;

  --shadow-l2: 0 2px 6px rgba(35, 39, 31, 0.08);
  --shadow-l3: 0 4px 14px rgba(35, 39, 31, 0.12);
  --shadow-l3-highlight: inset 0 1px 0 rgba(255, 255, 255, 0.5);
  --shadow-structural: inset -1px 0 0 rgba(35, 39, 31, 0.07); /* sidebar right seam */
  --shadow-navbar: 0 1px 0 rgba(35, 39, 31, 0.08);
  --shadow-inset: inset 0 1px 3px rgba(35, 39, 31, 0.10);
}
```

| Level | Surface | Background | Border | Shadow | Padding | Used for |
|---|---|---|---|---|---|---|
| **0** | Page | `--bg-page` + grain texture (see §9) | none | none | — | App background only |
| **1** | Structural | `--bg-structural` | none | `--shadow-structural` (sidebar) / `--shadow-navbar` (topnav) | — | Sidebar, top nav |
| **2** | Standard card | `--bg-card` | 1px solid `--border-hairline` | `--shadow-l2` | 20px | Most content cards |
| **3** | Primary/Anchor card | `--bg-card` | 1.5px solid `--border-anchor` | `--shadow-l3` + `--shadow-l3-highlight` | 32px | Exactly one per page — the page's hero exhibit |
| **-1** | Inset/recessed | `--bg-inset` | none (left marker only, see §4.4) | `--shadow-inset` | 16px | Technical/terminal output panels |

---

## 3. Layout System

### 3.1 Spacing scale
`4 / 8 / 12 / 16 / 24 / 32 / 48 / 64` (px). No arbitrary values outside this scale.

### 3.2 Grid
- Max content width: 1320px, centered.
- Sidebar: fixed 240px (up from 210px).
- Main content padding: 48px horizontal / 40px top on desktop; 24px / 24px on mobile (<768px).
- Two-zone content grid where applicable: primary column ~66%, secondary/metadata column ~34%, 32px gutter. (Used on NLP Analysis, Retrieval, Evaluation pages — see §7.)

### 3.3 Vertical rhythm rules
| Relationship | Gap |
|---|---|
| Eyebrow → Title | 8px |
| Title → Metadata strip | 16px |
| Metadata strip → first content section | 40px |
| Within a content group (e.g., card → its caption) | 8–12px |
| Between sibling cards in the same section | 16px |
| Between distinct page sections (§N → §N+1) | 48px |
| Before final CTA banner | 64px |

### 3.4 Card spacing & alignment rules
- All card left/right edges align to the 1320px grid columns — no card is allowed to be "approximately" aligned with its neighbor.
- All metadata strip values share one baseline (set via `align-items: baseline` on the flex row, not visually eyeballed).
- Internal card padding is fixed per elevation level (20 / 32 / 16px — see §2.3 table) — never varied ad hoc per page.

### 3.5 Density rule
Default to **higher density, fewer cards** — combine related fields into one structural pattern (e.g., the metadata strip) rather than one card per field. A page should never have more than one Level-3 card and no more than 4–5 Level-2 cards visible without scrolling.

---

## 4. Structural UI Patterns

### 4.1 Metadata Strip (replaces all floating metric boxes + standalone badges)

Single full-width horizontal bar. Exact spec:

```
height: 44px
background: transparent (sits directly on page bg, no card chrome)
border-bottom: 1px solid var(--border-hairline)
display: flex; align-items: baseline; justify-content: space-between
padding: 0 0 12px 0
```

Left cluster (flex row, gap 24px, each field separated by a 1px vertical divider `var(--border-hairline)` at 60% height):
```
[ MODEL          ]   [ SOURCE              ]   [ KEYWORDS ]   [ ENTITIES ]
[ PatentSBERTa   ]   [ spaCy Fallback      ]   [ 4        ]   [ 0        ]
   ↑ label: mono 10.5px uppercase ink-dim, value: mono 13px ink, stacked 2px apart
```

Right side: Reference number, right-aligned, single line:
```
REF. PI-2026-0617-A     ← mono 11px, ink-tertiary, letter-spacing 0.06em
```

Rule: the metadata strip is the **only** place these values appear. Never duplicate model/source/count info inside a separate badge or card elsewhere on the page.

### 4.2 Card Types (four distinct types — never one universal card)

**A. Primary / Anchor Card**
```css
background: var(--bg-card);
border: 1.5px solid var(--border-anchor);
border-radius: var(--radius-card);
box-shadow: var(--shadow-l3), var(--shadow-l3-highlight);
padding: 32px;
```
Header: `§N` (mono, brass, 13px) + Title (Playfair 600, 20px) on one line, no chip/count badge (anchor cards don't need a count — they ARE the content). Exactly one per page.

**B. Secondary Card**
```css
background: var(--bg-card);
border: 1px solid var(--border-hairline);
border-radius: var(--radius-card);
box-shadow: var(--shadow-l2);
padding: 20px;
```
Header: `§N` (mono, ink-tertiary, 13px) + Title (Playfair 600, 16px) + optional right-aligned count chip (bordered rectangle, mono 12px). Used for supporting content (Keywords, score breakdowns, expansion panels).

**C. Technical / Terminal Card**
```css
background: var(--bg-inset);
border: none;
border-left: 2px solid var(--border-technical);
border-radius: var(--radius-inset);
box-shadow: var(--shadow-inset);
padding: 16px;
font-family: var(--font-mono);
```
Header row: mono caps label (11px, ink-tertiary) + collapse chevron, NOT a Playfair title — technical cards never use the display font. Body in mono 13.5px, `--text-secondary`. Used for: FAISS query text, raw JSON, graph metadata, CPC code lists.

**D. Empty State**
No card chrome at all. Pattern:
```
[icon, 14px, ink-tertiary, line-drawn, animate=false]  No entities detected for this query.
```
Single line, `--text-tertiary`, Source Sans 13px italic, inline — never a bordered box, never matches the height of a populated sibling card. If an empty state sits beside a populated card (e.g. Entities beside Keywords), it occupies a plain-text column, not an equal card.

### 4.3 Sidebar — full specification

```
width: 240px
background: var(--bg-structural)
box-shadow: var(--shadow-structural)   /* right-edge seam */
display: flex; flex-direction: column
```

**Logo zone** (top, 64px height):
```
padding: 20px
border-bottom: 1px solid var(--border-hairline)
display: flex; align-items: center; gap: 10px
[PatentDocIcon, 18px, animate=false] [wordmark: Playfair 600, 16px, ink]
```

**Nav section** (below logo, 24px top padding):
```
"RESULTS" label: mono 10.5px uppercase, ink-tertiary, padding: 0 20px, margin-bottom: 8px
```

**Docket tab** (the "Your idea" preview — styled as a case-file tab, not a generic card):
```css
margin: 0 16px 20px 16px;
padding: 12px 14px;
background: var(--bg-card);
border-left: 3px solid var(--accent-sage);
border-radius: 0 var(--radius-card) var(--radius-card) 0;
box-shadow: var(--shadow-l2);
```
Content: `DOCKET` label (mono 10px uppercase, ink-tertiary) above truncated idea text (Playfair 500 italic, 13px, ink, 2-line clamp).

**Nav list items** (40px height each):
```css
display: flex; align-items: center; gap: 12px;
padding: 10px 20px;
font: Source Sans 14px 500;
color: var(--text-secondary);
```
- Default: icon `--text-tertiary`, label `--text-secondary`.
- Hover: `background: var(--bg-hover-tint)`.
- Active: `background: var(--bg-hover-tint)`; `border-left: 2px solid var(--accent-sage)` (inset, doesn't shift layout — use `box-shadow: inset 2px 0 0 var(--accent-sage)`); label weight 600, color `--text-primary`; icon color `--accent-sage`.

### 4.4 Technical Output Panels — exact styling

Applies to: FAISS query text, JSON/graph metadata, CPC code dumps, raw model output.

```css
background: var(--bg-inset);
border-left: 2px solid var(--border-technical);
border-radius: var(--radius-inset);
box-shadow: var(--shadow-inset);
padding: 16px;
```
Header row: `[chevron-icon] LABEL` in mono 11px uppercase ink-tertiary, letter-spacing 0.1em, clickable to expand/collapse (existing collapse behavior preserved). Body: mono 13.5px, `--text-secondary`, line-height 1.65, no italics (italics reserved for Playfair pull-quotes). If displaying JSON, use 2-space indent and color only `--accent-brass` for keys, `--text-secondary` for values — no full syntax-highlighting rainbow.

---

## 5. Typography Hierarchy Rules

| Element | Pattern | Example |
|---|---|---|
| Page header | Eyebrow + H1 + metadata strip | `§01 — LANGUAGE PROCESSING` / `NLP Analysis` / strip |
| Section header (Secondary/Anchor card) | `§N` mono + Playfair title, same line, baseline-aligned | `§2  Extracted Keywords` |
| Subsection header (inside a card) | Source Sans 13px 600 uppercase, no number | `BY DOMAIN` |
| Metadata label | Mono 10.5px uppercase, ink-tertiary | `KEYWORDS` |
| Status label | Mono 10.5px uppercase 600, bordered tag, color-coded | `RUNNING`, `COMPLETE` |

Section numbering sequence is **per page**, restarting at §1 — it represents that page's own document structure, not a global counter across the app. (e.g., NLP Analysis page: §1 Preprocessed Text, §2 Extracted Keywords, §3 Named Entities, §4 FAISS Query Text.)

Page eyebrow text maps to pipeline stage, fixed list:
```
/results/nlp          → §01 — LANGUAGE PROCESSING
/results/patents       → §02 — SEMANTIC RETRIEVAL
/results/graph          → §03 — KNOWLEDGE GRAPH EXPANSION
/results/gnn             → §04 — GRAPH-BASED RE-RANKING
/results/evaluation     → §05 — PATENT EVALUATION
/results/improvements   → §06 — IMPROVEMENT ANALYSIS
```

---

## 6. Component Rules (strict — apply to every page)

1. Every page has exactly **one** Level-3 anchor card. No page may have zero or more than one.
2. Empty states never receive card chrome and never occupy the same width/height as a populated sibling.
3. All cross-field metadata (model, source, counts, timestamps) lives in the Metadata Strip — never duplicated in standalone badges.
4. Technical/raw data never uses Playfair Display — mono only, inset surface only.
5. No card may use a drop shadow stronger than `--shadow-l3` — that is the visual ceiling of the entire app.
6. Section headers are always numbered (`§N`) within their page; subsection headers are never numbered.
7. No two sibling cards of unequal data volume (e.g., 4 keywords vs. 0 entities) may render at equal width/height — the lesser one demotes to plain text.
8. Accent colors are semantic, never decorative: sage = positive/primary action, brass = score/novelty, indigo = graph/structural, clay = risk/negative. No accent is ever chosen "because it looks nice here."
9. Every analysis run displays its Reference Number in the page header — consistently positioned, top-right of the title block.
10. The sidebar's active-state indicator is always the inset left rule + tint + weight-600 label combination — never a solid background fill.
11. Buttons: exactly two types — solid-ink primary, hairline-border secondary. No third button style is introduced anywhere.
12. All icons are line-only, `fill: none`, 1.5px stroke — no filled icon glyphs anywhere in the product.
13. Card border-radius is always 4px (cards) or 3px (inset panels) — never a third radius value.
14. No gradients, anywhere, on any element, for any reason — including hover/focus states.
15. Every page's primary CTA (e.g., "View Patent Results →") is the only solid-ink-filled element below the fold — it must remain the single highest-contrast actionable element per page.
16. Score/numeric values that drive comparison (FAISS score, novelty score, combined score) are always set in mono, right-aligned within their row, sharing a column baseline.
17. Collapsible technical panels default to **collapsed** on first view if their content exceeds 3 lines — narrative content is never hidden by default.
18. Hover states change border color and/or background tint only — never shadow blur radius or element scale.
19. Maximum of one stroke-draw icon animation may play per viewport at a time on mount — staggered, never simultaneous, to avoid visual noise.
20. Page titles are always followed by the metadata strip within 16px — no other element may be inserted between them.

---

## 7. Page-by-Page Specification

### 7.1 LandingPage (`/`)
- **Hero:** Eyebrow `RESEARCH-GRADE PATENT INTELLIGENCE` (mono, sage) → H1 Playfair 600 56px, solid ink, two-line max → subtitle Source Sans 18px ink-secondary, max-width 560px.
- Behind hero text: single faint line-drawn patent-figure SVG (stroke `--border-hairline` at 50% opacity), stroke-draws in once on load, `animate=true`.
- CTAs: solid-ink primary ("Analyze an idea"), hairline secondary ("View architecture"). No gradient, no glow.
- **Pipeline architecture:** one horizontal node-link diagram (6 nodes: NLP → Embedding → FAISS → GNN → KG → Evaluation), drawn as a single SVG with line connectors, not 6 separate cards. Each node is a small circle + mono label below it. This is a Secondary Card containing one diagram, not six cards.
- **Stats row:** 4 values, Playfair italic 32px numerals + mono caps 11px labels beneath, laid out in a single Level-1-background strip (matches Metadata Strip pattern), not individual cards.
- Tech stack list: footer, single line, mono 12px, `--text-tertiary`, separated by middots.
- Footer: plain caption, ink-tertiary.

### 7.2 IdeaInputPage (`/analyze`)
- Eyebrow `§00 — CASE INTAKE` / H1 `New Analysis`.
- Two-column grid: left 66% = input column, right 34% = example ideas column (Secondary Card, header `§1 Example Filings`).
- Textarea: Level 2 card treatment, focus state = border to `--border-anchor` (not sage, not glow) + the card promotes to Level 3 elevation on focus (shadow increases) — gives tactile "this is now the active document" feedback.
- Below textarea: a compact horizontal control strip (Top-K select + GNN mode toggle) styled like the Metadata Strip pattern (bordered fields, mono labels) rather than freeform form controls.
- Example ideas: plain list rows (not cards) with `PatentDocIcon` (animate=false) markers, hover = background tint only.
- Submit button: solid-ink, full width on mobile, right-aligned fixed width on desktop. Error state: inline clay-bordered technical-card-style message below the button, mono label `ERROR` + Source Sans message.

### 7.3 PipelineProgressPage (`/pipeline`)
- No sidebar (full-bleed, matches current standalone behavior).
- Center column, max-width 640px: Reference Number generated and displayed at top (mono, ink-tertiary) — this is the moment the docket is "opened."
- Single vertical Level-2 card containing the 6-stage process strip (not 6 separate cards): each row = icon (stroke-draws on activation) + stage name (Source Sans 600 14px) + status label (mono, right-aligned: `PENDING` ink-tertiary 40% / `RUNNING` ink + subtle pulse on the icon only, not the row / `DONE` sage with line-drawn checkmark).
- Connector line between stages: 1px `--border-hairline`, turns sage as each stage completes (fills downward, not a glow).
- Error state: row turns clay, mono `ERROR` label, message in Source Sans below the strip in a Technical Card, plus hairline-secondary "Back to Input" button.

### 7.4 NLPResultsPage (`/results/nlp`) — reference implementation
Exact structure (see V2 critique §6 wireframe for the visual target):
1. Eyebrow `§01 — LANGUAGE PROCESSING` / H1 `NLP Analysis` / Reference Number top-right of title row.
2. Metadata Strip: Model · Source · Keywords count · Entities count, Ref. number right-aligned.
3. **Anchor Card** (§1 Preprocessed Text): Playfair italic 18px pull-quote rendering of the cleaned text, no quotation-mark glyphs needed since the italic + indentation signals quotation.
4. Two-column row, 65/35 split: **Secondary Card** (§2 Extracted Keywords, count chip) | plain-text **Empty State** column for Entities if zero, or a matching Secondary Card (§3 Named Entities) if populated.
5. **Technical Card**: FAISS Query Text, collapsed by default, mono.
6. CTA banner: Level 2 card, left-aligned message + right-aligned solid-ink button "View Patent Results →".

### 7.5 RetrievalResultsPage (`/results/patents`)
- Eyebrow `§02 — SEMANTIC RETRIEVAL`.
- Metadata Strip: Indexed count · Top score · Results returned · Ref. number.
- Anchor Card: the **top-ranked patent** gets promoted to a Level-3 card (title, abstract, full score breakdown) — this is the page's one hero exhibit, solving "all rectangles look the same" directly.
- Remaining ranked patents: Secondary Cards in a single column below, each with rank number (mono, large, ink-tertiary, left-aligned in its own 32px gutter — not inside the card), title (Source Sans 600 16px), collapsible abstract, domain tag, score bar (4px, sage fill) and mono score value right-aligned.
- Sort toggle (FAISS/GNN order): styled as two mono-label segments in a bordered control, matches Idea Input's segmented control pattern.
- CTA banner → Knowledge Graph.

### 7.6 KGVisualizationPage (`/results/graph`)
- Eyebrow `§03 — KNOWLEDGE GRAPH EXPANSION`.
- Metadata Strip: Node count · Edge count · Expansion status · Ref. number.
- Anchor Card: the ReactFlow canvas itself (full width, 520px height, Level-3 border/shadow around the canvas container) — the graph IS this page's hero exhibit.
- ReactFlow background: dot grid, dots in `--border-hairline`, on `--bg-page`.
- Node styling (via `theme.ts` constants): patent = `--bg-card` fill / `--text-primary` border; company = `--accent-indigo` border; cpc = `--accent-brass` border; inventor = `--accent-sage` border. All nodes: white-ish fill, colored border only — no solid color fills (keeps the "line diagram" language consistent even inside ReactFlow).
- Expansion results (family members, CPC siblings): Secondary Cards below the canvas, §4 / §5 numbered.

### 7.7 GNNAnalysisPage (`/results/gnn`)
- Eyebrow `§04 — GRAPH-BASED RE-RANKING`.
- Metadata Strip: GNN mode · Patents reranked · Avg. delta · Ref. number.
- Anchor Card: the "Biggest GNN Boost" callout (the single most interesting fact this page produces) — promote it to Level 3, top of page, above the sliders.
- Secondary Card: weight sliders (semantic/sage, GNN/brass), with current values shown as mono numerals right-aligned to each slider, sum validation message in clay if invalid.
- Secondary Card: Recharts bar chart — bars in sage/brass/ink, gridlines `--border-hairline`, no chart background fill.
- Re-ranking table: Technical Card treatment (mono headers, mono data cells), rank delta shown as `+3` / `−2` / `—` in mono with sage/clay/ink-tertiary color, not arrow glyphs alone — pair the glyph with the signed number for unambiguous scanning.

### 7.8 EvaluationDashboardPage (`/results/evaluation`)
- Eyebrow `§05 — PATENT EVALUATION`.
- Metadata Strip: Avg. score · Top score · Risk level · Ref. number.
- **This page's anchor card is the Radar chart** — Level 3, centered, generous internal padding (40px), sage stroke, `--border-hairline` polar grid, no fill glow, axis labels in mono 11px uppercase.
- Risk level: shown as a single bordered status tag (mono, color-coded sage/brass/clay) positioned top-right of the anchor card header — not a separate card.
- Score breakdown: 3 Secondary Cards in a row below the radar, each with a single large mono numeral (24px) + Source Sans description beneath + thin score bar.
- Disclaimer: Technical Card style, single line, mono caption: `SCORES DERIVED FROM RETRIEVAL METRICS — NOT A LEGAL OPINION`.
- When the LLM analysis layer ships: add a mono tag `SOURCE: LLM ANALYSIS` vs `SOURCE: COMPUTED` beside any value so generated commentary is never visually confused with deterministic metrics.

### 7.9 ImprovementAgentPage (`/results/improvements`)
- Eyebrow `§06 — IMPROVEMENT ANALYSIS`.
- Metadata Strip: Overlaps found · Weak areas · Novel directions suggested · Ref. number.
- **Anchor Card:** the single highest-overlap patent comparison (the most important finding on this page) — Level 3, top of page, clay-accented left marker, mono overlap percentage at 28px.
- Remaining four sections (Weak Areas, Suggested Modifications, Novel Directions, Less-Crowded Spaces) render as Secondary Cards in sequence, each numbered §2–§5, differentiated only by a 3px left-edge accent (brass / sage / sage / sage respectively — clay reserved for the anchor's overlap framing).
- Novel Directions feasibility badges: bordered mono tags, no fill.
- Footer: Technical Card, mono caption `FULL AI AGENT — IN DEVELOPMENT`, no card glow, no "coming soon" gradient banner.

---

## 8. Motion System

| Interaction | Spec |
|---|---|
| Page transition | 200ms fade + 8px rise, ease `cubic-bezier(0.4,0,0.2,1)`. No scale, no blur. |
| Card hover | Border color → `--accent-sage` (or stays `--border-anchor` for anchor cards), 120ms linear. No shadow change, no translate. |
| Button hover | Background color shift only (ink→sage / transparent→tint), 120ms. |
| Nav active state | Background tint + left rule appear instantly on route change (no transition needed — it should feel immediate, like a selection, not an animation). |
| SVG icon stroke-draw | `stroke-dashoffset` 100%→0%, 600–900ms, ease `cubic-bezier(0.4,0,0.2,1)`, fires once on mount when `animate=true`. Max one concurrent stroke-draw per viewport; stagger by 80ms if multiple icons mount together. |
| Pipeline stage activation | Icon stroke-draws (700ms) the moment a stage's status flips to `running`; on completion, checkmark glyph stroke-draws in (400ms) replacing the stage icon. |
| Loading state (data fetch) | No spinners. Use a static technical-card skeleton: a single horizontal sage-colored bar at 2px height beneath the metadata strip, indeterminate width animation (slides left-to-right, 1.2s loop, opacity-based not glow-based) — disappears once data resolves. |
| Slider drag (GNN page) | Thumb follows pointer 1:1, no lag/spring. Combined-score bar chart re-renders instantly via existing `useMemo`, no transition animation on the bars themselves (instant feedback matters more than animation here). |
| Reduced motion | All of the above collapse to instant state changes — checked via `prefers-reduced-motion` once, centrally, in the icon component and the page-transition wrapper. |

---

## 9. Premium Polish Details (micro-specifications)

1. Page background carries a 2% opacity grayscale noise texture (SVG `feTurbulence` filter or a tiled 128×128px PNG), fixed position, never on cards — gives "paper" literal substance.
2. Anchor cards get a 1px inset top highlight (`inset 0 1px 0 rgba(255,255,255,0.5)`) in addition to their drop shadow — a barely-visible "catching the light" edge.
3. Section numbers (`§N`) are always set in `--accent-brass`, mono, slightly smaller than their accompanying title — consistent across every page, a recognizable system mark.
4. Reference numbers use a monospace tabular-figure font feature (`font-variant-numeric: tabular-nums`) so digits always align in a fixed-width grid.
5. All dividers (metadata strip verticals, card internal rules) are exactly 1px, `--border-hairline`, never 2px except the sidebar active-state rule and anchor card border.
6. Score values across the entire app share one mono numeral style and are always right-aligned within their containing row — never centered, never left-aligned.
7. Hairline-secondary buttons get a 1px border, not 1.5px — only anchor cards and the sidebar active-rule use the heavier 2px+ weights, reserving "heavy line = important" as a consistent signal.
8. Empty-state icon (when used) is always the same line-drawn glyph family, 14px, `--text-tertiary`, `animate=false` — never the Lucide fallback icon set.
9. The docket tab in the sidebar uses a subtly asymmetric border-radius (`0 4px 4px 0`) to read as a "tab" protruding from the sidebar edge, reinforcing the case-file metaphor.
10. Technical Card chevrons rotate 180° on expand, 150ms, no bounce/spring easing.
11. Status labels (`RUNNING`, `COMPLETE`, `ERROR`) are always mono, always uppercase, always inside a 1px bordered rectangle with 4px/8px padding — never a filled chip.
12. CPC/classification codes anywhere in the UI are always rendered in mono with a thin brass underline-on-hover (for future linking), distinguishing them from regular keywords at a glance.
13. The "Ready to explore..." CTA banners use a single hairline-sage top border (2px) rather than a full border, visually anchoring them as a closing statement for the section above rather than a floating card.
14. Numeral "0" in any empty-count context (e.g. `ENTITIES: 0`) renders in `--text-tertiary`, not `--text-primary` — even within the metadata strip, a zero value is visually quieter than a populated one.
15. Card corner radius is applied consistently at 4px using a single CSS variable — never hand-set per component.
16. All icons share one stroke-width (1.5px) regardless of their rendered size — checked at 16px, 18px, and 24px render sizes specifically, since stroke width perception changes with scale.
17. The sidebar logo wordmark uses Playfair at a slightly tighter letter-spacing (-0.01em) than body Playfair headings — small, deliberate brand-specific type tuning distinct from content headings.
18. Vertical rhythm before/after the metadata strip is asymmetric on purpose (16px above, 40px below) — it visually "closes" the header block and "opens" the content block, reinforcing the grouping logic from §3.3.
19. Tables (re-ranking table, score breakdowns) use a 1px hairline row separator only — no zebra-striping, no cell borders, consistent with the hairline-everywhere visual language.
20. The single permitted shadow ceiling (`--shadow-l3`) is never exceeded anywhere in the app, including on hover/focus states — this constraint is what keeps "premium depth" from sliding back into "glow."
21. Focus rings (keyboard navigation) use a 2px solid `--accent-sage` outline with 2px offset — visible, accessible, but not a glow — applied uniformly via one CSS rule, not per component.
22. Mono technical text never uses italics; Playfair never uses uppercase tracking — each face is given exactly one register, never blended, so the system stays legible as "two languages: narrative and technical."

---

## 10. Implementation Notes for Engineering

- All hex values in §2.1 must be mirrored in a `theme.ts` constants module (per the earlier review) for any component requiring JS-prop colors (ReactFlow node styles, Recharts fill/stroke, MiniMap, slider accent colors). CSS custom properties and `theme.ts` are the only two locations token hexes appear.
- The Metadata Strip, the four Card types, and the Technical Output Panel should each be built as one shared component (`<MetadataStrip>`, `<Card variant="primary"|"secondary"|"technical">`, `<EmptyState>`) and reused across all 9 pages — not re-implemented per page. This is what prevents the "every page styled separately" drift that produced the V1 result.
- Reference Number generation: derive from existing `query_id` / timestamp already returned by `POST /api/pipeline/run` — format client-side as `PI-{YYYY}-{MMDD}-{shortHash}`. No backend change required.
- Section numbering (§N) is page-local static JSX, not derived from data — hardcode per page per §7 above.
