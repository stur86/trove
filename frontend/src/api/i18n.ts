/**
 * Typed API wrapper for the Trove i18n domain.
 *
 * Exposes the locales listing endpoint, which returns a mapping of
 * BCP-47 codes to display names (e.g. { "en": "English", "it": "Italiano" }).
 */

import { get } from './client'
import { i18nApi as _mockI18nApi } from './mock/i18n'

const _realI18nApi = {
  /** Fetch the map of available locale codes to their display names. */
  listLocales: () => get<Record<string, string>>('/i18n/locales'),
}

/** API wrapper for the i18n domain. Switches to mock when VITE_MOCK_API=1. */
export const i18nApi = import.meta.env.VITE_MOCK_API ? _mockI18nApi : _realI18nApi
