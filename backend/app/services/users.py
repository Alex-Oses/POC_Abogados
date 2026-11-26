from psycopg import Connection

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import ahora, hash_password
from app.db.queries import SQL
from app.services import audit


def sembrar_admin(conexion: Connection) -> None:
    """U-06/U-21: admin de desarrollo desde entorno, nunca por endpoint.

    Lleva los tres roles para poder recorrer el flujo completo sin SSO. El
    arranque vuelve a dejarlo activo y con todos los roles.
    """
    if not settings.admin_email or not settings.admin_password:
        return
    fila = conexion.execute(
        SQL["sembrar_admin"],
        {
            "email": settings.admin_email,
            "nombre": "Admin de desarrollo",
            "password_hash": hash_password(settings.admin_password),
        },
    ).fetchone()
    for rol in ("transcriptor", "revisor", "admin"):
        conexion.execute(SQL["agregar_rol"], {"id": fila["id"], "rol": rol})


def listar(
    conexion: Connection,
    *,
    estado: str | None,
    rol: str | None,
    page: int,
    limit: int,
) -> tuple[list[dict], int]:
    filas = conexion.execute(
        SQL["listar_usuarios"],
        {
            "estado": estado,
            "rol": rol,
            "limit": limit,
            "offset": (page - 1) * limit,
        },
    ).fetchall()
    total = filas[0]["total"] if filas else 0
    for fila in filas:
        fila.pop("total", None)
        fila["roles"] = list(fila["roles"] or [])
    return filas, total


def _por_id(conexion: Connection, usuario_id) -> dict:
    fila = conexion.execute(SQL["usuario_por_id"], {"id": usuario_id}).fetchone()
    if not fila:
        raise AppError("USUARIO_NO_ENCONTRADO", "El usuario no existe", 404)
    fila["roles"] = list(fila["roles"] or [])
    return fila


def actualizar(
    conexion: Connection, usuario_id, cambios: dict, admin: dict, request
) -> dict:
    antes = _por_id(conexion, usuario_id)

    if "estado" in cambios:
        estado = cambios["estado"]
        if estado == "baja":
            motivo = (cambios.get("motivo_baja") or "").strip()
            if not motivo:
                raise AppError("MOTIVO_REQUERIDO", "Dar de baja exige motivo_baja", 422)
            eliminado_en = ahora()
        else:
            motivo = None
            eliminado_en = None
    else:
        estado = antes["estado"]
        motivo = antes["motivo_baja"]
        eliminado_en = antes["eliminado_en"]

    roles = cambios.get("roles")
    if roles is not None:
        roles = sorted(set(roles))

    conexion.execute(
        SQL["actualizar_usuario"],
        {
            "id": usuario_id,
            "estado": estado,
            "motivo_baja": motivo,
            "eliminado_en": eliminado_en,
        },
    )
    if roles is not None:
        conexion.execute(SQL["borrar_roles"], {"id": usuario_id})
        for rol in roles:
            conexion.execute(SQL["agregar_rol"], {"id": usuario_id, "rol": rol})

    revocar = estado != "activo" or (roles is not None and roles != antes["roles"])
    if revocar:
        conexion.execute(SQL["revocar_sesiones_usuario"], {"usuario_id": usuario_id})

    despues = _por_id(conexion, usuario_id)
    audit.registrar(
        conexion,
        "USUARIO_ACTUALIZADO",
        request=request,
        usuario_id=admin["usuario_id"],
        entidad_tipo="usuario",
        entidad_id=usuario_id,
        detalle={
            "antes": {"estado": antes["estado"], "roles": antes["roles"]},
            "despues": {"estado": despues["estado"], "roles": despues["roles"]},
            "sesiones_revocadas": revocar,
        },
    )
    return despues


def revocar_sesiones(conexion: Connection, usuario_id, admin: dict, request) -> None:
    _por_id(conexion, usuario_id)
    conexion.execute(SQL["revocar_sesiones_usuario"], {"usuario_id": usuario_id})
    audit.registrar(
        conexion,
        "SESIONES_REVOCADAS",
        request=request,
        usuario_id=admin["usuario_id"],
        entidad_tipo="usuario",
        entidad_id=usuario_id,
        detalle={"forzado_por_admin": True},
    )
