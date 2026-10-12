import type { Config } from 'tailwindcss'
import colors from 'tailwindcss/colors'

// A job-board look: one deep blue on white and neutral greys. `blue`, `indigo` and `brand` all
// point at the accent and `gray` at neutral, so every page shares the same palette.
const accent = {
  50: '#eef4fc',
  100: '#dce8f8',
  200: '#b9d0f0',
  300: '#8ab0e3',
  400: '#5a8bd2',
  500: '#3a6fc0',
  600: '#2557a7',
  700: '#1f4a8f',
  800: '#1b3d75',
  900: '#18335f',
  950: '#0f203d',
}

const config: Config = {
  // Only generate CSS for classes actually used in source files
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: accent,
        blue: accent,
        indigo: accent,
        gray: colors.neutral,
      },
      fontFamily: {
        sans: ['"Public Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
