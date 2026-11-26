from datetime import timedelta

from psycopg import Connection

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    ahora,
    hash_password,
    hash_token,
    nuevo_token,
    verify_password,
)
from app.db.queries import SQL
from app.services import audit


def login(conexion: Connection, email: str, password: str, request) -> dict:
    fila = conexion.execute(SQL["usuario_por_email"], {"email": email}).fetchone()
    # 401 genérico: no distingue email inexistente de contraseña incorrecta.
    if not fila or not verify_password(password, fila["password_hash"]):
        raise AppError("CREDENCIALES_INVALIDAS", "Email o contraseña incorrectos", 401)
    if fila["estado"] != "activo":
        raise AppError("CUENTA_NO_ACTIVA", "La cuenta no está activa", 403)

    token = nuevo_token()
    instante = ahora()
    conexion.execute(
        SQL["desalojar_sesiones"],
        {"usuario_id": fila["id"], "conservar": max(settings.sesiones_max - 1, 0)},
    )
    fila_sesion = conexion.execute(
        SQL["crear_sesion"],
        {
            "usuario_id": fila["id"],
            "token_hash": hash_token(token),
            "expira_en": instante + timedelta(hours=settings.session_horas),
            "ip": audit.ip_valida(request.client.host) if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    ).fetchone()
    audit.registrar(
        conexion,
        "SESION_INICIADA",
        request=request,
        usuario_id=fila["id"],
        entidad_tipo="sesion",
        entidad_id=fila_sesion["id"],
        detalle={"medio": "local"},
    )
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": settings.session_horas * 3600,
    }


def logout(conexion: Connection, usuario: dict, request) -> None:
    conexion.execute(SQL["revocar_sesion"], {"id": usuario["sesion_id"]})
    audit.registrar(
        conexion,
        "SESION_CERRADA",
        request=request,
        usuario_id=usuario["usuario_id"],
        entidad_tipo="sesion",
        entidad_id=usuario["sesion_id"],
        detalle={},
    )


def cambiar_password(
    conexion: Connection, usuario: dict, password_actual: str, password_nueva: str, request
) -> None:
    fila = conexion.execute(
        SQL["password_hash_por_id"], {"id": usuario["usuario_id"]}
    ).fetchone()
    if not fila or not verify_password(password_actual, fila["password_hash"]):
        raise AppError("CREDENCIALES_INVALIDAS", "La contraseña actual no coincide", 401)
    if password_actual == password_nueva:
        raise AppError("VALIDACION", "La contraseña nueva debe ser distinta", 400)

    conexion.execute(
        SQL["actualizar_password"],
        {"id": usuario["usuario_id"], "password_hash": hash_password(password_nueva)},
    )
    conexion.execute(SQL["revocar_sesiones_usuario"], {"usuario_id": usuario["usuario_id"]})
    audit.registrar(
        conexion,
        "PASSWORD_CAMBIADA",
        request=request,
        usuario_id=usuario["usuario_id"],
        entidad_tipo="usuario",
        entidad_id=usuario["usuario_id"],
        detalle={"sesiones_revocadas": True},
    )
