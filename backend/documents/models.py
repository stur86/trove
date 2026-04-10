"""Data models for the Trove document library.

Folder groups related documents under a human-readable name.
Document represents a single processed file with AI-generated metadata.
Both are immutable Pydantic models — the repository owns persistence.
"""
from datetime import datetime

from pydantic import BaseModel


class Folder(BaseModel, frozen=True):
    """A named folder grouping related documents in the library."""

    id: str
    """Slug identifier, e.g. 'hr-policies'."""
    name: str
    """Human-readable folder name, e.g. 'HR Policies'."""


class Document(BaseModel, frozen=True):
    """A processed document stored in the library.

    The markdown content is stored on disk at
    $XDG_DATA_HOME/trove/documents/<folder_id>/<id>.md.
    This model holds only the metadata.
    """

    id: str
    """Slug derived from the original filename, e.g. 'leave-policy-2024'."""
    folder_id: str
    """ID of the folder this document belongs to."""
    name: str
    """Original filename, used for display purposes."""
    description: str
    """AI-generated one-liner, or admin-supplied description if the document
    is too long for the model's context window."""
    mime_type: str
    """MIME type of the original uploaded file."""
    created_at: datetime
    """Timestamp when this document was added to the library."""
