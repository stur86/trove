/**
 * ManageDashboard — shown after setup completes and on return visits to setup mode.
 *
 * Displays:
 * - Optional success banner (when arriving from SetupWizard)
 * - Status cards: Ollama version, models count
 * - Prominent LAN URL box with copy button
 * - Live log viewer (last 1000 lines, auto-refreshed every 5 s)
 */

import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Alert, Button, Card } from 'flowbite-react'
import { configApi } from '../api/config'
import { ollamaApi, streamLines } from '../api/ollama'
import { setupApi, type LanUrl, type SetupStatus } from '../api/setup'
import { useTranslation } from '../i18n'

export default function ManageDashboard() {
  const location = useLocation()
  const justInstalled = (location.state as { justInstalled?: boolean } | null)?.justInstalled ?? false

  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)
  const [status, setStatus] = useState<SetupStatus | null>(null)
  const [lanUrl, setLanUrl] = useState<LanUrl | null>(null)
  const [ollamaVersion, setOllamaVersion] = useState<string>('')
  const [copied, setCopied] = useState(false)
  const [logLines, setLogLines] = useState<string[]>([])
  const [actionLog, setActionLog] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const logEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    setupApi.status().then(setStatus)
    setupApi.lanUrl().then(setLanUrl)
    setupApi.ollamaVersion().then(v => setOllamaVersion(v.version))
  }, [])

  // Fetch server logs immediately, then every 5 seconds.
  useEffect(() => {
    function fetchLogs() {
      setupApi.logs().then(r => setLogLines(r.lines))
    }
    fetchLogs()
    const id = setInterval(fetchLogs, 5000)
    return () => clearInterval(id)
  }, [])

  // Auto-scroll log box when new lines arrive.
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logLines])

  /** Append a line to the action log strip at the bottom of the page. */
  function appendActionLog(line: string) {
    if (line.startsWith('[DONE]')) return
    setActionLog(prev => [
      ...prev,
      line.startsWith('[ERROR]') ? `ERROR: ${line.replace('[ERROR] ', '')}` : line,
    ])
  }

  /** Run a management action (update Ollama, pull model) that streams SSE output. */
  async function runAction(action: () => Promise<Response>) {
    setBusy(true)
    setActionLog([])
    const res = await action()
    await streamLines(res, appendActionLog, () => {
      setBusy(false)
      setupApi.status().then(setStatus)
      setupApi.ollamaVersion().then(v => setOllamaVersion(v.version))
    })
  }

  /** Copy the LAN URL to the clipboard and briefly show a confirmation label. */
  function copyUrl() {
    if (!lanUrl) return
    navigator.clipboard.writeText(lanUrl.url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto flex flex-col gap-6">

        {justInstalled && (
          <Alert color="success">✓ {t('manage.setup_complete')}</Alert>
        )}

        <h1 className="text-2xl font-bold">{t('manage.title')}</h1>

        {/* Status cards */}
        {status && (
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <p className="text-xs text-gray-500 uppercase mb-1">{t('manage.service_label')}</p>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${status.service_installed ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="font-medium text-sm">
                  {status.service_installed ? t('manage.service_running') : t('manage.service_stopped')}
                </span>
              </div>
            </Card>
            <Card>
              <p className="text-xs text-gray-500 uppercase mb-1">{t('manage.ollama_label')}</p>
              <p className="font-medium text-sm">{ollamaVersion || '—'}</p>
            </Card>
            <Card>
              <p className="text-xs text-gray-500 uppercase mb-1">{t('manage.models_label')}</p>
              <p className="font-medium text-sm">
                {t('manage.models_count').replace('{count}', String(status.models_pulled.length))}
              </p>
            </Card>
          </div>
        )}

        {/* LAN URL */}
        {lanUrl && (
          <Card>
            <h2 className="font-semibold mb-1">{t('manage.access.title')}</h2>
            <p className="text-sm text-gray-500 mb-3">{t('manage.access.description')}</p>
            <div className="flex gap-3 items-center">
              <code className="flex-1 bg-gray-100 border border-gray-200 rounded-lg px-4 py-2 text-base font-mono">
                {lanUrl.url}
              </code>
              <Button size="sm" onClick={copyUrl}>
                {copied ? t('manage.access.copied') : t('manage.access.copy')}
              </Button>
            </div>
          </Card>
        )}

        {/* Management actions */}
        <div>
          <p className="text-xs text-gray-500 uppercase mb-3">{t('manage.actions')}</p>
          <div className="flex gap-3 flex-wrap">
            <Button color="gray" disabled={busy} onClick={() => runAction(() => setupApi.restart())}>
              {t('manage.restart')}
            </Button>
            <Button color="gray" disabled={busy} onClick={() => runAction(() => ollamaApi.install())}>
              {t('manage.update_ollama')}
            </Button>
            <Button color="gray" disabled={busy} onClick={() => {
              const tag = prompt('Model tag to download (e.g. gemma4:26b):')
              if (tag) runAction(() => ollamaApi.pull(tag))
            }}>
              {t('manage.pull_model')}
            </Button>
            <Button color="failure" disabled={busy} onClick={() => {
              if (confirm('Are you sure you want to uninstall Trove?')) {
                runAction(() => setupApi.uninstall())
              }
            }}>
              {t('manage.uninstall')}
            </Button>
          </div>
        </div>

        {/* Action SSE output */}
        {actionLog.length > 0 && (
          <pre className="bg-gray-900 text-gray-300 rounded-lg p-4 text-xs font-mono max-h-40 overflow-y-auto whitespace-pre-wrap">
            {actionLog.join('\n')}
          </pre>
        )}

        {/* Server log viewer */}
        <div>
          <p className="text-xs text-gray-500 uppercase mb-2">{t('manage.logs')}</p>
          <pre className="bg-gray-900 text-gray-300 rounded-lg p-4 text-xs font-mono h-80 overflow-y-auto whitespace-pre-wrap">
            {logLines.length > 0 ? logLines.join('\n') : '(no log entries yet)'}
            <div ref={logEndRef} />
          </pre>
        </div>

      </div>
    </div>
  )
}
