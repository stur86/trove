import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type OllamaStatus, ollamaApi, streamLines } from '../api/ollama'
import { type SystemCheck, systemApi } from '../api/system'
import { configApi } from '../api/config'
import { useTranslation } from '../i18n'

/**
 * Setup page — three-step ladder that blocks progression until each step succeeds.
 *
 * Steps:
 *   1. Install Ollama binary
 *   2. Start the Ollama service
 *   3. Pull the configured base model
 *
 * Each step has its own button. A step's button is only enabled when all
 * previous steps are done and the step itself hasn't completed yet. If a step
 * fails, it stays active for retry — no forward progression.
 *
 * Once all three are done, the user can continue to the Admin page.
 * Building trove_model is NOT done here — it depends on the admin's
 * model/context-window choices and is triggered from Admin on save.
 */
export default function Setup() {
  const navigate = useNavigate()
  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)
  const [status, setStatus] = useState<OllamaStatus | null>(null)
  const [system, setSystem] = useState<SystemCheck | null>(null)
  const [loading, setLoading] = useState(true)
  /** Which step is currently executing, or null if idle. */
  const [activeStep, setActiveStep] = useState<'install' | 'start' | 'pull' | null>(null)
  const [log, setLog] = useState<string[]>([])
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    Promise.all([ollamaApi.status(), systemApi.check()]).then(([s, sys]) => {
      setStatus(s)
      setSystem(sys)
      setLoading(false)
      if (s.installed && s.running && s.model_pulled) {
        navigate('/admin')
      }
    })
  }, [navigate])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [log])

  /** Append a line to the log, suppressing [DONE] sentinels and colouring errors. */
  function appendLog(line: string) {
    if (line.startsWith('[DONE]')) return
    const formatted = line.startsWith('[ERROR]')
      ? `ERROR: ${line.replace('[ERROR] ', '')}`
      : line
    setLog(prev => [...prev, formatted])
  }

  /** Stream an SSE response into the log. Returns true if no [ERROR] was emitted. */
  async function runStream(res: Response): Promise<boolean> {
    let failed = false
    await new Promise<void>(resolve =>
      streamLines(res, line => {
        if (line.startsWith('[ERROR]')) failed = true
        appendLog(line)
      }, resolve),
    )
    return !failed
  }

  /** Re-fetch authoritative status from the backend. */
  async function refreshStatus(): Promise<OllamaStatus> {
    const s = await ollamaApi.status()
    setStatus(s)
    return s
  }

  /** Run a setup step: stream output, refresh status, auto-navigate if all done. */
  async function runStep(
    step: 'install' | 'start' | 'pull',
    apiCall: () => Promise<Response>,
  ) {
    setActiveStep(step)
    setLog([])
    await runStream(await apiCall())
    const s = await refreshStatus()
    setActiveStep(null)
    if (s.installed && s.running && s.model_pulled) {
      navigate('/admin')
    }
  }

  if (loading) {
    return <div style={{ padding: '2rem' }}>{t('setup.system_check')}</div>
  }

  return (
    <div style={{ padding: '2rem', maxWidth: '640px', margin: '0 auto' }}>
      <h1>{t('setup.title')}</h1>

      {/* Compact system summary */}
      {system && (
        <p style={{ color: '#888', marginBottom: '1.5rem' }}>
          {system.ram_gb} GB RAM &middot; {system.disk_free_gb} GB free disk
          {system.gpu.available ? ` \u00b7 ${system.gpu.vram_gb} GB VRAM` : ' \u00b7 No GPU'}
        </p>
      )}

      {/* Step ladder */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <SetupStep
          number={1}
          label={t('setup.step_install')}
          done={!!status?.installed}
          active={activeStep === 'install'}
          enabled={activeStep === null && !status?.installed}
          onAction={() => runStep('install', ollamaApi.install)}
        />
        <SetupStep
          number={2}
          label={t('setup.step_start')}
          done={!!status?.running}
          active={activeStep === 'start'}
          enabled={activeStep === null && !!status?.installed && !status?.running}
          onAction={() => runStep('start', ollamaApi.start)}
        />
        <SetupStep
          number={3}
          label={t('setup.step_pull')}
          done={!!status?.model_pulled}
          active={activeStep === 'pull'}
          enabled={activeStep === null && !!status?.installed && !!status?.running && !status?.model_pulled}
          onAction={() => runStep('pull', ollamaApi.pull)}
        />
      </div>

      {/* Live log output from the active step */}
      {log.length > 0 && (
        <pre style={{
          marginTop: '1rem',
          background: '#111',
          color: '#cfc',
          padding: '1rem',
          borderRadius: '4px',
          maxHeight: '300px',
          overflowY: 'auto',
          fontSize: '0.8rem',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
        }}>
          {log.map((line, i) => (
            <span
              key={i}
              style={line.startsWith('ERROR:') ? { color: '#f88' } : undefined}
            >
              {line}{'\n'}
            </span>
          ))}
          <div ref={logEndRef} />
        </pre>
      )}
    </div>
  )
}

/**
 * A single row in the setup ladder.
 *
 * Shows a numbered circle (or checkmark when done), a label, and an action
 * button that is only clickable when enabled.
 */
function SetupStep({ number, label, done, active, enabled, onAction }: {
  number: number
  label: string
  done: boolean
  active: boolean
  enabled: boolean
  onAction: () => void
}) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.6rem 0.75rem',
      border: '1px solid #333',
      borderRadius: '6px',
      opacity: !done && !active && !enabled ? 0.5 : 1,
    }}>
      <span style={{
        width: '1.75rem',
        height: '1.75rem',
        borderRadius: '50%',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: done ? '#2a5' : '#333',
        color: done ? '#fff' : '#aaa',
        fontWeight: 'bold',
        fontSize: '0.85rem',
        flexShrink: 0,
      }}>
        {done ? '\u2713' : number}
      </span>
      <span style={{ flex: 1 }}>{label}</span>
      {!done && (
        <button
          onClick={onAction}
          disabled={!enabled}
          style={{
            padding: '0.35rem 1rem',
            fontSize: '0.85rem',
            cursor: enabled ? 'pointer' : 'default',
          }}
        >
          {active ? 'Running\u2026' : 'Run'}
        </button>
      )}
    </div>
  )
}
