/**
 * Typed API client for app-mode admin endpoints (/api/app/admin/*).
 *
 * All admin endpoints require HTTP Basic auth. Pass credentials via
 * basicAuth(username, password) from ./client.
 */
import { type TroveConfig } from './config'
import { basicAuth, post, put, get } from './client'
import { appApi as _mockAppApi } from './mock/app'

const _realAppApi = {
  /**
   * Cookie-based login: exchange Basic creds for an admin cookie.
   */
  login: (username: string, password: string): Promise<void> =>
    post('/app/admin/login', undefined, { Authorization: basicAuth(username, password) }).then(() => {}),

  /**
   * Check whether the admin cookie holds a live token.
   * Returns { valid: true } if the cookie is present and not expired.
   */
  checkAdminValid: (): Promise<{ valid: boolean }> =>
    get('/app/admin/valid'),

  /**
   * Logout by clearing the admin cookie on the server.
   */
  logout: (): Promise<void> =>
    post('/app/admin/logout').then(() => {}),

  /**
   * Save config using the admin cookie (no Basic auth header).
   */
  saveConfig: (config: TroveConfig): Promise<TroveConfig> =>
    put('/app/admin/config', config),

  /**
   * Build model using the admin cookie. Returns raw Response for SSE.
   */
  buildModel: (): Promise<Response> =>
    post('/app/admin/build-model'),

  /**
   * Return the LAN URL other devices can use to reach this Trove instance.
   */
  networkUrl: (): Promise<{ url: string | null }> =>
    get('/app/network-url'),

  /**
   * Return the last up to 1000 lines from the server log buffer. Requires admin cookie.
   */
  logs: (): Promise<{ lines: string[] }> =>
    get('/app/admin/logs'),

  /**
   * Return runtime capability flags for the current model configuration.
   * Currently: { audio: boolean } — True when the active model supports audio input.
   */
  capabilities: (): Promise<{ audio: boolean }> =>
    get('/app/capabilities'),
}

/** API wrapper for app-mode admin operations. Switches to mock when VITE_MOCK_API=1. */
export const appApi = import.meta.env.VITE_MOCK_API ? _mockAppApi : _realAppApi
