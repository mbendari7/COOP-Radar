import type { Config } from 'tailwindcss'

// The look started as a Canadian post office: postal red for the top bar and the main buttons,
// airmail blue for links and anything picked, and an ink grey. It is now a little more modern,
// with soft rounded corners, pill chips, white cards on a light grey page and Inter for text.
// blue and indigo point at airmail blue and brand at postal red so older class names still fit.

const post = {
  50: '#fdf1f0',
  100: '#fbe0de',
  200: '#f6c1bd',
  300: '#ee968f',
  400: '#e2655b',
  500: '#d43f33',
  600: '#c8281e',
  700: '#a81f17',
  800: '#8a1c16',
  900: '#721b16',
  950: '#3e0907',
}

const air = {
  50: '#eef2fb',
  100: '#dfe6f6',
  200: '#c3d0ee',
  300: '#9bb0e1',
  400: '#6d87cf',
  500: '#4a64bd',
  600: '#2f4aa3',
  700: '#1e3a8a',
  800: '#1c3272',
  900: '#1b2c5c',
  950: '#111a38',
}

// Greys pulled slightly toward the ink so they never look flat
const ink = {
  50: '#f6f7fa',
  100: '#eef1f6',
  200: '#dde2eb',
  300: '#c4cbd8',
  400: '#98a1b3',
  500: '#687185',
  600: '#4e5667',
  700: '#3a4150',
  800: '#252a34',
  900: '#16181d',
  950: '#0d0f13',
}

const config: Config = {
  // Only make CSS for classes the source files really use
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        post,
        air,
        brand: post,
        blue: air,
        indigo: air,
        gray: ink,
        slate: ink,
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Archivo', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      // Soft corners. Chips, dots and postmarks are fully round
      borderRadius: {
        none: '0',
        sm: '6px',
        DEFAULT: '8px',
        md: '8px',
        lg: '10px',
        xl: '14px',
        '2xl': '18px',
        full: '9999px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(22, 24, 29, 0.06)',
        DEFAULT: '0 2px 6px rgba(22, 24, 29, 0.08)',
        md: '0 4px 12px rgba(22, 24, 29, 0.10)',
        lg: '0 10px 24px rgba(22, 24, 29, 0.12)',
        xl: '0 18px 40px rgba(22, 24, 29, 0.18)',
      },
    },
  },
  plugins: [],
}

export default config
