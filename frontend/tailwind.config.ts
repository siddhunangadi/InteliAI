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
      // Three fonts, three jobs (DESIGN.md "The Verbatim-Gets-Mono Rule"):
      // Inter Tight for display headlines, Inter for body/UI, IBM Plex Mono
      // for retrieved/logged data (chunk text, citations, audit rows).
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
        display: ['"Inter Tight"', 'Inter', ...defaultTheme.fontFamily.sans],
        mono: ['"IBM Plex Mono"', ...defaultTheme.fontFamily.mono],
      },
      letterSpacing: {
        tight: '-0.01em',
        tighter: '-0.02em',
      },
      borderRadius: {
        sm: '6px',
        md: '10px',
        lg: '14px',
      },
      boxShadow: {
        // The only shadow in the system -- floating/portal elements only.
        // See DESIGN.md "The Flat-at-Rest Rule": never used on static cards.
        // Warm-tinted (from ink, not pure black) to match the nude palette.
        float: '0 12px 28px rgba(43,33,24,0.16)',
      },
      // DESIGN.md palette: "The Terminal for Trust" -- warm nude/paper
      // neutrals, one accent (clay) reserved for AI activity + primary
      // actions, three status colors reserved strictly for retrieval/
      // verification/health outcomes. Light register by explicit direction.
      colors: {
        sand: '#f1e9e2',
        paper: {
          DEFAULT: '#faf6f2',
          raised: '#e9ded3',
        },
        rule: '#d9c9b8',
        ink: {
          DEFAULT: '#2b2118',
          muted: '#6b5d52',
        },
        clay: {
          DEFAULT: '#a9613f',
          hover: '#8f4e32',
        },
        status: {
          verified: '#4f7a4a',
          caution: '#9c6b1f',
          critical: '#a4402f',
        },
      },
    },
  },
  plugins: [],
}

export default config
