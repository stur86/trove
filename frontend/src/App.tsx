import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import Admin from './pages/Admin'
import Setup from './pages/Setup'
import { ollamaApi } from './api/ollama'

/**
 * Guard component for /admin.
 *
 * Checks Ollama status on mount. If Ollama is not fully set up
 * (installed + running + model built), redirects to /setup so the
 * user cannot reach the admin page before setup is complete.
 * Shows a loading indicator while the check is in flight.
 */
function AdminRoute() {
  const navigate = useNavigate()
  const [ready, setReady] = useState<boolean | null>(null)

  useEffect(() => {
    ollamaApi.status().then(s => {
      if (s.installed && s.running && s.model_pulled) {
        setReady(true)
      } else {
        navigate('/setup', { replace: true })
      }
    })
  }, [navigate])

  if (ready === null) return <div style={{ padding: '2rem' }}>Loading...</div>
  return <Admin />
}

/**
 * Root application component.
 *
 * Routing:
 *   /setup  — Ollama install flow and system check (first-run page)
 *   /admin  — Server configuration (model picker, context window); guarded
 *   *       — Redirects to /setup by default
 *
 * /admin is protected by AdminRoute: direct navigation redirects to /setup
 * unless Ollama is confirmed installed, running, and the model is built.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/setup" element={<Setup />} />
        <Route path="/admin" element={<AdminRoute />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
