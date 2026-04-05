/**
 * Typed API wrapper for the Trove system check domain.
 *
 * Exposes a single GET operation that triggers hardware detection on the
 * backend and returns RAM, disk, GPU, and viable model information.
 */

import { get } from './client'
import { systemApi as _mockSystemApi } from './mock/system'

/** GPU detection result. */
export interface GpuInfo {
  available: boolean
  vram_gb: number | null
}

/** A Gemma 4 model variant with hardware requirements. */
export interface ModelInfo {
  /** Ollama model tag, e.g. 'gemma4:e4b' */
  tag: string
  /** Minimum RAM required for CPU inference (GB) */
  min_ram_gb: number
  /** Maximum context window supported by this model (tokens) */
  max_ctx: number
  /** Whether this model supports audio input */
  audio: boolean
}

/** Hardware snapshot returned by GET /api/system/check. */
export interface SystemCheck {
  ram_gb: number
  disk_free_gb: number
  gpu: GpuInfo
  ollama_running: boolean
  /** Models from the catalogue that fit within available RAM */
  viable_models: ModelInfo[]
}

const _realSystemApi = {
  /** Run system checks and return hardware info. */
  check: () => get<SystemCheck>('/system/check'),
}

/** API wrapper for the system check domain. Switches to mock when VITE_MOCK_API=1. */
export const systemApi = import.meta.env.VITE_MOCK_API ? _mockSystemApi : _realSystemApi
