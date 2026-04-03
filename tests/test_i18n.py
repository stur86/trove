"""
Tests for the i18n locale loading module.

Verifies that locale files can be loaded, that required keys are present,
and that the fallback-to-English behaviour works for unknown locales.
"""
from backend.i18n.loader import load_locale, list_locales


def test_load_locale_en_contains_required_keys():
    """Check that the English locale file has the expected UI string keys."""
    strings = load_locale("en")
    assert strings["setup.step_install"] == "Install Ollama"
    assert "config.base_model" in strings


def test_load_locale_falls_back_to_en_for_unknown():
    """Requesting a locale that doesn't exist should silently return English strings."""
    strings = load_locale("nonexistent_locale")
    assert "setup.step_install" in strings


def test_list_locales_includes_en():
    """The English locale must always be present in the list of available locales."""
    locales = list_locales()
    assert "en" in locales


def test_list_locales_returns_list_of_strings():
    """Every entry returned by list_locales() must be a plain string BCP-47 code."""
    locales = list_locales()
    assert all(isinstance(loc, str) for loc in locales)
