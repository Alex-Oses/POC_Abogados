from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from psycopg import Connection
from pydantic import BaseModel, Field

from app.api.deps import connection, require_role
from app.db.queries import SQL
from app.services import documents
from app.services import reviews as service

router = APIRouter(tags=["revisión"])
R = require_role("revisor")


class CierreIn(BaseModel):
    estado: Literal["aprobado", "rechazado_con_cambios", "devuelto"]
    comentario_general: str | None = Field(default=None, max_length=5000)


class ReabrirIn(BaseModel):
    comentario: str | None = Field(default=None, max_length=5000)
    modo: Literal["censurar", "borrar", "tachar", "etiqueta", "seudonimo", "iniciales"] = "censurar"


class AsignarIn(BaseModel):
    asignado_a: UUID | None = None
    comentario: str | None = Field(default=None, max_length=5000)


class VistoBuenoIn(BaseModel):
    comentario: str | None = Field(default=None, max_length=5000)


@router.get("/reviews")
def listar(estado: str | None = None, asignado_a: str | None = None,
           page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
           usuario: dict = Depends(R), conexion: Connection = Depends(connection)):
    asignado = usuario["usuario_id"] if asignado_a == "me" else asignado_a
    filas = conexion.execute(SQL["revisiones_listar"], {
        "estado": estado, "asignado_a": asignado, "limit": limit,
        "offset": (page - 1) * limit}).fetchall()
    total = filas[0]["total"] if filas else 0
    for fila in filas:
        fila.pop("total")
    return {"items": filas, "page": page, "limit": limit, "total": total}


@router.post("/documents/{documento_id}/reviews", status_code=201)
def abrir(documento_id: UUID, request: Request, usuario: dict = Depends(R),
          conexion: Connection = Depends(connection)):
    doc = documents.obtener(conexion, documento_id, usuario)
    return service.abrir(conexion, doc, usuario, request)


@router.post("/reviews/{revision_id}/claim")
def tomar(revision_id: UUID, request: Request, usuario: dict = Depends(R),
          conexion: Connection = Depends(connection)):
    return service.tomar(conexion, revision_id, usuario, request)


@router.patch("/reviews/{revision_id}/assign")
def asignar(revision_id: UUID, datos: AsignarIn, request: Request, usuario: dict = Depends(R),
            conexion: Connection = Depends(connection)):
    return service.asignar(conexion, revision_id, datos.asignado_a, datos.comentario,
                           usuario, request)


@router.post("/documents/{documento_id}/sign-off")
def visto_bueno(documento_id: UUID, datos: VistoBuenoIn, request: Request,
                usuario: dict = Depends(R), conexion: Connection = Depends(connection)):
    doc = documents.obtener(conexion, documento_id, usuario)
    return service.visto_bueno(conexion, doc, datos.comentario, usuario, request)


@router.patch("/reviews/{revision_id}")
def cerrar(revision_id: UUID, datos: CierreIn, request: Request,
           if_match: str | None = Header(default=None), usuario: dict = Depends(R),
           conexion: Connection = Depends(connection)):
    return service.cerrar(conexion, revision_id, datos.estado, datos.comentario_general,
                          if_match, usuario, request)


@router.post("/documents/{documento_id}/reopen", status_code=201)
def reabrir(documento_id: UUID, datos: ReabrirIn, request: Request, usuario: dict = Depends(R),
            conexion: Connection = Depends(connection)):
    doc = documents.obtener(conexion, documento_id, usuario)
    return service.reabrir(conexion, doc, datos.comentario, datos.modo, usuario, request)

