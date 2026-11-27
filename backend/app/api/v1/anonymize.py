"""Anonimización y anotaciones (0004, 0006): el router solo valida y delega."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from psycopg import Connection
from pydantic import BaseModel, Field

from app.api.deps import connection, require_role
from app.db.queries import SQL
from app.services import anonymize
from app.services import documents as service

router = APIRouter(tags=["documentos"])
TR = require_role("transcriptor", "revisor")
R = require_role("revisor")
Modo = Literal["censurar", "borrar", "tachar", "etiqueta", "seudonimo", "iniciales"]


class AnonimizarIn(BaseModel):
    regla_id: UUID | None = None
    modo: Modo = "censurar"  # por defecto de V15 (rgpd-considerations.md)


class AnotacionIn(BaseModel):
    accion_aplicada: Literal["censurar", "etiqueta", "iniciales", "pseudonimizado", "eliminado",
                             "mantenido", "tachado"] | None = None
    texto_sustitucion: str | None = Field(default=None, max_length=500)
    decision_revisor: Literal["confirmado", "modificado", "falso_positivo", "falso_negativo"]
    observaciones_revisor: str | None = Field(default=None, max_length=2000)


class AnotacionNuevaIn(BaseModel):
    bloque_id: UUID
    categoria_id: UUID
    inicio_offset: int = Field(ge=0)
    fin_offset: int = Field(gt=0)
    accion_aplicada: Literal["censurar", "etiqueta", "iniciales", "pseudonimizado", "eliminado",
                             "tachado"] | None = None
    texto_sustitucion: str | None = Field(default=None, max_length=500)


@router.post("/documents/{documento_id}/anonymize", status_code=201)
def anonimizar(documento_id: UUID, datos: AnonimizarIn, request: Request,
               usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, documento_id, usuario)
    return anonymize.anonimizar(conexion, doc, datos.regla_id, datos.modo, usuario, request)


@router.get("/documents/{documento_id}/annotations")
def anotaciones(documento_id: UUID, version: UUID | None = None, categoria: UUID | None = None,
                pendientes: bool = False, usuario: dict = Depends(R),
                conexion: Connection = Depends(connection)):
    service.obtener(conexion, documento_id, usuario)
    return {"items": conexion.execute(SQL["anotaciones_listar"], {
        "documento_id": documento_id, "version_id": version, "categoria_id": categoria,
        "pendientes": pendientes}).fetchall()}


@router.post("/documents/{documento_id}/annotations", status_code=201)
def anotacion_nueva(documento_id: UUID, datos: AnotacionNuevaIn, request: Request,
                    usuario: dict = Depends(R), conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, documento_id, usuario)
    return anonymize.crear_manual(conexion, doc, datos.model_dump(), usuario, request)


@router.patch("/annotations/{anotacion_id}")
def decidir(anotacion_id: UUID, datos: AnotacionIn, request: Request, usuario: dict = Depends(R),
            conexion: Connection = Depends(connection)):
    return anonymize.decidir(conexion, anotacion_id, datos.model_dump(exclude_unset=True),
                             usuario, request)
