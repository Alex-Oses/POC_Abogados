from fastapi import Depends, Request
from psycopg import Connection

from app.core.errors import AppError
from app.core.security import ahora, expira_sesion, hash_token
from app.db.pool import tx
from app.db.queries import SQL


def connection(request: Request):
    if not getattr(request.app.state, "bd_disponible", False):
        raise AppError("BD_NO_DISPONIBLE", "La base de datos no está disponible", 503)
    with tx() as conexion:
        yield conexion


def require_token(request: Request) -> str:
    token = getattr(request.state, "token", None)
    if not token:
        raise AppError("SESSION_NOT_FOUND", "La sesión no existe o ha caducado", 401)
    return token


def current_user(
    token: str = Depends(require_token),
    conexion: Connection = Depends(connection),
) -> dict:
    fila = conexion.execute(
        SQL["sesion_por_token"], {"token_hash": hash_token(token)}
    ).fetchone()
    instante = ahora()
    if not fila or fila["expira_en"] <= instante or fila["estado"] != "activo":
        raise AppError("SESSION_NOT_FOUND", "La sesión no existe o ha caducado", 401)

    nueva_expira = expira_sesion(fila["creado_en"], instante)
    if nueva_expira <= instante:
        raise AppError("SESSION_NOT_FOUND", "La sesión no existe o ha caducado", 401)
    conexion.execute(
        SQL["tocar_sesion"], {"id": fila["sesion_id"], "expira_en": nueva_expira}
    )
    # shortcut: una escritura por petición para renovar la sesión; agrupar si el volumen lo pide.
    fila["roles"] = list(fila["roles"] or [])
    return fila


def require_role(*permitidos: str):
    def comprobar(usuario: dict = Depends(current_user)) -> dict:
        if not set(permitidos) & set(usuario["roles"]):
            raise AppError("FORBIDDEN", "No tienes permiso para esta acción", 403)
        return usuario

    return comprobar
