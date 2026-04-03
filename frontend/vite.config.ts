import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Vite configuration for Trove frontend.
 *
 * In development, proxies /api requests to the FastAPI backend on port 8000
 * so the frontend dev server (port 5173) can call the API without CORS issues.
 *
 * In production, FastAPI serves the built frontend as static files, so
 * the proxy is not needed.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward all /api requests to the FastAPI backend during development
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
