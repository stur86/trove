/**
 * SetupWizard — six-step guided setup flow.
 *
 * Steps:
 *   0. Language   — pick locale, saved to config immediately
 *   1. Welcome    — system info table, begin button
 *   2. Ollama     — install Ollama (skipped if already installed)
 *   3. Models     — multi-select viable models, pull each in sequence
 *   4. Admin      — set admin username + password
 *   5. Service    — install systemd service, then redirect to /manage
 *
 * The step indicator at the top shows completed steps as ticked.
 * A step can only proceed once its action succeeds.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { configApi } from '../api/config'
import { ollamaApi, streamLines } from '../api/ollama'
import { setupApi, type SetupStatus } from '../api/setup'
import { systemApi, type ModelInfo, type SystemCheck } from '../api/system'
import { useTranslation } from '../i18n'

export default function SetupWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [locale, setLocale] = useState('en')
  const { t, ready } = useTranslation(locale)
  const [status, setStatus] = useState<SetupStatus | null>(null)
  const [system, setSystem] = useState<SystemCheck | null>(null)
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set())
  const [log, setLog] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [adminUser, setAdminUser] = useState('')
  const [adminPass, setAdminPass] = useState('')
  const logEndRef = useRef<HTMLDivElement>(null)

  // Load initial state on mount
  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    setupApi.status().then(setStatus)
    systemApi.check().then(setSystem)
  }, [])

  // Auto-scroll log to the bottom whenever a new line is appended
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [log])

  /** Append a log line, filtering [DONE] events and formatting errors. */
  function appendLog(line: string) {
    if (line.startsWith('[DONE]')) return
    setLog(prev => [
      ...prev,
      line.startsWith('[ERROR]') ? `ERROR: ${line.replace('[ERROR] ', '')}` : line,
    ])
  }

  // Step 0 — Language picker: save locale to config immediately
  async function handleLanguageSelect(newLocale: string) {
    setLocale(newLocale)
    await setupApi.setLanguage(newLocale)
  }

  // Step 2 — Install Ollama via SSE stream
  async function handleInstallOllama() {
    setBusy(true)
    setLog([])
    const res = await ollamaApi.install()
    await new Promise<void>(resolve =>
      streamLines(res, appendLog, resolve)
    )
    setBusy(false)
    setupApi.status().then(setStatus)
  }

  // Step 3 — Pull selected models one at a time, streaming progress
  async function handlePullModels() {
    if (selectedModels.size === 0) return
    setBusy(true)
    setLog([])
    for (const tag of selectedModels) {
      appendLog(`--- Downloading ${tag} ---`)
      const res = await ollamaApi.pull(tag)
      await new Promise<void>(resolve =>
        streamLines(res, appendLog, resolve)
      )
    }
    setBusy(false)
    setupApi.status().then(setStatus)
  }

  // Step 4 — Persist admin username and password
  async function handleSaveAdmin() {
    if (!adminUser || !adminPass) return
    setBusy(true)
    await setupApi.saveAdminCredentials(adminUser, adminPass)
    setBusy(false)
    setupApi.status().then(setStatus)
  }

  // Step 5 — Install the systemd service, then navigate to the management dashboard
  async function handleInstallService() {
    setBusy(true)
    setLog([])
    const res = await setupApi.installService()
    await new Promise<void>(resolve =>
      streamLines(res, appendLog, () => {
        resolve()
        navigate('/manage', { state: { justInstalled: true } })
      })
    )
    setBusy(false)
  }

  // Show a loading screen while config, setup status, and hardware info are fetched
  if (!ready || !status || !system) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <p className="text-gray-400">{t('setup.system_check')}</p>
      </div>
    )
  }

  const steps = [
    t('setup.language.title'),
    t('setup.welcome.title'),
    t('setup.install.title'),
    t('setup.models.title'),
    t('setup.admin.title'),
    t('setup.service.title'),
  ]

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Step indicator — completed steps show a tick, current step is highlighted */}
      <div className="border-b border-gray-700 bg-gray-800 px-6 py-4">
        <ol className="flex items-center gap-2 text-sm overflow-x-auto">
          {steps.map((label, i) => (
            <li key={i} className="flex items-center gap-2 whitespace-nowrap">
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  i < step
                    ? 'bg-green-600 text-white'
                    : i === step
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-600 text-gray-400'
                }`}
              >
                {i < step ? '✓' : i + 1}
              </span>
              <span className={i === step ? 'text-white font-medium' : 'text-gray-400'}>
                {label}
              </span>
              {i < steps.length - 1 && <span className="text-gray-600">›</span>}
            </li>
          ))}
        </ol>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-10">

        {/* Step 0: Language selection */}
        {step === 0 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.language.title')}</h1>
            <select
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
              value={locale}
              onChange={e => handleLanguageSelect(e.target.value)}
            >
              <option value="en">English</option>
              <option value="it">Italiano</option>
            </select>
            <button
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium"
              onClick={() => setStep(1)}
            >
              {t('setup.welcome.begin')}
            </button>
          </div>
        )}

        {/* Step 1: Welcome — show hardware summary */}
        {step === 1 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.welcome.title')}</h1>
            <p className="text-gray-300">{t('setup.welcome.description')}</p>
            <table className="w-full text-sm border border-gray-700 rounded-lg overflow-hidden">
              <tbody>
                <tr className="border-b border-gray-700">
                  <td className="px-4 py-2 text-gray-400 bg-gray-800">RAM</td>
                  <td className="px-4 py-2">{system.ram_gb.toFixed(1)} GB</td>
                </tr>
                <tr className="border-b border-gray-700">
                  <td className="px-4 py-2 text-gray-400 bg-gray-800">Disk</td>
                  <td className="px-4 py-2">{system.disk_free_gb.toFixed(1)} GB free</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 text-gray-400 bg-gray-800">GPU</td>
                  <td className="px-4 py-2">
                    {/* gpu.available is a boolean; vram_gb may be null if no GPU */}
                    {system.gpu.available && system.gpu.vram_gb !== null
                      ? `Detected (${system.gpu.vram_gb.toFixed(1)} GB VRAM)`
                      : 'None detected'}
                  </td>
                </tr>
              </tbody>
            </table>
            <button
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium"
              onClick={() => setStep(2)}
            >
              {t('setup.welcome.begin')}
            </button>
          </div>
        )}

        {/* Step 2: Install Ollama */}
        {step === 2 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.install.title')}</h1>
            <p className="text-gray-300">{t('setup.install.description')}</p>

            {status.ollama_installed ? (
              <div className="flex items-center gap-2 text-green-400">
                <span>✓</span>
                <span>{t('setup.install.already_done')}</span>
              </div>
            ) : (
              <button
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
                disabled={busy}
                onClick={handleInstallOllama}
              >
                {busy ? '...' : t('setup.install.button')}
              </button>
            )}

            {log.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-48 overflow-y-auto">
                {log.map((l, i) => <div key={i}>{l}</div>)}
                <div ref={logEndRef} />
              </div>
            )}

            <button
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium disabled:opacity-50"
              disabled={!status.ollama_installed || busy}
              onClick={() => setStep(3)}
            >
              {t('setup.install.next')}
            </button>
          </div>
        )}

        {/* Step 3: Choose and pull models */}
        {step === 3 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.models.title')}</h1>
            <p className="text-gray-300">{t('setup.models.description')}</p>

            <div className="space-y-3">
              {system.viable_models.map((m: ModelInfo) => (
                <label
                  key={m.tag}
                  className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedModels.has(m.tag)
                      ? 'border-blue-500 bg-blue-950'
                      : 'border-gray-700 bg-gray-800 hover:border-gray-500'
                  }`}
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selectedModels.has(m.tag)}
                    onChange={e => {
                      const next = new Set(selectedModels)
                      if (e.target.checked) next.add(m.tag)
                      else next.delete(m.tag)
                      setSelectedModels(next)
                    }}
                  />
                  <div>
                    <div className="font-medium">{m.tag}</div>
                    <div className="text-sm text-gray-400">
                      Min {m.min_ram_gb} GB RAM · Max {(m.max_ctx / 1024).toFixed(0)}K context
                      {m.audio && ' · Audio'}
                      {status.models_pulled.includes(m.tag) && (
                        <span className="ml-2 text-green-400">✓ downloaded</span>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </div>

            {log.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-48 overflow-y-auto">
                {log.map((l, i) => <div key={i}>{l}</div>)}
                <div ref={logEndRef} />
              </div>
            )}

            <div className="flex gap-3">
              <button
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
                disabled={selectedModels.size === 0 || busy}
                onClick={handlePullModels}
              >
                {busy ? '...' : t('setup.models.pull_button')}
              </button>
              <button
                className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium disabled:opacity-50"
                disabled={status.models_pulled.length === 0 || busy}
                onClick={() => setStep(4)}
              >
                {t('setup.models.next')}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Create admin account */}
        {step === 4 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.admin.title')}</h1>
            <p className="text-gray-300">{t('setup.admin.description')}</p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">{t('setup.admin.username')}</label>
                <input
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  value={adminUser}
                  onChange={e => setAdminUser(e.target.value)}
                  autoComplete="username"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">{t('setup.admin.password')}</label>
                <input
                  type="password"
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  value={adminPass}
                  onChange={e => setAdminPass(e.target.value)}
                  autoComplete="new-password"
                />
              </div>
            </div>

            {status.admin_configured && (
              <p className="text-green-400 text-sm">✓ Admin account saved</p>
            )}

            <div className="flex gap-3">
              <button
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
                disabled={!adminUser || !adminPass || busy}
                onClick={handleSaveAdmin}
              >
                {busy ? '...' : t('setup.admin.button')}
              </button>
              <button
                className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium disabled:opacity-50"
                disabled={!status.admin_configured || busy}
                onClick={() => setStep(5)}
              >
                {t('setup.admin.next')}
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Install systemd service and finish */}
        {step === 5 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.service.title')}</h1>
            <p className="text-gray-300">{t('setup.service.description')}</p>

            <button
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
              disabled={busy}
              onClick={handleInstallService}
            >
              {busy ? '...' : t('setup.service.button')}
            </button>

            {log.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-48 overflow-y-auto">
                {log.map((l, i) => <div key={i}>{l}</div>)}
                <div ref={logEndRef} />
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
