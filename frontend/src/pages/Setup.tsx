import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type OllamaStatus, ollamaApi, streamLines } from '../api/ollama'
import { type SystemCheck, systemApi } from '../api/system'
import { configApi } from '../api/config'
import { useTranslation } from '../i18n'

/** The setup flow progresses through these phases in order. */
type Phase = 'checking' | 'ready' | 'installing' | 'pulling' | 'building' | 'done'

/**
 * Setup page — shown on first run and whenever Ollama needs configuration.
 *
 * Flow:
 * 1. On mount: fetch system info and Ollama status in parallel
 * 2. If already fully set up: redirect to /admin immediately
 * 3. Otherwise: show system check table and "Install Ollama" button
 * 4. On button click: run install → pull → build in sequence, streaming output
 * 5. On completion: redirect to /admin
 */
export default function Setup() {
  const navigate = useNavigate()
  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)
  const [status, setStatus] = useState<OllamaStatus | null>(null)
  const [system, setSystem] = useState<SystemCheck | null>(null)
  const [phase, setPhase] = useState<Phase>('checking')
  const [log, setLog] = useState<string[]>([])
  // Auto-scroll the log to the bottom as new lines arrive
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Fetch locale preference, system info, and Ollama status in parallel
    configApi.get().then(c => setLocale(c.locale))
    Promise.all([ollamaApi.status(), systemApi.check()]).then(([s, sys]) => {
      setStatus(s)
      setSystem(sys)
      if (s.installed && s.running && s.model_built) {
        // Already set up — skip straight to admin
        navigate('/admin')
      } else {
        setPhase('ready')
      }
    })
  }, [])

  useEffect(() => {
    // Scroll log to bottom whenever a new line arrives
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [log])

  /** Append a line to the log, colouring errors red via a prefix. */
  function appendLog(line: string) {
    if (line.startsWith('[DONE]')) return // suppress sentinel
    const formatted = line.startsWith('[ERROR]')
      ? `ERROR: ${line.replace('[ERROR] ', '')}`
      : line
    setLog(prev => [...prev, formatted])
  }

  /** Run the full install → pull → build sequence. */
  async function runSetup() {
    setLog([])

    if (!status?.installed) {
      setPhase('installing')
      const res = await ollamaApi.install()
      await new Promise<void>(resolve => streamLines(res, appendLog, resolve))
    }

    setPhase('pulling')
    const pullRes = await ollamaApi.pull()
    await new Promise<void>(resolve => streamLines(pullRes, appendLog, resolve))

    setPhase('building')
    const buildRes = await ollamaApi.build()
    await new Promise<void>(resolve => streamLines(buildRes, appendLog, resolve))

    setPhase('done')
    setTimeout(() => navigate('/admin'), 1500)
  }

  /** Human-readable label for the button based on current phase. */
  const buttonLabel =
    phase === 'ready' ? t('setup.install_button') :
    phase === 'installing' ? t('setup.installing') :
    phase === 'pulling' ? t('setup.pulling') :
    phase === 'building' ? 'Building model...' :
    'Done'

  if (phase === 'checking') {
    return <div style={{ padding: '2rem' }}>{t('setup.system_check')}</div>
  }

  return (
    <div style={{ padding: '2rem', maxWidth: '640px', margin: '0 auto' }}>
      <h1>{t('setup.title')}</h1>

      {/* System hardware summary table */}
      {system && (
        <table style={{ marginBottom: '1.5rem', borderCollapse: 'collapse', width: '100%' }}>
          <tbody>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.ram')}</td>
              <td>{system.ram_gb} GB</td>
            </tr>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.disk')}</td>
              <td>{system.disk_free_gb} GB free</td>
            </tr>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.gpu')}</td>
              <td>{system.gpu.available ? `${system.gpu.vram_gb} GB VRAM` : 'None'}</td>
            </tr>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.ollama_status')}</td>
              <td>
                {status?.installed
                  ? (status.running ? t('setup.running') : t('setup.not_running'))
                  : t('setup.not_installed')}
              </td>
            </tr>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.model_built')}</td>
              <td>{status?.model_built ? '✓' : '✗'}</td>
            </tr>
          </tbody>
        </table>
      )}

      {phase === 'done' ? (
        <p>Setup complete. Redirecting to admin...</p>
      ) : (
        <button
          onClick={runSetup}
          disabled={phase !== 'ready'}
          style={{ padding: '0.75rem 2rem', fontSize: '1.1rem', cursor: phase === 'ready' ? 'pointer' : 'default' }}
        >
          {buttonLabel}
        </button>
      )}

      {/* Live log output from install/pull/build */}
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
