"""Pydantic models for the Trove bundle export/import format.

The bundle is a ZIP file containing:
  - manifest.json: all metadata (folders, documents, gems) as JSON
  - documents/<folder_id>/<doc_id>.md: converted markdown content per document

BundleManifest is the authoritative representation of manifest.json.
ImportResult is returned by import_bundle() to summarise what changed.
"""
from enum import Enum

from pydantic import BaseModel


class BundleFolder(BaseModel, frozen=True):
    """Folder entry in the bundle manifest."""

    id: str
    name: str


class BundleDocument(BaseModel, frozen=True):
    """Document metadata entry in the bundle manifest.

    The corresponding markdown content is stored at
    documents/<folder_id>/<id>.md inside the ZIP.
    """

    id: str
    folder_id: str
    name: str
    description: str
    mime_type: str
    created_at: str
    """ISO 8601 timestamp string — preserved verbatim from the original."""


class BundleGem(BaseModel, frozen=True):
    """Gem (UserTask) entry in the bundle manifest.

    Args are stored as raw dicts — the discriminated union is reconstructed
    at import time via Pydantic's TypeAdapter.
    """

    id: str
    name: str
    description: str
    hue: str
    template: str
    args: list[dict]
    has_image: bool
    has_audio: bool
    output_mode: str
    doc_folder_ids: list[str]
    doc_ids: list[str]
    tools: list[str] = []
    """Tool IDs enabled for this gem, stored as their string values."""


class BundleManifest(BaseModel, frozen=True):
    """Top-level manifest written as manifest.json inside the bundle ZIP."""

    version: int = 1
    exported_at: str
    """ISO 8601 timestamp of when the bundle was created."""
    folders: list[BundleFolder]
    documents: list[BundleDocument]
    gems: list[BundleGem]


class ImportMode(str, Enum):
    """Controls how imported items are merged with existing data."""

    REPLACE = "replace"
    """Wipe all existing gems, documents, and folders before importing."""
    ADD = "add"
    """Import new items alongside existing ones; rename on ID collision."""


class ImportResult(BaseModel):
    """Summary of what changed during a bundle import operation."""

    folders_created: int
    """Number of folders created (Add mode: skips existing; Replace: always all)."""
    documents_imported: int
    """Total number of documents written (including renamed ones)."""
    documents_renamed: dict[str, str]
    """Mapping of original doc ID → new ID for any renamed documents (Add mode)."""
    gems_imported: int
    """Total number of gems written (including renamed ones)."""
    gems_renamed: dict[str, str]
    """Mapping of original gem ID → new ID for any renamed gems (Add mode)."""
