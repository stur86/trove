"""
MkDocs hook: copy the root sitemap into every language subdirectory.

Material for MkDocs emits a relative <link rel="sitemap" href="sitemap.xml">
on every page.  For pages under /de/, /fr/, etc. that resolves to
/<lang>/sitemap.xml which doesn't exist — generating 404s.  Copying the
root sitemap (which already carries hreflang entries for all languages) into
each language directory silences those 404s without any server configuration.
"""
import shutil
from pathlib import Path


# Language codes produced by mkdocs-static-i18n (must match mkdocs.yml).
_LANGUAGE_CODES = {"de", "es", "fr", "it", "pt", "zh"}


def on_post_build(config: dict) -> None:
    """Copy sitemap.xml (and .gz) from site root into each language directory."""
    site_dir = Path(config["site_dir"])
    root_sitemap = site_dir / "sitemap.xml"
    root_gz = site_dir / "sitemap.xml.gz"

    if not root_sitemap.exists():
        return

    for lang in _LANGUAGE_CODES:
        lang_dir = site_dir / lang
        if lang_dir.is_dir():
            shutil.copy2(root_sitemap, lang_dir / "sitemap.xml")
            if root_gz.exists():
                shutil.copy2(root_gz, lang_dir / "sitemap.xml.gz")
