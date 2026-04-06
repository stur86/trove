/**
 * Typed API client for the Gems (UserTask) domain.
 *
 * Exports gemsApi — switches to the mock implementation when
 * VITE_MOCK_API=1 is set in the environment.
 */
import { del, get, post, put } from './client'

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

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Encode a Blob to a base64 string (without the data URL prefix).
 * Uses FileReader so it works in all browsers without Buffer.
 */
async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve((reader.result as string).split(',')[1])
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

// ── Real API implementation ───────────────────────────────────────────────────

const _realGemsApi = {
  /** List all user tasks. */
  list: (): Promise<UserTask[]> =>
    get<UserTask[]>('/app/gems'),

  /** Get a single user task by slug id. Throws 404 if missing. */
  get: (id: string): Promise<UserTask> =>
    get<UserTask>(`/app/gems/${id}`),

  /** Create a new user task using admin cookie. */
  create: (task: UserTask): Promise<UserTask> =>
    post('/app/admin/gems', task).then(r => r.json()),

  /** Update using admin cookie. */
  update: (id: string, task: UserTask): Promise<UserTask> =>
    put<UserTask>(`/app/admin/gems/${id}`, task),

  /** Delete using admin cookie. */
  delete: (id: string): Promise<void> =>
    del(`/app/admin/gems/${id}`),

  /**
   * Run a gem. Returns a raw Response whose body is an SSE stream.
   * Parse with readSSEStream() below.
   *
   * @param id     Gem slug id.
   * @param values Argument values keyed by arg name.
   * @param image  Optional image to send — { blob, mime } from a file input or canvas.
   * @param audio  Optional audio to send — { blob, mime } from a file input or MediaRecorder.
   */
  run: async (
    id: string,
    values: Record<string, string>,
    image?: { blob: Blob; mime: string },
    audio?: { blob: Blob; mime: string },
  ): Promise<Response> => {
    const body: Record<string, unknown> = { values }
    if (image) {
      body.image = await blobToBase64(image.blob)
      body.image_mime = image.mime
    }
    if (audio) {
      body.audio = await blobToBase64(audio.blob)
      body.audio_mime = audio.mime
    }
    return post(`/app/gems/${id}/run`, body)
  },
}

// ── Mock selector ─────────────────────────────────────────────────────────────

import { gemsApi as _mockGemsApi } from './mock/tasks'
export const gemsApi = import.meta.env.VITE_MOCK_API ? _mockGemsApi : _realGemsApi

// ── SSE streaming helper ──────────────────────────────────────────────────────

/**
 * Async-iterate SSE tokens from a /run response.
 * Yields each data payload, stops when `[DONE]` is received.
 * Throws an Error when an `event: error` SSE line is followed by a `data:` line.
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
  // Track whether the most recent event type was "error"
  let isError = false
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line === 'event: error') {
        isError = true
        continue
      }
      if (!line.startsWith('data: ')) {
        // Non-data lines (blank lines, other event fields) — reset error flag on blank line
        if (line === '') isError = false
        continue
      }
      const data = line.slice(6)
      if (data === '[DONE]') return
      if (isError) throw new Error(data)
      yield data
    }
  }
}
