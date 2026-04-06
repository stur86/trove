/**
 * Mock implementation of setupApi.
 *
 * Reports all setup steps as already complete. Streaming operations return
 * fake SSE progress lines.
 */
import type { SetupStatus, LanUrl } from '../setup'
import { mockSSELines } from './_stream'

export const setupApi = {
  status: async (): Promise<SetupStatus> => {
    await new Promise(r => setTimeout(r, 100))
    return {
      ollama_installed: true,
      models_pulled: ['gemma4:e4b'],
      admin_configured: true,
      service_installed: true,
    }
  },

  setLanguage: async (locale: string): Promise<{ saved: boolean; locale: string }> => {
    await new Promise(r => setTimeout(r, 100))
    return { saved: true, locale }
  },

  saveAdminCredentials: async (_username: string, _password: string): Promise<{ saved: boolean }> => {
    await new Promise(r => setTimeout(r, 150))
    return { saved: true }
  },

  installService: (_appPort = 7770): Promise<Response> =>
    mockSSELines([
      'Writing systemd unit file…',
      'Enabling trove.service…',
      'Starting trove.service…',
      'Service installed and running.',
    ], 350),

  uninstall: (): Promise<Response> =>
    mockSSELines([
      'Stopping trove.service…',
      'Disabling trove.service…',
      'Removing unit file…',
      'Uninstall complete.',
    ], 300),

  restart: (): Promise<Response> =>
    mockSSELines(['Restarting trove.service…', 'Service restarted.'], 300),

  lanUrl: async (): Promise<LanUrl> => {
    await new Promise(r => setTimeout(r, 50))
    return { ip: '192.168.1.100', port: 7770, url: 'http://192.168.1.100:7770' }
  },

  ollamaVersion: async (): Promise<{ version: string }> => {
    await new Promise(r => setTimeout(r, 50))
    return { version: '0.9.0' }
  },

  logs: async (): Promise<{ lines: string[] }> => {
    await new Promise(r => setTimeout(r, 50))
    return {
      lines: [
        '2026-04-06 12:00:00 INFO     uvicorn.server: Started server process',
        '2026-04-06 12:00:00 INFO     uvicorn.lifespan.on: Waiting for application startup.',
        '2026-04-06 12:00:00 INFO     uvicorn.lifespan.on: Application startup complete.',
        '2026-04-06 12:00:01 INFO     backend.ollama.service: Ollama ready on port 11435.',
      ],
    }
  },
}
