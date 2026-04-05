import { useState } from 'react'
import { Card, Label, TextInput, Button, Alert } from 'flowbite-react'

type Props = {
  onSubmit: (username: string, password: string) => Promise<void>
  loginError?: boolean
  title?: string
}

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
