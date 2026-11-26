import hashlib
import json
import time

from psycopg import Connection

from app.core import storage
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import log
from app.db.pool import tx
from app.db.queries import SQL
from app.services import audit, ocr

MIMES = {b"%PDF": "application/pdf", b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg"}


def es_revisor(usuario: dict) -> bool:
    return bool({"revisor", "admin"} & set(usuario["roles"]))


def obtener(conexion: Connection, documento_id, usuario: dict) -> dict:
    doc = conexion.execute(SQL["doc_por_id"], {"id": documento_id}).fetchone()
    # El transcriptor solo ve lo suyo: 404 y no 403, para no revelar que existe.
    if not doc or (not es_revisor(usuario) and doc["creado_por"] != usuario["usuario_id"]):
        raise AppError("DOCUMENTO_NO_ENCONTRADO", "El documento no existe", 404)
    return doc


def detalle(doc: dict) -> dict:
    salida = {k: doc[k] for k in ("id", "nombre_original", "mime_type", "num_paginas", "estado",
                                  "creado_en", "actualizado_en", "exportado_en")}
    salida["justicia_gratuita"] = doc["metadatos_extras"].get("justicia_gratuita")
    salida["version_actual"] = None if not doc["v_id"] else {
        "id": doc["v_id"], "numero_version": doc["v_numero"], "tipo_version": doc["v_tipo"],
        "confianza_layout_promedio": doc["v_confianza"], "metadatos_proceso": doc["v_meta"]}
    return salida


def nueva_version(conexion: Connection, documento_id, tipo: str, usuario_id, *, texto=None,
                  meta: dict | None = None, regla_id=None, motor_ocr=None, modelo_ia=None) -> dict:
    conexion.execute(SQL["version_desmarcar"], {"documento_id": documento_id})
    return conexion.execute(SQL["version_insertar"], {
        "documento_id": documento_id, "tipo": tipo, "texto": texto, "motor_ocr": motor_ocr,
        "modelo_ia": modelo_ia, "confianza": None, "meta": json.dumps(meta or {}),
        "creado_por": usuario_id, "pipeline": "paddleocr-vl-1.6" if motor_ocr else None,
        "regla_id": regla_id}).fetchone()


# --- Subida y OCR -----------------------------------------------------------------------

def registrar_subida(nombre: str, datos: bytes, usuario: dict, request) -> dict:
    """Valida, guarda el original cifrado y crea documento + versión `original` (confirmado)."""
    if len(datos) > settings.max_upload_mb * 1024 * 1024:
        raise AppError("FICHERO_GRANDE", f"Máximo {settings.max_upload_mb} MB", 413)
    mime = next((m for firma, m in MIMES.items() if datos.startswith(firma)), None)
    if not datos or not mime:
        raise AppError("FORMATO_NO_SOPORTADO", "Solo PDF, JPG o PNG", 415)
    huella = hashlib.sha256(datos).hexdigest()
    with tx() as conexion:
        if conexion.execute(SQL["doc_por_hash"],
                            {"creado_por": usuario["usuario_id"], "hash": huella}).fetchone():
            raise AppError("DOCUMENTO_DUPLICADO", "Ya subiste este documento", 409)
        doc = conexion.execute(SQL["doc_insertar"], {
            "nombre": nombre[:500] or "documento", "hash": huella, "mime": mime,
            "tamano": len(datos), "ruta": "pendiente", "creado_por": usuario["usuario_id"],
            "clave": storage.id_clave()}).fetchone()
        ruta = f"{doc['id']}/original.bin"
        storage.guardar(ruta, datos)
        conexion.execute("UPDATE documentos SET ruta_almacenamiento = %(r)s WHERE id = %(id)s",
                         {"r": ruta, "id": doc["id"]})
        nueva_version(conexion, doc["id"], "original", usuario["usuario_id"])
        audit.registrar(conexion, "DOCUMENTO_SUBIDO", request=request,
                        usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                        entidad_id=doc["id"], detalle={"mime": mime, "bytes": len(datos),
                                                       "hash": huella})
    return {"id": doc["id"], "mime": mime}


def _pagina_bd(resultado: dict) -> dict:
    # V14 limita contraste a 0-100; la medida es 0-255 y el umbral 80 se conserva con el tope.
    # shortcut: se guarda min(c, 100); el valor bruto queda en metadatos_proceso.
    return {"contraste": min(resultado["contraste"], 100), "estado": resultado["estado"],
            "avisos": json.dumps(resultado["avisos"], ensure_ascii=False),
            "leida": resultado["leida_ocr"]}


def _semaforo(resultado: dict) -> str:
    return {"ok": "verde", "revisar": "amarillo", "ilegible": "rojo"}[resultado["estado"]]


def _meta_pagina(r: dict) -> dict:
    return {"contraste_bruto": r["contraste"], "diferencias": r["diferencias"],
            "tiempo": r["tiempo"]}


def flujo_ocr(documento_id, mime: str, datos: bytes, doble: bool, usuario_id, request):
    """Generador NDJSON: start, una línea por página, done (o error). Persiste al final."""
    inicio = time.time()
    try:
        paginas = ocr.renderizar(datos, mime)
        yield {"type": "start", "id": documento_id, "total_pages": len(paginas),
               "mode": "double" if doble else "single"}
        resultados = []
        for numero, pagina in enumerate(paginas, 1):
            r = ocr.procesar_pagina(pagina, numero, doble,
                                    datos if mime == "application/pdf" else None)
            resultados.append(r)
            yield {"type": "page", **r}
        with tx() as conexion:
            version = nueva_version(
                conexion, documento_id, "ocr_texto", usuario_id,
                texto="\n\n".join(r["texto"] for r in resultados),
                motor_ocr="paddleocr-vl", modelo_ia="mock" if settings.ocr_mock else settings.ocr_model,
                meta={"pipeline_version": "v1.6", "modo": "doble" if doble else "simple",
                      "origen_geometria": "secuencial", "paginas_validadas": [],
                      "paginas": {str(r["numero"]): _meta_pagina(r) for r in resultados}})
            for r in resultados:
                conexion.execute(SQL["bloque_insertar"], {
                    "version_id": version["id"], "pagina": r["numero"], "ancho": r["ancho"],
                    "alto": r["alto"], "contenido": r["texto"], "semaforo": _semaforo(r)})
                conexion.execute(SQL["pagina_insertar"],
                                 {"documento_id": documento_id, "numero": r["numero"],
                                  **_pagina_bd(r)})
            conexion.execute(SQL["doc_fin_ocr"], {"id": documento_id,
                                                  "num_paginas": len(resultados)})
            audit.registrar(conexion, "OCR_COMPLETADO", request=request, usuario_id=usuario_id,
                            entidad_tipo="documento", entidad_id=documento_id,
                            detalle={"paginas": len(resultados),
                                     "ilegibles": sum(r["estado"] == "ilegible" for r in resultados),
                                     "segundos": round(time.time() - inicio, 1)})
        total = sum(r["tiempo"] for r in resultados)
        yield {"type": "done", "id": documento_id, "num_paginas": len(resultados),
               "estado": "ocr_completado", "total_time": round(total, 2),
               "total_chars": sum(len(r["texto"]) for r in resultados)}
    except Exception as error:  # noqa: BLE001 - el documento vuelve a `pendiente` y se audita
        log.exception("ocr_fallido")
        with tx() as conexion:
            conexion.execute(SQL["doc_estado"], {"id": documento_id, "estado": "pendiente"})
            audit.registrar(conexion, "OCR_FALLIDO", request=request, usuario_id=usuario_id,
                            entidad_tipo="documento", entidad_id=documento_id,
                            detalle={"error": type(error).__name__})
        yield {"type": "error", "id": documento_id, "code": "OCR_FALLIDO",
               "message": "Falló el OCR; el documento queda en pendiente"}


# --- Páginas ----------------------------------------------------------------------------

def paginas(conexion: Connection, doc: dict) -> list[dict]:
    meta = doc["v_meta"] or {}
    validadas = set(meta.get("paginas_validadas", []))
    por_pagina = meta.get("paginas", {})
    filas = conexion.execute(SQL["paginas_listar"],
                             {"documento_id": doc["id"], "version_id": doc["v_id"]}).fetchall()
    for fila in filas:
        extra = por_pagina.get(str(fila["numero"]), {})
        fila["validada"] = fila["numero"] in validadas
        fila["diferencias"] = extra.get("diferencias")
        fila["contraste_bruto"] = extra.get("contraste_bruto", fila["contraste"])
    return filas


def _editable(doc: dict) -> None:
    # Editar la transcripción solo antes de anonimizar: después los offsets dependen del texto.
    if doc["estado"] != "ocr_completado" or doc["v_tipo"] != "ocr_texto":
        raise AppError("DOCUMENTO_NO_EDITABLE",
                       "Solo se edita la transcripción antes de anonimizar", 409)


def _bloque(conexion: Connection, doc: dict, numero: int) -> dict:
    bloque = conexion.execute(SQL["bloque_de_pagina"],
                              {"version_id": doc["v_id"], "pagina": numero}).fetchone()
    if not bloque:
        raise AppError("PAGINA_NO_ENCONTRADA", "La página no existe", 404)
    return bloque


def editar_pagina(conexion: Connection, doc: dict, numero: int, texto: str | None,
                  validada: bool | None, usuario: dict, request) -> None:
    _editable(doc)
    bloque = _bloque(conexion, doc, numero)
    detalle: dict = {"pagina": numero}
    if texto is not None and texto != bloque["contenido"]:
        conexion.execute(SQL["bloque_actualizar"],
                         {"id": bloque["id"], "contenido": texto, "semaforo": "verde"})
        conexion.execute(SQL["version_texto_recalcular"], {"id": doc["v_id"]})
        # Sin texto en la auditoría: solo tamaños y huellas (nada de datos personales).
        detalle |= {"caracteres_antes": len(bloque["contenido"]), "caracteres_despues": len(texto),
                    "sha_antes": hashlib.sha256(bloque["contenido"].encode()).hexdigest()[:16],
                    "sha_despues": hashlib.sha256(texto.encode()).hexdigest()[:16]}
    if validada is not None:
        actuales = set((doc["v_meta"] or {}).get("paginas_validadas", []))
        actuales = actuales | {numero} if validada else actuales - {numero}
        conexion.execute(SQL["version_meta_set"], {"id": doc["v_id"], "ruta": ["paginas_validadas"],
                                                   "valor": json.dumps(sorted(actuales))})
        detalle["validada"] = validada
    audit.registrar(conexion, "PAGINA_EDITADA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="documento", entidad_id=doc["id"], detalle=detalle)


def _original(doc: dict) -> bytes:
    if not storage.existe(doc["ruta_almacenamiento"]):
        raise AppError("ORIGINAL_PURGADO", "El original ya no está disponible", 410)
    return storage.leer(doc["ruta_almacenamiento"])


def imagen_pagina(doc: dict, numero: int) -> bytes:
    reescaneo = f"{doc['id']}/reescaneo_{numero}.png"
    if storage.existe(reescaneo):
        return storage.leer(reescaneo)
    png = ocr.png_pagina(_original(doc), doc["mime_type"], numero)
    if not png:
        raise AppError("PAGINA_NO_ENCONTRADA", "La página no existe", 404)
    return png


def localizar(doc: dict, numero: int, texto: str) -> dict | None:
    png = imagen_pagina(doc, numero)
    pdf = None
    if doc["mime_type"] == "application/pdf" and not storage.existe(
            f"{doc['id']}/reescaneo_{numero}.png"):
        pdf = _original(doc)
    return ocr.localizar(png, pdf, numero, texto)


def releer_pagina(conexion: Connection, doc: dict, numero: int, fichero: bytes | None,
                  doble: bool, usuario: dict, request) -> dict:
    """Vuelve a leer una página; con `fichero` (PDF o imagen) la sustituye antes (reescaneo)."""
    _editable(doc)
    bloque = _bloque(conexion, doc, numero)
    pdf = None
    if fichero:
        mime = next((m for firma, m in MIMES.items() if fichero.startswith(firma)), None)
        if not mime:
            raise AppError("FORMATO_NO_SOPORTADO", "Solo PDF, JPG o PNG", 415)
        png = ocr.renderizar(fichero, mime)[0]["png"]
        storage.guardar(f"{doc['id']}/reescaneo_{numero}.png", png)
    else:
        png = imagen_pagina(doc, numero)
        if doc["mime_type"] == "application/pdf" and not storage.existe(
                f"{doc['id']}/reescaneo_{numero}.png"):
            pdf = _original(doc)
    import io

    from PIL import Image

    ancho, alto = Image.open(io.BytesIO(png)).size
    capa = ""
    if pdf:
        capa = ocr.renderizar(pdf, "application/pdf")[numero - 1]["capa"]
    r = ocr.procesar_pagina({"png": png, "ancho": ancho, "alto": alto, "capa": capa},
                            numero, doble, pdf)
    conexion.execute(SQL["bloque_actualizar"],
                     {"id": bloque["id"], "contenido": r["texto"], "semaforo": _semaforo(r)})
    conexion.execute(SQL["version_texto_recalcular"], {"id": doc["v_id"]})
    conexion.execute(SQL["version_meta_set"], {"id": doc["v_id"], "ruta": ["paginas", str(numero)],
                                               "valor": json.dumps(_meta_pagina(r))})
    conexion.execute(SQL["pagina_actualizar"], {"documento_id": doc["id"], "numero": numero,
                                                **_pagina_bd(r)})
    audit.registrar(conexion, "PAGINA_REESCANEADA" if fichero else "PAGINA_RELEIDA",
                    request=request, usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                    entidad_id=doc["id"], detalle={"pagina": numero, "estado": r["estado"],
                                                   "contraste": r["contraste"]})
    return {"type": "page", **r}
