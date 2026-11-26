from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.api.deps import connection, require_role
from app.db.queries import SQL

router = APIRouter(tags=["catálogo, auditoría e informes"])
# Lectura del catálogo abierta a todos los roles: el panel de anonimización la necesita.
TODOS = require_role("transcriptor", "revisor", "admin")


@router.get("/categories")
def categorias(activa: bool | None = None, _u: dict = Depends(TODOS),
               conexion: Connection = Depends(connection)):
    return {"items": conexion.execute(SQL["categorias_listar"], {"activa": activa}).fetchall()}


@router.get("/rules")
def reglas(activa: bool | None = None, _u: dict = Depends(TODOS),
           conexion: Connection = Depends(connection)):
    return {"items": conexion.execute(SQL["reglas_listar"], {"activa": activa}).fetchall()}


@router.get("/audit")
def auditoria(entidad_tipo: str | None = None, entidad_id: UUID | None = None,
              usuario_id: UUID | None = None, desde: datetime | None = None,
              hasta: datetime | None = None, page: int = Query(1, ge=1),
              limit: int = Query(50, ge=1, le=200),
              _u: dict = Depends(require_role("revisor", "admin")),
              conexion: Connection = Depends(connection)):
    filas = conexion.execute(SQL["auditoria_listar"], {
        "entidad_tipo": entidad_tipo, "entidad_id": entidad_id, "usuario_id": usuario_id,
        "desde": desde, "hasta": hasta, "limit": limit, "offset": (page - 1) * limit}).fetchall()
    total = filas[0]["total"] if filas else 0
    for fila in filas:
        fila.pop("total")
    return {"items": filas, "page": page, "limit": limit, "total": total}


@router.get("/reports/summary")
def informe(_u: dict = Depends(require_role("revisor", "admin")),
            conexion: Connection = Depends(connection)):
    return conexion.execute(SQL["informe_resumen"]).fetchone()
