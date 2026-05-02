import fs from 'node:fs'
import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Vite configuration for Trove frontend.
 *
 * In development, proxies /api requests to the FastAPI backend on port 8001.
 * A custom server plugin serves ../locales/*.json at /locales/ so that
 * useTranslation() can fetch locale files when running without a backend
 * (VITE_MOCK_API=1 mode).
 *
 * In production, FastAPI serves the built frontend as static files.
 */
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'serve-locales',
      configureServer(server) {
        /**
         * Serve GET /locales/{locale}.json directly from the project-root
         * locales/ directory. Only active during `vite dev` — in production
         * locale files are served by the FastAPI i18n endpoint.
         */
        server.middlewares.use((req, res, next) => {
          if (!req.url?.startsWith('/locales/')) { next(); return }
          const filename = path.basename(req.url.split('?')[0])
          const filePath = path.resolve(__dirname, '..', 'locales', filename)
          if (fs.existsSync(filePath)) {
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.end(fs.readFileSync(filePath, 'utf-8'))
          } else {
            next()
          }
        })
        // Add API endpoints for mode and health
        server.middlewares.use((req, res, next) => {
          if (req.url === '/api/mode') {
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.end(JSON.stringify({ mode: 'app' }))
          } else if (req.url === '/api/health') {
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.end(JSON.stringify({ status: 'ok' }))
          } else {
            next()
          }
        })
      },
    },
  ],
  server: {
    proxy: {
      '/api': 'http://localhost:8001',
    },
  },
  build: {
    // Output directly into backend/static so the Python wheel includes the
    // compiled frontend as package-data without a separate copy step.
    outDir: '../backend/static',
    emptyOutDir: true,
  },
})
