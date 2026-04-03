/**
 * i18n hook and locale fetching utilities for Trove.
 *
 * Locale files are flat JSON maps of translation keys to localised strings,
 * served by the backend at /api/i18n/{locale}. The backend handles fallback
 * to English automatically, so clients just request their preferred locale.
 *
 * An in-memory cache prevents redundant network requests within a session.
 */

import { useEffect, useState } from 'react'
import { get } from '../api/client'

/** Flat map of translation keys to localised strings. */
type Strings = Record<string, string>

/** In-memory cache so locale files are only fetched once per session. */
const cache: Record<string, Strings> = {}

/**
 * Fetch a locale file by BCP-47 code and cache it.
 * Falls back to 'en' automatically (handled by the backend).
 */
async function fetchLocale(locale: string): Promise<Strings> {
  if (cache[locale]) return cache[locale]
  const strings = await get<Strings>(`/i18n/${locale}`)
  cache[locale] = strings
  return strings
}

/**
 * React hook for UI string translation.
 *
 * Fetches the locale file on mount and whenever locale changes.
 * Returns a `t(key)` function that looks up a translation key,
 * falling back to the key itself if not yet loaded or missing.
 *
 * @param locale - BCP-47 locale code, e.g. 'en'. Defaults to 'en'.
 *
 * @example
 * const { t } = useTranslation('en')
 * return <button>{t('setup.install_button')}</button>
 */
export function useTranslation(locale: string = 'en') {
  const [strings, setStrings] = useState<Strings>(cache[locale] ?? {})

  useEffect(() => {
    fetchLocale(locale).then(setStrings)
  }, [locale])

  /**
   * Look up a translation key.
   * Returns the translated string, or fallback, or the key itself.
   */
  function t(key: string, fallback?: string): string {
    return strings[key] ?? fallback ?? key
  }

  return {
    t,
    /** True once the locale file has loaded — use to defer rendering if needed. */
    ready: Object.keys(strings).length > 0,
  }
}
