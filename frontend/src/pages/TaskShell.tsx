/**
 * TaskShell — user-facing landing page in app mode.
 *
 * Displays all gems as a card grid. Clicking a card navigates to the
 * GemRunner page for that gem.
 */
import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Card, Spinner } from 'flowbite-react'
import { gemsApi, type UserTask } from '../api/tasks'
import { configApi } from '../api/config'
import { appApi } from '../api/app'
import GemIcon from '../components/GemIcon'
import { useTranslation } from '../i18n'

export default function TaskShell() {
  const [gems, setGems] = useState<UserTask[]>([])
  const [loading, setLoading] = useState(true)
  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)
  const navigate = useNavigate()
  const [networkUrl, setNetworkUrl] = useState<string | null>(null)
  const [urlCopied, setUrlCopied] = useState(false)

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    gemsApi.list()
      .then(list => { setGems(list); setLoading(false) })
      .catch(() => setLoading(false))
    appApi.networkUrl().then(r => setNetworkUrl(r.url))
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Trove</h1>
          <Link to="/admin">
            <span className="text-sm text-gray-500 hover:text-gray-700 cursor-pointer">
              {t('admin.login.title', 'Admin')}
            </span>
          </Link>
        </div>

        {networkUrl && (
          <div className="flex items-center gap-2 mb-6 p-3 bg-white border border-gray-200 rounded-lg">
            <span className="text-xs text-gray-500 shrink-0">{t('app.share_url')}</span>
            <code className="flex-1 text-sm font-mono text-gray-700 truncate">{networkUrl}</code>
            <button
              className="text-xs text-blue-600 hover:text-blue-800 shrink-0"
              onClick={() => {
                navigator.clipboard.writeText(networkUrl)
                setUrlCopied(true)
                setTimeout(() => setUrlCopied(false), 2000)
              }}
            >
              {urlCopied ? t('manage.access.copied') : t('manage.access.copy')}
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <Spinner size="lg" />
          </div>
        ) : gems.length === 0 ? (
          <p className="text-center text-gray-400 py-20">
            {t('app.tasks.placeholder', 'No gems yet. Ask an admin to create some.')}
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {gems.map(gem => (
              <Card
                key={gem.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => navigate(`/gems/${gem.id}`)}
              >
                <div className="flex flex-col gap-3">
                  <GemIcon hue={gem.hue} size={40} />
                  <div>
                    <h2 className="text-base font-semibold text-gray-900">{gem.name}</h2>
                    {gem.description && (
                      <p className="text-sm text-gray-500 mt-1 leading-snug">{gem.description}</p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
