import type { Config } from 'tailwindcss'
import colors from 'tailwindcss/colors'

// One accent colour (pine green) on warm neutrals. `blue`, `indigo` and `brand` all point at
// the accent and `gray` at warm stone, so every page shares the same palette.
const pine = {
  50: '#f0f7f3',
  100: '#dcede3',
  200: '#bbdcc9',
  300: '#8ec3a7',
  400: '#5ea381',
  500: '#3d8764',
  600: '#2c6d4f',
  700: '#245840',
  800: '#1f4735',
  900: '#1a3b2d',
  950: '#0d2119',
}

const config: Config = {
  // Only generate CSS for classes actually used in source files
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: pine,
        blue: pine,
        indigo: pine,
        gray: colors.stone,
      },
      fontFamily: {
        sans: ['"Public Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
