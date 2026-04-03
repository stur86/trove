import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Admin from './pages/Admin'
import Setup from './pages/Setup'

/**
 * Root application component.
 *
 * Routing:
 *   /setup  — Ollama install flow and system check (first-run page)
 *   /admin  — Server configuration (model picker, context window)
 *   *       — Redirects to /setup by default
 *
 * The Setup page redirects to /admin automatically once Ollama is
 * installed, running, and the model is built.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/setup" element={<Setup />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
