from uuid import UUID

from psycopg import Connection

from app.core.errors import AppError
from app.db.queries import SQL
from app.services.audit import registrar_evento
from app.services.documents import obtener_documento


def listar_revisiones(conexion: Connection, page: int, limit: int) -> dict:
    offset = (page - 1) * limit
    items = conexion.execute(SQL["listar_revisiones"], {"limit": limit, "offset": offset}).fetchall()
    total = conexion.execute(SQL["contar_revisiones"]).fetchone()["total"]
    return {"items": items, "page": page, "limit": limit, "total": total}


def crear_revision(conexion: Connection, usuario: dict, documento_id: UUID, revisor_id: UUID | None) -> dict:
    obtener_documento(conexion, documento_id)
    estado = "en_curso" if revisor_id else "pendiente"
    rev = conexion.execute(
        SQL["crear_revision"],
        {"documento_id": documento_id, "revisor_id": revisor_id, "estado": estado},
    ).fetchone()
    conexion.execute(
        SQL["actualizar_estado_documento"],
        {"id": documento_id, "estado": "en_revision"},
    )
    registrar_evento(conexion, usuario["id"], "revision_creada", "revisiones", str(rev["id"]))
    return rev


def reclamar_revision(conexion: Connection, usuario: dict, revision_id: UUID) -> dict:
    rev = conexion.execute(
        SQL["reclamar_revision"],
        {"id": revision_id, "revisor_id": usuario["id"]},
    ).fetchone()
    if not rev:
        raise AppError("REVIEW_CONFLICT", "La revisión no está disponible para reclamar", 409)
    registrar_evento(conexion, usuario["id"], "revision_reclamada", "revisiones", str(revision_id))
    return rev


def asignar_revision(conexion: Connection, usuario: dict, revision_id: UUID, revisor_id: UUID) -> dict:
    rev = conexion.execute(
        SQL["asignar_revision"],
        {"id": revision_id, "revisor_id": revisor_id},
    ).fetchone()
    if not rev:
        raise AppError("REVIEW_NOT_FOUND", "Revisión no encontrada", 404)
    registrar_evento(conexion, usuario["id"], "revision_asignada", "revisiones", str(revision_id))
    return rev


def cerrar_revision(
    conexion: Connection,
    usuario: dict,
    revision_id: UUID,
    estado: str,
    motivo: str | None,
    if_match: str | None,
) -> dict:
    actual = conexion.execute(SQL["obtener_revision"], {"id": revision_id}).fetchone()
    if not actual:
        raise AppError("REVIEW_NOT_FOUND", "Revisión no encontrada", 404)
    if if_match and if_match.strip('"') != actual["actualizado_en"].isoformat():
        raise AppError("CONFLICT", "La revisión fue modificada por otro usuario", 409)
    if estado == "rechazada" and not (motivo and motivo.strip()):
        raise AppError("REASON_REQUIRED", "El motivo es obligatorio al rechazar", 422)

    version = conexion.execute(
        SQL["obtener_version_actual"], {"documento_id": actual["documento_id"]}
    ).fetchone()
    if estado == "aprobada" and version:
        pendientes = conexion.execute(
            SQL["contar_anotaciones_pendientes"], {"version_id": version["id"]}
        ).fetchone()["total"]
        if pendientes > 0:
            raise AppError(
                "PENDING_ANNOTATIONS",
                "Quedan anotaciones pendientes de revisar",
                422,
            )

    rev = conexion.execute(
        SQL["cerrar_revision"],
        {"id": revision_id, "estado": estado, "motivo": motivo},
    ).fetchone()
    nuevo_doc_estado = "aprobado" if estado == "aprobada" else "rechazado"
    conexion.execute(
        SQL["actualizar_estado_documento"],
        {"id": actual["documento_id"], "estado": nuevo_doc_estado},
    )
    registrar_evento(conexion, usuario["id"], f"revision_{estado}", "revisiones", str(revision_id))
    return rev


def reabrir_documento(conexion: Connection, usuario: dict, documento_id: UUID, motivo: str) -> dict:
    doc = obtener_documento(conexion, documento_id)
    if doc["estado"] not in {"aprobado", "rechazado"}:
        raise AppError("INVALID_STATE", "Solo se pueden reabrir documentos aprobados o rechazados", 422)
    actualizado = conexion.execute(
        SQL["actualizar_estado_documento"],
        {"id": documento_id, "estado": "en_revision"},
    ).fetchone()
    registrar_evento(
        conexion,
        usuario["id"],
        "documento_reabierto",
        "documentos",
        str(documento_id),
        {"motivo": motivo},
    )
    return actualizado


def firmar_documento(conexion: Connection, usuario: dict, documento_id: UUID) -> dict:
    doc = obtener_documento(conexion, documento_id)
    if doc["estado"] != "aprobado":
        raise AppError("INVALID_STATE", "El documento debe estar aprobado para firmarlo", 422)
    registrar_evento(conexion, usuario["id"], "documento_firmado", "documentos", str(documento_id))
    return doc
