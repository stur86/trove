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
import { useLocation, useNavigate } from 'react-router-dom'
import { Alert, Button, Label, Select, Spinner, TabItem, Tabs } from 'flowbite-react'
import { appApi } from '../api/app'
import AdminLogin from '../components/AdminLogin'
import { type TroveConfig, configApi } from '../api/config'
import { streamLines } from '../api/ollama'
import { systemApi, type ModelInfo } from '../api/system'
import { gemsApi, type UserTask } from '../api/tasks'
import GemIcon from '../components/GemIcon'
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
  const [authed, setAuthed] = useState(false)
  const [loginError, setLoginError] = useState(false)
  const location = useLocation()

  const [config, setConfig] = useState<TroveConfig | null>(null)
  const [viableModels, setViableModels] = useState<ModelInfo[]>([])
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [buildLog, setBuildLog] = useState<string[]>([])
  const [networkUrl, setNetworkUrl] = useState<string | null>(null)
  const [urlCopied, setUrlCopied] = useState(false)
  const { t } = useTranslation(config?.locale ?? 'en')
  const navigate = useNavigate()
  const [gems, setGems] = useState<UserTask[]>([])
  const [gemsLoading, setGemsLoading] = useState(false)
  const [gemDeleteId, setGemDeleteId] = useState<string | null>(null)

  useEffect(() => {
    if (!authed) return
    Promise.all([configApi.get(), systemApi.check(), appApi.networkUrl()]).then(([c, sys, net]) => {
      setConfig(c)
      setViableModels(sys.viable_models)
      setNetworkUrl(net.url)
    })
  }, [authed])

  useEffect(() => {
    if (!authed) return
    setGemsLoading(true)
    gemsApi.list()
      .then(list => { setGems(list); setGemsLoading(false) })
      .catch(() => setGemsLoading(false))
  }, [authed])

  // On first render, check whether the admin cookie is already present.
  useEffect(() => {
    appApi.checkAdminValid()
      .then(res => { if (res.admin_auth === 'true') setAuthed(true) })
      .catch(() => {})
  }, [])

  /**
   * Verify admin credentials by attempting a config save with the supplied
   * username/password. 401 responses land in the catch branch.
   */
  async function handleLogin(usernameArg: string, passwordArg: string) {
    setLoginError(false)
    try {
      await appApi.login(usernameArg, passwordArg)
      setAuthed(true)
    } catch {
      setLoginError(true)
    }
  }

  async function handleLogout() {
    await appApi.logout().catch(() => {})
    setAuthed(false)
  }

  /**
   * Save updated config then rebuild trove_model, streaming SSE progress lines.
   */
  async function handleSave() {
    if (!config) return
    setSaveState('saving')
    setBuildLog([])
    try {
      await appApi.saveConfig(config)
      setSaveState('building')
      const res = await appApi.buildModel()
      await new Promise<void>(resolve =>
        streamLines(
          res,
          line => { if (!line.startsWith('[DONE]')) setBuildLog(prev => [...prev, line]) },
          () => { setSaveState('done'); resolve() },
        )
      )
    } catch {
      setSaveState('error')
    }
  }

  // ── Login screen ──────────────────────────────────────────────────────────
  if (!authed) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <AdminLogin onSubmit={handleLogin} loginError={loginError} title={t('admin.login.title')} />
        
      </div>
    )
  }

  // Cap num_ctx slider at the selected model's context limit
  const selectedModel = viableModels.find(m => m.tag === config?.base_model)
  const maxCtx = selectedModel?.max_ctx ?? 131072

  // Whether to open on the Gems tab (set by GemForm after create/update)
  const startOnGems = (location.state as { tab?: string } | null)?.tab === 'gems'

  // ── Admin panel ───────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex justify-between items-center mb-2">
          <button
            onClick={() => navigate('/')}
            className="text-gray-400 hover:text-gray-600 text-sm"
          >
            {t('admin.back')}
          </button>
          <Button color="light" size="xs" onClick={handleLogout}>
            {t('admin.logout')}
          </Button>
        </div>
        <Tabs variant="underline">

          <TabItem title={t('admin.tab.settings')}>
            {config && (
              <div className="flex flex-col gap-6 pt-4">
                <div>
                  <div className="mb-2"><Label htmlFor="base-model">{t('config.base_model')}</Label></div>
                  <Select
                    id="base-model"
                    value={config.base_model}
                    onChange={e => {
                      const m = viableModels.find(m => m.tag === e.target.value)
                      setConfig({
                        ...config,
                        base_model: e.target.value,
                        // Clamp num_ctx to the new model's maximum when switching
                        num_ctx: Math.min(config.num_ctx, m?.max_ctx ?? maxCtx),
                      })
                    }}
                  >
                    {(viableModels.length > 0 ? viableModels : [{ tag: config.base_model } as ModelInfo]).map(m => (
                      <option key={m.tag} value={m.tag}>{MODEL_LABELS[m.tag] ?? m.tag}</option>
                    ))}
                  </Select>
                </div>

                <div>
                  <div className="mb-2">
                    <Label htmlFor="num-ctx-range">{t('config.num_ctx')}: {config.num_ctx.toLocaleString()}</Label>
                  </div>
                  {/*
                    * Plain range input instead of Flowbite RangeSlider: Flowbite's component
                    * uses `appearance-none` which prevents `accent-color` from applying the
                    * progress fill. Using a native input with accent-blue-700 lets the browser
                    * render the filled track natively in all modern browsers.
                    */}
                  <input
                    id="num-ctx-range"
                    type="range"
                    min={512}
                    max={maxCtx}
                    step={512}
                    value={config.num_ctx}
                    onChange={e => setConfig({ ...config, num_ctx: Number(e.target.value) })}
                    className="w-full cursor-pointer accent-blue-700"
                  />
                </div>

                <div>
                  <div className="mb-2"><Label htmlFor="locale">{t('config.locale')}</Label></div>
                  <Select id="locale" value={config.locale} onChange={e => setConfig({ ...config, locale: e.target.value })}>
                    <option value="en">English</option>
                    <option value="it">Italiano</option>
                  </Select>
                </div>

                {/* LAN URL */}
                {networkUrl && (
                  <div>
                    <div className="mb-2"><Label>{t('admin.network_url.label')}</Label></div>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-gray-100 text-gray-800 text-sm font-mono px-3 py-2 rounded-lg truncate">
                        {networkUrl}
                      </code>
                      <Button
                        color="light"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(networkUrl)
                          setUrlCopied(true)
                          setTimeout(() => setUrlCopied(false), 2000)
                        }}
                      >
                        {urlCopied ? t('admin.network_url.copied') : t('admin.network_url.copy')}
                      </Button>
                    </div>
                  </div>
                )}

                <div>
                  <Button
                    color="blue"
                    disabled={saveState === 'saving' || saveState === 'building'}
                    onClick={handleSave}
                  >
                    {saveState === 'done' ? t('config.saved') : t('config.save')}
                  </Button>
                </div>

                {/* Live build log */}
                {buildLog.length > 0 && (
                  <pre className="bg-gray-900 text-gray-300 rounded-lg p-4 text-xs font-mono max-h-48 overflow-y-auto whitespace-pre-wrap">
                    {buildLog.join('\n')}
                  </pre>
                )}

                {saveState === 'error' && <Alert color="failure">Failed to save. Check credentials.</Alert>}
              </div>
            )}
          </TabItem>

          <TabItem title={t('admin.tab.documents')}>
            <p className="pt-4 text-gray-500">{t('admin.documents.placeholder')}</p>
          </TabItem>

          <TabItem title={t('admin.tab.tasks', 'Gems')} active={startOnGems}>
            <div className="pt-4 flex flex-col gap-4">
              <div className="flex justify-end">
                <Button
                  color="blue"
                  size="sm"
                  onClick={() => navigate('/admin/gems/new')}
                >
                  {t('admin.gems.new')}
                </Button>
              </div>

              {gemsLoading ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : gems.length === 0 ? (
                <p className="text-gray-400 text-sm">{t('admin.gems.empty')}</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {gems.map(gem => (
                    <div
                      key={gem.id}
                      className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg p-3"
                    >
                      <GemIcon hue={gem.hue} size={32} />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-gray-900 truncate">{gem.name}</p>
                        {gem.description && (
                          <p className="text-xs text-gray-400 truncate">{gem.description}</p>
                        )}
                      </div>
                      <div className="flex gap-2 shrink-0">
                        <Button
                          color="light"
                          size="xs"
                          onClick={() => navigate(`/admin/gems/${gem.id}/edit`)}
                        >
                          {t('admin.gems.edit')}
                        </Button>
                        <Button
                          color="failure"
                          size="xs"
                          disabled={gemDeleteId === gem.id}
                          onClick={async () => {
                            setGemDeleteId(gem.id)
                            try {
                              await gemsApi.delete(gem.id)
                              setGems(gs => gs.filter(g => g.id !== gem.id))
                            } finally {
                              setGemDeleteId(null)
                            }
                          }}
                        >
                          {gemDeleteId === gem.id ? <Spinner size="xs" /> : t('admin.gems.delete')}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabItem>

        </Tabs>
      </div>
    </div>
  )
}
