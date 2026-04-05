# Gems Design

**Date:** 2026-04-05

## Overview

"Gems" are the user-facing name for Tasks. This spec covers the full Gems feature: model changes, backend CRUD + run APIs, a reusable Pydantic AI runner, and the React frontend (gem grid, runner, admin management).

---

## Model Changes

### Task (base — stripped down)

`Task` becomes a pure prompt definition with no identity or display fields:

```python
class Task(BaseModel, frozen=True):
    template: str
    args: tuple[TaskArg, ...] = ()
    has_image: bool = False
    has_audio: bool = False
    output_mode: OutputMode = OutputMode.TEXT
```

Internal tasks (document summariser, schema suggester) are plain `Task` instances — no id, name, or hue needed.

### GemHue

16 preconfigured hues, named after Tailwind colour palette entries:

```python
class GemHue(str, Enum):
    RED = "red"; ORANGE = "orange"; AMBER = "amber"; YELLOW = "yellow"
    LIME = "lime"; GREEN = "green"; EMERALD = "emerald"; TEAL = "teal"
    CYAN = "cyan"; SKY = "sky"; BLUE = "blue"; INDIGO = "indigo"
    VIOLET = "violet"; PURPLE = "purple"; FUCHSIA = "fuchsia"; ROSE = "rose"
```

### UserTask

Extends `Task` with identity and display metadata:

```python
class UserTask(Task):
    id: str            # slug, e.g. "summarise-text"
    name: str          # human-readable title shown in UI
    description: str = ""
    hue: GemHue = GemHue.INDIGO
```

`render_prompt()` and the runner operate on `Task`, so they work for both `UserTask` and internal `Task` instances.

---

## Backend

### File Structure

```
backend/tasks/
├── models.py       # Task, UserTask, GemHue, TaskArg, OutputMode (updated)
├── repository.py   # save/load/list UserTask (updated — hue column migration)
├── render.py       # render_prompt(task, values) — unchanged
├── runner.py       # NEW: stream_task + run_task via Pydantic AI
└── router.py       # NEW: thin FastAPI wrapper
```

### runner.py

The reusable execution core. Imports `render_prompt` internally.

```python
async def stream_task(task: Task, values: dict[str, str]) -> AsyncIterator[str]:
    """
    Stream text tokens for a task.
    Thinking tokens (<think>…</think> and similar) are filtered out before yielding.
    """

async def run_task(task: Task, values: dict[str, str]) -> str:
    """
    Run a task and return the full response string.
    Used for structured (JSON) output and internal task invocations.
    """
```

Both use Pydantic AI with `OllamaModel("trove_model")`. Neither is aware of HTTP — they are pure async functions callable from anywhere.

### router.py

Mounted into `backend/app/router.py`. Uses the existing `require_admin` dependency for protected routes.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/app/gems` | none | List all UserTasks |
| `GET` | `/api/app/gems/{id}` | none | Get single UserTask (404 if missing) |
| `POST` | `/api/app/admin/gems` | admin | Create UserTask |
| `PUT` | `/api/app/admin/gems/{id}` | admin | Update UserTask (404 if missing) |
| `DELETE` | `/api/app/admin/gems/{id}` | admin | Delete UserTask (404 if missing) |
| `POST` | `/api/app/gems/{id}/run` | none | Run gem — SSE for TEXT, JSON for STRUCTURED (501 for now) |

The run endpoint accepts `{ values: Record<string, string> }` in the request body. For `output_mode=TEXT` it calls `stream_task` and wraps tokens as SSE `data:` lines, ending with `data: [DONE]`. For `output_mode=STRUCTURED` it returns 501 until implemented.

`save_task` / `load_task` / `list_tasks` updated to handle `UserTask` instead of `Task`. The `tasks` table schema gains a `hue` column; the existing `_CREATE_TABLE` statement is updated in place (no migration needed — nothing to be backwards compatible with).

---

## Frontend

### File Structure

```
frontend/src/
├── components/
│   └── GemIcon.tsx         # Hexagon SVG gem, hue + size props
├── pages/
│   ├── TaskShell.tsx       # Updated: Flowbite card grid of gems
│   ├── GemRunner.tsx       # NEW: collapsible arg form + streaming output
│   ├── AdminPanel.tsx      # Updated: implement Gems tab
│   └── GemForm.tsx         # NEW: full-page create/edit form
└── api/
    └── tasks.ts            # NEW: typed API client for all gem endpoints
