import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          deep:    '#080d18',
          base:    '#0a0f1e',
          card:    '#0f172a',
          elevated:'#111827',
        },
        'border-default': '#1e293b',
        'border-accent':  '#4338ca',
        violet: {
          DEFAULT: '#6366f1',
          light:   '#a5b4fc',
          dark:    '#4338ca',
          muted:   '#1e1b4b',
        },
        purple: {
          DEFAULT: '#8b5cf6',
          light:   '#c4b5fd',
          muted:   '#1a1040',
        },
        cyan: {
          DEFAULT: '#06b6d4',
          light:   '#22d3ee',
          muted:   '#0c2a2a',
        },
        emerald: {
          DEFAULT: '#22c55e',
          light:   '#4ade80',
          muted:   '#0a1f14',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4)',
      },
    },
  },
  plugins: [],
} satisfies Config
