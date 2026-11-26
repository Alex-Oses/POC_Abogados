from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Jsonb

from app.core.errors import AppError
from app.db.queries import SQL
from app.integrations.etl import extraer_ocr_documento
from app.integrations.storage import guardar_original, leer_original
from app.services.audit import registrar_evento


def _es_dueno_o_revisor(doc: dict, usuario: dict) -> bool:
    return doc["creado_por"] == usuario["id"] or "revisor" in usuario["roles"]


def subir_documento(
    conexion: Connection, usuario: dict, titulo: str, contenido: bytes, nombre_fichero: str
) -> dict:
    if not contenido:
        raise AppError("EMPTY_FILE", "El fichero está vacío", 400)
    doc = conexion.execute(
        SQL["crear_documento"],
        {"titulo": titulo, "estado": "procesando", "creado_por": usuario["id"]},
    ).fetchone()
    ruta, digest = guardar_original(str(doc["id"]), contenido)
    paginas = extraer_ocr_documento(contenido, nombre_fichero)
    texto_total = "\n\n".join(p.get("texto", "") for p in paginas).strip()
    version = conexion.execute(
        SQL["crear_version_documento"],
        {
            "documento_id": doc["id"],
            "texto_contenido": texto_total,
            "metadatos_proceso": Jsonb({"sha256_original": digest, "ruta_original": str(ruta)}),
        },
    ).fetchone()
    for p in paginas:
        conexion.execute(
            SQL["insertar_pagina_documento"],
            {
                "documento_id": doc["id"],
                "numero_pagina": p["numero_pagina"],
                "semaforo": p.get("semaforo", "verde"),
                "avisos": Jsonb(p.get("avisos", [])),
            },
        )
    conexion.execute(
        SQL["insertar_bloque_layout"],
        {
            "version_id": version["id"],
            "pagina": 1,
            "orden": 1,
            "tipo": "parrafo",
            "texto": texto_total or " ",
            "bbox": Jsonb({}),
        },
    )
    registrar_evento(conexion, usuario["id"], "documento_subido", "documentos", str(doc["id"]))
    return doc


def transformar_texto_plano(
    conexion: Connection, usuario: dict, titulo: str, texto: str, documento_id: UUID | None = None
) -> dict:
    if documento_id is None:
        doc = conexion.execute(
            SQL["crear_documento"],
            {"titulo": titulo, "estado": "borrador", "creado_por": usuario["id"]},
        ).fetchone()
    else:
        doc = obtener_documento(conexion, documento_id)
    version = conexion.execute(
        SQL["crear_version_documento"],
        {
            "documento_id": doc["id"],
            "texto_contenido": texto,
            "metadatos_proceso": Jsonb({"origen": "texto_plano"}),
        },
    ).fetchone()
    conexion.execute(
        SQL["insertar_bloque_layout"],
        {
            "version_id": version["id"],
            "pagina": 1,
            "orden": 1,
            "tipo": "parrafo",
            "texto": texto,
            "bbox": Jsonb({}),
        },
    )
    registrar_evento(conexion, usuario["id"], "texto_plano_creado", "documentos", str(doc["id"]))
    return version


def construir_version(conexion: Connection, usuario: dict, documento_id: UUID, texto: str) -> dict:
    obtener_documento(conexion, documento_id)
    version = conexion.execute(
        SQL["crear_version_documento"],
        {
            "documento_id": documento_id,
            "texto_contenido": texto,
            "metadatos_proceso": Jsonb({"origen": "build"}),
        },
    ).fetchone()
    conexion.execute(
        SQL["insertar_bloque_layout"],
        {
            "version_id": version["id"],
            "pagina": 1,
            "orden": 1,
            "tipo": "parrafo",
            "texto": texto,
            "bbox": Jsonb({}),
        },
    )
    registrar_evento(conexion, usuario["id"], "version_construida", "versiones_documento", str(version["id"]))
    return version


def listar_documentos(conexion: Connection, page: int, limit: int) -> dict:
    offset = (page - 1) * limit
    items = conexion.execute(SQL["listar_documentos"], {"limit": limit, "offset": offset}).fetchall()
    total = conexion.execute(SQL["contar_documentos"]).fetchone()["total"]
    return {"items": items, "page": page, "limit": limit, "total": total}


def obtener_documento(conexion: Connection, documento_id: UUID) -> dict:
    doc = conexion.execute(SQL["obtener_documento"], {"id": documento_id}).fetchone()
    if not doc:
        raise AppError("DOCUMENT_NOT_FOUND", "Documento no encontrado", 404)
    return doc


def eliminar_documento(conexion: Connection, usuario: dict, documento_id: UUID) -> None:
    doc = obtener_documento(conexion, documento_id)
    if doc["creado_por"] != usuario["id"] and "admin" not in usuario["roles"]:
        raise AppError("FORBIDDEN", "No tienes permiso para eliminar este documento", 403)
    conexion.execute(SQL["eliminar_documento_logico"], {"id": documento_id})
    registrar_evento(conexion, usuario["id"], "documento_eliminado", "documentos", str(documento_id))


def listar_paginas(conexion: Connection, documento_id: UUID) -> list[dict]:
    obtener_documento(conexion, documento_id)
    return conexion.execute(SQL["listar_paginas_documento"], {"documento_id": documento_id}).fetchall()


def obtener_original(conexion: Connection, usuario: dict, documento_id: UUID) -> bytes:
    doc = obtener_documento(conexion, documento_id)
    if not _es_dueno_o_revisor(doc, usuario):
        raise AppError("FORBIDDEN", "No tienes permiso para descargar el original", 403)
    contenido = leer_original(str(documento_id))
    if contenido is None:
        raise AppError("ORIGINAL_NOT_FOUND", "Fichero original no disponible", 404)
    return contenido


def listar_versiones(conexion: Connection, documento_id: UUID) -> list[dict]:
    obtener_documento(conexion, documento_id)
    return conexion.execute(SQL["listar_versiones_documento"], {"documento_id": documento_id}).fetchall()


def obtener_version(conexion: Connection, documento_id: UUID, numero_version: int) -> dict:
    obtener_documento(conexion, documento_id)
    version = conexion.execute(
        SQL["obtener_version_por_numero"],
        {"documento_id": documento_id, "numero_version": numero_version},
    ).fetchone()
    if not version:
        raise AppError("VERSION_NOT_FOUND", "Versión no encontrada", 404)
    return version


def listar_bloques(conexion: Connection, documento_id: UUID, numero_version: int) -> list[dict]:
    version = obtener_version(conexion, documento_id, numero_version)
    return conexion.execute(SQL["listar_bloques_version"], {"version_id": version["id"]}).fetchall()
