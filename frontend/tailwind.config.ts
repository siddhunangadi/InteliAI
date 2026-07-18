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
      },
      // Neutral base: cool steel-blue near-black (hue ~230), not generic
      // Tailwind slate -- the instrument-panel/compliance-terminal register.
      // Replaces the default `slate` scale project-wide (37 files already
      // use slate-* utilities), the single highest-leverage lever for a
      // full identity change without touching every component.
      colors: {
        slate: {
          50: '#f4f6fa',
          100: '#e7ebf3',
          200: '#d0d7e6',
          300: '#a9b4cc',
          400: '#7986a6',
          500: '#576181',
          600: '#414a66',
          700: '#2f374f',
          800: '#1c2236',
          900: '#131826',
          950: '#0a0d16',
        },
        // Primary: chronometer/instrument blue (hue ~210), the confident
        // precision accent -- primary actions, current selection, links.
        blue: {
          50: '#eef7fd',
          100: '#d7edfb',
          200: '#b0daf5',
          300: '#7cc0eb',
          400: '#43a1db',
          500: '#2183c4',
          600: '#1667a0',
          700: '#14547f',
          800: '#154568',
          900: '#163a56',
          950: '#0e2436',
        },
      },
    },
  },
  plugins: [],
}

export default config
