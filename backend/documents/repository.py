"""SQLite repository for the Trove document library.

Owns the 'folders' and 'documents' tables in trove.db.
Uses backend.db.get_db() for connections.
"""
from datetime import datetime

from backend.db import get_db
from backend.documents.models import Document, Folder

_CREATE_TABLES = """\
CREATE TABLE IF NOT EXISTS folders (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    folder_id   TEXT NOT NULL REFERENCES folders(id),
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    mime_type   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""


def _ensure_tables(conn) -> None:
    """Create folders and documents tables if they do not exist."""
    conn.executescript(_CREATE_TABLES)


def _row_to_folder(row) -> Folder:
    """Deserialise a sqlite3.Row into a Folder model."""
    return Folder(id=row["id"], name=row["name"])


def _row_to_document(row) -> Document:
    """Deserialise a sqlite3.Row into a Document model, parsing the ISO timestamp."""
    return Document(
        id=row["id"],
        folder_id=row["folder_id"],
        name=row["name"],
        description=row["description"],
        mime_type=row["mime_type"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


# ── Folder CRUD ────────────────────────────────────────────────────────────────

def save_folder(folder: Folder) -> None:
    """Insert or replace a folder record."""
    with get_db() as conn:
        _ensure_tables(conn)
        conn.execute(
            "INSERT OR REPLACE INTO folders (id, name) VALUES (?, ?)",
            (folder.id, folder.name),
        )


def get_folder(folder_id: str) -> Folder:
    """Load a folder by id. Raises KeyError if not found."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
    if row is None:
        raise KeyError(folder_id)
    return _row_to_folder(row)


def list_folders() -> list[Folder]:
    """Return all folders ordered by name."""
    with get_db() as conn:
        _ensure_tables(conn)
        rows = conn.execute("SELECT * FROM folders ORDER BY name").fetchall()
    return [_row_to_folder(r) for r in rows]


def update_folder(folder_id: str, *, name: str) -> Folder:
    """Update a folder's name. Returns the updated Folder. Raises KeyError if not found."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
        if row is None:
            raise KeyError(folder_id)
        conn.execute(
            "UPDATE folders SET name = ? WHERE id = ?", (name, folder_id)
        )
        row = conn.execute(
            "SELECT * FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
    return _row_to_folder(row)


def delete_folder(folder_id: str) -> list[str]:
    """Delete a folder and all its documents. Returns list of deleted document IDs."""
    with get_db() as conn:
        _ensure_tables(conn)
        doc_rows = conn.execute(
            "SELECT id FROM documents WHERE folder_id = ?", (folder_id,)
        ).fetchall()
        doc_ids = [r["id"] for r in doc_rows]
        conn.execute("DELETE FROM documents WHERE folder_id = ?", (folder_id,))
        conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
    return doc_ids


# ── Document CRUD ──────────────────────────────────────────────────────────────

def save_document(doc: Document) -> None:
    """Insert or replace a document record."""
    with get_db() as conn:
        _ensure_tables(conn)
        conn.execute(
            """INSERT OR REPLACE INTO documents
               (id, folder_id, name, description, mime_type, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                doc.id,
                doc.folder_id,
                doc.name,
                doc.description,
                doc.mime_type,
                doc.created_at.isoformat(),
            ),
        )


def get_document(doc_id: str) -> Document:
    """Load a document by id. Raises KeyError if not found."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    if row is None:
        raise KeyError(doc_id)
    return _row_to_document(row)


def list_documents(folder_id: str | None = None) -> list[Document]:
    """List documents, optionally filtered by folder_id, ordered by name."""
    with get_db() as conn:
        _ensure_tables(conn)
        if folder_id is not None:
            rows = conn.execute(
                "SELECT * FROM documents WHERE folder_id = ? ORDER BY name",
                (folder_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM documents ORDER BY name").fetchall()
    return [_row_to_document(r) for r in rows]


def update_document(
    doc_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    folder_id: str | None = None,
) -> Document:
    """Update document fields. Returns updated Document. Raises KeyError if not found.

    Only keyword arguments that are not None are written to the database.
    """
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            raise KeyError(doc_id)
        updates: dict[str, object] = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if folder_id is not None:
            updates["folder_id"] = folder_id
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [doc_id]
            conn.execute(
                f"UPDATE documents SET {set_clause} WHERE id = ?", values
            )
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return _row_to_document(row)


def delete_document(doc_id: str) -> str | None:
    """Delete a document by id. Returns its folder_id for filesystem cleanup, or None if not found."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT folder_id FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    return row["folder_id"]


def document_id_exists(doc_id: str) -> bool:
    """Return True if a document with the given id already exists."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT 1 FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return row is not None


def resolve_documents(folder_ids: list[str], doc_ids: list[str]) -> list[Document]:
    """Return the union of all documents in the given folders and individual doc IDs.

    Deduplicates by document ID. Results are ordered by name.

    Args:
        folder_ids: IDs of folders whose entire contents are accessible.
        doc_ids: IDs of individually accessible documents.

    Returns:
        Deduplicated list of Documents, ordered by name.
    """
    if not folder_ids and not doc_ids:
        return []
    seen: dict[str, Document] = {}
    with get_db() as conn:
        _ensure_tables(conn)
        if folder_ids:
            placeholders = ",".join("?" * len(folder_ids))
            rows = conn.execute(
                f"SELECT * FROM documents WHERE folder_id IN ({placeholders}) ORDER BY name",
                folder_ids,
            ).fetchall()
            for r in rows:
                doc = _row_to_document(r)
                seen[doc.id] = doc
        if doc_ids:
            placeholders = ",".join("?" * len(doc_ids))
            rows = conn.execute(
                f"SELECT * FROM documents WHERE id IN ({placeholders}) ORDER BY name",
                doc_ids,
            ).fetchall()
            for r in rows:
                doc = _row_to_document(r)
                seen[doc.id] = doc
    return sorted(seen.values(), key=lambda d: d.name)
