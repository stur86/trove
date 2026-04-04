/**
 * AdminPanel — tabbed admin interface for app mode (/admin).
 *
 * Requires admin login (HTTP Basic). On first render shows a login form.
 * Credentials are stored in component state only (cleared on page refresh).
 *
 * Tabs:
 *   Settings  — model picker, num_ctx slider, language selector, save + build
 *   Documents — placeholder
 *   Tasks     — placeholder
 */

import { useEffect, useState } from 'react'
import { appApi } from '../api/app'
import { type TroveConfig, configApi } from '../api/config'
import { streamLines } from '../api/ollama'
import { systemApi, type ModelInfo } from '../api/system'
import { useTranslation } from '../i18n'

/** Possible states for the save + build operation. */
type SaveState = 'idle' | 'saving' | 'building' | 'done' | 'error'

/** Human-readable labels for each Gemma 4 model variant. */
const MODEL_LABELS: Record<string, string> = {
  'gemma4:e2b': 'Gemma 4 E2B — 2.3B effective (fastest, audio)',
  'gemma4:e4b': 'Gemma 4 E4B — 4.5B effective (balanced, audio)',
  'gemma4:26b': 'Gemma 4 26B MoE — 4B activated (efficient large)',
  'gemma4:31b': 'Gemma 4 31B — dense (most capable)',
}

export default function AdminPanel() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authed, setAuthed] = useState(false)
  const [loginError, setLoginError] = useState(false)
  const [activeTab, setActiveTab] = useState<'settings' | 'documents' | 'tasks'>('settings')

  const [config, setConfig] = useState<TroveConfig | null>(null)
  const [viableModels, setViableModels] = useState<ModelInfo[]>([])
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [buildLog, setBuildLog] = useState<string[]>([])
  const { t } = useTranslation(config?.locale ?? 'en')

  // Load config and viable models after successful login
  useEffect(() => {
    if (!authed) return
    Promise.all([configApi.get(), systemApi.check()]).then(([c, sys]) => {
      setConfig(c)
      setViableModels(sys.viable_models)
    })
  }, [authed])

  /**
   * Verify admin credentials by attempting a config save with the supplied
   * username/password. If the backend returns 401 the catch branch fires and
   * we show the inline error message.
   */
  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoginError(false)
    try {
      // Use the current config to probe authentication
      const current = await configApi.get()
      await appApi.saveConfig(current, username, password)
      setAuthed(true)
    } catch {
      setLoginError(true)
    }
  }

  /**
   * Save updated config then rebuild trove_model from the new settings.
   *
   * The build step streams SSE lines from the backend; each line is appended
   * to buildLog so the admin can see progress in real time.
   */
  async function handleSave() {
    if (!config) return
    setSaveState('saving')
    setBuildLog([])
    try {
      await appApi.saveConfig(config, username, password)
      setSaveState('building')
      const res = await appApi.buildModel(username, password)
      await new Promise<void>(resolve =>
        streamLines(
          res,
          line => {
            // Filter out the terminal [DONE] sentinel from the log display
            if (!line.startsWith('[DONE]')) {
              setBuildLog(prev => [...prev, line])
            }
          },
          () => {
            setSaveState('done')
            resolve()
          },
        )
      )
    } catch {
      setSaveState('error')
    }
  }

  // ── Login screen ──────────────────────────────────────────────────────────
  if (!authed) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="w-full max-w-sm bg-gray-800 border border-gray-700 rounded-xl p-8 space-y-6">
          <h1 className="text-xl font-bold text-center">{t('admin.login.title')}</h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                {t('admin.login.username')}
              </label>
              <input
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                value={username}
                onChange={e => setUsername(e.target.value)}
                autoComplete="username"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                {t('admin.login.password')}
              </label>
              <input
                type="password"
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            {loginError && (
              <p className="text-red-400 text-sm">{t('admin.login.error')}</p>
            )}
            <button
              type="submit"
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium"
            >
              {t('admin.login.button')}
            </button>
          </form>
        </div>
      </div>
    )
  }

  // Cap num_ctx slider at the selected model's context limit
  const selectedModel = viableModels.find(m => m.tag === config?.base_model)
  const maxCtx = selectedModel?.max_ctx ?? 131072

  // ── Admin panel — tabs ────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Tab bar */}
      <div className="border-b border-gray-700 bg-gray-800 px-6">
        <div className="flex gap-1">
          {(['settings', 'documents', 'tasks'] as const).map(tab => (
            <button
              key={tab}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-blue-500 text-white'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
              onClick={() => setActiveTab(tab)}
            >
              {t(`admin.tab.${tab}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-10">

        {/* Settings tab */}
        {activeTab === 'settings' && config && (
          <div className="space-y-6">
            {/* Base model selector — only models that fit available RAM */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                {t('config.base_model')}
              </label>
              <select
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
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
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                {t('config.num_ctx')}: {config.num_ctx.toLocaleString()}
              </label>
              <input
                type="range"
                min={512}
                max={maxCtx}
                step={512}
                value={config.num_ctx}
                onChange={e => setConfig({ ...config, num_ctx: Number(e.target.value) })}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>512</span>
                <span>{Math.round(maxCtx / 1000)}K</span>
              </div>
            </div>

            {/* Language selector */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                {t('config.locale')}
              </label>
              <select
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
                value={config.locale}
                onChange={e => setConfig({ ...config, locale: e.target.value })}
              >
                <option value="en">English</option>
                <option value="it">Italiano</option>
              </select>
            </div>

            <button
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
              disabled={saveState === 'saving' || saveState === 'building'}
              onClick={handleSave}
            >
              {saveState === 'saving'
                ? 'Saving...'
                : saveState === 'building'
                ? 'Building model...'
                : saveState === 'done'
                ? t('config.saved')
                : t('config.save')}
            </button>

            {/* Live build log */}
            {buildLog.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-48 overflow-y-auto">
                {buildLog.map((line, i) => (
                  <div key={i}>{line}</div>
                ))}
              </div>
            )}

            {saveState === 'error' && (
              <p className="text-red-400 text-sm">Failed to save. Check credentials.</p>
            )}
          </div>
        )}

        {/* Documents tab — placeholder until Task N */}
        {activeTab === 'documents' && (
          <p className="text-gray-400">{t('admin.documents.placeholder')}</p>
        )}

        {/* Tasks tab — placeholder until Task N */}
        {activeTab === 'tasks' && (
          <p className="text-gray-400">{t('admin.tasks.placeholder')}</p>
        )}

      </div>
    </div>
  )
}
