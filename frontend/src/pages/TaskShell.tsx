import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { configApi } from '../api/config'
import { useTranslation } from '../i18n'

/**
 * TaskShell — user-facing landing page in app mode.
 *
 * Regular users land here without any login. The task runner UI
 * will be built here in a future sprint. For now shows a placeholder
 * with a link to the admin panel.
 */
export default function TaskShell() {
  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
  }, [])

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center gap-6">
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-bold">Trove</h1>
        <p className="text-gray-400">{t('app.tasks.placeholder')}</p>
      </div>
      <Link
        to="/admin"
        className="text-sm text-gray-500 hover:text-gray-300 underline"
      >
        Admin
      </Link>
    </div>
  )
}
