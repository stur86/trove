# Gems — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Gems frontend: typed API client, GemIcon SVG, mock API layer, locale middleware, and all pages (TaskShell gem grid, GemRunner, AdminPanel Gems tab, GemForm).

**Architecture:** Real API clients live in `frontend/src/api/`; a parallel `mock/` layer is activated by `VITE_MOCK_API=1`. A Vite server plugin serves `locales/` at `/locales/` so `useTranslation` works without a backend. All pages use Flowbite React components exclusively; `GemIcon` is the only custom SVG.

**Tech Stack:** TypeScript, React, Vite, Flowbite React, Bun

---

### Task 1: Add `del()` to client + create `tasks.ts` API client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/api/tasks.ts`

Define all shared types (`GemHue`, `OutputMode`, `StringArg`, `ChoiceArg`, `TaskArg`, `UserTask`) and the real `gemsApi` object. The mock selector at the bottom conditionally swaps in the mock implementation.

- [ ] **Step 1: Add `del()` helper to `client.ts`**

Append to `frontend/src/api/client.ts` after the `basicAuth` export:

```ts
/**
 * Make a DELETE request. Returns void on 204, throws on error.
 * @param path API path
 * @param headers Optional additional request headers
 */
export async function del(path: string, headers?: HeadersInit): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'DELETE',
    headers: headers as Record<string, string> ?? {},
  })
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`)
}
```

- [ ] **Step 2: Create `frontend/src/api/tasks.ts`**

```ts
/**
 * Typed API client for the Gems (UserTask) domain.
 *
 * Exports gemsApi — switches to the mock implementation when
 * VITE_MOCK_API=1 is set in the environment.
 */
import { basicAuth, del, get, post, put } from './client'

// ── Types ────────────────────────────────────────────────────────────────────

/** 16 preconfigured gem hues, named after Tailwind colour palette entries. */
export type GemHue =
  | 'red' | 'orange' | 'amber' | 'yellow'
  | 'lime' | 'green' | 'emerald' | 'teal'
  | 'cyan' | 'sky' | 'blue' | 'indigo'
  | 'violet' | 'purple' | 'fuchsia' | 'rose'

/** All valid GemHue values in display order. */
export const GEM_HUES: GemHue[] = [
  'red', 'orange', 'amber', 'yellow',
  'lime', 'green', 'emerald', 'teal',
  'cyan', 'sky', 'blue', 'indigo',
  'violet', 'purple', 'fuchsia', 'rose',
]

export type OutputMode = 'text' | 'structured'

/** A free-text argument with an optional default. */
export interface StringArg {
  type: 'string'
  name: string
  description: string
  default: string
}

/** A fixed-choice argument with a list of allowed values. */
export interface ChoiceArg {
  type: 'choice'
  name: string
  description: string
  default: string
  choices: string[]
}

export type TaskArg = StringArg | ChoiceArg

/** A user-defined task with identity and display metadata. */
export interface UserTask {
  id: string
  name: string
  description: string
  hue: GemHue
  template: string
  args: TaskArg[]
  has_image: boolean
  has_audio: boolean
  output_mode: OutputMode
}

// ── Real API implementation ───────────────────────────────────────────────────

const _realGemsApi = {
  /** List all user tasks. */
  list: (): Promise<UserTask[]> =>
    get<UserTask[]>('/app/gems'),

  /** Get a single user task by slug id. Throws 404 if missing. */
  get: (id: string): Promise<UserTask> =>
    get<UserTask>(`/app/gems/${id}`),

  /** Create a new user task. Requires admin credentials. */
  create: (task: UserTask, username: string, password: string): Promise<UserTask> =>
    post('/app/admin/gems', task, { Authorization: basicAuth(username, password) })
      .then(r => r.json()),

  /** Update an existing user task. Requires admin credentials. */
  update: (id: string, task: UserTask, username: string, password: string): Promise<UserTask> =>
    put<UserTask>(`/app/admin/gems/${id}`, task, { Authorization: basicAuth(username, password) }),

  /** Delete a user task. Requires admin credentials. */
  delete: (id: string, username: string, password: string): Promise<void> =>
    del(`/app/admin/gems/${id}`, { Authorization: basicAuth(username, password) }),

  /**
   * Run a gem. Returns a raw Response whose body is an SSE stream.
   * Parse with readSSEStream() below.
   */
  run: (id: string, values: Record<string, string>): Promise<Response> =>
    post(`/app/gems/${id}/run`, { values }),
}

// ── Mock selector ─────────────────────────────────────────────────────────────

import { gemsApi as _mockGemsApi } from './mock/tasks'
export const gemsApi = import.meta.env.VITE_MOCK_API ? _mockGemsApi : _realGemsApi

// ── SSE streaming helper ──────────────────────────────────────────────────────

/**
 * Async-iterate SSE tokens from a /run response.
 * Yields each data payload, stops when `[DONE]` is received.
 *
 * @example
 * const res = await gemsApi.run(id, values)
 * for await (const token of readSSEStream(res)) { ... }
 */
