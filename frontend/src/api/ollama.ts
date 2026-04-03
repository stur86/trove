/**
 * Typed API wrapper for the Trove Ollama domain.
 *
 * Provides status polling and streaming POST operations for Ollama
 * installation, model pull, and model build. Streaming responses use
 * Server-Sent Events (SSE) and are consumed via the streamLines helper.
 */

import { get, post } from './client'

/** Current Ollama installation status. */
export interface OllamaStatus {
  installed: boolean
  running: boolean
  /** Whether the configured base model has been pulled from the registry. */
  model_pulled: boolean
  /** Whether trove_model (the custom derived model) has been built. */
  model_built: boolean
}

/**
 * Read a Server-Sent Events stream and call onLine for each data line.
 *
 * SSE lines are formatted as `data: <content>\n\n` by the backend.
 * Calls onDone when the stream closes.
 *
 * @param response - The Response from a streaming POST endpoint
 * @param onLine   - Called with each non-empty data line
 * @param onDone   - Called when the stream ends
 */
export function streamLines(
  response: Response,
  onLine: (line: string) => void,
  onDone: () => void,
): void {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  function read() {
    reader.read().then(({ done, value }) => {
      if (done) {
        onDone()
        return
      }
      buffer += decoder.decode(value, { stream: true })
      // SSE events are separated by double newlines
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() ?? ''
      for (const chunk of chunks) {
        const line = chunk.replace(/^data: /, '').trim()
        if (line) onLine(line)
      }
      read()
    })
  }
  read()
}

/** API wrapper for the Ollama domain. */
export const ollamaApi = {
  /** Get current Ollama installation status. */
  status: () => get<OllamaStatus>('/ollama/status'),
  /** Start Ollama install; returns a streaming Response. */
  install: () => post('/ollama/install'),
  /** Start the Ollama service; returns a streaming Response. */
  start: () => post('/ollama/start'),
  /** Pull the configured model; returns a streaming Response. */
  pull: () => post('/ollama/pull'),
  /** Build trove_model from Modelfile; returns a streaming Response. */
  build: () => post('/ollama/build'),
}
