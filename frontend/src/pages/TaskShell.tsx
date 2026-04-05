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
import GemIcon from '../components/GemIcon'
import { useTranslation } from '../i18n'

export default function TaskShell() {
  const [gems, setGems] = useState<UserTask[]>([])
  const [loading, setLoading] = useState(true)
  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)
  const navigate = useNavigate()

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    gemsApi.list().then(list => { setGems(list); setLoading(false) })
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