export async function* readSSEStream(response: Response): AsyncGenerator<string> {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6)
      if (data === '[DONE]') return
      yield data
    }
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/simon/trove
git add frontend/src/api/client.ts frontend/src/api/tasks.ts
git commit -m "feat: add del() helper and typed gemsApi client"
```

---

### Task 2: Create GemIcon component

**Files:**
- Create: `frontend/src/components/GemIcon.tsx`

The hexagon-cut SVG gem (option A from design). Four polygon facets: top crown (lightest), upper sides (mid-light), lower sides (mid-dark), base (darkest). Maps each `GemHue` to a set of four hex colors.

- [ ] **Step 1: Create `frontend/src/components/GemIcon.tsx`**

```tsx
/**
 * GemIcon — hexagon-cut SVG gem icon used on task cards and in the admin UI.
 *
 * Renders a top-view gem with four polygon facets. Hue controls colour;
 * size controls the rendered dimensions (default 40px).
 */
import type { GemHue } from '../api/tasks'

/** Four-shade colour set for one gem facet layer: crown, upper, lower, base. */
interface HueColors {
  crown: string
  upper: string
  lower: string
  base: string
}

/** Tailwind colour palette values for each supported hue. */
const HUE_COLORS: Record<GemHue, HueColors> = {
  red:     { crown: '#f87171', upper: '#ef4444', lower: '#dc2626', base: '#b91c1c' },
  orange:  { crown: '#fb923c', upper: '#f97316', lower: '#ea580c', base: '#c2410c' },
  amber:   { crown: '#fbbf24', upper: '#f59e0b', lower: '#d97706', base: '#b45309' },
  yellow:  { crown: '#fde047', upper: '#eab308', lower: '#ca8a04', base: '#a16207' },
  lime:    { crown: '#a3e635', upper: '#84cc16', lower: '#65a30d', base: '#4d7c0f' },
  green:   { crown: '#4ade80', upper: '#22c55e', lower: '#16a34a', base: '#15803d' },
  emerald: { crown: '#34d399', upper: '#10b981', lower: '#059669', base: '#047857' },
  teal:    { crown: '#2dd4bf', upper: '#14b8a6', lower: '#0d9488', base: '#0f766e' },
  cyan:    { crown: '#22d3ee', upper: '#06b6d4', lower: '#0891b2', base: '#0e7490' },
  sky:     { crown: '#38bdf8', upper: '#0ea5e9', lower: '#0284c7', base: '#0369a1' },
  blue:    { crown: '#60a5fa', upper: '#3b82f6', lower: '#2563eb', base: '#1d4ed8' },
  indigo:  { crown: '#818cf8', upper: '#6366f1', lower: '#4f46e5', base: '#4338ca' },
  violet:  { crown: '#a78bfa', upper: '#8b5cf6', lower: '#7c3aed', base: '#6d28d9' },
  purple:  { crown: '#c084fc', upper: '#a855f7', lower: '#9333ea', base: '#7e22ce' },
  fuchsia: { crown: '#e879f9', upper: '#d946ef', lower: '#c026d3', base: '#a21caf' },
  rose:    { crown: '#fb7185', upper: '#f43f5e', lower: '#e11d48', base: '#be123c' },
}

interface GemIconProps {
  /** Gem hue — maps to a set of four shaded polygon fill colors. */
  hue: GemHue
  /** Rendered width and height in pixels. Default: 40. */
  size?: number
}

/**
 * Hexagon-cut gem SVG icon.
 *
 * @example
 * <GemIcon hue="indigo" size={36} />
 */
