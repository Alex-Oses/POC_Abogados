from datetime import datetime

from psycopg import Connection

from app.core.errors import AppError
from app.db.queries import SQL
from app.services import audit
from app.services.anonymize import anonimizar
from app.services.documents import nueva_version


def abrir(conexion: Connection, doc: dict, usuario: dict, request) -> dict:
    if doc["estado"] != "en_revision" or doc["v_tipo"] != "anonimizado_ia":
        raise AppError("ESTADO_INVALIDO", "El documento no está anonimizado", 409)
    if conexion.execute(SQL["revision_abierta_doc"], {"documento_id": doc["id"]}).fetchone():
        raise AppError("REVISION_ABIERTA", "Ya hay una revisión abierta", 409)
    fila = conexion.execute(SQL["revision_abrir"],
                            {"version_id": doc["v_id"], "documento_id": doc["id"]}).fetchone()
    audit.registrar(conexion, "REVISION_ABIERTA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="revision", entidad_id=fila["id"],
                    detalle={"documento_id": str(doc["id"]), "intento": fila["numero_intento"]})
    return fila


def tomar(conexion: Connection, revision_id, usuario: dict, request) -> dict:
    fila = conexion.execute(SQL["revision_tomar"],
                            {"id": revision_id, "usuario_id": usuario["usuario_id"]}).fetchone()
    if not fila:
        raise AppError("REVISION_NO_DISPONIBLE", "La revisión no está en cola", 409)
    audit.registrar(conexion, "REVISION_TOMADA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="revision", entidad_id=revision_id, detalle={})
    return fila


def asignar(conexion: Connection, revision_id, asignado_a, comentario: str | None,
            usuario: dict, request) -> dict:
    """Contrato §6: asigna o reasigna; `asignado_a` nulo la devuelve a la cola."""
    rev = conexion.execute(SQL["revision_por_id"], {"id": revision_id}).fetchone()
    if not rev:
        raise AppError("REVISION_NO_ENCONTRADA", "La revisión no existe", 404)
    if rev["estado"] not in ("en_cola", "en_proceso"):
        raise AppError("REVISION_CERRADA", "La revisión ya está cerrada", 409)
    if rev["estado"] == "en_proceso" and not (comentario or "").strip():
        raise AppError("COMENTARIO_REQUERIDO", "Reasignar una revisión en proceso exige comentario",
                       422)
    if asignado_a and not conexion.execute(SQL["revisor_activo"], {"id": asignado_a}).fetchone():
        raise AppError("REVISOR_NO_ENCONTRADO", "No hay un revisor activo con ese id", 404)
    fila = conexion.execute(SQL["revision_asignar"],
                            {"id": revision_id, "asignado_a": asignado_a}).fetchone()
    if not fila:
        raise AppError("CONFLICTO_REVISION", "La revisión cambió; recarga", 409)
    audit.registrar(conexion, "REVISION_ASIGNADA", request=request,
                    usuario_id=usuario["usuario_id"], entidad_tipo="revision",
                    entidad_id=revision_id,
                    detalle={"asignado_a": None if asignado_a is None else str(asignado_a),
                             "comentario": comentario})
    return fila


def visto_bueno(conexion: Connection, doc: dict, comentario: str | None, usuario: dict,
                request) -> dict:
    """Contrato §6: visto bueno de A-15 (en pausa). Quien cerró la revisión no puede firmarlo."""
    if doc["estado"] != "pendiente_visto_bueno":
        raise AppError("ESTADO_INVALIDO", "El documento no está pendiente de visto bueno", 409)
    revision = conexion.execute(SQL["revision_aprobada_doc"],
                                {"documento_id": doc["id"]}).fetchone()
    if revision:
        cerrada = conexion.execute(SQL["version_creador"],
                                   {"id": revision["version_id"]}).fetchone()
        if cerrada and cerrada["creado_por"] == usuario["usuario_id"]:
            raise AppError("FORBIDDEN", "Quien cerró la revisión no puede firmar el visto bueno",
                           403)
    fila = conexion.execute(SQL["doc_sign_off"],
                            {"id": doc["id"], "usuario_id": usuario["usuario_id"]}).fetchone()
    if not fila:
        raise AppError("ESTADO_INVALIDO", "El documento ya no está pendiente de visto bueno", 409)
    audit.registrar(conexion, "DOCUMENTO_VISTO_BUENO", request=request,
                    usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                    entidad_id=doc["id"], detalle={"comentario": comentario})
    return fila


def cerrar(conexion: Connection, revision_id, estado: str, comentario: str | None,
           if_match: str | None, usuario: dict, request) -> dict:
    rev = conexion.execute(SQL["revision_por_id"], {"id": revision_id}).fetchone()
    if not rev:
        raise AppError("REVISION_NO_ENCONTRADA", "La revisión no existe", 404)
    if not if_match:
        raise AppError("IF_MATCH_REQUERIDO", "Falta If-Match con actualizado_en", 428)
    try:
        marca = datetime.fromisoformat(if_match.strip('"'))
    except ValueError as error:
        raise AppError("VALIDACION", "If-Match no es una fecha ISO 8601", 400) from error
    if estado in ("rechazado_con_cambios", "devuelto") and not (comentario or "").strip():
        raise AppError("COMENTARIO_REQUERIDO", "Falta comentario_general", 422)
    if estado == "aprobado":
        # A-09: no se aprueba con anotaciones sin decidir.
        pendientes = conexion.execute(SQL["anotaciones_pendientes"],
                                      {"version_id": rev["version_id"]}).fetchall()
        if pendientes:
            raise AppError("ANOTACIONES_PENDIENTES",
                           "Quedan anotaciones sin decidir: "
                           + ", ".join(str(p["id"]) for p in pendientes), 422)

    params = {"id": revision_id, "estado": estado, "comentario": comentario, "if_match": marca}
    fila = conexion.execute(SQL["revision_devolver" if estado == "devuelto" else "revision_cerrar"],
                            params).fetchone()
    if not fila:
        raise AppError("CONFLICTO_REVISION",
                       "La revisión cambió o no está en proceso; recarga", 409)

    documento_estado = "en_revision"
    if estado == "aprobado":
        texto = conexion.execute("SELECT contenido_texto FROM versiones_documento WHERE id = %(id)s",
                                 {"id": rev["version_id"]}).fetchone()["contenido_texto"]
        nueva_version(conexion, rev["documento_id"], "final_aprobado", usuario["usuario_id"],
                      texto=texto, meta={"version_revisada_id": str(rev["version_id"]),
                                         "revision_id": str(revision_id)})
        documento_estado = "aprobado"  # A-15 en pausa: requiere_visto_bueno siempre false
    elif estado == "rechazado_con_cambios":
        documento_estado = "rechazado"
    conexion.execute(SQL["doc_estado"], {"id": rev["documento_id"], "estado": documento_estado})
    audit.registrar(conexion, f"REVISION_{estado.upper()}", request=request,
                    usuario_id=usuario["usuario_id"], entidad_tipo="revision",
                    entidad_id=revision_id, detalle={"documento_estado": documento_estado})
    return {"id": revision_id, "estado": fila["estado"], "documento_estado": documento_estado,
            "requiere_visto_bueno": False, "tiempo_revision_seg": fila.get("tiempo_revision_seg")}


def reabrir(conexion: Connection, doc: dict, comentario: str | None, modo: str, usuario: dict,
            request) -> dict:
    if doc["estado"] not in ("rechazado", "aprobado"):
        raise AppError("ESTADO_INVALIDO", "Solo se reabre un documento rechazado o aprobado", 409)
    if doc["estado"] == "aprobado" and not (comentario or "").strip():
        raise AppError("COMENTARIO_REQUERIDO", "Reabrir un aprobado exige comentario (A-19)", 422)
    version = anonimizar(conexion, doc, None, modo, usuario, request,
                         estados=("rechazado", "aprobado"))
    doc = {**doc, "estado": "en_revision", "v_id": version["version_id"], "v_tipo": "anonimizado_ia"}
    revision = abrir(conexion, doc, usuario, request)
    audit.registrar(conexion, "DOCUMENTO_REABIERTO", request=request,
                    usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                    entidad_id=doc["id"], detalle={"comentario": comentario})
    return {"version_id": version["version_id"], "numero_version": version["numero_version"],
            "revision_id": revision["id"], "numero_intento": revision["numero_intento"]}
