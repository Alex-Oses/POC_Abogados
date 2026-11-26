from psycopg import Connection

from app.db.queries import SQL
from app.services.audit import registrar_evento


def listar_auditoria(conexion: Connection, page: int, limit: int) -> dict:
    offset = (page - 1) * limit
    items = conexion.execute(SQL["listar_auditoria"], {"limit": limit, "offset": offset}).fetchall()
    total = conexion.execute(SQL["contar_auditoria"]).fetchone()["total"]
    return {"items": items, "page": page, "limit": limit, "total": total}


def listar_configuracion(conexion: Connection) -> list[dict]:
    return conexion.execute(SQL["listar_configuracion"]).fetchall()


def actualizar_configuracion(
    conexion: Connection, usuario: dict, clave: str, valor: str, descripcion: str | None
) -> dict:
    cfg = conexion.execute(
        SQL["upsert_configuracion"],
        {"clave": clave, "valor": valor, "descripcion": descripcion},
    ).fetchone()
    registrar_evento(conexion, usuario["id"], "config_actualizada", "configuracion_sistema", clave)
    return cfg
