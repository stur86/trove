/**
 * Typed API client for app-mode admin endpoints (/api/app/admin/*).
 *
 * All admin endpoints require HTTP Basic auth. Pass credentials via
 * basicAuth(username, password) from ./client.
 */
import { type TroveConfig } from './config'
import { basicAuth, post, put, get } from './client'

export const appApi = {
  /**
   * Cookie-based login: exchange Basic creds for an admin cookie.
   */
  login: (username: string, password: string): Promise<void> =>
    post('/app/admin/login', undefined, { Authorization: basicAuth(username, password) }).then(() => {}),

  /**
   * Check whether the admin cookie is present/valid.
   */
  checkAdminValid: (): Promise<{ admin_auth: string | null }> =>
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
}
