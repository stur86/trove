"""Upload pipeline for the Trove document library.

Handles slug derivation, context-length guard, AI summary generation,
markdown file writing, and database persistence. Both upload paths
(file and URL) call process_document() after content is retrieved.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

from backend.config.service import load_config
from backend.db import get_data_dir
from backend.documents.models import Document
from backend.documents.repository import document_id_exists, save_document


class DocumentTooLongError(Exception):
    """Raised when a document exceeds the model's context window and no description was supplied.

    The router catches this and returns a needs_description response so the
    frontend can prompt the admin for a manual description.
    """

    def __init__(self, word_count: int, num_ctx: int) -> None:
        self.word_count = word_count
        self.num_ctx = num_ctx
        super().__init__(
            f"Document has ~{word_count * 2} estimated tokens; context window is {num_ctx}."
        )


def slugify(name: str) -> str:
    """Derive a lowercase hyphenated slug from a filename, stripping the extension.

    Examples:
        'HR Policy 2024.docx' → 'hr-policy-2024'
        '.hidden'             → 'document'
    """
    stem = Path(name).stem
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or "document"


def _unique_id(base: str) -> str:
    """Return base if available, otherwise base-2, base-3, … until unique."""
    if not document_id_exists(base):
        return base
    n = 2
    while document_id_exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


async def _ai_summary(content: str, fallback: str) -> str:
    """Generate a one-sentence AI summary of content.

    Imports run_task at call time to avoid a circular import at module load
    (service → runner → documents.models is fine; service → runner at module
    level would cause an import cycle with runner → service for the summary task).

    Falls back to the filename on any failure (Ollama unavailable, timeout, etc.).
    """
    from backend.tasks.models import StringArg, Task
    from backend.tasks.runner import run_task

    summary_task = Task(
        template=(
            "In one sentence, describe what this document is about:\n\n{{ content }}"
        ),
        args=(StringArg(name="content"),),
    )
    try:
        return await run_task(summary_task, {"content": content})
    except Exception:
        return fallback


async def process_document(
    content: str,
    name: str,
    folder_id: str,
    mime_type: str,
    description: str = "",
) -> Document:
    """Convert, summarise, and persist a document.

    Steps:
      1. Derive a unique slug from the filename.
      2. If no description was supplied, check content length against num_ctx.
         Raises DocumentTooLongError if content exceeds the context window.
      3. If no description supplied and content is short enough, run AI summary.
      4. Write markdown content to disk.
      5. Insert metadata row into the database.

    Args:
        content:     Full markdown text of the document (post-Markitdown).
        name:        Original filename — used for slug and as description fallback.
        folder_id:   ID of the destination folder (must already exist in DB).
        mime_type:   MIME type of the original file.
        description: Admin-supplied description. Non-empty values bypass length
                     check and AI summary entirely.

    Raises:
        DocumentTooLongError: When content is too long and no description given.
    """
    doc_id = _unique_id(slugify(name))

    if not description:
        word_count = len(content.split())
        config = load_config()
        if word_count * 2 > config.num_ctx:
            raise DocumentTooLongError(word_count, config.num_ctx)
        description = await _ai_summary(content, name)

    # Write markdown to disk
    doc_dir = get_data_dir() / "documents" / folder_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / f"{doc_id}.md").write_text(content, encoding="utf-8")

    # Persist metadata
    doc = Document(
        id=doc_id,
        folder_id=folder_id,
        name=name,
        description=description,
        mime_type=mime_type,
        created_at=datetime.now(timezone.utc),
    )
    save_document(doc)
    return doc