```

All layout uses Flowbite React components (Card, Button, TextInput, Select, Spinner, etc.). Custom styling is limited to `GemIcon`.

### Mock API (`VITE_MOCK_API=1`)

A parallel mock implementation of every API client, activated by the `VITE_MOCK_API=1` env var in a `.env.development.local` file. Allows `bun run dev` to run with no backend. Each mock module mirrors the real client's interface but returns hardcoded data after a short `setTimeout` delay (to simulate latency and make spinners visible).

```
frontend/src/api/
├── client.ts          # real HTTP helpers
├── mock/
│   ├── index.ts       # re-exports all mock clients
│   ├── tasks.ts       # 4-5 sample UserTasks covering all hues + arg types
│   ├── config.ts      # default TroveConfig
│   └── system.ts      # viable models list
└── tasks.ts           # imports real or mock based on import.meta.env.VITE_MOCK_API
```

Each API module selects its implementation at module load time:

```ts
import { gemsApi as realGemsApi } from './real/tasks'
import { gemsApi as mockGemsApi } from './mock/tasks'
export const gemsApi = import.meta.env.VITE_MOCK_API ? mockGemsApi : realGemsApi
```

The mock `run` function simulates streaming by yielding words from a canned response one at a time via `ReadableStream`, matching the real SSE interface so `GemRunner` needs no special casing.

A `task dev-mock` taskipy entry runs `VITE_MOCK_API=1 bun run dev` for convenience.

**Locale files** are the one resource mock mode fetches for real. Locale files move from `backend/i18n/locales/` to a top-level `locales/` directory (single source of truth, owned by neither backend nor frontend). The backend i18n service is updated to read from there. In mock dev mode, Vite is configured to serve `../locales/` as a static directory at `/locales/`, so `useTranslation` can `fetch('/locales/{locale}.json')` directly without the backend. In real mode the hook continues using `/api/i18n/{locale}` unchanged.

### GemIcon.tsx

Renders the hexagon cut SVG (option A from design session). Accepts `hue: GemHue` and `size?: number` (default 40). Maps hue name to a set of hex colour values for the facets (crown lighter, pavilion darker).

### TaskShell.tsx

Replaces the placeholder with a Flowbite card grid. Each card shows the `GemIcon`, gem `name`, and `description`. Clicking navigates to `/gems/:id`.

### GemRunner.tsx (`/gems/:id`)

Two-phase UI on a single page:

**Phase 1 — Form:** Dynamically built from `UserTask.args`. `StringArg` → `TextInput`. `ChoiceArg` → `Select`. `has_image` → file upload `Button` (no-op, disabled with tooltip). `has_audio` → same. "Run" button submits.

**Phase 2 — Output:** Form collapses to a summary bar showing arg values (e.g. "Topic: Climate change · Language: English"). Tapping/clicking the bar re-expands the form back to Phase 1. Flowbite `Spinner` shown until first token arrives. Output streams into a text area below. A "Run again" button re-submits with current values.

### AdminPanel.tsx — Gems Tab

Lists all gems with `GemIcon`, name, description, and Edit / Delete buttons (Flowbite). "New Gem" button navigates to `/admin/gems/new`. Edit navigates to `/admin/gems/:id/edit`.

### GemForm.tsx (`/admin/gems/new`, `/admin/gems/:id/edit`)

Full-page Flowbite form. Fields:
- **Name** — TextInput
- **Description** — Textarea
- **Hue** — 16-button colour picker (one button per GemHue, each showing a small GemIcon preview)
- **Template** — Textarea (Jinja2 source)
- **Arguments** — dynamic list: add/remove args, each with type toggle (String / Choice), name, description, default; Choice also has an options list
- **has_image / has_audio** — Toggles (checkboxes)
- **Output mode** — Select (Text / Structured)

Save calls POST or PUT. Cancel navigates back to admin Gems tab.

### tasks.ts

```typescript
export const gemsApi = {
  list: () => get<UserTask[]>('/app/gems'),
  get: (id: string) => get<UserTask>(`/app/gems/${id}`),
  create: (task: UserTask, u: string, p: string) => post('/app/admin/gems', task, auth(u, p)),
  update: (id: string, task: UserTask, u: string, p: string) => put(`/app/admin/gems/${id}`, task, auth(u, p)),
  delete: (id: string, u: string, p: string) => del(`/app/admin/gems/${id}`, auth(u, p)),
  run: (id: string, values: Record<string, string>) => fetch(`/api/app/gems/${id}/run`, {
    method: 'POST', body: JSON.stringify({ values }),
    headers: { 'Content-Type': 'application/json' },
  }),
}
```

---

## Routing Changes (App.tsx)

```tsx
// app mode routes additions:
<Route path="/gems/:id" element={<GemRunner />} />
<Route path="/admin/gems/new" element={<GemForm />} />
<Route path="/admin/gems/:id/edit" element={<GemForm />} />
```

---

## Testing

- **`models.py`**: UserTask inherits Task fields, GemHue enum values, DB round-trip with hue.
- **`runner.py`**: fake Pydantic AI model returning fixed tokens. `stream_task` filters thinking tokens. `run_task` returns full string.
- **`router.py`**: FastAPI `TestClient`. Dependency-override fake runner. Covers: list/get (empty + populated + 404), admin CRUD (401 without creds, 200 with), run SSE format.

---

## Out of Scope

- Real image/audio upload handling (no-op buttons only)
- Structured (JSON) output execution (501 placeholder)
- Document library integration in tasks
- Per-gem access control

## Future Notes

- **Frontend error handling**: task runs can fail (Ollama unreachable, model error, timeout). A snackbar/toast notification should be added to `GemRunner` to surface these errors clearly to non-technical users. Not in scope for this sprint.
