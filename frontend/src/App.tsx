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
 * Shown in app mode when the admin account has never been configured.
 * Instructs end-users to ask their IT manager to complete the setup wizard.
 */
function SetupIncompletePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white text-center p-8 gap-6">
      <h1 className="text-3xl font-bold">Trove is not ready yet</h1>
      <p className="text-gray-400 max-w-md text-lg">
        This system hasn't been fully configured. Please ask your IT manager to run the Trove setup before using this page.
      </p>
    </div>
  )
}

/**
 * Root application component.
 *
 * Fetches a session token first (GET /api/session), then GET /api/mode to
 * determine which surface to render. The mode response also carries
 * setup_complete — false means the admin account was never configured, in
 * which case app mode renders only the SetupIncompletePage.
 *
 * Setup mode exposes the setup wizard and management dashboard.
 * App mode exposes the task runner shell and the admin panel.
 */
export default function App() {
  const [mode, setMode] = useState<'setup' | 'app' | null>(null)
  const [setupComplete, setSetupComplete] = useState<boolean>(true)
  const [sessionError, setSessionError] = useState(false)

  useEffect(() => {
    fetchSession()
      .then(() => get<{ mode: string; setup_complete?: boolean }>('/mode'))
      .then(({ mode: m, setup_complete }) => {
        setMode(m as 'setup' | 'app')
        setSetupComplete(setup_complete ?? true)
      })
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
          ) : !setupComplete ? (
            <Route path="*" element={<SetupIncompletePage />} />
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
