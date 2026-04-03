import { useEffect, useState } from 'react'
import { type TroveConfig, configApi } from '../api/config'
import { type ModelInfo, systemApi } from '../api/system'
import { useTranslation } from '../i18n'

/** Human-readable labels for each Gemma 4 model variant. */
const MODEL_LABELS: Record<string, string> = {
  'gemma4:e2b': 'Gemma 4 E2B — 2.3B effective (fastest, audio)',
  'gemma4:e4b': 'Gemma 4 E4B — 4.5B effective (balanced, audio)',
  'gemma4:26b': 'Gemma 4 26B MoE — 4B activated (efficient large)',
  'gemma4:31b': 'Gemma 4 31B — dense (most capable)',
}

/**
 * Admin configuration page.
 *
 * Loads current config and viable models on mount. Allows the admin to:
 * - Pick a base model (only models that fit in available RAM are shown)
 * - Set the context window size (slider capped at the selected model's max)
 * - Choose the UI language
 *
 * Saves changes to the backend on button click.
 */
export default function Admin() {
  const [config, setConfig] = useState<TroveConfig | null>(null)
  const [viableModels, setViableModels] = useState<ModelInfo[]>([])
  const [saved, setSaved] = useState(false)
  const { t } = useTranslation(config?.locale ?? 'en')

  useEffect(() => {
    // Load config and system check in parallel
    Promise.all([configApi.get(), systemApi.check()]).then(([c, sys]) => {
      setConfig(c)
      setViableModels(sys.viable_models)
    })
  }, [])

  /** Persist the current config to the backend. */
  async function handleSave() {
    if (!config) return
    await configApi.update(config)
    setSaved(true)
    // Reset the "Saved" confirmation after 2 seconds
    setTimeout(() => setSaved(false), 2000)
  }

  if (!config) {
    return <div style={{ padding: '2rem' }}>Loading...</div>
  }

  // Cap the slider maximum at the selected model's context window limit
  const selectedModel = viableModels.find(m => m.tag === config.base_model)
  const maxCtx = selectedModel?.max_ctx ?? 131072

  return (
    <div style={{ padding: '2rem', maxWidth: '480px', margin: '0 auto' }}>
      <h1>{t('config.title')}</h1>

      {/* Base model selector — only shows models viable for this machine's RAM */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.4rem' }}>
          {t('config.base_model')}
        </label>
        <select
          value={config.base_model}
          onChange={e => {
            const newModel = viableModels.find(m => m.tag === e.target.value)
            const newMaxCtx = newModel?.max_ctx ?? maxCtx
            setConfig({
              ...config,
              base_model: e.target.value,
              // Clamp num_ctx to the new model's maximum when switching
              num_ctx: Math.min(config.num_ctx, newMaxCtx),
            })
          }}
          style={{ width: '100%', padding: '0.5rem' }}
        >
          {viableModels.length > 0
            ? viableModels.map(m => (
                <option key={m.tag} value={m.tag}>
                  {MODEL_LABELS[m.tag] ?? m.tag}
                </option>
              ))
            : (
              // Fallback: show current model even if viable_models is empty
              <option value={config.base_model}>
                {MODEL_LABELS[config.base_model] ?? config.base_model}
              </option>
            )
          }
        </select>
      </div>

      {/* Context window slider — bounded by the selected model's max */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.4rem' }}>
          {t('config.num_ctx')}: {config.num_ctx.toLocaleString()}
        </label>
        <input
          type="range"
          min={512}
          max={maxCtx}
          step={512}
          value={config.num_ctx}
          onChange={e => setConfig({ ...config, num_ctx: parseInt(e.target.value) })}
          style={{ width: '100%' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#888' }}>
          <span>512</span>
          <span>{Math.round(maxCtx / 1000)}K</span>
        </div>
      </div>

      {/* Language selector — populated from available locale files */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.4rem' }}>
          {t('config.locale')}
        </label>
        <select
          value={config.locale}
          onChange={e => setConfig({ ...config, locale: e.target.value })}
          style={{ width: '100%', padding: '0.5rem' }}
        >
          <option value="en">English</option>
        </select>
      </div>

      <button
        onClick={handleSave}
        style={{ padding: '0.75rem 2rem', fontSize: '1rem', cursor: 'pointer' }}
      >
        {saved ? t('config.saved') : t('config.save')}
      </button>
    </div>
  )
}
