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


# ── Private helpers ───────────────────────────────────────────────────────────

def _unique_doc_id(base: str) -> str:
    """Return base if unused as a document ID, else base-2, base-3, …"""
    if not document_id_exists(base):
        return base
    n = 2
    while document_id_exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


def _unique_task_id(base: str) -> str:
    """Return base if unused as a task ID, else base-2, base-3, …"""
    if not task_id_exists(base):
        return base
    n = 2
    while task_id_exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


def _bundle_gem_to_user_task(
    bg: BundleGem,
    doc_renames: dict[str, str],
    new_id: str,
) -> UserTask:
    """Convert a BundleGem to a UserTask, applying doc_id renames.

    Args:
        bg:          The BundleGem from the manifest.
        doc_renames: Mapping of original doc ID → new ID from Add-mode renaming.
        new_id:      The (possibly renamed) task ID to assign.

    Returns:
        A fully-constructed UserTask ready for save_task().
    """
    args = tuple(_arg_adapter.validate_python(a) for a in bg.args)
    new_doc_ids = tuple(doc_renames.get(did, did) for did in bg.doc_ids)
    return UserTask(
        id=new_id,
        name=bg.name,
        description=bg.description,
        hue=GemHue(bg.hue),
        template=bg.template,
        args=args,
        has_image=bg.has_image,
        has_audio=bg.has_audio,
        output_mode=OutputMode(bg.output_mode),
        doc_folder_ids=tuple(bg.doc_folder_ids),
        doc_ids=new_doc_ids,
    )


def _wipe_all(data_dir: Path) -> None:
    """Delete all gems, document .md files, document DB rows, and folder DB rows.

    Processes gems first, then documents+folders so foreign key order is respected.
    """
    for task in list_tasks():
        delete_task(task.id)

    for folder in list_folders():
        folder_dir = data_dir / "documents" / folder.id
        for doc in list_documents(folder.id):
            (folder_dir / f"{doc.id}.md").unlink(missing_ok=True)
        try:
            folder_dir.rmdir()
        except OSError:
            pass
        # delete_folder() removes all document rows then the folder row
        delete_folder(folder.id)


def _write_document(
    bd: BundleDocument,
    new_id: str,
    content: str,
    data_dir: Path,
) -> None:
    """Write a document's .md file and save its DB row."""
    doc_dir = data_dir / "documents" / bd.folder_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / f"{new_id}.md").write_text(content, encoding="utf-8")
    save_document(Document(
        id=new_id,
        folder_id=bd.folder_id,
        name=bd.name,
        description=bd.description,
        mime_type=bd.mime_type,
        created_at=datetime.fromisoformat(bd.created_at),
    ))


# ── Import ────────────────────────────────────────────────────────────────────

def import_bundle(zip_bytes: bytes, mode: ImportMode) -> ImportResult:
    """Parse and import a bundle ZIP produced by export_bundle().

    Args:
        zip_bytes: Raw bytes of the ZIP file.
        mode:      REPLACE wipes existing data first; ADD merges with renaming.

    Returns:
        ImportResult with counts and rename maps.

    Raises:
        zipfile.BadZipFile: If zip_bytes is not a valid ZIP.
        KeyError:           If manifest.json is missing from the archive.
    """
    data_dir = get_data_dir()
    buf = io.BytesIO(zip_bytes)

    with zipfile.ZipFile(buf, "r") as zf:
        manifest = BundleManifest.model_validate_json(zf.read("manifest.json"))
        namelist = set(zf.namelist())

        if mode == ImportMode.REPLACE:
            _wipe_all(data_dir)

            for bf in manifest.folders:
                save_folder(Folder(id=bf.id, name=bf.name))

            for bd in manifest.documents:
                md_key = f"documents/{bd.folder_id}/{bd.id}.md"
                content = zf.read(md_key).decode("utf-8") if md_key in namelist else ""
                _write_document(bd, bd.id, content, data_dir)

            for bg in manifest.gems:
                save_task(_bundle_gem_to_user_task(bg, {}, bg.id))

            return ImportResult(
                folders_created=len(manifest.folders),
                documents_imported=len(manifest.documents),
                documents_renamed={},
                gems_imported=len(manifest.gems),
                gems_renamed={},
            )

        else:  # ADD
            return _import_add(manifest, zf, namelist, data_dir)


def _import_add(
    manifest: BundleManifest,
    zf: zipfile.ZipFile,
    namelist: set[str],
    data_dir: Path,
) -> ImportResult:
    """Import bundle in Add mode: merge with existing data, rename on collision."""
    folders_created = 0
    doc_renames: dict[str, str] = {}
    gem_renames: dict[str, str] = {}

    # Step 1: Folders — create if absent; skip (keep existing) if ID taken
    for bf in manifest.folders:
        try:
            get_folder(bf.id)
        except KeyError:
            save_folder(Folder(id=bf.id, name=bf.name))
            folders_created += 1

    # Step 2: Documents — import with rename on collision
    for bd in manifest.documents:
        new_id = _unique_doc_id(bd.id)
        if new_id != bd.id:
            doc_renames[bd.id] = new_id
        md_key = f"documents/{bd.folder_id}/{bd.id}.md"
        content = zf.read(md_key).decode("utf-8") if md_key in namelist else ""
        _write_document(bd, new_id, content, data_dir)

    # Step 3: Gems — rewrite doc_ids using renames, rename gem ID on collision
    for bg in manifest.gems:
        new_id = _unique_task_id(bg.id)
        if new_id != bg.id:
            gem_renames[bg.id] = new_id
        save_task(_bundle_gem_to_user_task(bg, doc_renames, new_id))

    return ImportResult(
        folders_created=folders_created,
        documents_imported=len(manifest.documents),
        documents_renamed=doc_renames,
        gems_imported=len(manifest.gems),
        gems_renamed=gem_renames,
    )
