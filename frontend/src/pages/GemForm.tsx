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
 *
 * Arguments are derived automatically from `{{ variable_name }}` placeholders in
 * the template. All derived args are free-text StringArgs — no manual editing.
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Checkbox, Label, Select, Spinner, Textarea, TextInput,
} from 'flowbite-react'
import {
  gemsApi, GEM_HUES, type OutputMode, type TaskArg, type UserTask,
} from '../api/tasks'
import { appApi } from '../api/app'
import AdminLogin from '../components/AdminLogin'
import GemIcon from '../components/GemIcon'

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

/**
 * Extract unique variable names from a Jinja2-style template string.
 * Matches `{{ variable_name }}` placeholders (whitespace-tolerant, word chars only).
 * Preserves first-occurrence order and deduplicates.
 */
function extractTemplateVars(template: string): string[] {
  const seen = new Set<string>()
  const vars: string[] = []
  for (const match of template.matchAll(/{{\s*(\w+)\s*}}/g)) {
    if (!seen.has(match[1])) { seen.add(match[1]); vars.push(match[1]) }
  }
  return vars
}

/**
 * Rebuild the args list from the template, keeping free-text StringArgs.
 * Order follows first appearance in the template.
 */
function deriveArgs(template: string): TaskArg[] {
  return extractTemplateVars(template).map(name => ({
    type: 'string' as const,
    name,
    description: '',
    default: '',
  }))
}

export default function GemForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  // Admin cookie state — check whether admin cookie is present
  const [authReady, setAuthReady] = useState(false)

  const [gem, setGem] = useState<UserTask>(blankGem())
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // In edit mode, load the existing gem
  useEffect(() => {
    if (!isEdit || !id) return
    gemsApi.get(id)
      .then(g => {
        setGem(g)
        setLoading(false)
      })
      .catch(() => { setError('Gem not found.'); setLoading(false) })
  }, [id, isEdit])

  useEffect(() => {
    appApi.checkAdminValid()
      .then(res => { if (res.admin_auth === 'true') setAuthReady(true) })
      .catch(() => {})
  }, [])

  async function handleSave() {
    setError(null)
    setSaving(true)
    // Args are always freshly derived from the template at save time
    const cleanGem: UserTask = { ...gem, args: deriveArgs(gem.template) }
    try {
      if (isEdit && id) {
        await gemsApi.update(id, cleanGem)
      } else {
        await gemsApi.create(cleanGem)
      }
      navigate('/admin')
    } catch {
      setError('Save failed. Check your credentials and try again.')
    } finally {
      setSaving(false)
    }
  }

  // Re-auth screen if admin cookie is not present
  if (!authReady) {
    return (
      <AdminLogin
        onSubmit={async (u, p) => {
          try {
            await appApi.login(u, p)
            setAuthReady(true)
          } catch {
            setError('Login failed')
          }
        }}
        loginError={false}
        title="Admin login required"
      />
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
            placeholder="Jinja2 template — use {{ variable_name }} for user inputs"
            rows={6}
            className="font-mono text-sm"
          />
        </div>

        {/* Detected variables — read-only, derived from template */}
        {extractTemplateVars(gem.template).length > 0 && (
          <div>
            <div className="mb-2"><Label>Detected inputs</Label></div>
            <div className="flex flex-wrap gap-2">
              {extractTemplateVars(gem.template).map(v => (
                <span
                  key={v}
                  className="inline-block bg-gray-100 text-gray-700 text-xs font-mono px-2 py-1 rounded"
                >
                  {v}
                </span>
              ))}
            </div>
            <p className="mt-1 text-xs text-gray-400">
              Each placeholder becomes a free-text field for the user.
            </p>
          </div>
        )}

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
