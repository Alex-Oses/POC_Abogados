from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.api.deps import connection, require_role
from app.schemas.admin import AuditOut, ConfigOut, ConfigPutIn
from app.schemas.common import PaginatedOut
from app.services import admin as admin_service

router = APIRouter(tags=["administración"])


@router.get("/audit", response_model=PaginatedOut[AuditOut])
def list_audit(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    usuario: dict = Depends(require_role("revisor", "admin")),
    conexion: Connection = Depends(connection),
):
    return admin_service.listar_auditoria(conexion, page, limit)


@router.get("/config", response_model=list[ConfigOut])
def list_config(
    usuario: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    return admin_service.listar_configuracion(conexion)


@router.put("/config/{clave}", response_model=ConfigOut)
def put_config(
    clave: str,
    body: ConfigPutIn,
    usuario: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    return admin_service.actualizar_configuracion(
        conexion, usuario, clave, body.valor, body.descripcion
    )
