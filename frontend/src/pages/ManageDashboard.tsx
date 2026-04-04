/**
 * ManageDashboard — shown after setup completes and on return visits to setup mode.
 *
 * Displays:
 * - Optional success banner (when arriving from SetupWizard via /manage state)
 * - Status cards: service, Ollama version, models count
 * - Prominent LAN URL box with copy button
 * - Management action buttons: restart, update Ollama, pull model, uninstall
 */

import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
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
  const [log, setLog] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [activeAction, setActiveAction] = useState<string | null>(null)

  useEffect(() => {
    // Load locale from config, then fetch status and LAN URL in parallel
    configApi.get().then(c => setLocale(c.locale))
    setupApi.status().then(setStatus)
    setupApi.lanUrl().then(setLanUrl)
    setupApi.ollamaVersion().then(v => setOllamaVersion(v.version))
  }, [])

  /**
   * Append a single SSE log line to the visible log, stripping protocol tokens.
   * Lines starting with [DONE] are silently dropped.
   */
  function appendLog(line: string) {
    if (line.startsWith('[DONE]')) return
    setLog(prev => [
      ...prev,
      line.startsWith('[ERROR]') ? `ERROR: ${line.replace('[ERROR] ', '')}` : line,
    ])
  }

  /**
   * Run a management action that streams SSE output.
   * Locks the UI while in progress and refreshes status on completion.
   *
   * @param label  - Identifier used to highlight the active button
   * @param action - Async function that kicks off the SSE request
   */
  async function runAction(label: string, action: () => Promise<Response>) {
    setBusy(true)
    setActiveAction(label)
    setLog([])
    const res = await action()
    await streamLines(res, appendLog, () => {
      setBusy(false)
      setActiveAction(null)
      // Refresh status after action completes so cards reflect new state
      setupApi.status().then(setStatus)
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
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-2xl mx-auto px-6 py-10 space-y-6">

        {/* Success banner — only shown right after setup completes */}
        {justInstalled && (
          <div className="p-4 rounded-lg bg-green-900 border border-green-700 text-green-300">
            ✓ {t('manage.setup_complete')}
          </div>
        )}

        <h1 className="text-2xl font-bold">{t('manage.title')}</h1>

        {/* Status cards: service health, Ollama version, pulled models count */}
        {status && (
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase mb-1">{t('manage.service_label')}</p>
              <div className="flex items-center gap-2">
                {/* Coloured dot indicates running vs stopped */}
                <span className={`w-2 h-2 rounded-full ${status.service_installed ? 'bg-green-400' : 'bg-red-400'}`} />
                <span className="font-medium text-sm">
                  {status.service_installed ? t('manage.service_running') : t('manage.service_stopped')}
                </span>
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase mb-1">{t('manage.ollama_label')}</p>
              <p className="font-medium text-sm">{ollamaVersion || '—'}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase mb-1">{t('manage.models_label')}</p>
              <p className="font-medium text-sm">
                {t('manage.models_count').replace('{count}', String(status.models_pulled.length))}
              </p>
            </div>
          </div>
        )}

        {/* LAN URL — prominent access instructions for non-technical users */}
        {lanUrl && (
          <div className="bg-gray-800 rounded-lg p-5 border border-blue-600">
            <h2 className="font-semibold mb-1">{t('manage.access.title')}</h2>
            <p className="text-sm text-gray-400 mb-3">{t('manage.access.description')}</p>
            <div className="flex gap-3 items-center">
              <code className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-2 text-base font-mono">
                {lanUrl.url}
              </code>
              <button
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium whitespace-nowrap"
                onClick={copyUrl}
              >
                {copied ? t('manage.access.copied') : t('manage.access.copy')}
              </button>
            </div>
          </div>
        )}

        {/* Management actions — restart, update, pull model, uninstall */}
        <div>
          <p className="text-xs text-gray-400 uppercase mb-3">Management</p>
          <div className="flex gap-3 flex-wrap">
            <button
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm disabled:opacity-50"
              disabled={busy}
              onClick={() => runAction('restart', setupApi.restart)}
            >
              {activeAction === 'restart' ? '...' : t('manage.restart')}
            </button>
            <button
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm disabled:opacity-50"
              disabled={busy}
              onClick={() => runAction('update', () => ollamaApi.install())}
            >
              {activeAction === 'update' ? '...' : t('manage.update_ollama')}
            </button>
            <button
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm disabled:opacity-50"
              disabled={busy}
              onClick={() => {
                // Use a browser prompt to ask for the model tag — avoids a full modal UI
                const tag = prompt('Model tag to download (e.g. gemma4:26b):')
                if (tag) runAction('pull', () => ollamaApi.pull(tag))
              }}
            >
              {activeAction === 'pull' ? '...' : t('manage.pull_model')}
            </button>
            {/* Destructive uninstall action — styled red with a confirmation guard */}
            <button
              className="px-4 py-2 bg-red-900 hover:bg-red-800 border border-red-700 text-red-300 rounded-lg text-sm disabled:opacity-50"
              disabled={busy}
              onClick={() => {
                if (confirm('Are you sure you want to uninstall Trove?')) {
                  runAction('uninstall', setupApi.uninstall)
                }
              }}
            >
              {activeAction === 'uninstall' ? '...' : t('manage.uninstall')}
            </button>
          </div>
        </div>

        {/* SSE log — appears only while an action is streaming output */}
        {log.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-48 overflow-y-auto">
            {log.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        )}

      </div>
    </div>
  )
}
