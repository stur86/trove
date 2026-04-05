/**
 * Mock implementation of systemApi.
 * Returns a pre-populated SystemCheck so the admin settings tab renders.
 */
import type { SystemCheck } from '../system'

export const systemApi = {
  check: async (): Promise<SystemCheck> => {
    await new Promise(r => setTimeout(r, 150))
    return {
      ram_gb: 16,
      disk_free_gb: 120,
      gpu: { available: false, vram_gb: null },
      ollama_running: true,
      viable_models: [
        { tag: 'gemma4:e2b', min_ram_gb: 4,  max_ctx: 131072, audio: true  },
        { tag: 'gemma4:e4b', min_ram_gb: 6,  max_ctx: 131072, audio: true  },
        { tag: 'gemma4:26b', min_ram_gb: 10, max_ctx: 262144, audio: false },
      ],
    }
  },
}
