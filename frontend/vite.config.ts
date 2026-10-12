import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The browser calls /api on this same origin and Vite forwards it to FastAPI,
    // so session cookies are first-party and no CORS is involved.
    // `python start.py --dev` sets API_PROXY_TARGET to the API server it starts.
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    // Use jsdom so React components can render in tests
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
  },
})
