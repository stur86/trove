/**
 * Typed API client for app-mode admin endpoints (/api/app/admin/*).
 *
 * All admin endpoints require HTTP Basic auth. Pass credentials via
 * basicAuth(username, password) from ./client.
 */
import { type TroveConfig } from './config'
import { basicAuth, post, put } from './client'

export const appApi = {
  /**
   * Save updated configuration. Requires admin credentials.
   * @param config Updated configuration object
   * @param username Admin username
   * @param password Admin password
   */
  saveConfig: (
    config: TroveConfig,
    username: string,
    password: string,
  ): Promise<TroveConfig> =>
    put('/app/admin/config', config, { Authorization: basicAuth(username, password) }),

  /**
   * Build trove_model from the current config. Requires admin credentials.
   * Returns a raw Response for SSE streaming.
   */
  buildModel: (username: string, password: string): Promise<Response> =>
    post('/app/admin/build-model', undefined, {
      Authorization: basicAuth(username, password),
    }),
}
