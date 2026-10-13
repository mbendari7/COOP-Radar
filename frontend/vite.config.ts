import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The browser calls /api on this same origin and Vite passes it on to FastAPI,
    // so session cookies stay normal and there is no CORS trouble.
    // `python start.py --dev` sets API_PROXY_TARGET to the API server it starts
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    // jsdom lets React components draw in tests
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
  },
})
