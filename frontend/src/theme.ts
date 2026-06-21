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
 *  - Only the 9 color tokens live here. Font names, radii, and shadow strings
 *    stay in CSS.
 */
export const T = {
  paper:       '#F6F4EE',
  paperRaised: '#FBFAF6',
  ink:         '#23271F',
  inkSoft:     '#5B5F54',
  line:        '#DEDACE',
  sage:        '#5B7A66',
  indigo:      '#3E4D72',
  brass:       '#A47C3B',
  clay:        '#B5654A',
} as const

export type ThemeKey = keyof typeof T
