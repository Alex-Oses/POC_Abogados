from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from psycopg import Connection

from app.api.deps import connection, require_role
from app.schemas.users import Estado, Rol, UserListOut, UserOut, UserPatchIn
from app.services import users as service

router = APIRouter(prefix="/admin/users", tags=["administración"])


@router.get("", response_model=UserListOut)
def listar(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    estado: Estado | None = None,
    roles: Rol | None = None,
    _admin: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    items, total = service.listar(
        conexion, estado=estado, rol=roles, page=page, limit=limit
    )
    return {"items": items, "page": page, "limit": limit, "total": total}


@router.patch("/{usuario_id}", response_model=UserOut)
def actualizar(
    usuario_id: UUID,
    cambios: UserPatchIn,
    request: Request,
    admin: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    return service.actualizar(
        conexion,
        usuario_id,
        cambios.model_dump(exclude_unset=True),
        admin,
        request,
    )


@router.delete("/{usuario_id}/sessions", status_code=204)
def revocar_sesiones(
    usuario_id: UUID,
    request: Request,
    admin: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
) -> None:
    service.revocar_sesiones(conexion, usuario_id, admin, request)
