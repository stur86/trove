/**
 * Typed API wrapper for the Trove config domain.
 *
 * Exposes GET and PUT operations for server configuration persisted
 * to ~/.config/trove/config.json on the backend.
 */

import { get, put } from './client'

/** Server configuration persisted to ~/.config/trove/config.json. */
export interface TroveConfig {
  /** Ollama model tag, e.g. 'gemma4:e4b' */
  base_model: string
  /** Context window size in tokens (512–262144) */
  num_ctx: number
  /** BCP-47 locale code for the UI, e.g. 'en' */
  locale: string
}

/** API wrapper for the config domain. */
export const configApi = {
  /** Fetch the current server configuration. */
  get: () => get<TroveConfig>('/config'),
  /** Persist updated configuration and return it. */
  update: (config: TroveConfig) => put<TroveConfig>('/config', config),
}
