"""
Tests for the i18n locale loading module.

Verifies that locale files can be loaded, that required keys are present,
that the fallback-to-English behaviour works for unknown locales, and that
file-based values ({"path": "..."}) are resolved to their file contents.
"""
import json
from pathlib import Path

import pytest

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


def test_list_locales_returns_dict_of_code_to_name():
    """list_locales() must return a dict mapping BCP-47 codes to display names."""
    locales = list_locales()
    assert isinstance(locales, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in locales.items())


def test_list_locales_en_display_name_is_english():
    """The English locale's display name must be 'English'."""
    locales = list_locales()
    assert locales["en"] == "English"


def test_italian_locale_has_all_english_keys():
    """it.json must contain every key that en.json contains."""
    en = load_locale("en")
    it = load_locale("it")
    missing = set(en.keys()) - set(it.keys())
    assert missing == set(), f"it.json missing keys: {missing}"


def test_italian_locale_loads():
    it = load_locale("it")
    assert it["config.save"] == "Salva"


# ---------------------------------------------------------------------------
# File-based value tests — use a tmp_path locale tree, not the real locales/.
# ---------------------------------------------------------------------------

@pytest.fixture()
def locale_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Create a minimal locale tree in tmp_path and redirect LOCALES_DIR to it.

    Structure produced:
        tmp_path/
            en.json
            en/
                tutorial.md
            it.json
            it/          (empty — used for fallback tests)
    """
    import backend.i18n.loader as loader_mod

    # English JSON with one string key and one file-based key.
    en_json = {
        "greeting": "Hello",
        "tutorial": {"path": "tutorial.md"},
    }
    (tmp_path / "en.json").write_text(json.dumps(en_json))
    (tmp_path / "en").mkdir()
    (tmp_path / "en" / "tutorial.md").write_text("# English Tutorial\n")

    # Italian JSON: string key translated, file key points to its own file.
    it_json = {
        "greeting": "Ciao",
        "tutorial": {"path": "tutorial.md"},
    }
    (tmp_path / "it.json").write_text(json.dumps(it_json))
    (tmp_path / "it").mkdir()
    # No tutorial.md in it/ yet — used to test fallback.

    monkeypatch.setattr(loader_mod, "LOCALES_DIR", tmp_path)
    return tmp_path


def test_string_values_pass_through(locale_dir: Path):
    """Plain string values are returned unchanged."""
    strings = load_locale("en")
    assert strings["greeting"] == "Hello"


def test_file_based_value_resolves(locale_dir: Path):
    """A {"path": "..."} value is replaced with the file's contents."""
    strings = load_locale("en")
    assert strings["tutorial"] == "# English Tutorial\n"


def test_file_based_value_resolves_non_english(locale_dir: Path):
    """A {"path": "..."} value in a non-English locale is read from that locale's directory."""
    (locale_dir / "it" / "tutorial.md").write_text("# Tutorial Italiano\n")
    strings = load_locale("it")
    assert strings["tutorial"] == "# Tutorial Italiano\n"


def test_file_based_value_falls_back_to_en_file(locale_dir: Path):
    """If the locale's file is missing, the English file is used instead."""
    # it/ has no tutorial.md — should silently use en/tutorial.md.
    strings = load_locale("it")
    assert strings["tutorial"] == "# English Tutorial\n"


def test_file_based_value_uses_locale_file_when_present(locale_dir: Path):
    """When the locale's own file exists, it takes priority over the English one."""
    (locale_dir / "it" / "tutorial.md").write_text("# Tutorial Italiano\n")
    strings = load_locale("it")
    assert strings["tutorial"] == "# Tutorial Italiano\n"


def test_file_based_value_missing_entirely_returns_empty(locale_dir: Path):
    """If the file is absent in both the locale and English dirs, return empty string."""
    en_json = {"broken": {"path": "nonexistent.md"}}
    (locale_dir / "en.json").write_text(json.dumps(en_json))
    strings = load_locale("en")
    assert strings["broken"] == ""


def test_help_bar_keys_present():
    """All six HelpBar placements must have prompt, title, and content keys in English."""
    en = load_locale("en")
    prefixes = [
        "help.model", "help.ctx", "help.bundle",
        "help.gem.intro", "help.gem.template", "help.gem.documents",
    ]
    for prefix in prefixes:
        assert f"{prefix}.prompt" in en, f"missing {prefix}.prompt"
        assert f"{prefix}.title" in en, f"missing {prefix}.title"
        assert f"{prefix}.content" in en, f"missing {prefix}.content"
        # content must be non-empty (file was found and read)
        assert en[f"{prefix}.content"], f"empty content for {prefix}.content"


def test_path_traversal_rejected(locale_dir: Path):
    """A path attempting directory traversal must not be followed; returns empty string."""
    en_json = {"danger": {"path": "../../etc/passwd"}}
    (locale_dir / "en.json").write_text(json.dumps(en_json))
    strings = load_locale("en")
    assert strings["danger"] == ""
