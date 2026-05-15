"""Locale file editor for Trove i18n JSON files.

Reads, adds, or edits individual keys in locale JSON files without loading
the entire file into context. Locale files live at
``backend/i18n/locales/<locale>.json``.

Usage::

    uv run scripts/i18n.py get <key> [--locale en]
    uv run scripts/i18n.py set <key> <value> [--locale en]
    uv run scripts/i18n.py all <key>
    uv run scripts/i18n.py keys [--locale en] [--prefix setup]
    uv run scripts/i18n.py locales
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCALES_DIR = REPO_ROOT / "backend" / "i18n" / "locales"

app = typer.Typer(help="Read, add, or edit Trove locale JSON file entries by key.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _locale_path(locale: str) -> Path:
    """Return the path to a locale JSON file, erroring if it does not exist."""
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        typer.echo(f"Locale file not found: {path}", err=True)
        raise typer.Exit(code=1)
    return path


def _load(locale: str) -> dict[str, str]:
    """Load and return the JSON dict for *locale*."""
    return json.loads(_locale_path(locale).read_text(encoding="utf-8"))


def _save(locale: str, data: dict[str, str]) -> None:
    """Write *data* back to the locale file, preserving sorted key order and indentation."""
    _locale_path(locale).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _available_locales() -> list[str]:
    """Return the list of locale codes that have a JSON file."""
    return sorted(p.stem for p in LOCALES_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def get(
    key: str = typer.Argument(..., help="Locale key to read, e.g. setup.title"),
    locale: str = typer.Option("en", "--locale", "-l", help="Locale code (e.g. en, it, fr)"),
) -> None:
    """Print the value of KEY in the given locale file."""
    data = _load(locale)
    if key not in data:
        typer.echo(f"Key '{key}' not found in locale '{locale}'.", err=True)
        raise typer.Exit(code=1)
    typer.echo(data[key])


@app.command(name="set")
def set_key(
    key: str = typer.Argument(..., help="Locale key to create or update"),
    value: str = typer.Argument(..., help="New value for the key"),
    locale: str = typer.Option("en", "--locale", "-l", help="Locale code (e.g. en, it, fr)"),
) -> None:
    """Create or update KEY in the given locale file."""
    data = _load(locale)
    existed = key in data
    data[key] = value
    _save(locale, data)
    verb = "Updated" if existed else "Added"
    typer.echo(f"{verb} [{locale}] {key} = {value!r}")


@app.command(name="all")
def all_locales(
    key: str = typer.Argument(..., help="Locale key to read across all locale files"),
) -> None:
    """Print KEY's value from every available locale file."""
    for locale in _available_locales():
        data = _load(locale)
        value = data.get(key)
        if value is None:
            typer.echo(f"  {locale}: (missing)")
        else:
            typer.echo(f"  {locale}: {value!r}")


@app.command()
def keys(
    locale: str = typer.Option("en", "--locale", "-l", help="Locale code (e.g. en, it, fr)"),
    prefix: Optional[str] = typer.Option(None, "--prefix", "-p", help="Filter keys by prefix"),
) -> None:
    """List all keys in a locale file, optionally filtered by PREFIX."""
    data = _load(locale)
    for k in data:
        if prefix is None or k.startswith(prefix):
            typer.echo(k)


@app.command()
def locales() -> None:
    """List all available locale codes."""
    for locale in _available_locales():
        typer.echo(locale)


@app.command()
def missing(
    locale: str = typer.Argument(..., help="Locale code to check against English"),
) -> None:
    """List keys present in 'en' but missing from LOCALE."""
    en = _load("en")
    other = _load(locale)
    absent = [k for k in en if k not in other]
    if not absent:
        typer.echo(f"No missing keys in '{locale}'.")
        sys.exit(0)
    for k in absent:
        typer.echo(k)


if __name__ == "__main__":
    app()
