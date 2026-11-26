from uuid import UUID

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.api.deps import connection, require_role
from app.schemas.review import AnnotationOut, AnnotationPatchIn, AnonymizeIn
from app.services import anonymize as anonymize_service

router = APIRouter(tags=["anonimización"])


@router.post("/documents/{documento_id}/anonymize", response_model=list[AnnotationOut])
def anonymize_document(
    documento_id: UUID,
    body: AnonymizeIn | None = None,
    usuario: dict = Depends(require_role("transcriptor", "revisor")),
    conexion: Connection = Depends(connection),
):
    return anonymize_service.anonimizar_documento(
        conexion, usuario, documento_id, body.numero_version if body else None
    )


@router.get("/documents/{documento_id}/annotations", response_model=list[AnnotationOut])
def list_annotations(
    documento_id: UUID,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return anonymize_service.listar_anotaciones(conexion, documento_id)


@router.patch("/annotations/{anotacion_id}", response_model=AnnotationOut)
def patch_annotation(
    anotacion_id: UUID,
    body: AnnotationPatchIn,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return anonymize_service.actualizar_anotacion(
        conexion, usuario, anotacion_id, body.estado, body.texto_sustitucion
    )
