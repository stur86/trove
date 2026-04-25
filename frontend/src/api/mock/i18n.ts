/**
 * Mock implementation of i18nApi.
 * Returns the full set of supported locales with a short delay.
 */
export const i18nApi = {
  listLocales: async (): Promise<Record<string, string>> => {
    await new Promise(r => setTimeout(r, 50))
    return {
      en: 'English',
      it: 'Italiano',
      de: 'Deutsch',
      es: 'Español',
      fr: 'Français',
      pt: 'Português',
      zh: '中文',
    }
  },
}
