"""Bundle export and import service for Trove.

export_bundle() — serialise all gems, folders, and documents into an
                  in-memory ZIP and return the raw bytes.
import_bundle() — parse a ZIP produced by export_bundle() and reconstruct
                  data in two modes:
                    REPLACE: wipe existing data, then import everything.
                    ADD:     import alongside existing data, renaming on
                             any ID collision and rewriting gem references.
"""
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from backend.bundle.models import (
    BundleDocument,
    BundleFolder,
    BundleGem,
    BundleManifest,
    ImportMode,
    ImportResult,
)
from backend.db import get_data_dir
from backend.documents.models import Document, Folder
from backend.documents.repository import (
    delete_folder,
    document_id_exists,
    get_folder,
    list_documents,
    list_folders,
    save_document,
    save_folder,
)
from backend.tasks.models import GemHue, OutputMode, TaskArg, UserTask
from backend.tasks.repository import (
    delete_task,
    list_tasks,
    save_task,
    task_id_exists,
)
from pydantic import TypeAdapter

_arg_adapter: TypeAdapter[TaskArg] = TypeAdapter(TaskArg)


# ── Export ────────────────────────────────────────────────────────────────────

def export_bundle() -> bytes:
    """Build an in-memory ZIP bundle of all gems, folders, and documents.

    The ZIP contains:
      - manifest.json: all metadata as JSON.
      - documents/<folder_id>/<doc_id>.md: one file per document.

    Returns:
        Raw ZIP bytes suitable for streaming as a file download.
    """
    folders = list_folders()
    documents = list_documents()
    gems = list_tasks()
    data_dir = get_data_dir()

    manifest = BundleManifest(
        version=1,
        exported_at=datetime.now(timezone.utc).isoformat(),
        folders=[BundleFolder(id=f.id, name=f.name) for f in folders],
        documents=[
            BundleDocument(
                id=d.id,
                folder_id=d.folder_id,
                name=d.name,
                description=d.description,
                mime_type=d.mime_type,
                created_at=d.created_at.isoformat(),
            )
            for d in documents
        ],
        gems=[
            BundleGem(
                id=g.id,
                name=g.name,
                description=g.description,
                hue=g.hue.value,
                template=g.template,
                args=[arg.model_dump() for arg in g.args],
                has_image=g.has_image,
                has_audio=g.has_audio,
                output_mode=g.output_mode.value,
                doc_folder_ids=list(g.doc_folder_ids),
                doc_ids=list(g.doc_ids),
            )
            for g in gems
        ],
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest.model_dump_json(indent=2))
        for doc in documents:
            md_path = data_dir / "documents" / doc.folder_id / f"{doc.id}.md"
            if md_path.exists():
                zf.writestr(
                    f"documents/{doc.folder_id}/{doc.id}.md",
                    md_path.read_text(encoding="utf-8"),
                )

    return buf.getvalue()
