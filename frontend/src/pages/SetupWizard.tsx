/**
 * SetupWizard — five-step guided setup flow.
 *
 * Steps:
 *   0. Language   — pick locale, saved to config immediately
 *   1. Welcome    — system info table, begin button
 *   2. Ollama     — install Ollama (skipped if already installed)
 *   3. Models     — multi-select viable models, pull each in sequence
 *   4. Admin      — set admin username + password, then redirect to /
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Label, Select, Spinner, Table, TableBody, TableCell, TableRow, TextInput } from 'flowbite-react'
import { configApi } from '../api/config'
import { ollamaApi, streamLines } from '../api/ollama'
import { setupApi, type SetupStatus } from '../api/setup'
import { systemApi, type ModelInfo, type SystemCheck } from '../api/system'
import { useTranslation } from '../i18n'
import type { TranslationFunction } from '../i18n'

import type { Dispatch, SetStateAction, RefObject } from 'react'

/**
 * Tracks whether Ollama is ready during step 2 (Install Ollama).
 *
 * - idle        — not yet checked (initial state before entering step 2)
 * - starting    — POST /ollama/start in progress
 * - running     — server is up and accepting requests
 * - not_installed — binary not found; user must install
 * - failed      — server is installed but did not start in time
 */
type OllamaPhase = 'idle' | 'starting' | 'running' | 'not_installed' | 'failed'

/** Presentational components for each step (defined before main component) */
function LogBox({ log, logEndRef }: { log: string[]; logEndRef: RefObject<HTMLDivElement | null> }) {
  return log.length > 0 ? (
    <pre className="bg-gray-900 text-gray-300 rounded-lg p-4 text-xs font-mono max-h-48 overflow-y-auto whitespace-pre-wrap">
      {log.join('\n')}
      <div ref={logEndRef} />
    </pre>
  ) : null
}

function LanguageStep({ t, locale, onChangeLocale, onNext }: { t: TranslationFunction; locale: string; onChangeLocale: (l: string) => Promise<void>; onNext: () => void }) {
  return (
    <>
      <h1 className="text-2xl font-bold">{t('setup.language.title')}</h1>
      <div>
        <div className="mb-2"><Label htmlFor="language-select">Language</Label></div>
        <Select id="language-select" value={locale} onChange={e => void onChangeLocale(e.target.value)}>
          <option value="en">English</option>
          <option value="it">Italiano</option>
        </Select>
      </div>
      <div><Button color="blue" onClick={onNext}>{t('setup.welcome.begin')}</Button></div>
    </>
  )
}

function WelcomeStep({ t, system, onNext }: { t: TranslationFunction; system: SystemCheck; onNext: () => void }) {
  return (
    <>
      <h1 className="text-2xl font-bold">{t('setup.welcome.title')}</h1>
      <p className="text-gray-600">{t('setup.welcome.description')}</p>
      <Table>
        <TableBody className="divide-y">
          <TableRow className="bg-white">
            <TableCell className="font-medium text-gray-900">RAM</TableCell>
            <TableCell>{system.ram_gb.toFixed(1)} GB</TableCell>
          </TableRow>
          <TableRow className="bg-white">
            <TableCell className="font-medium text-gray-900">Disk</TableCell>
            <TableCell>{system.disk_free_gb.toFixed(1)} GB free</TableCell>
          </TableRow>
          <TableRow className="bg-white">
            <TableCell className="font-medium text-gray-900">GPU</TableCell>
            <TableCell>
              {system.gpu.available && system.gpu.vram_gb !== null
                ? `Detected (${system.gpu.vram_gb.toFixed(1)} GB VRAM)`
                : 'None detected'}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
      <div><Button color="blue" onClick={onNext}>{t('setup.welcome.begin')}</Button></div>
    </>
  )
}

