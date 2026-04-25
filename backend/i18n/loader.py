"""
i18n locale loader.

Reads JSON locale files from the shared locales/ directory at the project root.
Falls back to English if the requested locale doesn't exist.

JSON values may be either plain strings or file-reference objects:
  {"path": "relative/file.md"}

File paths are resolved relative to locales/{locale}/ and fall back to
locales/en/ when the locale-specific file is absent.
"""
import json
from pathlib import Path

# Locale files live at the project root, shared between backend and frontend dev server.
# This file is at backend/i18n/loader.py — three parents up is the project root.
LOCALES_DIR = Path(__file__).parent.parent.parent / "locales"


def _read_locale_file(rel_path: str, locale: str) -> str:
    """
    Read a content file referenced by a locale JSON entry.

    Tries locales/{locale}/{rel_path} first, then locales/en/{rel_path}.
    Returns an empty string if neither exists or if rel_path attempts traversal.
    """
    candidates = [locale] if locale != "en" else []
    candidates.append("en")

    for loc in candidates:
        locale_dir = (LOCALES_DIR / loc).resolve()
        try:
            target = (LOCALES_DIR / loc / rel_path).resolve()
            # Reject any path that escapes the locale directory.
            target.relative_to(locale_dir)
        except ValueError:
            return ""
        if target.exists():
            return target.read_text()

    return ""


def load_locale(locale: str) -> dict[str, str]:
    """
    Load a locale file by BCP-47 code (e.g. 'en', 'fr').

    Falls back to 'en' silently if the requested locale doesn't exist.
    Returns a flat dict of dot-separated keys to resolved strings.

    Values in the JSON may be plain strings or {"path": "..."} objects;
    the latter are replaced with the contents of the referenced file.
    """
    json_path = LOCALES_DIR / f"{locale}.json"
    if not json_path.exists():
        json_path = LOCALES_DIR / "en.json"
        locale = "en"

    raw: dict[str, object] = json.loads(json_path.read_text())
    result: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(value, str):
            result[key] = value
        elif isinstance(value, dict) and "path" in value:
            result[key] = _read_locale_file(str(value["path"]), locale)

    return result


def list_locales() -> dict[str, str]:
    """Return a mapping of BCP-47 code → display name for all available locales.

    The display name is read from the ``locale.name`` key in each JSON file.
    Falls back to the code itself if the key is absent.
    """
    result: dict[str, str] = {}
    for path in sorted(LOCALES_DIR.glob("*.json")):
        code = path.stem
        try:
            data: dict[str, object] = json.loads(path.read_text())
            name = data.get("locale.name", code)
            result[code] = str(name)
        except Exception:
            result[code] = code
    return result
