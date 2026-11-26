import ipaddress
import json

from psycopg import Connection

from app.db.queries import SQL


def ip_valida(valor: str | None) -> str | None:
    try:
        return str(ipaddress.ip_address(valor))
    except (TypeError, ValueError):
        return None


def registrar(
    conexion: Connection,
    evento: str,
    *,
    request=None,
    usuario_id=None,
    entidad_tipo: str | None = None,
    entidad_id=None,
    detalle: dict | None = None,
) -> None:
    ip = ip_valida(request.client.host) if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    # Serializa la cadena: dos inserciones a la vez no pueden leer el mismo "anterior".
    conexion.execute("SELECT pg_advisory_xact_lock(20261127)")
    conexion.execute(
        SQL["insertar"],
        {
            "evento": evento,
            "entidad_tipo": entidad_tipo,
            "entidad_id": entidad_id,
            "usuario_id": usuario_id,
            "ip": ip,
            "user_agent": user_agent,
            "detalle": json.dumps(detalle or {}, ensure_ascii=False),
        },
    )


def registrar_evento(
    conexion: Connection,
    usuario_id,
    evento: str,
    entidad_tipo: str | None = None,
    entidad_id=None,
    detalle: dict | None = None,
) -> None:
    registrar(
        conexion,
        evento,
        usuario_id=usuario_id,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        detalle=detalle,
    )
