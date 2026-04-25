"""
FastAPI router for i18n locale endpoints.

Exposes two endpoints:
  GET /api/i18n/locales       — list of available locale codes
  GET /api/i18n/{locale}      — flat key/value map for a given locale

The frontend fetches the active locale once on load and caches it locally.
"""
from fastapi import APIRouter

from backend.i18n.loader import list_locales, load_locale

router = APIRouter(prefix="/api/i18n", tags=["i18n"])


@router.get("/locales")
def get_locales() -> dict[str, str]:
    """Return a mapping of BCP-47 code → display name for every available locale."""
    return list_locales()


@router.get("/{locale}")
def get_locale(locale: str) -> dict[str, str]:
    """
    Return all UI strings for the requested locale.

    Falls back to English if the locale is not found, so the frontend
    always receives a usable response.
    """
    return load_locale(locale)
