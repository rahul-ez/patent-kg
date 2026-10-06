import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--bg-page)',
        surface: 'var(--bg-card)',
        ink: 'var(--text-primary)',
        muted: 'var(--text-secondary)',
        line: 'var(--border-hairline)',
        action: 'var(--accent-sage)',
        caution: 'var(--accent-brass)',
        danger: 'var(--accent-clay)',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'Segoe UI', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config
