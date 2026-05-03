/**
 * Mock implementation of ollamaApi.
 *
 * Status reports Ollama as fully installed and running with the model built.
 * Streaming operations return fake SSE progress lines.
 */
import type { OllamaStatus, StartServiceResult } from '../ollama'
import { mockSSELines } from './_stream'

export const ollamaApi = {
  status: async (): Promise<OllamaStatus> => {
    await new Promise(r => setTimeout(r, 100))
    return {
      installed: true,
      running: true,
      model_pulled: true,
      model_built: true,
    }
  },

  listModels: async (): Promise<{ models: string[] }> => {
    await new Promise(r => setTimeout(r, 50))
    return { models: ['gemma4:e4b'] }
  },

  install: (): Promise<Response> =>
    mockSSELines([
      'Downloading Ollama installer…',
      'Running installer…',
      'Ollama installed successfully.',
    ], 400),

  start: async (): Promise<StartServiceResult> => {
    await new Promise(r => setTimeout(r, 300))
    return { success: true }
  },

  pull: (_modelTag?: string): Promise<Response> =>
    mockSSELines([
      `Pulling ${_modelTag ?? 'model'}…`,
      'Downloading layer 1/4…',
      'Downloading layer 2/4…',
      'Downloading layer 3/4…',
      'Downloading layer 4/4…',
      'Pull complete.',
    ], 350),

  build: (): Promise<Response> =>
    mockSSELines([
      'Generating Modelfile…',
      'Building trove_model…',
      'Build complete.',
    ], 300),
}