function InstallOllamaStep({ t, busy, ollamaPhase, onInstall, onRetryStart, onNext, log, logEndRef }: {
  t: TranslationFunction
  busy: boolean
  /** Current Ollama readiness phase — drives which UI is shown. */
  ollamaPhase: OllamaPhase
  onInstall: () => Promise<void>
  /** Retry the /start call when the server failed to become ready. */
  onRetryStart: () => Promise<void>
  onNext: () => void
  log: string[]
  logEndRef: RefObject<HTMLDivElement | null>
}) {
  return (
    <>
      <h1 className="text-2xl font-bold">{t('setup.install.title')}</h1>
      <p className="text-gray-600">{t('setup.install.description')}</p>

      {/* Checking / starting — show a spinner while we wait for /start */}
      {(ollamaPhase === 'idle' || ollamaPhase === 'starting') && (
        <div className="flex items-center gap-3 text-gray-500">
          <Spinner size="sm" />
          <span>Checking Ollama status…</span>
        </div>
      )}

      {/* Already running */}
      {ollamaPhase === 'running' && (
        <Alert color="success">✓ {t('setup.install.already_done')}</Alert>
      )}

      {/* Not installed — show install button (disabled while install is streaming) */}
      {ollamaPhase === 'not_installed' && (
        <Button color="blue" disabled={busy} onClick={onInstall}>
          {t('setup.install.button')}
        </Button>
      )}

      {/* Installed but failed to start in time */}
      {ollamaPhase === 'failed' && (
        <>
          <Alert color="failure">Ollama failed to start. Check the log below or retry.</Alert>
          <Button color="blue" disabled={busy} onClick={onRetryStart}>Retry</Button>
        </>
      )}

      <LogBox log={log} logEndRef={logEndRef} />

      <div>
        <Button color="gray" disabled={ollamaPhase !== 'running' || busy} onClick={onNext}>
          {t('setup.install.next')}
        </Button>
      </div>
    </>
  )
}

function ModelsStep({ t, system, selectedModels, setSelectedModels, busy, onPull, onNext, status, log, logEndRef }: { t: TranslationFunction; system: SystemCheck; selectedModels: Set<string>; setSelectedModels: Dispatch<SetStateAction<Set<string>>>; busy: boolean; onPull: () => Promise<void>; onNext: () => void; status: SetupStatus; log: string[]; logEndRef: RefObject<HTMLDivElement | null> }) {
  return (
    <>
      <h1 className="text-2xl font-bold">{t('setup.models.title')}</h1>
      <p className="text-gray-600">{t('setup.models.description')}</p>

      <div className="flex flex-col gap-3">
        {system.viable_models.map((m: ModelInfo) => (
          <label
            key={m.tag}
            className={`flex space-x-3 p-4 border rounded-lg cursor-pointer transition-colors ${
              selectedModels.has(m.tag)
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 bg-white hover:border-gray-400'
            }`}
          >
            <input
              type="checkbox"
              className="mt-1 w-4 h-4 border border-gray-300 rounded bg-gray-50 focus:ring-2 focus:ring-blue-500"
              checked={selectedModels.has(m.tag)}
              onChange={e => {
                const next = new Set(selectedModels)
                if (e.target.checked) next.add(m.tag)
                else next.delete(m.tag)
                setSelectedModels(next)
              }}
            />
            <div>
              <p className="font-medium text-gray-900">{m.tag}</p>
              <p className="text-sm text-gray-500">
                Min {m.min_ram_gb} GB RAM · Max {(m.max_ctx / 1024).toFixed(0)}K context
                {m.audio && ' · Audio'}
                {status.models_pulled.includes(m.tag) && (
                  <span className="ml-2 text-green-600">✓ downloaded</span>
                )}
              </p>
            </div>
          </label>
        ))}
      </div>

      <LogBox log={log} logEndRef={logEndRef} />

      <div className="flex gap-3">
        <Button color="blue" disabled={selectedModels.size === 0 || busy} onClick={onPull}>
          {t('setup.models.pull_button')}
        </Button>
        <Button color="gray" disabled={status.models_pulled.length === 0 || busy} onClick={onNext}>
          {t('setup.models.next')}
        </Button>
      </div>
    </>
  )
}

