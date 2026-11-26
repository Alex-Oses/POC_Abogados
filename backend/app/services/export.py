from uuid import UUID

from psycopg import Connection

from app.core.errors import AppError
from app.db.queries import SQL
from app.integrations.pdf import aplicar_sustituciones_bloque, generar_pdf_bytes
from app.integrations.storage import guardar_pdf_exportado
from app.services.audit import registrar_evento
from app.services.documents import obtener_documento, obtener_version


def exportar_documento(
    conexion: Connection,
    usuario: dict,
    documento_id: UUID,
    numero_version: int | None,
    modo: str,
) -> tuple[bytes, dict]:
    doc = obtener_documento(conexion, documento_id)
    if doc["creado_por"] != usuario["id"] and "revisor" not in usuario["roles"]:
        raise AppError("FORBIDDEN", "No tienes permiso para exportar este documento", 403)

    if numero_version is not None:
        version = obtener_version(conexion, documento_id, numero_version)
    else:
        version = conexion.execute(
            SQL["obtener_version_actual"], {"documento_id": documento_id}
        ).fetchone()
        if not version:
            raise AppError("VERSION_NOT_FOUND", "No existe versión actual", 404)

    bloques = conexion.execute(SQL["listar_bloques_version"], {"version_id": version["id"]}).fetchall()
    anotaciones = conexion.execute(
        SQL["listar_anotaciones_version"], {"version_id": version["id"]}
    ).fetchall()
    por_bloque: dict[UUID, list[dict]] = {}
    for a in anotaciones:
        por_bloque.setdefault(a["bloque_id"], []).append(a)

    bloques_finales = []
    for b in bloques:
        copia = dict(b)
        copia["texto_final"] = aplicar_sustituciones_bloque(b["texto"], por_bloque.get(b["id"], []))
        bloques_finales.append(copia)

    pdf_bytes = generar_pdf_bytes(bloques_finales, modo=modo)
    ruta, digest = guardar_pdf_exportado(str(documento_id), version["numero_version"], pdf_bytes)
    conexion.execute(SQL["marcar_documento_exportado"], {"id": documento_id})
    registrar_evento(
        conexion,
        usuario["id"],
        "documento_exportado",
        "documentos",
        str(documento_id),
        {"hash_export": digest, "numero_version": version["numero_version"]},
    )
    meta = {
        "documento_id": documento_id,
        "numero_version": version["numero_version"],
        "hash_export": digest,
        "ruta_pdf": str(ruta),
    }
    return pdf_bytes, meta
