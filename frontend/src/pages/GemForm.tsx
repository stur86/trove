/**
 * GemForm — full-page create/edit form for a UserTask (gem).
 *
 * Routes:
 *   /admin/gems/new          — create mode: blank form, calls gemsApi.create()
 *   /admin/gems/:id/edit     — edit mode: loads existing gem, calls gemsApi.update()
 *
 * Admin credentials are passed via React Router location.state as
 * { username, password } (set by AdminPanel when navigating here).
 * If state is missing, shows a lightweight re-auth form.
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import {
  Alert, Button, Checkbox, Label, Select, Spinner, Textarea, TextInput,
} from 'flowbite-react'
import {
  gemsApi, GEM_HUES, type OutputMode, type TaskArg, type UserTask,
} from '../api/tasks'
import GemIcon from '../components/GemIcon'

type AuthState = { username: string; password: string }

/** Blank UserTask used as a starting point for the create form. */
function blankGem(): UserTask {
  return {
    id: '',
    name: '',
    description: '',
    hue: 'indigo',
    template: '',
    args: [],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
  }
}

/** Blank StringArg for the "Add argument" button. */
function blankStringArg(): TaskArg {
  return { type: 'string', name: '', description: '', default: '', _key: crypto.randomUUID() }
}

export default function GemForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const isEdit = Boolean(id)

  // Admin credentials — prefer navigation state, fall back to local re-auth
  const [auth, setAuth] = useState<AuthState>(
    (location.state as AuthState | null) ?? { username: '', password: '' },
  )
  const [authReady, setAuthReady] = useState(Boolean(location.state))

  const [gem, setGem] = useState<UserTask>(blankGem())
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // In edit mode, load the existing gem
  useEffect(() => {
    if (!isEdit || !id) return
    gemsApi.get(id)
      .then(g => {
        setGem({ ...g, args: g.args.map(a => ({ ...a, _key: crypto.randomUUID() })) })
        setLoading(false)
      })
      .catch(() => { setError('Gem not found.'); setLoading(false) })
  }, [id, isEdit])

  async function handleSave() {
    setError(null)
    setSaving(true)
    // Strip _key from args before sending to the API
    const cleanGem = {
      ...gem,
      args: gem.args.map(({ _key: _, ...rest }) => rest as TaskArg),
    }
    try {
      if (isEdit && id) {
        await gemsApi.update(id, cleanGem, auth.username, auth.password)
      } else {
        await gemsApi.create(cleanGem, auth.username, auth.password)
      }
      navigate('/admin')
    } catch {
      setError('Save failed. Check your credentials and try again.')
    } finally {
      setSaving(false)
    }
  }

  function updateArg(index: number, patch: Partial<TaskArg>) {
    setGem(g => {
      const args = [...g.args]
      args[index] = { ...args[index], ...patch } as TaskArg
      return { ...g, args }
    })
  }

  function removeArg(index: number) {
    setGem(g => ({ ...g, args: g.args.filter((_, i) => i !== index) }))
  }

  function addArg() {
    setGem(g => ({ ...g, args: [...g.args, blankStringArg()] }))
  }

  // Re-auth screen if credentials weren't passed via navigation state
  if (!authReady) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="w-full max-w-sm flex flex-col gap-4 bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold">Admin login required</h2>
          <div>
            <div className="mb-1"><Label htmlFor="reauth-user">Username</Label></div>
            <TextInput
              id="reauth-user"
              value={auth.username}
              onChange={e => setAuth(a => ({ ...a, username: e.target.value }))}
              autoComplete="username"
            />
          </div>
          <div>
            <div className="mb-1"><Label htmlFor="reauth-pass">Password</Label></div>
            <TextInput
              id="reauth-pass"
              type="password"
              value={auth.password}
              onChange={e => setAuth(a => ({ ...a, password: e.target.value }))}
              autoComplete="current-password"
            />
          </div>
          <Button
            color="blue"
            disabled={!auth.username || !auth.password}
            onClick={() => setAuthReady(true)}
          >
            Continue
          </Button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto flex flex-col gap-6">

        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/admin')}
            className="text-gray-400 hover:text-gray-600 text-sm"
          >
            ← Back
          </button>
          <h1 className="text-xl font-bold text-gray-900">
            {isEdit ? 'Edit gem' : 'New gem'}
          </h1>
        </div>

        {error && <Alert color="failure">{error}</Alert>}

        {/* Name */}
        <div>
          <div className="mb-1"><Label htmlFor="gem-name">Name</Label></div>
          <TextInput
            id="gem-name"
            value={gem.name}
            onChange={e => setGem(g => ({ ...g, name: e.target.value }))}
            placeholder="e.g. Summarise Text"
          />
        </div>

        {/* ID (slug) — only shown in create mode */}
        {!isEdit && (
          <div>
            <div className="mb-1"><Label htmlFor="gem-id">ID (slug)</Label></div>
            <TextInput
              id="gem-id"
              value={gem.id}
              onChange={e => setGem(g => ({ ...g, id: e.target.value }))}
              placeholder="e.g. summarise-text"
            />
          </div>
        )}

        {/* Description */}
        <div>
          <div className="mb-1"><Label htmlFor="gem-description">Description</Label></div>
          <TextInput
            id="gem-description"
            value={gem.description}
            onChange={e => setGem(g => ({ ...g, description: e.target.value }))}
            placeholder="Short description shown on the gem card"
          />
        </div>

        {/* Hue picker */}
        <div>
          <div className="mb-2"><Label>Hue</Label></div>
          <div className="flex flex-wrap gap-2">
            {GEM_HUES.map(hue => (
              <button
                key={hue}
                onClick={() => setGem(g => ({ ...g, hue }))}
                title={hue}
                className={`rounded p-1 border-2 transition-colors ${
                  gem.hue === hue
                    ? 'border-gray-800'
                    : 'border-transparent hover:border-gray-300'
                }`}
              >
                <GemIcon hue={hue} size={28} />
              </button>
            ))}
          </div>
        </div>

        {/* Template */}
        <div>
          <div className="mb-1"><Label htmlFor="gem-template">Template</Label></div>
          <Textarea
            id="gem-template"
            value={gem.template}
            onChange={e => setGem(g => ({ ...g, template: e.target.value }))}
            placeholder="Jinja2 template — use {{ variable_name }} for arguments"
            rows={6}
            className="font-mono text-sm"
          />
        </div>

        {/* Arguments */}
        <div className="flex flex-col gap-3">
          <Label>Arguments</Label>

          {gem.args.map((arg, i) => (
            <div key={arg._key ?? i} className="border border-gray-200 rounded-lg p-4 flex flex-col gap-3 bg-white">
              <div className="flex gap-3 items-start">
                {/* Type toggle */}
                <div className="shrink-0">
                  <div className="mb-1"><Label htmlFor={`arg-type-${i}`}>Type</Label></div>
                  <Select
                    id={`arg-type-${i}`}
                    value={arg.type}
                    onChange={e => {
                      const newType = e.target.value as 'string' | 'choice'
                      if (newType === 'choice' && arg.type === 'string') {
                        updateArg(i, { type: 'choice', options: [] } as Partial<TaskArg>)
                      } else if (newType === 'string' && arg.type === 'choice') {
                        const { options: _, ...rest } = arg as { options: string[] } & Omit<TaskArg, 'type'>
                        setGem(g => {
                          const args = [...g.args]
                          args[i] = { ...rest, type: 'string' } as TaskArg
                          return { ...g, args }
                        })
                      }
                    }}
                  >
                    <option value="string">String</option>
                    <option value="choice">Choice</option>
                  </Select>
                </div>
                {/* Name */}
                <div className="flex-1">
                  <div className="mb-1"><Label htmlFor={`arg-name-${i}`}>Name</Label></div>
                  <TextInput
                    id={`arg-name-${i}`}
                    value={arg.name}
                    onChange={e => updateArg(i, { name: e.target.value })}
                    placeholder="variable_name"
                    sizing="sm"
                  />
                </div>
                {/* Remove button */}
                <button
                  onClick={() => removeArg(i)}
                  className="mt-6 text-gray-400 hover:text-red-500 text-lg leading-none"
                  title="Remove argument"
                >
                  ×
                </button>
              </div>

              {/* Description + default */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <div className="mb-1"><Label htmlFor={`arg-desc-${i}`}>Description</Label></div>
                  <TextInput
                    id={`arg-desc-${i}`}
                    value={arg.description}
                    onChange={e => updateArg(i, { description: e.target.value })}
                    placeholder="Shown as field hint"
                    sizing="sm"
                  />
                </div>
                <div className="w-32">
                  <div className="mb-1"><Label htmlFor={`arg-default-${i}`}>Default</Label></div>
                  <TextInput
                    id={`arg-default-${i}`}
                    value={arg.default}
                    onChange={e => updateArg(i, { default: e.target.value })}
                    sizing="sm"
                  />
                </div>
              </div>

              {/* Choice options (only for choice args) */}
              {arg.type === 'choice' && (
                <div>
                  <div className="mb-1"><Label htmlFor={`arg-choices-${i}`}>Options (one per line)</Label></div>
                  <Textarea
                    id={`arg-choices-${i}`}
                    value={arg.options.join('\n')}
                    onChange={e =>
                      updateArg(i, {
                        options: e.target.value.split('\n').map(s => s.trim()).filter(Boolean),
                      })
                    }
                    rows={3}
                  />
                </div>
              )}
            </div>
          ))}

          <Button color="light" size="sm" onClick={addArg}>
            + Add argument
          </Button>
        </div>

        {/* Capability flags */}
        <div className="flex flex-col gap-2">
          <Label>Capabilities</Label>
          <div className="flex items-center gap-2">
            <Checkbox
              id="has-image"
              checked={gem.has_image}
              onChange={e => setGem(g => ({ ...g, has_image: e.target.checked }))}
            />
            <Label htmlFor="has-image">Accepts image input</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="has-audio"
              checked={gem.has_audio}
              onChange={e => setGem(g => ({ ...g, has_audio: e.target.checked }))}
            />
            <Label htmlFor="has-audio">Accepts audio input</Label>
          </div>
        </div>

        {/* Output mode */}
        <div>
          <div className="mb-1"><Label htmlFor="output-mode">Output mode</Label></div>
          <Select
            id="output-mode"
            value={gem.output_mode}
            onChange={e => setGem(g => ({ ...g, output_mode: e.target.value as OutputMode }))}
            className="w-48"
          >
            <option value="text">Text</option>
            <option value="structured">Structured (JSON)</option>
          </Select>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pb-8">
          <Button color="blue" disabled={saving} onClick={handleSave}>
            {saving ? <Spinner size="sm" /> : (isEdit ? 'Save changes' : 'Create gem')}
          </Button>
          <Button color="light" onClick={() => navigate('/admin')}>
            Cancel
          </Button>
        </div>

      </div>
    </div>
  )
}
