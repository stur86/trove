import { lazy, Suspense, useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Spinner } from 'flowbite-react'
import { get } from './api/client'
import { fetchSession } from './api/session'

const AdminPanel = lazy(() => import('./pages/AdminPanel'))
const GemForm = lazy(() => import('./pages/GemForm'))
const GemRunner = lazy(() => import('./pages/GemRunner'))
const ManageDashboard = lazy(() => import('./pages/ManageDashboard'))
const SetupWizard = lazy(() => import('./pages/SetupWizard'))
const TaskShell = lazy(() => import('./pages/TaskShell'))

/**
 * Root application component.
 *
 * Fetches a session token first (GET /api/session), then GET /api/mode to
 * determine which surface to render. The session token is stored in module
 * memory and injected into every subsequent API call by client.ts.
 *
 * Setup mode exposes the setup wizard and management dashboard.
 * App mode exposes the task runner shell and the admin panel.
 */
export default function App() {
  const [mode, setMode] = useState<'setup' | 'app' | null>(null)
  const [sessionError, setSessionError] = useState(false)

  useEffect(() => {
    fetchSession()
      .then(() => get<{ mode: string }>('/mode'))
      .then(({ mode: m }) => setMode(m as 'setup' | 'app'))
      .catch((err) => {
        // If session fetch fails we cannot communicate with the server at all.
        if (err instanceof Error && err.message.includes('Session')) {
          setSessionError(true)
        } else {
          // Mode fetch failed — fall back to app mode so the UI renders.
          setMode('app')
        }
      })
  }, [])

  if (sessionError) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white text-center p-8">
        <p>Could not connect to the Trove server. Please make sure it is running and reload the page.</p>
      </div>
    )
  }

  if (mode === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Suspense fallback={
        <div className="flex items-center justify-center min-h-screen bg-gray-900">
          <Spinner size="lg" />
        </div>
      }>
        <Routes>
          {mode === 'setup' ? (
            <>
              <Route path="/" element={<SetupWizard />} />
              <Route path="/manage" element={<ManageDashboard />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </>
          ) : (
            <>
              <Route path="/" element={<TaskShell />} />
              <Route path="/gems/:id" element={<GemRunner />} />
              <Route path="/admin" element={<AdminPanel />} />
              <Route path="/admin/gems/new" element={<GemForm />} />
              <Route path="/admin/gems/:id/edit" element={<GemForm />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </>
          )}
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
