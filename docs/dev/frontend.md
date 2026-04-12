# Frontend reference

The frontend is a React SPA in `frontend/src/`, built with Vite and Bun.

## Structure

```
frontend/src/
├── App.tsx              # React Router root — decides setup vs app mode
├── main.tsx             # Vite entry point
│
├── pages/
│   ├── SetupWizard.tsx  # Six-step setup wizard (setup mode)
│   ├── ManageDashboard.tsx  # Post-setup management (setup mode)
│   ├── GemRunner.tsx    # Run a gem (app mode, user-facing)
│   ├── AdminPanel.tsx   # Tabbed admin interface (app mode, localhost only)
│   ├── GemForm.tsx      # Create / edit a gem (app mode, admin)
│   └── DocumentsPanel.tsx  # Document library panel (app mode, admin)
│
├── components/
│   ├── AdminLogin.tsx   # Reusable login card
│   ├── GemIcon.tsx      # Coloured SVG gem icon
│   └── InfoButton.tsx   # Popover help tooltip
│
├── api/
│   ├── client.ts        # Base fetch wrapper, basicAuth helper
│   ├── config.ts        # GET + PUT /api/config
│   ├── app.ts           # Admin endpoints (/api/app/admin/*)
│   ├── ollama.ts        # Ollama endpoints + streamLines()
│   ├── setup.ts         # Setup wizard endpoints
│   ├── system.ts        # System check
│   ├── tasks.ts         # Gem CRUD + run
│   ├── documents.ts     # Document library
│   └── mock/            # Mock implementations (VITE_MOCK_API=1)
│
└── i18n/
    └── index.ts         # useLocale(), useTranslation() hooks
```

## Routing

`App.tsx` fetches `GET /api/mode` on mount and renders either the setup flow or the app flow. There is no static routing split — mode is determined at runtime.

## API clients

Each `api/*.ts` module exports a typed object (e.g. `configApi`, `appApi`). When `VITE_MOCK_API=1`, the real object is swapped for a mock that returns hardcoded data after a small simulated delay. This lets you develop the UI without a running backend:

```bash
task dev-mock
```

All API functions return typed promises. SSE-streaming endpoints return a raw `Promise<Response>` and are consumed via `streamLines()`:

```typescript
const res = await ollamaApi.install()
await streamLines(
  res,
  line => console.log(line),   // called for each SSE data line
  () => console.log('done'),   // called when [DONE] arrives
)
```

## i18n

```typescript
const { t } = useTranslation(useLocale())
return <button>{t('setup.install.button')}</button>
```

`useLocale()` fetches the active locale from `/api/config` and caches it. `useTranslation(locale)` fetches the locale file from `/api/i18n/{locale}` (or `/locales/{locale}.json` in mock mode) and returns a `t(key, fallback?)` lookup function.

Locale files live in `frontend/public/locales/` (for mock mode) and `backend/i18n/locales/` (for production).

## Styling

Use [Flowbite React](https://flowbite-react.com/) components for all layout, forms, and UI elements. Custom Tailwind classes are acceptable only where Flowbite has no equivalent. The only truly custom visual element is `GemIcon.tsx`.

## Adding a new page

1. Create `pages/MyPage.tsx` with a default export.
2. Add a route in `App.tsx`.
3. Add the corresponding API client calls in `api/`.
4. Add a mock in `api/mock/` if the page should work with `VITE_MOCK_API=1`.
