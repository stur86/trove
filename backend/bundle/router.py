"""FastAPI router for bundle export/import.

Mounted at /api/app via backend.app.router. All endpoints require
the admin cookie set by POST /api/app/admin/login.
"""
import io
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.app.auth import require_admin_cookie
from backend.bundle.models import ImportMode, ImportResult
from backend.bundle.service import export_bundle, import_bundle

router = APIRouter(tags=["bundle"])


@router.get("/admin/bundle/export", dependencies=[Depends(require_admin_cookie)])
def bundle_export() -> Response:
    """Export all gems and documents as a downloadable ZIP bundle.

    The archive contains manifest.json and one .md file per document.
    Requires admin cookie.
    """
    zip_bytes = export_bundle()
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="trove-bundle.zip"'},
    )


@router.post("/admin/bundle/import", dependencies=[Depends(require_admin_cookie)])
async def bundle_import(
    file: UploadFile = File(...),
    mode: str = Form("add"),
) -> ImportResult:
    """Import a bundle ZIP, merging or replacing existing data.

    Args:
        file: The ZIP bundle produced by the export endpoint.
        mode: 'add' (default) or 'replace'. Invalid values return 422.

    Returns:
        ImportResult with counts and rename maps.

    Requires admin cookie.
    """
    try:
        import_mode = ImportMode(mode)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid mode '{mode}'. Must be 'add' or 'replace'.",
        )
    zip_bytes = await file.read()
    try:
        return import_bundle(zip_bytes, import_mode)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail="Uploaded file is not a valid ZIP archive.")
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Bundle is missing required entry: {e}")