export default function GemIcon({ hue, size = 40 }: GemIconProps) {
  const c = HUE_COLORS[hue]
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 52 52"
      aria-hidden="true"
    >
      {/* Outer hexagon outline */}
      <polygon points="26,4 46,16 46,36 26,48 6,36 6,16" fill={c.upper} opacity={0.9} />
      {/* Crown facet (top, lightest) */}
      <polygon points="26,4 46,16 26,22 6,16" fill={c.crown} opacity={0.95} />
      {/* Upper side facets */}
      <polygon points="26,22 46,16 46,36 26,48 6,36 6,16" fill={c.lower} opacity={0.85} />
      {/* Base facet (bottom, darkest) */}
      <polygon points="26,22 46,36 26,48 6,36" fill={c.base} opacity={0.8} />
    </svg>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/simon/trove
git add frontend/src/components/GemIcon.tsx
git commit -m "feat: add GemIcon SVG component with 16 hues"
```

---

### Task 3: Create mock API layer

**Files:**
- Create: `frontend/src/api/mock/tasks.ts`
- Create: `frontend/src/api/mock/config.ts`
- Create: `frontend/src/api/mock/system.ts`
- Create: `frontend/src/api/mock/index.ts`
- Modify: `frontend/src/api/config.ts`
- Modify: `frontend/src/api/system.ts`

5 sample UserTasks covering diverse hues and arg types. The mock `run` simulates SSE streaming via `ReadableStream`. `config.ts` and `system.ts` also gain mock selectors so the full UI works with no backend.

- [ ] **Step 1: Create `frontend/src/api/mock/tasks.ts`**

```ts
/**
 * Mock implementation of gemsApi.
 *
 * Returns hardcoded UserTasks with a short delay to make spinners visible.
 * The run() function simulates SSE streaming via ReadableStream, matching
 * the real interface so GemRunner needs no special casing.
 */
import type { UserTask } from '../tasks'

const SAMPLE_TASKS: UserTask[] = [
  {
    id: 'summarise-text',
    name: 'Summarise Text',
    description: 'Condense any passage into a clear, concise summary.',
    hue: 'indigo',
    template: 'Summarise the following text in {{ language }}:\n\n{{ text }}',
    args: [
      { type: 'string', name: 'text', description: 'The text to summarise', default: '' },
      {
        type: 'choice',
        name: 'language',
        description: 'Output language',
        default: 'English',
        choices: ['English', 'Italian', 'French', 'Spanish'],
      },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
  },
  {
    id: 'translate',
    name: 'Translate',
    description: 'Convert text from one language to another.',
    hue: 'emerald',
    template: 'Translate the following text into {{ target_language }}:\n\n{{ text }}',
    args: [
      { type: 'string', name: 'text', description: 'Text to translate', default: '' },
      {
        type: 'choice',
        name: 'target_language',
        description: 'Target language',
        default: 'Italian',
        choices: ['Italian', 'French', 'Spanish', 'German', 'Portuguese'],
      },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
  },
  {
    id: 'draft-letter',
    name: 'Draft a Letter',
    description: 'Write a professional letter from key bullet points.',
    hue: 'amber',
    template: 'Write a professional letter about the following:\n\n{{ topic }}\n\nTone: {{ tone }}',
    args: [
      { type: 'string', name: 'topic', description: 'Main points to cover', default: '' },
      {
        type: 'choice',
        name: 'tone',
        description: 'Letter tone',
        default: 'Formal',
        choices: ['Formal', 'Friendly', 'Apologetic', 'Assertive'],
      },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
  },
  {
    id: 'explain-simply',
    name: 'Explain Simply',
    description: 'Break down a complex topic for a beginner audience.',
    hue: 'rose',
    template: 'Explain "{{ topic }}" simply, as if speaking to a {{ audience }}.',
    args: [
      { type: 'string', name: 'topic', description: 'Topic to explain', default: '' },
      {
        type: 'choice',
        name: 'audience',
        description: 'Target audience',
        default: 'curious 12-year-old',
        choices: ['curious 12-year-old', 'non-technical adult', 'complete beginner'],
      },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
  },
  {
    id: 'meeting-notes',
    name: 'Meeting Notes',
    description: 'Turn rough meeting notes into structured minutes.',
    hue: 'violet',
    template: 'Convert these rough meeting notes into structured minutes:\n\n{{ notes }}',
    args: [
      { type: 'string', name: 'notes', description: 'Rough notes from the meeting', default: '' },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
  },
]

/** Simulated canned response text for the run mock. */
const CANNED_RESPONSE =
  'This is a simulated response from the mock API. ' +
  'It streams word by word to demonstrate the streaming UI. ' +
  'In production, tokens come from the local Ollama model. ' +
  'The output area updates in real time as each token arrives.'

function delay(ms: number): Promise<void> {
  return new Promise(r => setTimeout(r, ms))
}

export const gemsApi = {
  list: async (): Promise<UserTask[]> => {
    await delay(200)
    return [...SAMPLE_TASKS]
  },

  get: async (id: string): Promise<UserTask> => {
    await delay(150)
    const task = SAMPLE_TASKS.find(t => t.id === id)
    if (!task) throw new Error(`Gem not found: ${id}`)
    return { ...task }
  },

  create: async (task: UserTask, _u: string, _p: string): Promise<UserTask> => {
    await delay(300)
    return { ...task }
  },

  update: async (_id: string, task: UserTask, _u: string, _p: string): Promise<UserTask> => {
    await delay(300)
    return { ...task }
  },

  delete: async (_id: string, _u: string, _p: string): Promise<void> => {
    await delay(200)
  },

  /**
   * Simulates SSE streaming by yielding words from a canned response one at a
   * time via ReadableStream. Matches the real Response interface so GemRunner
   * needs no special casing.
   */
  run: (_id: string, _values: Record<string, string>): Promise<Response> => {
    const words = CANNED_RESPONSE.split(' ')
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(controller) {
        await delay(400) // simulate model startup latency
        for (const word of words) {
          controller.enqueue(encoder.encode(`data: ${word} \n\n`))
          await delay(80)
        }
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      },
    })
    return Promise.resolve(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    )
  },
}
```

- [ ] **Step 2: Create `frontend/src/api/mock/config.ts`**

```ts
/**
 * Mock implementation of configApi.
 * Returns a default TroveConfig with a short delay.
 */
import type { TroveConfig } from '../config'

const DEFAULT_CONFIG: TroveConfig = {
  base_model: 'gemma4:e4b',
  num_ctx: 8192,
  locale: 'en',
}

export const configApi = {
  get: async (): Promise<TroveConfig> => {
    await new Promise(r => setTimeout(r, 100))
    return { ...DEFAULT_CONFIG }
  },
  update: async (config: TroveConfig): Promise<TroveConfig> => {
    await new Promise(r => setTimeout(r, 200))
    return { ...config }
  },
}
```

- [ ] **Step 3: Create `frontend/src/api/mock/system.ts`**

```ts
/**
 * Mock implementation of systemApi.
 * Returns a pre-populated SystemCheck so the admin settings tab renders.
 */
import type { SystemCheck } from '../system'

export const systemApi = {
  check: async (): Promise<SystemCheck> => {
    await new Promise(r => setTimeout(r, 150))
    return {
      ram_gb: 16,
      disk_free_gb: 120,
      gpu: { available: false, vram_gb: null },
      ollama_running: true,
      viable_models: [
        { tag: 'gemma4:e2b', min_ram_gb: 4,  max_ctx: 131072, audio: true  },
        { tag: 'gemma4:e4b', min_ram_gb: 6,  max_ctx: 131072, audio: true  },
        { tag: 'gemma4:26b', min_ram_gb: 10, max_ctx: 262144, audio: false },
      ],
    }
  },
}
```

- [ ] **Step 4: Create `frontend/src/api/mock/index.ts`**

```ts
/** Re-exports all mock API clients for convenience. */
export { configApi } from './config'
export { gemsApi } from './tasks'
export { systemApi } from './system'
```

- [ ] **Step 5: Add mock selector to `frontend/src/api/config.ts`**

Replace the export at the bottom of `frontend/src/api/config.ts`:

Current last block:
```ts
/** API wrapper for the config domain. */
export const configApi = {
  /** Fetch the current server configuration. */
  get: () => get<TroveConfig>('/config'),
  /** Persist updated configuration and return it. */
  update: (config: TroveConfig) => put<TroveConfig>('/config', config),
}
```

Replace with:
```ts
import { configApi as _mockConfigApi } from './mock/config'

const _realConfigApi = {
  /** Fetch the current server configuration. */
  get: () => get<TroveConfig>('/config'),
  /** Persist updated configuration and return it. */
  update: (config: TroveConfig) => put<TroveConfig>('/config', config),
}

/** API wrapper for the config domain. Switches to mock when VITE_MOCK_API=1. */
export const configApi = import.meta.env.VITE_MOCK_API ? _mockConfigApi : _realConfigApi
```

- [ ] **Step 6: Add mock selector to `frontend/src/api/system.ts`**

Replace the export at the bottom of `frontend/src/api/system.ts`:

Current last block:
```ts
/** API wrapper for the system check domain. */
export const systemApi = {
  /** Run system checks and return hardware info. */
  check: () => get<SystemCheck>('/system/check'),
}
```

Replace with:
```ts
import { systemApi as _mockSystemApi } from './mock/system'

const _realSystemApi = {
  /** Run system checks and return hardware info. */
  check: () => get<SystemCheck>('/system/check'),
}

/** API wrapper for the system check domain. Switches to mock when VITE_MOCK_API=1. */
export const systemApi = import.meta.env.VITE_MOCK_API ? _mockSystemApi : _realSystemApi
```

- [ ] **Step 7: Commit**

```bash
cd /home/simon/trove
git add frontend/src/api/mock/ frontend/src/api/config.ts frontend/src/api/system.ts
git commit -m "feat: add mock API layer for frontend-only dev mode"
```

---

### Task 4: Locale middleware + i18n update + dev-mock task

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/i18n/index.ts`
- Modify: `pyproject.toml`

Add a Vite server plugin that serves `../locales/*.json` at `/locales/` so `useTranslation` can load locale files without the backend. Update `fetchLocale` to use the direct `/locales/` path in mock mode. Add `dev-mock` to taskipy.

- [ ] **Step 1: Update `frontend/vite.config.ts`**

```ts
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
      },
    },
  ],
  server: {
    proxy: {
      '/api': 'http://localhost:8001',
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

- [ ] **Step 2: Update `frontend/src/i18n/index.ts`**

Replace the `fetchLocale` function body:

Current:
```ts
async function fetchLocale(locale: string): Promise<Strings> {
  if (cache[locale]) return cache[locale]
  const strings = await get<Strings>(`/i18n/${locale}`)
  cache[locale] = strings
  return strings
}
```

Replace with:
```ts
async function fetchLocale(locale: string): Promise<Strings> {
  if (cache[locale]) return cache[locale]
  // In mock dev mode, locale files are served directly by the Vite dev server
  // at /locales/{locale}.json (via the serve-locales plugin in vite.config.ts).
  // In real mode, the FastAPI i18n endpoint handles fallback to English.
  const url = import.meta.env.VITE_MOCK_API
    ? `/locales/${locale}.json`
    : `/api/i18n/${locale}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to load locale ${locale}: ${res.status}`)
  const strings: Strings = await res.json()
  cache[locale] = strings
  return strings
}
```

Also remove the `import { get } from '../api/client'` line at the top of the file since `get` is no longer used.

- [ ] **Step 3: Add `dev-mock` task to `pyproject.toml`**

In `[tool.taskipy.tasks]`, add after `dev-frontend`:
```toml
dev-mock     = "cd frontend && VITE_MOCK_API=1 bun run dev"
```

- [ ] **Step 4: Verify locale serving works**

```bash
cd /home/simon/trove
task dev-mock &
sleep 3
curl -s http://localhost:5173/locales/en.json | head -5
kill %1
```

Expected: JSON output with translation keys (e.g. `{"app.tasks.placeholder": ...}`).

- [ ] **Step 5: Commit**

```bash
cd /home/simon/trove
git add frontend/vite.config.ts frontend/src/i18n/index.ts pyproject.toml
git commit -m "feat: add locale middleware and dev-mock task"
```

---

### Task 5: Update TaskShell to gem card grid

**Files:**
- Modify: `frontend/src/pages/TaskShell.tsx`

Replace the placeholder with a Flowbite `Card` grid. Each card shows `GemIcon`, name, and description. Clicking navigates to `/gems/:id`. Uses `gemsApi.list()`.

- [ ] **Step 1: Replace `frontend/src/pages/TaskShell.tsx`**

```tsx
/**
 * TaskShell — user-facing landing page in app mode.
 *
 * Displays all gems as a card grid. Clicking a card navigates to the
 * GemRunner page for that gem.
 */
import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Card, Spinner } from 'flowbite-react'
import { gemsApi, type UserTask } from '../api/tasks'
import { configApi } from '../api/config'
import GemIcon from '../components/GemIcon'
import { useTranslation } from '../i18n'

export default function TaskShell() {
  const [gems, setGems] = useState<UserTask[]>([])
  const [loading, setLoading] = useState(true)
  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)
  const navigate = useNavigate()

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    gemsApi.list().then(list => { setGems(list); setLoading(false) })
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Trove</h1>
          <Link to="/admin">
            <span className="text-sm text-gray-500 hover:text-gray-700 cursor-pointer">
              {t('admin.login.title', 'Admin')}
            </span>
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <Spinner size="lg" />
          </div>
        ) : gems.length === 0 ? (
          <p className="text-center text-gray-400 py-20">
            {t('app.tasks.placeholder', 'No gems yet. Ask an admin to create some.')}
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {gems.map(gem => (
              <Card
                key={gem.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => navigate(`/gems/${gem.id}`)}
              >
                <div className="flex flex-col gap-3">
                  <GemIcon hue={gem.hue} size={40} />
                  <div>
                    <h2 className="text-base font-semibold text-gray-900">{gem.name}</h2>
                    {gem.description && (
                      <p className="text-sm text-gray-500 mt-1 leading-snug">{gem.description}</p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify visually with mock**

```bash
cd /home/simon/trove && task dev-mock
```

Open http://localhost:5173 — expect a 3-column card grid with 5 sample gems, each showing a coloured hexagon icon, name, and description.

- [ ] **Step 3: Commit**

```bash
cd /home/simon/trove
git add frontend/src/pages/TaskShell.tsx
git commit -m "feat: replace TaskShell placeholder with gem card grid"
```

---

### Task 6: Create GemRunner page

**Files:**
- Create: `frontend/src/pages/GemRunner.tsx`

Two-phase UI: Phase 1 shows the dynamic arg form; Phase 2 collapses the form to a clickable summary bar and streams output below. Spinner shown until first token. "Run again" re-submits with current values.

- [ ] **Step 1: Create `frontend/src/pages/GemRunner.tsx`**

```tsx
/**
 * GemRunner — run a gem by filling its arguments and streaming the output.
 *
 * Phase 1 (form): Dynamic form built from UserTask.args. StringArg → TextInput.
 * ChoiceArg → Select. has_image / has_audio → disabled upload buttons.
 *
 * Phase 2 (output): Form collapses to a summary bar showing arg values.
 * Clicking the bar re-expands the form. Spinner shown until first token arrives.
 * Output streams into a scrolling text area. "Run again" re-submits.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Label, Select, Spinner, TextInput, Tooltip } from 'flowbite-react'
import { gemsApi, readSSEStream, type UserTask } from '../api/tasks'
import GemIcon from '../components/GemIcon'

type Phase = 'form' | 'running' | 'done'

export default function GemRunner() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [gem, setGem] = useState<UserTask | null>(null)
  const [loadError, setLoadError] = useState(false)

  // Form state: keyed by arg name
  const [values, setValues] = useState<Record<string, string>>({})
  const [phase, setPhase] = useState<Phase>('form')
  const [output, setOutput] = useState('')
  const outputRef = useRef<HTMLDivElement>(null)

  // Load gem on mount
  useEffect(() => {
    if (!id) return
    gemsApi.get(id)
      .then(g => {
        setGem(g)
        // Pre-fill defaults
        const defaults: Record<string, string> = {}
        for (const arg of g.args) {
          defaults[arg.name] = arg.default
        }
        setValues(defaults)
      })
      .catch(() => setLoadError(true))
  }, [id])

  // Auto-scroll output area as tokens arrive
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [output])

  async function handleRun() {
    if (!gem || !id) return
    setOutput('')
    setPhase('running')
    try {
      const res = await gemsApi.run(id, values)
      let firstToken = true
      for await (const token of readSSEStream(res)) {
        if (firstToken) {
          firstToken = false
          // Transition from running (spinner) to done (output visible) on first token
          setPhase('done')
        }
        setOutput(prev => prev + token)
      }
      setPhase('done')
    } catch {
      setOutput('An error occurred while running this gem.')
      setPhase('done')
    }
  }

  if (loadError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Gem not found.</p>
      </div>
    )
  }

  if (!gem) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  /** Human-readable summary of current arg values for the collapsed bar. */
  const argSummary = gem.args
    .filter(a => values[a.name])
    .map(a => `${a.name}: ${values[a.name]}`)
    .join(' · ')

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto flex flex-col gap-4">

        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="text-gray-400 hover:text-gray-600 text-sm"
          >
            ← Back
          </button>
          <GemIcon hue={gem.hue} size={28} />
          <h1 className="text-xl font-bold text-gray-900">{gem.name}</h1>
        </div>

        {/* Phase 1: Form — shown when phase is 'form' */}
        {phase === 'form' && (
          <div className="bg-white border border-gray-200 rounded-lg p-5 flex flex-col gap-4">
            {gem.description && (
              <p className="text-sm text-gray-500">{gem.description}</p>
            )}

            {gem.args.map(arg => (
              <div key={arg.name}>
                <div className="mb-1">
                  <Label htmlFor={`arg-${arg.name}`}>
                    {arg.name}
                    {arg.description && (
                      <span className="text-gray-400 font-normal ml-1 text-xs">— {arg.description}</span>
                    )}
                  </Label>
                </div>
                {arg.type === 'string' ? (
                  <TextInput
                    id={`arg-${arg.name}`}
                    value={values[arg.name] ?? ''}
                    onChange={e => setValues(v => ({ ...v, [arg.name]: e.target.value }))}
                    placeholder={arg.default || arg.description}
                  />
                ) : (
                  <Select
                    id={`arg-${arg.name}`}
                    value={values[arg.name] ?? arg.default}
                    onChange={e => setValues(v => ({ ...v, [arg.name]: e.target.value }))}
                  >
                    {arg.choices.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </Select>
                )}
              </div>
            ))}

            {/* Image / audio upload stubs */}
            {gem.has_image && (
              <Tooltip content="Image upload coming soon">
                <Button color="light" disabled>Upload image</Button>
              </Tooltip>
            )}
            {gem.has_audio && (
              <Tooltip content="Audio upload coming soon">
                <Button color="light" disabled>Upload audio</Button>
              </Tooltip>
            )}

            <Button color="blue" onClick={handleRun}>
              Run
            </Button>
          </div>
        )}

        {/* Phase 2: Collapsed summary bar — shown when running or done */}
        {(phase === 'running' || phase === 'done') && (
          <button
            onClick={() => { setPhase('form'); setOutput('') }}
            className="w-full text-left bg-white border border-gray-200 rounded-lg px-4 py-3 flex justify-between items-center hover:bg-gray-50 transition-colors"
          >
            <span className="text-sm text-gray-600 truncate">{argSummary || gem.name}</span>
            <span className="text-xs text-indigo-500 ml-3 shrink-0">Edit ✎</span>
          </button>
        )}

        {/* Spinner — shown while running before first token */}
        {phase === 'running' && (
          <div className="flex justify-center py-6">
            <Spinner size="lg" />
          </div>
        )}

        {/* Output area — shown once first token arrives */}
        {phase === 'done' && (
          <div className="flex flex-col gap-3">
            <div
              ref={outputRef}
              className="bg-white border border-gray-200 rounded-lg p-4 min-h-32 max-h-[60vh] overflow-y-auto text-sm text-gray-800 leading-relaxed whitespace-pre-wrap font-mono"
            >
              {output}
              <span
                className="inline-block w-0.5 h-3.5 bg-indigo-500 ml-0.5 align-middle animate-pulse"
                aria-hidden="true"
              />
            </div>
            <Button color="light" onClick={handleRun}>
              Run again ↺
            </Button>
          </div>
        )}

      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify visually with mock**

```bash
cd /home/simon/trove && task dev-mock
```

Open http://localhost:5173, click a gem card. Expected:
- Phase 1: arg form with TextInput/Select fields, Run button
- After clicking Run: form collapses to summary bar, spinner appears, then output streams in word-by-word
- Clicking summary bar re-expands form

- [ ] **Step 3: Commit**

```bash
cd /home/simon/trove
git add frontend/src/pages/GemRunner.tsx
git commit -m "feat: add GemRunner page with collapsible form and SSE streaming"
```

---

### Task 7: Create GemForm page

**Files:**
- Create: `frontend/src/pages/GemForm.tsx`

Full-page Flowbite form for creating and editing gems. Fields: Name, Description, Hue (16-button colour picker), Template textarea, Args list (add/remove, type toggle, per-field editing), has_image/has_audio toggles, Output mode select. Requires admin credentials (passed from AdminPanel via navigation state or re-login).

- [ ] **Step 1: Create `frontend/src/pages/GemForm.tsx`**

```tsx
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
  gemsApi, GEM_HUES, type GemHue, type OutputMode, type TaskArg, type UserTask,
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
  return { type: 'string', name: '', description: '', default: '' }
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
      .then(g => { setGem(g); setLoading(false) })
      .catch(() => { setError('Gem not found.'); setLoading(false) })
  }, [id, isEdit])

  async function handleSave() {
    setError(null)
    setSaving(true)
    try {
      if (isEdit && id) {
        await gemsApi.update(id, gem, auth.username, auth.password)
      } else {
        await gemsApi.create(gem, auth.username, auth.password)
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
            <div key={i} className="border border-gray-200 rounded-lg p-4 flex flex-col gap-3 bg-white">
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
                        updateArg(i, { type: 'choice', choices: [] } as Partial<TaskArg>)
                      } else if (newType === 'string' && arg.type === 'choice') {
                        const { choices: _, ...rest } = arg as { choices: string[] } & Omit<TaskArg, 'type'>
                        setGem(g => {
                          const args = [...g.args]
                          args[i] = { ...rest, type: 'string' } as TaskArg
                          return { ...g, args }
                        })
                      }
                    }}
                    sizing="sm"
                    className="w-28"
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
                    value={arg.choices.join('\n')}
                    onChange={e =>
                      updateArg(i, {
                        choices: e.target.value.split('\n').map(s => s.trim()).filter(Boolean),
                      })
                    }
                    rows={3}
                    sizing="sm"
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
```

- [ ] **Step 2: Verify visually with mock**

```bash
cd /home/simon/trove && task dev-mock
```

Navigate to http://localhost:5173/admin/gems/new — should show re-auth form (no state passed), then a full form with all fields. Navigate to http://localhost:5173/admin/gems/summarise-text/edit — should pre-fill with the mock gem's data.

- [ ] **Step 3: Commit**

```bash
cd /home/simon/trove
git add frontend/src/pages/GemForm.tsx
git commit -m "feat: add GemForm create/edit page"
```

---

### Task 8: Update AdminPanel with Gems tab

**Files:**
- Modify: `frontend/src/pages/AdminPanel.tsx`

Replace the Tasks tab placeholder with a functional Gems tab: list with GemIcon + name + description + Edit/Delete buttons, plus a "New Gem" button that navigates to `/admin/gems/new`. Pass credentials via navigation state.

- [ ] **Step 1: Update the Tasks tab in `frontend/src/pages/AdminPanel.tsx`**

Add these imports at the top (after existing imports):

```ts
import { useNavigate } from 'react-router-dom'
import { gemsApi, type UserTask } from '../api/tasks'
import GemIcon from '../components/GemIcon'
```

Add this state inside the `AdminPanel` component, after `const { t }` line:

```ts
const navigate = useNavigate()
const [gems, setGems] = useState<UserTask[]>([])
const [gemsLoading, setGemsLoading] = useState(false)
const [gemDeleteId, setGemDeleteId] = useState<string | null>(null)
```

Add this effect inside the component, after the existing `useEffect` for config load (it should only run when `authed` is true):

```ts
useEffect(() => {
  if (!authed) return
  setGemsLoading(true)
  gemsApi.list().then(list => { setGems(list); setGemsLoading(false) })
}, [authed])
```

Replace the existing Tasks TabItem:
```tsx
<TabItem title={t('admin.tab.tasks')}>
  <p className="pt-4 text-gray-500">{t('admin.tasks.placeholder')}</p>
</TabItem>
```

With:
```tsx
<TabItem title={t('admin.tab.tasks', 'Gems')}>
  <div className="pt-4 flex flex-col gap-4">
    <div className="flex justify-end">
      <Button
        color="blue"
        size="sm"
        onClick={() => navigate('/admin/gems/new', { state: { username, password } })}
      >
        + New Gem
      </Button>
    </div>

    {gemsLoading ? (
      <div className="flex justify-center py-8"><Spinner /></div>
    ) : gems.length === 0 ? (
      <p className="text-gray-400 text-sm">No gems yet.</p>
    ) : (
      <div className="flex flex-col gap-2">
        {gems.map(gem => (
          <div
            key={gem.id}
            className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg p-3"
          >
            <GemIcon hue={gem.hue} size={32} />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm text-gray-900 truncate">{gem.name}</p>
              {gem.description && (
                <p className="text-xs text-gray-400 truncate">{gem.description}</p>
              )}
            </div>
            <div className="flex gap-2 shrink-0">
              <Button
                color="light"
                size="xs"
                onClick={() =>
                  navigate(`/admin/gems/${gem.id}/edit`, { state: { username, password } })
                }
              >
                Edit
              </Button>
              <Button
                color="failure"
                size="xs"
                disabled={gemDeleteId === gem.id}
                onClick={async () => {
                  setGemDeleteId(gem.id)
                  try {
                    await gemsApi.delete(gem.id, username, password)
                    setGems(gs => gs.filter(g => g.id !== gem.id))
                  } finally {
                    setGemDeleteId(null)
                  }
                }}
              >
                {gemDeleteId === gem.id ? <Spinner size="xs" /> : 'Delete'}
              </Button>
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
</TabItem>
```

- [ ] **Step 2: Verify visually with mock**

```bash
cd /home/simon/trove && task dev-mock
```

Navigate to http://localhost:5173/admin. Log in (any credentials work in mock). Switch to the Gems/Tasks tab — should show 5 mock gems with Edit/Delete buttons and a "+ New Gem" button.

- [ ] **Step 3: Commit**

```bash
cd /home/simon/trove
git add frontend/src/pages/AdminPanel.tsx
git commit -m "feat: implement Gems tab in AdminPanel with list and delete"
```

---

### Task 9: Update App.tsx routing

**Files:**
- Modify: `frontend/src/App.tsx`

Add the three new routes for GemRunner, GemForm (new), and GemForm (edit).

- [ ] **Step 1: Update `frontend/src/App.tsx`**

Add these imports after the existing page imports:

```ts
import GemRunner from './pages/GemRunner'
import GemForm from './pages/GemForm'
```

Replace the app-mode routes block:

Current:
```tsx
<>
  <Route path="/" element={<TaskShell />} />
  <Route path="/admin" element={<AdminPanel />} />
  <Route path="*" element={<Navigate to="/" replace />} />
</>
```

Replace with:
```tsx
<>
  <Route path="/" element={<TaskShell />} />
  <Route path="/gems/:id" element={<GemRunner />} />
  <Route path="/admin" element={<AdminPanel />} />
  <Route path="/admin/gems/new" element={<GemForm />} />
  <Route path="/admin/gems/:id/edit" element={<GemForm />} />
  <Route path="*" element={<Navigate to="/" replace />} />
</>
```

- [ ] **Step 2: Verify full flow with mock**

```bash
cd /home/simon/trove && task dev-mock
```

Check:
1. http://localhost:5173 — gem card grid loads
2. Click any gem — GemRunner opens, run it, output streams in
3. Click summary bar — form re-expands
4. http://localhost:5173/admin — login, go to Gems tab
5. Click "+ New Gem" — GemForm opens with blank fields
6. Click Edit on a gem — GemForm opens with pre-filled fields
7. Click Delete — gem removed from list

- [ ] **Step 3: Commit**

```bash
cd /home/simon/trove
git add frontend/src/App.tsx
git commit -m "feat: add GemRunner and GemForm routes to App"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Covered by |
|---|---|
| GemHue enum, 16 values | Task 1 (`GemHue`, `GEM_HUES`) |
| UserTask type with id/name/description/hue | Task 1 (`UserTask` interface) |
| `gemsApi` typed client: list/get/create/update/delete/run | Task 1 |
| SSE stream reader | Task 1 (`readSSEStream`) |
| Mock API layer, VITE_MOCK_API selector | Task 3 |
| Mock `run` simulates streaming via ReadableStream | Task 3 |
| Mock config + system for full UI | Task 3 |
| `del()` helper in client.ts | Task 1 |
| Locale files at `/locales/` for mock mode | Task 4 |
| `useTranslation` mock-mode path | Task 4 |
| `dev-mock` taskipy task | Task 4 |
| GemIcon SVG with 16 hues | Task 2 |
| TaskShell gem card grid | Task 5 |
| GemRunner: dynamic form, SSE output, collapsible bar | Task 6 |
| GemRunner: StringArg → TextInput, ChoiceArg → Select | Task 6 |
| GemRunner: has_image/has_audio → disabled buttons | Task 6 |
| GemRunner: spinner before first token | Task 6 |
| GemRunner: "Run again" button | Task 6 |
| AdminPanel: Gems tab with list + edit + delete | Task 8 |
| GemForm: full-page create/edit | Task 7 |
| GemForm: 16-button hue picker with GemIcon preview | Task 7 |
| GemForm: dynamic args list (add/remove, type toggle) | Task 7 |
| GemForm: ChoiceArg options textarea | Task 7 |
| App.tsx: `/gems/:id`, `/admin/gems/new`, `/admin/gems/:id/edit` | Task 9 |
| Flowbite-first (no custom Tailwind except GemIcon) | All pages |

### Notes

- The backend plan (Task 1 of `2026-04-05-gems-backend.md`) moves locale files to `locales/` at the project root. This plan assumes that move is complete before Task 4 runs. If running plans independently, ensure `locales/en.json` and `locales/it.json` exist at the project root.
- `config.ts` and `system.ts` mock selectors import from `./mock/config` and `./mock/system` — these modules must exist (created in Task 3) before Task 3's steps 5 and 6 run. Execute steps within Task 3 sequentially.
- The `del` function name in `client.ts` is a valid JavaScript identifier (not a reserved word at expression scope).
