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
  // In mock dev mode, locale files are served directly by the Vite dev server
  // at /locales/{locale}.json (via the serve-locales plugin in vite.config.ts).
  // In real mode, the FastAPI i18n endpoint handles fallback to English.
  const url = import.meta.env.VITE_MOCK_API
    ? `/locales/${locale}.json`
    : `/api/i18n/${locale}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to load locale ${locale}: ${res.status}`)
  const strings: Strings = await res.json()
  cache[locale] = strings
  return strings
}

export type TranslationFunction = (key: string, fallback?: string) => string;
type UseTranslationResult = {
  t: TranslationFunction;
  ready: boolean;
};

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
/**
 * Fetch and cache the active locale code from the server config.
 * Returns 'en' immediately while the request is in flight.
 * Subsequent calls within the same session resolve from the cache.
 */
let _localeCache: string | null = null
let _localeFetch: Promise<string> | null = null

export function useLocale(): string {
  const [locale, setLocale] = useState<string>(_localeCache ?? 'en')
  useEffect(() => {
    if (_localeCache) { setLocale(_localeCache); return }
    if (!_localeFetch) {
      _localeFetch = fetch('/api/config')
        .then(r => r.json())
        .then((cfg: { locale?: string }) => {
          _localeCache = cfg.locale ?? 'en'
          return _localeCache
        })
        .catch(() => { _localeCache = 'en'; return 'en' })
    }
    _localeFetch.then(setLocale)
  }, [])
  return locale
}

export function useTranslation(locale: string = 'en'): UseTranslationResult {
  const [strings, setStrings] = useState<Strings>(cache[locale] ?? {})


  useEffect(() => {
    fetchLocale(locale).then((newStrings: Strings) => {
      setStrings(newStrings)
      cache[locale] = newStrings
    })
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