function ServiceStep({ t, busy, onInstall, log, logEndRef }: { t: TranslationFunction; busy: boolean; onInstall: () => Promise<void>; log: string[]; logEndRef: RefObject<HTMLDivElement | null> }) {
  return (
    <>
      <h1 className="text-2xl font-bold">{t('setup.service.title')}</h1>
      <p className="text-gray-600">{t('setup.service.description')}</p>
      <div>
        <Button color="blue" disabled={busy} onClick={onInstall}>
          {t('setup.service.button')}
        </Button>
      </div>
      <LogBox log={log} logEndRef={logEndRef} />
    </>
  )
}

function AdminStep({ t, adminUser, setAdminUser, adminPass, setAdminPass, busy, onSave, onNext, status }: { t: TranslationFunction; adminUser: string; setAdminUser: Dispatch<SetStateAction<string>>; adminPass: string; setAdminPass: Dispatch<SetStateAction<string>>; busy: boolean; onSave: () => Promise<void>; onNext: () => void; status: SetupStatus }) {
  return (
    <>
      <h1 className="text-2xl font-bold">{t('setup.admin.title')}</h1>
      <p className="text-gray-600">{t('setup.admin.description')}</p>

      <div className="flex flex-col gap-4">
        <div>
          <div className="mb-2"><Label htmlFor="admin-user">{t('setup.admin.username')}</Label></div>
          <TextInput id="admin-user" value={adminUser} onChange={e => setAdminUser(e.target.value)} autoComplete="username" />
        </div>
        <div>
          <div className="mb-2"><Label htmlFor="admin-pass">{t('setup.admin.password')}</Label></div>
          <TextInput id="admin-pass" type="password" value={adminPass} onChange={e => setAdminPass(e.target.value)} autoComplete="new-password" />
        </div>
      </div>

      {status.admin_configured && <Alert color="success">✓ Admin account saved</Alert>}

      <div className="flex gap-3">
        <Button color="blue" disabled={!adminUser || !adminPass || busy} onClick={onSave}>
          {t('setup.admin.button')}
        </Button>
        <Button color="gray" disabled={!status.admin_configured || busy} onClick={onNext}>
          {t('setup.admin.next')}
        </Button>
      </div>
    </>
  )
}


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
  const logEndRef = useRef<HTMLDivElement | null>(null)
  const [ollamaPhase, setOllamaPhase] = useState<OllamaPhase>('idle')
  /** Prevents the auto-start effect from firing more than once per visit to step 2. */
  const ollamaStartAttempted = useRef(false)

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    setupApi.status().then(setStatus)
    systemApi.check().then(setSystem)
  }, [])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [log])

  /** On entering step 2, try to start Ollama once to determine readiness. */
  useEffect(() => {
    if (step !== 2 || ollamaStartAttempted.current) return
    ollamaStartAttempted.current = true
    void handleStartOllama()
    // handleStartOllama only calls stable setters and module-level API wrappers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step])

  /** Append a log line, filtering [DONE] events and formatting errors. */
  function appendLog(line: string) {
    if (line.startsWith('[DONE]')) return
    setLog(prev => [
      ...prev,
      line.startsWith('[ERROR]') ? `ERROR: ${line.replace('[ERROR] ', '')}` : line,
    ])
  }

  /**
   * POST /api/ollama/start and update ollamaPhase based on the result.
   *
   * Called automatically when the user enters step 2, and again after
   * a successful Ollama installation to confirm the service is running.
   */
  async function handleStartOllama() {
    setOllamaPhase('starting')
    const result = await ollamaApi.start()
    if (result.success) {
      setOllamaPhase('running')
      // Refresh status so models_pulled is accurate when step 3 loads.
      setupApi.status().then(setStatus)
    } else if (result.reason === 'not_installed') {
      setOllamaPhase('not_installed')
    } else {
      setOllamaPhase('failed')
    }
  }

  async function handleLanguageSelect(newLocale: string) {
    setLocale(newLocale)
    await setupApi.setLanguage(newLocale)
  }

  async function handleInstallOllama() {
    setBusy(true)
    setLog([])
    const res = await ollamaApi.install()
    // Intercept [DONE] to know whether the install succeeded, while still
    // passing all other lines through appendLog for display.
    let installSucceeded = false
    await new Promise<void>(resolve =>
      streamLines(res, line => {
        if (line.startsWith('[DONE]')) { installSucceeded = true; return }
        appendLog(line)
      }, resolve)
    )
    // Confirm the service is up — this also flips ollamaPhase to 'running'
    // if successful, which unlocks the Next button.
    if (installSucceeded) await handleStartOllama()
    setBusy(false)
    setupApi.status().then(setStatus)
  }

  async function handlePullModels() {
    if (selectedModels.size === 0) return
    setBusy(true)
    setLog([])
    for (const tag of selectedModels) {
      appendLog(`--- Downloading ${tag} ---`)
      const res = await ollamaApi.pull(tag)
      await new Promise<void>(resolve => streamLines(res, appendLog, resolve))
    }
    setBusy(false)
    setupApi.status().then(setStatus)
  }

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

  async function handleSaveAdmin() {
    if (!adminUser || !adminPass) return
    setBusy(true)
    await setupApi.saveAdminCredentials(adminUser, adminPass)
    setBusy(false)
    setupApi.status().then(setStatus)
  }

  if (!ready || !status || !system) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="xl" />
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
    <div className="min-h-screen bg-gray-50">
      {/* Breadcrumb stepper */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <ol className="flex items-center w-full p-3 space-x-2 text-sm font-medium text-center text-gray-500 bg-white sm:space-x-4 overflow-x-auto">
          {steps.map((label, i) => (
            <li key={i} className={`flex items-center whitespace-nowrap ${i === step ? 'text-blue-600' : i < step ? 'text-green-600' : 'text-gray-500'}`}>
              <span className={`flex items-center justify-center w-5 h-5 me-2 text-xs border rounded-full shrink-0 ${
                i < step ? 'border-green-600' : i === step ? 'border-blue-600' : 'border-gray-500'
              }`}>
                {i < step ? '✓' : i + 1}
              </span>
              <span className="hidden sm:inline">{label}</span>
              {i < steps.length - 1 && (
                <svg className="w-4 h-4 ms-2 text-gray-400 shrink-0" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="m7 16 4-4-4-4m6 8 4-4-4-4"/>
                </svg>
              )}
            </li>
          ))}
        </ol>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-10 flex flex-col gap-6">

        {step === 0 && (
          <LanguageStep t={t} locale={locale} onChangeLocale={handleLanguageSelect} onNext={() => setStep(1)} />
        )}

        {step === 1 && (
          <WelcomeStep t={t} system={system!} onNext={() => setStep(2)} />
        )}

        {step === 2 && (
          <InstallOllamaStep
            t={t}
            busy={busy}
            ollamaPhase={ollamaPhase}
            onInstall={handleInstallOllama}
            onRetryStart={handleStartOllama}
            onNext={() => setStep(3)}
            log={log}
            logEndRef={logEndRef}
          />
        )}

        {step === 3 && (
          <ModelsStep
            t={t}
            system={system!}
            selectedModels={selectedModels}
            setSelectedModels={setSelectedModels}
            busy={busy}
            onPull={handlePullModels}
            onNext={() => setStep(4)}
            status={status!}
            log={log}
            logEndRef={logEndRef}
          />
        )}

        {step === 4 && (
          <AdminStep
            t={t}
            adminUser={adminUser}
            setAdminUser={setAdminUser}
            adminPass={adminPass}
            setAdminPass={setAdminPass}
            busy={busy}
            onSave={handleSaveAdmin}
            onNext={() => setStep(5)}
            status={status!}
          />
        )}

        {step === 5 && (
          <ServiceStep t={t} busy={busy} onInstall={handleInstallService} log={log} logEndRef={logEndRef} />
        )}

      </div>
    </div>
  )
}
