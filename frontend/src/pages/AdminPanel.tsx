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
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Label, RangeSlider, Select, Spinner, TabItem, Tabs, TextInput } from 'flowbite-react'
import { appApi } from '../api/app'
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
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authed, setAuthed] = useState(false)
  const [loginError, setLoginError] = useState(false)

  const [config, setConfig] = useState<TroveConfig | null>(null)
  const [viableModels, setViableModels] = useState<ModelInfo[]>([])
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [buildLog, setBuildLog] = useState<string[]>([])
  const { t } = useTranslation(config?.locale ?? 'en')
  const navigate = useNavigate()
  const [gems, setGems] = useState<UserTask[]>([])
  const [gemsLoading, setGemsLoading] = useState(false)
  const [gemDeleteId, setGemDeleteId] = useState<string | null>(null)

  useEffect(() => {
    if (!authed) return
    Promise.all([configApi.get(), systemApi.check()]).then(([c, sys]) => {
      setConfig(c)
      setViableModels(sys.viable_models)
    })
  }, [authed])

  useEffect(() => {
    if (!authed) return
    setGemsLoading(true)
    gemsApi.list().then(list => { setGems(list); setGemsLoading(false) })
  }, [authed])

  /**
   * Verify admin credentials by attempting a config save with the supplied
   * username/password. 401 responses land in the catch branch.
   */
  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoginError(false)
    try {
      const current = await configApi.get()
      await appApi.saveConfig(current, username, password)
      setAuthed(true)
    } catch {
      setLoginError(true)
    }
  }

  /**
   * Save updated config then rebuild trove_model, streaming SSE progress lines.
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
        <Card className="w-full max-w-sm">
          <h1 className="text-xl font-bold text-center">{t('admin.login.title')}</h1>
          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <div>
              <div className="mb-2"><Label htmlFor="login-username">{t('admin.login.username')}</Label></div>
              <TextInput
                id="login-username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                autoComplete="username"
              />
            </div>
            <div>
              <div className="mb-2"><Label htmlFor="login-password">{t('admin.login.password')}</Label></div>
              <TextInput
                id="login-password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete="current-password"
                color={loginError ? 'failure' : undefined}
              />
            </div>
            {loginError && <Alert color="failure">{t('admin.login.error')}</Alert>}
            <Button color="blue" type="submit">{t('admin.login.button')}</Button>
          </form>
        </Card>
      </div>
    )
  }

  // Cap num_ctx slider at the selected model's context limit
  const selectedModel = viableModels.find(m => m.tag === config?.base_model)
  const maxCtx = selectedModel?.max_ctx ?? 131072

  // ── Admin panel ───────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto">
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
                  <RangeSlider
                    id="num-ctx-range"
                    min={512}
                    max={maxCtx}
                    step={512}
                    value={config.num_ctx}
                    onChange={e => setConfig({ ...config, num_ctx: Number(e.target.value) })}
                  />
                </div>

                <div>
                  <div className="mb-2"><Label htmlFor="locale">{t('config.locale')}</Label></div>
                  <Select id="locale" value={config.locale} onChange={e => setConfig({ ...config, locale: e.target.value })}>
                    <option value="en">English</option>
                    <option value="it">Italiano</option>
                  </Select>
                </div>

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

          <TabItem title={t('admin.tab.tasks', 'Gems')}>
            <div className="pt-4 flex flex-col gap-4">
              <div className="flex justify-end">
                <Button
                  color="blue"
                  size="sm"
                  onClick={() => navigate('/admin/gems/new', { state: { username, password } })}
                >
                  + New Gem
                </Button>
              </div>

              {gemsLoading ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : gems.length === 0 ? (
                <p className="text-gray-400 text-sm">No gems yet.</p>
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
                          onClick={() =>
                            navigate(`/admin/gems/${gem.id}/edit`, { state: { username, password } })
                          }
                        >
                          Edit
                        </Button>
                        <Button
                          color="failure"
                          size="xs"
                          disabled={gemDeleteId === gem.id}
                          onClick={async () => {
                            setGemDeleteId(gem.id)
                            try {
                              await gemsApi.delete(gem.id, username, password)
                              setGems(gs => gs.filter(g => g.id !== gem.id))
                            } finally {
                              setGemDeleteId(null)
                            }
                          }}
                        >
                          {gemDeleteId === gem.id ? <Spinner size="xs" /> : 'Delete'}
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
