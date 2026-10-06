/**
 * theme.ts — JS design token constants
 *
 * Single source of truth for token hex values consumed by components that
 * must pass colors as JS props (ReactFlow node style={}, Recharts fill/stroke,
 * MiniMap nodeColor, slider accentColor, etc.).
 *
 * Rules:
 *  - Any design-token hex in a JS prop MUST come from T.*, never hardcoded inline.
 *  - index.css :root variables and this object are the only two places token
 *    hexes appear. Keep them in sync manually.
 *  - Only the color tokens live here. Font names, radii, and shadow strings
 *    stay in CSS.
 */
export const T = {
  // Surfaces
  bgPage:         '#F3F5F5',
  bgStructural:   '#EDF1F1',
  bgCard:         '#FFFFFF',
  bgInset:        '#F0F4F4',
  bgHoverTint:    '#E5EFED',

  // Borders
  borderHairline: '#D9E0E2',
  borderAnchor:   '#899A9F',
  borderTechnical:'#6F8087',

  // Text
  textPrimary:    '#26343A',
  textSecondary:  '#5B6870',
  textTertiary:   '#63737B',
  textOnDark:     '#FFFFFF',

  // Accents
  accentSage:     '#11675F',
  accentIndigo:   '#49616F',
  accentBrass:    '#88611B',
  accentClay:     '#AC3F39',

  // Solid-ink surfaces
  surfaceInk:     '#11675F',
  surfaceInkHover:'#0C514B',

  // Legacy mappings for backwards-compatibility with pages we haven't touched yet
  paper:          '#F3F5F5',
  paperRaised:    '#FFFFFF',
  ink:            '#26343A',
  inkSoft:        '#5B6870',
  line:           '#D9E0E2',
  sage:           '#11675F',
  indigo:         '#49616F',
  brass:          '#88611B',
  clay:           '#AC3F39'
} as const

export type ThemeKey = keyof typeof T
