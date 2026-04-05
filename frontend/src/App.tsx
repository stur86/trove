import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Spinner } from 'flowbite-react'
import { get } from './api/client'
import AdminPanel from './pages/AdminPanel'
import GemForm from './pages/GemForm'
import GemRunner from './pages/GemRunner'
import ManageDashboard from './pages/ManageDashboard'
import SetupWizard from './pages/SetupWizard'
import TaskShell from './pages/TaskShell'

/**
 * Root application component.
 *
 * Fetches GET /api/mode on load to determine which surface to render.
 * Setup mode exposes the setup wizard and management dashboard.
 * App mode exposes the task runner shell and the admin panel.
 */
export default function App() {
  const [mode, setMode] = useState<'setup' | 'app' | null>(null)

  useEffect(() => {
    get<{ mode: string }>('/mode')
      .then(({ mode: m }) => setMode(m as 'setup' | 'app'))
      .catch(() => setMode('app'))
  }, [])

  if (mode === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <BrowserRouter>
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
    </BrowserRouter>
  )
}
