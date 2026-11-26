from uuid import UUID

from psycopg import Connection

from app.core.errors import AppError
from app.db.queries import SQL
from app.services.audit import registrar_evento
from app.services.documents import obtener_documento, obtener_version
from app.services.presidio import detectar_entidades_presidio


def anonimizar_documento(
    conexion: Connection, usuario: dict, documento_id: UUID, numero_version: int | None
) -> list[dict]:
    obtener_documento(conexion, documento_id)
    if numero_version is not None:
        version = obtener_version(conexion, documento_id, numero_version)
    else:
        version = conexion.execute(
            SQL["obtener_version_actual"], {"documento_id": documento_id}
        ).fetchone()
        if not version:
            raise AppError("VERSION_NOT_FOUND", "No existe versión actual del documento", 404)

    bloques = conexion.execute(SQL["listar_bloques_version"], {"version_id": version["id"]}).fetchall()
    creadas: list[dict] = []
    for bloque in bloques:
        entidades = detectar_entidades_presidio(bloque["texto"])
        for ent in entidades:
            anot = conexion.execute(
                SQL["insertar_anotacion"],
                {
                    "version_id": version["id"],
                    "bloque_id": bloque["id"],
                    "categoria_id": ent.get("categoria_id"),
                    "inicio": ent["inicio"],
                    "fin": ent["fin"],
                    "texto_original": ent["texto_original"],
                    "texto_sustitucion": ent.get("texto_sustitucion", "[ANONIMIZADO]"),
                    "estado": "pendiente",
                },
            ).fetchone()
            creadas.append(anot)
    registrar_evento(
        conexion, usuario["id"], "documento_anonimizado", "versiones_documento", str(version["id"])
    )
    return creadas


def listar_anotaciones(conexion: Connection, documento_id: UUID) -> list[dict]:
    obtener_documento(conexion, documento_id)
    version = conexion.execute(
        SQL["obtener_version_actual"], {"documento_id": documento_id}
    ).fetchone()
    if not version:
        return []
    return conexion.execute(SQL["listar_anotaciones_version"], {"version_id": version["id"]}).fetchall()


def actualizar_anotacion(
    conexion: Connection,
    usuario: dict,
    anotacion_id: UUID,
    estado: str,
    texto_sustitucion: str | None,
) -> dict:
    anot = conexion.execute(
        SQL["actualizar_anotacion"],
        {"id": anotacion_id, "estado": estado, "texto_sustitucion": texto_sustitucion},
    ).fetchone()
    if not anot:
        raise AppError("ANNOTATION_NOT_FOUND", "Anotación no encontrada", 404)
    registrar_evento(
        conexion, usuario["id"], "anotacion_actualizada", "anotaciones_entidad", str(anotacion_id)
    )
    return anot
