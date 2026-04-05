/**
 * Mock implementation of configApi.
 * Returns a default TroveConfig with a short delay.
 */
import type { TroveConfig } from '../config'

const DEFAULT_CONFIG: TroveConfig = {
  base_model: 'gemma4:e4b',
  num_ctx: 8192,
  locale: 'en',
}

export const configApi = {
  get: async (): Promise<TroveConfig> => {
    await new Promise(r => setTimeout(r, 100))
    return { ...DEFAULT_CONFIG }
  },
  update: async (config: TroveConfig): Promise<TroveConfig> => {
    await new Promise(r => setTimeout(r, 200))
    return { ...config }
  },
}
