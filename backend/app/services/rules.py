from uuid import UUID

from psycopg import Connection

from app.core.errors import AppError
from app.db.queries import SQL
from app.services.audit import registrar_evento


def listar_reglas(conexion: Connection, page: int, limit: int) -> dict:
    offset = (page - 1) * limit
    items = conexion.execute(SQL["listar_reglas"], {"limit": limit, "offset": offset}).fetchall()
    total = conexion.execute(SQL["contar_reglas"]).fetchone()["total"]
    return {"items": items, "page": page, "limit": limit, "total": total}


def crear_regla(conexion: Connection, usuario: dict, datos: dict) -> dict:
    regla = conexion.execute(SQL["crear_regla"], datos).fetchone()
    registrar_evento(conexion, usuario["id"], "regla_creada", "reglas_anonimizacion", str(regla["id"]))
    return regla


def actualizar_regla(conexion: Connection, usuario: dict, regla_id: UUID, datos: dict) -> dict:
    datos["id"] = regla_id
    regla = conexion.execute(SQL["actualizar_regla"], datos).fetchone()
    if not regla:
        raise AppError("RULE_NOT_FOUND", "Regla no encontrada", 404)
    registrar_evento(conexion, usuario["id"], "regla_actualizada", "reglas_anonimizacion", str(regla_id))
    return regla


def listar_categorias(conexion: Connection, page: int, limit: int) -> dict:
    offset = (page - 1) * limit
    items = conexion.execute(SQL["listar_categorias"], {"limit": limit, "offset": offset}).fetchall()
    total = conexion.execute(SQL["contar_categorias"]).fetchone()["total"]
    return {"items": items, "page": page, "limit": limit, "total": total}


def crear_categoria(conexion: Connection, usuario: dict, datos: dict) -> dict:
    cat = conexion.execute(SQL["crear_categoria"], datos).fetchone()
    registrar_evento(
        conexion, usuario["id"], "categoria_creada", "categorias_sensibles", str(cat["id"])
    )
    return cat


def actualizar_categoria(conexion: Connection, usuario: dict, categoria_id: UUID, datos: dict) -> dict:
    datos["id"] = categoria_id
    cat = conexion.execute(SQL["actualizar_categoria"], datos).fetchone()
    if not cat:
        raise AppError("CATEGORY_NOT_FOUND", "Categoría no encontrada", 404)
    registrar_evento(
        conexion, usuario["id"], "categoria_actualizada", "categorias_sensibles", str(categoria_id)
    )
    return cat
