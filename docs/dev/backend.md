# Backend reference

The backend is a FastAPI application in `backend/`. Entry point: `backend/main.py`.

## Module structure

```
backend/
├── main.py          # App factories, SessionMiddleware, SPA serving
├── session.py       # ExpirableTokenDict: session + admin token stores
├── network.py       # get_lan_ip() — shared LAN IP detection
├── db.py            # SQLite connection, schema initialisation
├── log_buffer.py    # Ring-buffer log handler (last 1 000 lines)
├── cli.py           # Typer CLI (trove setup / trove start)
│
├── config/          # GET + PUT /api/config, XDG persistence
├── i18n/            # GET /api/i18n/{locale}, locale file loading
├── system/          # GET /api/system/check — RAM, disk, GPU, viable models
├── ollama/          # Install/pull/build (SSE), status, Modelfile generation
│
├── setup/           # Setup-mode wizard endpoints (/api/setup/*)
│   ├── router.py
│   └── service.py   # ServiceInstaller Protocol + Real + Fake
│
└── app/             # App-mode endpoints (/api/app/*)
    ├── router.py    # Admin endpoints, delegates to tasks + documents sub-routers
    ├── auth.py      # bcrypt verify, admin cookie validation
    ├── tasks/       # Gem CRUD + runner (/api/app/gems/*)
    └── documents/   # Document upload + library (/api/app/documents/*)
```

## Service pattern

Every external dependency follows the same pattern:

```python
class OllamaService(Protocol):
    def get_status(self) -> OllamaStatus: ...

class RealOllamaService:          # talks to the real Ollama process
    ...

class FakeOllamaService:          # returns hardcoded test data
    ...

def get_ollama_service() -> OllamaService:
    if os.getenv("TROVE_FAKE_OLLAMA"):
        return FakeOllamaService()
    return RealOllamaService()
```

FastAPI dependencies inject `get_ollama_service()`. Tests set `TROVE_FAKE_OLLAMA=1` and never touch a real Ollama server.

## Session and auth

**Session tokens** — all browser clients call `GET /api/session` on load. This returns a token that must be included as `X-Trove-Session` in every subsequent request. `SessionMiddleware` in `main.py` validates each token against the in-memory `session_store`. Tokens expire after 2 hours of inactivity.

**Admin cookie** — the admin login endpoint (`POST /api/app/admin/login`) verifies the password with bcrypt and sets an `httponly` cookie. Subsequent admin API calls are authenticated by this cookie. The cookie expires after 8 hours.

## SSE streaming

Long-running operations (Ollama install, model pull, gem run) stream progress as Server-Sent Events. The pattern:

```python
from sse_starlette.sse import EventSourceResponse

@router.post("/some-action")
def some_action():
    def generate():
        for line in do_the_work():
            yield {"data": line}
        yield {"data": "[DONE]"}
    return EventSourceResponse(generate())
```

The frontend uses `streamLines()` from `frontend/src/api/ollama.ts` to consume SSE streams.

## Adding a new domain

1. Create `backend/newdomain/` with `__init__.py`, `router.py`, `service.py`, `models.py`.
2. Follow the Protocol/Real/Fake pattern in `service.py`.
3. Register the router in `backend/main.py` (shared) or in the appropriate mode router.
4. Write tests in `tests/test_newdomain.py` using `FakeXxxService`.
