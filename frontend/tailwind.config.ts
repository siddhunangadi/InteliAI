import type { Config } from 'tailwindcss'
import defaultTheme from 'tailwindcss/defaultTheme'

const config: Config = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
      },
      letterSpacing: {
        tight: '-0.02em',
        tighter: '-0.035em',
      },
      boxShadow: {
        premium: '0 1px 2px rgba(0,0,0,0.4), 0 8px 24px -8px rgba(0,0,0,0.5)',
        glow: '0 0 0 1px rgba(124,92,240,0.4), 0 8px 32px -8px rgba(98,56,232,0.5)',
      },
      backdropBlur: {
        xs: '2px',
      },
      // True near-black neutrals (Vercel-register, minimal chroma, faint
      // violet tint toward the primary hue) -- overrides the default
      // `slate` scale project-wide (~40 files use slate-* utilities), the
      // single highest-leverage lever for a full identity change.
      colors: {
        slate: {
          50: '#f6f6f9',
          100: '#ececf3',
          200: '#d6d6e4',
          300: '#b0b0c9',
          400: '#8484a3',
          500: '#5e5e79',
          600: '#46465d',
          700: '#313142',
          800: '#1a1a24',
          900: '#101015',
          950: '#08080b',
        },
        // Primary: punchy indigo-violet -- premium/Linear-Vercel register,
        // deliberately not generic SaaS blue. Primary actions, current
        // selection, focus rings, links.
        blue: {
          50: '#f1eefe',
          100: '#e1dafd',
          200: '#c3b6fb',
          300: '#9f88f7',
          400: '#7c5cf0',
          500: '#6238e8',
          600: '#4f28c9',
          700: '#4020a3',
          800: '#351c80',
          900: '#2c1a63',
          950: '#1a0f3d',
        },
        // Accent: warm coral/rose, used sparingly (gradient highlights,
        // rare emphasis) -- never a primary-action color.
        accent: {
          400: '#fb7a9b',
          500: '#f4507a',
          600: '#dc3563',
        },
      },
    },
  },
  plugins: [],
}

export default config
