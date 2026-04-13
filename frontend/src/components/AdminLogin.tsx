/**
 * AdminLogin — standalone login card used by AdminPanel and GemForm.
 *
 * Renders a username/password form inside a Flowbite Card. The caller
 * supplies an async onSubmit handler; this component handles the
 * submitting state and re-enables the button once the promise settles.
 */
import { useState } from 'react'
import { Card, Label, TextInput, Button, Alert } from 'flowbite-react'

/** Props for AdminLogin. */
type Props = {
  /** Called when the user submits the form. Should throw on auth failure. */
  onSubmit: (username: string, password: string) => Promise<void>
  /** When true, shows an "Invalid credentials" alert below the form. */
  loginError?: boolean
  /** Card heading. Defaults to 'Admin login'. */
  title?: string
}

/** Returns true if the current hostname is allowed for admin access. */
export function isAllowedAdmin(): boolean {
  return ['localhost', '127.0.0.1'].includes(window.location.hostname);
}

/** Reusable admin login card with username, password, and submit button. */
export default function AdminLogin({ onSubmit, loginError, title }: Props) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <h1 className="text-xl font-bold text-center">{title ?? 'Admin login'}</h1>
        <form
          onSubmit={async e => {
            e.preventDefault()
            setSubmitting(true)
            try {
              await onSubmit(username, password)
            } finally {
              setSubmitting(false)
            }
          }}
          className="flex flex-col gap-4"
        >
          <div>
            <div className="mb-2"><Label htmlFor="login-username">Username</Label></div>
            <TextInput
              id="login-username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div>
            <div className="mb-2"><Label htmlFor="login-password">Password</Label></div>
            <TextInput
              id="login-password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              color={loginError ? 'failure' : undefined}
            />
          </div>
          {loginError && <Alert color="failure">Invalid credentials</Alert>}
          <Button color="blue" type="submit" disabled={!username || !password || submitting}>
            {submitting ? 'Signing in...' : 'Sign in'}
          </Button>
        </form>
      </Card>
    </div>
  )
}
