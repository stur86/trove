"""
i18n locale loader.

Reads JSON locale files from the shared locales/ directory at the project root.
Falls back to English if the requested locale doesn't exist.
"""
import json
from pathlib import Path

# Locale files live at the project root, shared between backend and frontend dev server.
# This file is at backend/i18n/loader.py — three parents up is the project root.
LOCALES_DIR = Path(__file__).parent.parent.parent / "locales"


def load_locale(locale: str) -> dict[str, str]:
    """
    Load a locale file by BCP-47 code (e.g. 'en', 'fr').

    Falls back to 'en' silently if the requested locale doesn't exist.
    Returns a flat dict of dot-separated keys to translated strings.
    """
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        path = LOCALES_DIR / "en.json"
    return json.loads(path.read_text())


def list_locales() -> list[str]:
    """Return the BCP-47 codes of all available locales (stems of .json files)."""
    return [p.stem for p in LOCALES_DIR.glob("*.json")]
