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

import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Alert, Button, Label, Modal, ModalBody, ModalFooter, ModalHeader, Select, Spinner, TabItem, Tabs, RangeSlider } from 'flowbite-react'
import { appApi } from '../api/app'
import AdminLogin, { isAllowedAdmin } from '../components/AdminLogin'
import { type TroveConfig, configApi } from '../api/config'
import { streamLines } from '../api/ollama'
import { systemApi, type ModelInfo } from '../api/system'
import { gemsApi, type UserTask } from '../api/tasks'
import { bundleApi, type ImportResult } from '../api/bundle'
import GemIcon from '../components/GemIcon'
import DocumentsPanel from './DocumentsPanel'
import HelpBar from '../components/HelpBar'
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
  // Admin login is only possible from the machine running the server.
  // On any other device the login form is hidden and replaced with a notice.
  const isAllowed = isAllowedAdmin();

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
  const [logLines, setLogLines] = useState<string[]>([])
  const logEndRef = useRef<HTMLDivElement | null>(null)

  // Bundle export/import state
  const [exporting, setExporting] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importMode, setImportMode] = useState<'add' | 'replace'>('add')
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [importError, setImportError] = useState<string | null>(null)

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

  // Fetch logs immediately once authed, then every 5 seconds.
  useEffect(() => {
    if (!authed) return
    function fetchLogs() {
      appApi.logs().then(r => setLogLines(r.lines))
    }
    fetchLogs()
    const id = setInterval(fetchLogs, 5000)
    return () => clearInterval(id)
  }, [authed])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logLines])

  // On first render, check whether the admin cookie is already present.
  useEffect(() => {
    appApi.checkAdminValid()
      .then(res => { if (res.valid) setAuthed(true) })
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

  /** Fetch the bundle ZIP from the server and trigger a browser download. */
  async function handleExport() {
    setExporting(true)
    try {
      const blob = await bundleApi.exportBundle()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'trove-bundle.zip'
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }

  /** POST the chosen ZIP file to the import endpoint. */
  async function handleImport() {
    if (!importFile) return
    setImporting(true)
    setImportError(null)
    setImportResult(null)
    try {
      const result = await bundleApi.importBundle(importFile, importMode)
      setImportResult(result)
    } catch (e) {
      setImportError(String(e))
    } finally {
      setImporting(false)
    }
  }

  // ── Login screen ──────────────────────────────────────────────────────────
  if (!authed) {
    if (!isAllowed) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="text-center max-w-sm">
            <p className="text-gray-700 text-lg font-semibold mb-2">Admin access unavailable</p>
            <p className="text-gray-500 text-sm">
              Admin login is only available from the server machine.
              Open <code className="bg-gray-100 px-1 rounded">http://localhost:7770</code> in a browser on that machine.
            </p>
          </div>
        </div>
      )
    }
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

  // True when the selected model lacks audio AND at least one saved gem uses audio.
  // Shown as a warning so the admin knows those gems will be hidden from users.
  const audioGemsExist = gems.some(g => g.has_audio)
  const selectedModelSupportsAudio = ["gemma4:e2b", "gemma4:e4b"].includes(config?.base_model ?? '')
  const showAudioWarning = audioGemsExist && !selectedModelSupportsAudio

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
                  <div className="mt-2">
                    <HelpBar
                      prompt={t('help.model.prompt')}
                      title={t('help.model.title')}
                      content={t('help.model.content')}
                    />
                  </div>
                </div>

                {showAudioWarning && (
                  <Alert color="warning">
                    {t('admin.settings.audio_warning')}
                  </Alert>
                )}

                <div>
                  <div className="mb-2">
                    <Label htmlFor="num-ctx-range">{t('config.num_ctx')}: {config.num_ctx.toLocaleString()}</Label>
                  </div>
                  <RangeSlider
                    id="num-ctx-range"
                    min={512}
                    max={maxCtx}
                    sizing='lg'
                    step={512}
                    value={config.num_ctx}
                    onChange={e => setConfig({ ...config, num_ctx: Number(e.target.value) })}
                  />
                  {config.num_ctx > 8192 && (
                    <Alert color="warning" className="mt-2">
                      High context windows use a lot of extra memory. On some machines this can cause the server to slow down or become unresponsive. Try a short test run before using this setting with real users.
                    </Alert>
                  )}
                  <div className="mt-2">
                    <HelpBar
                      prompt={t('help.ctx.prompt')}
                      title={t('help.ctx.title')}
                      content={t('help.ctx.content')}
                    />
                  </div>
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

                {/* Data section — export and import bundle */}
                <div className="border-t border-gray-200 pt-6 flex flex-col gap-4">
                  <Label className="text-base font-semibold text-gray-800">Data</Label>
                  <HelpBar
                    prompt={t('help.bundle.prompt')}
                    title={t('help.bundle.title')}
                    content={t('help.bundle.content')}
                  />
                  <div className="flex gap-3">
                    <Button color="light" disabled={exporting} onClick={handleExport}>
                      {exporting ? <><Spinner size="sm" className="mr-2" />Exporting…</> : 'Export bundle'}
                    </Button>
                    <Button color="light" onClick={() => {
                      setImportFile(null)
                      setImportMode('add')
                      setImportResult(null)
                      setImportError(null)
                      setShowImportModal(true)
                    }}>
                      Import bundle
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </TabItem>

          <TabItem title={t('admin.tab.documents')}>
            <DocumentsPanel />
          </TabItem>

          <TabItem title={t('admin.tab.logs')}>
            <div className="pt-4">
              <pre className="bg-gray-900 text-gray-300 rounded-lg p-4 text-xs font-mono h-96 overflow-y-auto whitespace-pre-wrap">
                {logLines.length > 0 ? logLines.join('\n') : '(no log entries yet)'}
                <div ref={logEndRef} />
              </pre>
            </div>
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

      {/* Import bundle modal */}
      <Modal show={showImportModal} onClose={() => setShowImportModal(false)} size="md">
        <ModalHeader>Import bundle</ModalHeader>
        <ModalBody>
          <div className="flex flex-col gap-4">
            {/* Mode selector */}
            <div className="flex flex-col gap-2">
              <Label>Import mode</Label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="import-mode"
                    value="add"
                    checked={importMode === 'add'}
                    onChange={() => setImportMode('add')}
                  />
                  <span className="text-sm text-gray-700">Add — merge with existing data</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="import-mode"
                    value="replace"
                    checked={importMode === 'replace'}
                    onChange={() => setImportMode('replace')}
                  />
                  <span className="text-sm text-gray-700">Replace — wipe and reimport</span>
                </label>
              </div>
              {importMode === 'replace' && (
                <Alert color="warning">
                  This will permanently delete all current gems and documents before importing.
                </Alert>
              )}
            </div>

            {/* File picker */}
            <div>
              <Label htmlFor="bundle-file">Bundle ZIP file</Label>
              <input
                id="bundle-file"
                type="file"
                accept=".zip"
                className="mt-1 block w-full text-sm text-gray-500"
                onChange={e => setImportFile(e.target.files?.[0] ?? null)}
              />
            </div>

            {/* Result feedback */}
            {importResult && (
              <Alert color="success">
                Import complete: {importResult.gems_imported} gem{importResult.gems_imported !== 1 ? 's' : ''} and{' '}
                {importResult.documents_imported} document{importResult.documents_imported !== 1 ? 's' : ''} imported.
                {Object.keys(importResult.documents_renamed).length > 0 && (
                  <> {Object.keys(importResult.documents_renamed).length} document{Object.keys(importResult.documents_renamed).length !== 1 ? 's' : ''} renamed.</>
                )}
                {Object.keys(importResult.gems_renamed).length > 0 && (
                  <> {Object.keys(importResult.gems_renamed).length} gem{Object.keys(importResult.gems_renamed).length !== 1 ? 's' : ''} renamed.</>
                )}
              </Alert>
            )}
            {importError && <Alert color="failure">{importError}</Alert>}
          </div>
        </ModalBody>
        <ModalFooter>
          <Button
            color="blue"
            disabled={!importFile || importing}
            onClick={handleImport}
          >
            {importing ? <><Spinner size="sm" className="mr-2" />Importing…</> : 'Import'}
          </Button>
          <Button color="light" onClick={() => setShowImportModal(false)}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}
