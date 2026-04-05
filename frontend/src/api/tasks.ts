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
  _key?: string  // stable identity for React list rendering — stripped before API calls
}

/** A fixed-choice argument with a list of allowed values. */
export interface ChoiceArg {
  type: 'choice'
  name: string
  description: string
  default: string
  options: string[]
  _key?: string  // stable identity for React list rendering — stripped before API calls
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
  if (!response.body) throw new Error('Response has no body — cannot stream SSE')
  const reader = response.body.getReader()
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
