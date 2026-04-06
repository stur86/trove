/**
 * Mock implementation of appApi.
 *
 * In mock mode the admin is always considered logged in (checkAdminValid
 * returns 'true') and all write operations succeed silently.
 */
import type { TroveConfig } from '../config'
import { mockSSELines } from './_stream'

export const appApi = {
  login: async (_username: string, _password: string): Promise<void> => {
    await new Promise(r => setTimeout(r, 150))
  },

  checkAdminValid: async (): Promise<{ admin_auth: string | null }> => {
    await new Promise(r => setTimeout(r, 50))
    return { admin_auth: 'true' }
  },

  logout: async (): Promise<void> => {
    await new Promise(r => setTimeout(r, 100))
  },

  saveConfig: async (config: TroveConfig): Promise<TroveConfig> => {
    await new Promise(r => setTimeout(r, 200))
    return { ...config }
  },

  buildModel: (): Promise<Response> =>
    mockSSELines([
      'Generating Modelfile…',
      'FROM gemma4:e4b',
      'PARAMETER num_ctx 8192',
      'Building trove_model…',
      'Successfully built trove_model',
    ], 300),

  networkUrl: async (): Promise<{ url: string | null }> => {
    await new Promise(r => setTimeout(r, 50))
    return { url: 'http://192.168.1.100:7770' }
  },
}
