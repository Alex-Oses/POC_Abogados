from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from psycopg import Connection

from app.api.deps import connection, require_role
from app.schemas.common import PaginatedOut
from app.schemas.documents import DocumentOut
from app.schemas.review import (
    ReopenIn,
    ReviewAssignIn,
    ReviewCreateIn,
    ReviewOut,
    ReviewPatchIn,
)
from app.services import review as review_service

router = APIRouter(tags=["revisiones"])


@router.get("/reviews", response_model=PaginatedOut[ReviewOut])
def list_reviews(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return review_service.listar_revisiones(conexion, page, limit)


@router.post("/documents/{documento_id}/reviews", response_model=ReviewOut, status_code=201)
def create_review(
    documento_id: UUID,
    body: ReviewCreateIn | None = None,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return review_service.crear_revision(
        conexion, usuario, documento_id, body.revisor_id if body else None
    )


@router.post("/reviews/{revision_id}/claim", response_model=ReviewOut)
def claim_review(
    revision_id: UUID,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return review_service.reclamar_revision(conexion, usuario, revision_id)


@router.patch("/reviews/{revision_id}/assign", response_model=ReviewOut)
def assign_review(
    revision_id: UUID,
    body: ReviewAssignIn,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return review_service.asignar_revision(conexion, usuario, revision_id, body.revisor_id)


@router.patch("/reviews/{revision_id}", response_model=ReviewOut)
def close_review(
    revision_id: UUID,
    body: ReviewPatchIn,
    if_match: str | None = Header(default=None),
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return review_service.cerrar_revision(
        conexion, usuario, revision_id, body.estado, body.motivo, if_match
    )


@router.post("/documents/{documento_id}/reopen", response_model=DocumentOut)
def reopen_document(
    documento_id: UUID,
    body: ReopenIn,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return review_service.reabrir_documento(conexion, usuario, documento_id, body.motivo)


@router.post("/documents/{documento_id}/sign-off", response_model=DocumentOut)
def sign_off_document(
    documento_id: UUID,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return review_service.firmar_documento(conexion, usuario, documento_id)
