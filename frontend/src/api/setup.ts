/**
 * Typed API client for setup-mode endpoints (/api/setup/*).
 *
 * These endpoints are only available when Trove is running in setup mode
 * (trove setup). Calling them in app mode returns 404.
 */
import { get, post } from './client'

/** POST and parse the JSON response body into the given type. */
async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const res = await post(path, body)
  return res.json() as Promise<T>
}

/** Completion state returned by GET /api/setup/status. */
export interface SetupStatus {
  ollama_installed: boolean
  models_pulled: string[]
  admin_configured: boolean
  service_installed: boolean
}

/** LAN URL info returned by GET /api/setup/lan-url. */
export interface LanUrl {
  ip: string
  port: number
  url: string
}

export const setupApi = {
  /** Return which setup steps are complete. */
  status: (): Promise<SetupStatus> => get('/setup/status'),

  /** Save the chosen locale to config. */
  setLanguage: (locale: string): Promise<{ saved: boolean; locale: string }> =>
    postJson('/setup/language', { locale }),

  /** Save admin username and password to config. */
  saveAdminCredentials: (username: string, password: string): Promise<{ saved: boolean }> =>
    postJson('/setup/admin-credentials', { username, password }),

  /** Install the systemd service. Returns a raw Response for SSE streaming. */
  installService: (appPort = 7770): Promise<Response> =>
    post('/setup/install-service', { app_port: appPort }),

  /** Uninstall the systemd service. Returns a raw Response for SSE streaming. */
  uninstall: (): Promise<Response> => post('/setup/uninstall'),

  /** Restart the systemd service. Returns a raw Response for SSE streaming. */
  restart: (): Promise<Response> => post('/setup/restart-service'),

  /** Get the LAN URL for the app mode. */
  lanUrl: (): Promise<LanUrl> => get('/setup/lan-url'),

  /** Get the installed Ollama version string. */
  ollamaVersion: (): Promise<{ version: string }> => get('/setup/ollama-version'),
}
