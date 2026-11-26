from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from psycopg import Connection

from app.api.deps import connection, require_role
from app.schemas.common import PaginatedOut
from app.schemas.documents import (
    BlockOut,
    DocumentOut,
    PageOut,
    TransformBuildIn,
    TransformPlainTextIn,
    VersionOut,
)
from app.services import documents as doc_service

router = APIRouter(tags=["documentos"])


@router.post("/transform/document", response_model=DocumentOut, status_code=201)
def transform_document(
    titulo: str = Form(...),
    archivo: UploadFile = File(...),
    usuario: dict = Depends(require_role("transcriptor")),
    conexion: Connection = Depends(connection),
):
    contenido = archivo.file.read()
    return doc_service.subir_documento(
        conexion, usuario, titulo, contenido, archivo.filename or "documento.pdf"
    )


@router.post("/transform/plain-text", response_model=VersionOut, status_code=201)
def transform_plain_text(
    body: TransformPlainTextIn,
    usuario: dict = Depends(require_role("transcriptor", "revisor")),
    conexion: Connection = Depends(connection),
):
    return doc_service.transformar_texto_plano(
        conexion, usuario, body.titulo, body.texto, body.documento_id
    )


@router.post("/transform/build", response_model=VersionOut, status_code=201)
def transform_build(
    body: TransformBuildIn,
    usuario: dict = Depends(require_role("transcriptor", "revisor")),
    conexion: Connection = Depends(connection),
):
    return doc_service.construir_version(conexion, usuario, body.documento_id, body.texto)


@router.get("/documents", response_model=PaginatedOut[DocumentOut])
def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    usuario: dict = Depends(require_role("transcriptor", "revisor")),
    conexion: Connection = Depends(connection),
):
    return doc_service.listar_documentos(conexion, page, limit)


@router.get("/documents/{documento_id}", response_model=DocumentOut)
def get_document(
    documento_id: UUID,
    usuario: dict = Depends(require_role("transcriptor", "revisor")),
    conexion: Connection = Depends(connection),
):
    return doc_service.obtener_documento(conexion, documento_id)


@router.get("/documents/{documento_id}/pages", response_model=list[PageOut])
def get_document_pages(
    documento_id: UUID,
    usuario: dict = Depends(require_role("transcriptor", "revisor")),
    conexion: Connection = Depends(connection),
):
    return doc_service.listar_paginas(conexion, documento_id)


@router.get("/documents/{documento_id}/original")
def get_document_original(
    documento_id: UUID,
    usuario: dict = Depends(require_role("transcriptor", "revisor")),
    conexion: Connection = Depends(connection),
):
    contenido = doc_service.obtener_original(conexion, usuario, documento_id)
    return Response(content=contenido, media_type="application/pdf")


@router.delete("/documents/{documento_id}", status_code=204)
def delete_document(
    documento_id: UUID,
    usuario: dict = Depends(require_role("transcriptor", "admin")),
    conexion: Connection = Depends(connection),
):
    doc_service.eliminar_documento(conexion, usuario, documento_id)
    return Response(status_code=204)


@router.get("/documents/{documento_id}/versions", response_model=list[VersionOut])
def list_versions(
    documento_id: UUID,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return doc_service.listar_versiones(conexion, documento_id)


@router.get("/documents/{documento_id}/versions/{numero_version}", response_model=VersionOut)
def get_version(
    documento_id: UUID,
    numero_version: int,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return doc_service.obtener_version(conexion, documento_id, numero_version)


@router.get(
    "/documents/{documento_id}/versions/{numero_version}/blocks",
    response_model=list[BlockOut],
)
def get_version_blocks(
    documento_id: UUID,
    numero_version: int,
    usuario: dict = Depends(require_role("revisor")),
    conexion: Connection = Depends(connection),
):
    return doc_service.listar_bloques(conexion, documento_id, numero_version)
