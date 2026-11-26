from uuid import UUID

from fastapi import APIRouter, Depends, Response
from psycopg import Connection

from app.api.deps import connection, require_role
from app.schemas.export import ExportIn
from app.services import export as export_service

router = APIRouter(tags=["exportación"])


@router.post("/documents/{documento_id}/export")
def export_document(
    documento_id: UUID,
    body: ExportIn | None = None,
    usuario: dict = Depends(require_role("transcriptor", "revisor")),
    conexion: Connection = Depends(connection),
):
    pdf_bytes, meta = export_service.exportar_documento(
        conexion,
        usuario,
        documento_id,
        body.numero_version if body else None,
        body.modo if body else "layout",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "X-Export-Hash": meta["hash_export"],
            "Content-Disposition": f'attachment; filename="{documento_id}_v{meta["numero_version"]}.pdf"',
        },
    )
