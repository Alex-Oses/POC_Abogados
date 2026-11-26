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
from app.services import audit, ocr, richtext

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
                                  "creado_en", "actualizado_en", "exportado_en", "subido_por")}
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

def nombre_de(usuario: dict) -> str:
    return " ".join(p for p in (usuario.get("nombre"), usuario.get("apellidos")) if p) or usuario.get("email", "")


def registrar_subida(nombre: str, datos: bytes, doble: bool, usuario: dict, request,
                     subido_por: str | None = None, origen: str = "app") -> dict:
    """Valida, guarda el original cifrado y deja el documento en cola (`pendiente`, 0017).
    `subido_por` queda fijo en el documento: la persona logueada o la carpeta de SharePoint."""
    if len(datos) > settings.max_upload_mb * 1024 * 1024:
        raise AppError("FICHERO_GRANDE", f"Máximo {settings.max_upload_mb} MB", 413)
    mime = next((m for firma, m in MIMES.items() if datos.startswith(firma)), None)
    if not datos or not mime:
        raise AppError("FORMATO_NO_SOPORTADO", "Solo PDF, JPG o PNG", 415)
    try:
        num_paginas = ocr.contar(datos, mime)
    except Exception as error:  # fichero dañado: se rechaza antes de guardarlo
        raise AppError("FORMATO_NO_SOPORTADO", "No se puede abrir el fichero", 415) from error
    huella = hashlib.sha256(datos).hexdigest()
    with tx() as conexion:
        if conexion.execute(SQL["doc_por_hash"],
                            {"creado_por": usuario["usuario_id"], "hash": huella}).fetchone():
            raise AppError("DOCUMENTO_DUPLICADO", "Ya subiste este documento", 409)
        doc = conexion.execute(SQL["doc_insertar"], {
            "nombre": nombre[:500] or "documento", "hash": huella, "mime": mime,
            "tamano": len(datos), "ruta": "pendiente", "creado_por": usuario["usuario_id"],
            "clave": storage.id_clave(), "num_paginas": num_paginas,
            "meta": json.dumps({"ocr": {"modo": "doble" if doble else "simple"},
                                "subido_por": subido_por or nombre_de(usuario),
                                "origen": origen}, ensure_ascii=False)}).fetchone()
        ruta = f"{doc['id']}/original.bin"
        storage.guardar(ruta, datos)
        conexion.execute("UPDATE documentos SET ruta_almacenamiento = %(r)s WHERE id = %(id)s",
                         {"r": ruta, "id": doc["id"]})
        nueva_version(conexion, doc["id"], "original", usuario["usuario_id"])
        audit.registrar(conexion, "DOCUMENTO_SUBIDO", request=request,
                        usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                        entidad_id=doc["id"], detalle={"mime": mime, "bytes": len(datos),
                                                       "hash": huella, "paginas": num_paginas})
    return {"id": doc["id"], "num_paginas": num_paginas, "estado": "pendiente"}


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
            "tiempo": r["tiempo"], "ancho": r["ancho"], "alto": r["alto"]}


def progreso(conexion: Connection, documento_id) -> dict:
    fila = conexion.execute(SQL["doc_progreso"], {"id": documento_id}).fetchone()
    ocr_meta = fila["ocr"] or {}
    procesando = fila["estado"] == "ocr_procesando"
    return {"estado": fila["estado"], "total_pages": fila["num_paginas"],
            "pages_done": fila["pages_done"],
            "current_page": fila["pages_done"] + 1 if procesando else None,
            "queue_position": fila["queue_position"], "error": ocr_meta.get("error")}


def _evento_pagina(fila: dict) -> dict:
    return {"type": "page", "numero": fila["numero"], "contraste": fila["contraste_bruto"],
            "estado": fila["estado"], "leida_ocr": fila["leida_ocr"], "texto": fila["texto"] or "",
            "diferencias": fila["diferencias"], "avisos": fila["avisos"],
            "tiempo": fila["tiempo"], "ancho": fila["ancho"], "alto": fila["alto"]}


def seguir_ocr(documento_id, usuario: dict):
    """Generador NDJSON (start, page…, done | error) leído de la BD cada `ocr_sondeo_seg`.

    El trabajo lo hace la cola: cerrar este flujo no detiene el OCR.
    """
    enviadas: set[int] = set()
    inicio = True
    while True:
        with tx() as conexion:
            doc = obtener(conexion, documento_id, usuario)
            prog = progreso(conexion, documento_id)
            filas = paginas(conexion, doc) if doc["v_tipo"] == "ocr_texto" else []
        if inicio:
            modo = (doc["metadatos_extras"].get("ocr") or {}).get("modo", "doble")
            yield {"type": "start", "id": documento_id, "total_pages": doc["num_paginas"],
                   "mode": "double" if modo == "doble" else "single",
                   "queue_position": prog["queue_position"]}
            inicio = False
        for fila in filas:
            if fila["numero"] not in enviadas:
                enviadas.add(fila["numero"])
                yield _evento_pagina(fila)
        if prog["error"]:
            yield {"type": "error", "id": documento_id, "code": prog["error"],
                   "message": "El OCR no terminó; el documento queda en pendiente"}
            return
        if prog["estado"] not in ("pendiente", "ocr_procesando"):
            yield {"type": "done", "id": documento_id, "num_paginas": doc["num_paginas"],
                   "estado": prog["estado"],
                   "total_time": round(sum(f["tiempo"] or 0 for f in filas), 2),
                   "total_chars": sum(len(f["texto"] or "") for f in filas)}
            return
        time.sleep(settings.ocr_sondeo_seg)


def procesar_documento(doc: dict, parar=lambda: False) -> None:
    """Lo llama la cola con el documento ya en `ocr_procesando`. Guarda y confirma página a
    página; si se reanuda tras una caída, salta las páginas ya guardadas."""
    documento_id, inicio = doc["id"], time.time()
    doble = (doc["metadatos_extras"].get("ocr") or {}).get("modo", "doble") == "doble"
    usuario_id = doc["creado_por"]
    hechas: set[int] = set()
    try:
        datos = storage.leer(doc["ruta_almacenamiento"])
        pdf = datos if doc["mime_type"] == "application/pdf" else None
        with tx() as conexion:
            actual = conexion.execute(SQL["doc_por_id"], {"id": documento_id}).fetchone()
            if actual["v_tipo"] != "ocr_texto":
                nueva_version(
                    conexion, documento_id, "ocr_texto", usuario_id, texto="",
                    motor_ocr="paddleocr-vl",
                    modelo_ia="mock" if settings.ocr_mock else settings.ocr_model,
                    meta={"pipeline_version": "v1.6", "modo": "doble" if doble else "simple",
                          "origen_geometria": "secuencial", "paginas_validadas": [],
                          "paginas": {}})
                actual = conexion.execute(SQL["doc_por_id"], {"id": documento_id}).fetchone()
            hechas = {f["numero"] for f in conexion.execute(
                SQL["paginas_numeros"], {"documento_id": documento_id}).fetchall()}
        version_id = actual["v_id"]
        for numero in range(1, doc["num_paginas"] + 1):
            if numero in hechas:
                continue
            with tx() as conexion:  # cancelado mientras tanto: se para entre páginas
                ocr_meta = conexion.execute(SQL["doc_progreso"],
                                            {"id": documento_id}).fetchone()["ocr"] or {}
            if ocr_meta.get("error") or parar():  # parado: sigue en ocr_procesando y se reanuda
                return
            r = ocr.procesar_pagina(ocr.una_pagina(datos, doc["mime_type"], numero), numero,
                                    doble, pdf)
            with tx() as conexion:
                conexion.execute(SQL["bloque_insertar"], {
                    "version_id": version_id, "pagina": numero, "ancho": r["ancho"],
                    "alto": r["alto"], "contenido": r["texto"], "semaforo": _semaforo(r)})
                conexion.execute(SQL["pagina_insertar"],
                                 {"documento_id": documento_id, "numero": numero, **_pagina_bd(r)})
                conexion.execute(SQL["version_meta_set"], {
                    "id": version_id, "ruta": ["paginas", str(numero)],
                    "valor": json.dumps(_meta_pagina(r), ensure_ascii=False)})
                conexion.execute(SQL["version_texto_recalcular"], {"id": version_id})
        with tx() as conexion:
            ilegibles = conexion.execute(
                "SELECT count(*) AS n FROM paginas_documento WHERE documento_id = %(id)s "
                "AND estado = 'ilegible'", {"id": documento_id}).fetchone()["n"]
            conexion.execute(SQL["doc_fin_ocr"], {"id": documento_id,
                                                  "num_paginas": doc["num_paginas"]})
            audit.registrar(conexion, "OCR_COMPLETADO", usuario_id=usuario_id,
                            entidad_tipo="documento", entidad_id=documento_id,
                            detalle={"paginas": doc["num_paginas"], "ilegibles": ilegibles,
                                     "reanudado": bool(hechas),
                                     "segundos": round(time.time() - inicio, 1)})
    except Exception as error:  # noqa: BLE001 - sale de la cola con el error y se audita
        log.exception("ocr_fallido")
        if parar():  # apagado a mitad de página: no es un fallo, se reanuda al arrancar
            return
        with tx() as conexion:
            conexion.execute(SQL["doc_estado"], {"id": documento_id, "estado": "pendiente"})
            conexion.execute(SQL["doc_meta_set"], {"id": documento_id, "ruta": ["ocr", "error"],
                                                   "valor": json.dumps("OCR_FALLIDO")})
            audit.registrar(conexion, "OCR_FALLIDO", usuario_id=usuario_id,
                            entidad_tipo="documento", entidad_id=documento_id,
                            detalle={"error": type(error).__name__, "paginas_hechas": len(hechas)})


def cancelar(conexion: Connection, doc: dict, usuario: dict, request) -> dict:
    """Saca el documento de la cola; las páginas ya leídas se conservan."""
    ocr_meta = doc["metadatos_extras"].get("ocr")
    if doc["estado"] not in ("pendiente", "ocr_procesando") or not ocr_meta or ocr_meta.get("error"):
        raise AppError("DOCUMENTO_NO_EN_COLA", "El documento no está en la cola de OCR", 409)
    conexion.execute(SQL["doc_meta_set"], {"id": doc["id"], "ruta": ["ocr", "error"],
                                           "valor": json.dumps("CANCELADO")})
    conexion.execute(SQL["doc_estado"], {"id": doc["id"], "estado": "pendiente"})
    audit.registrar(conexion, "OCR_CANCELADO", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="documento", entidad_id=doc["id"],
                    detalle={"estado_anterior": doc["estado"]})
    return progreso(conexion, doc["id"])


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
        fila["html"] = meta.get("paginas_html", {}).get(str(fila["numero"]))
        fila["diferencias"] = extra.get("diferencias")
        fila["contraste_bruto"] = extra.get("contraste_bruto", fila["contraste"])
        fila["tiempo"] = extra.get("tiempo")
        fila["ancho"], fila["alto"] = extra.get("ancho"), extra.get("alto")
    return filas


def _editable(doc: dict) -> None:
    # Editar la transcripción solo antes de anonimizar: después los offsets dependen del texto.
    # 0017: también mientras la cola sigue leyendo otras páginas (o quedó parada a medias).
    if (doc["estado"] not in ("pendiente", "ocr_procesando", "ocr_completado")
            or doc["v_tipo"] != "ocr_texto"):
        raise AppError("DOCUMENTO_NO_EDITABLE",
                       "Solo se edita la transcripción antes de anonimizar", 409)


def _bloque(conexion: Connection, doc: dict, numero: int) -> dict:
    bloque = conexion.execute(SQL["bloque_de_pagina"],
                              {"version_id": doc["v_id"], "pagina": numero}).fetchone()
    if not bloque and doc["estado"] != "ocr_completado" and 1 <= numero <= (doc["num_paginas"] or 0):
        raise AppError("PAGINA_EN_PROCESO", "La página aún no se ha transcrito", 409)
    if not bloque:
        raise AppError("PAGINA_NO_ENCONTRADA", "La página no existe", 404)
    return bloque


def _html_set(conexion: Connection, doc: dict, numero: int, html: str | None) -> None:
    """Guarda (o quita, con None) el HTML saneado de la página en metadatos_proceso."""
    actuales = dict((doc["v_meta"] or {}).get("paginas_html", {}))
    if html is None and str(numero) not in actuales:
        return
    if html is None:
        actuales.pop(str(numero))
    else:
        actuales[str(numero)] = html
    conexion.execute(SQL["version_meta_set"], {"id": doc["v_id"], "ruta": ["paginas_html"],
                                               "valor": json.dumps(actuales, ensure_ascii=False)})


def editar_pagina(conexion: Connection, doc: dict, numero: int, texto: str | None,
                  validada: bool | None, usuario: dict, request, html: str | None = None) -> None:
    _editable(doc)
    bloque = _bloque(conexion, doc, numero)
    detalle: dict = {"pagina": numero}
    if html is not None:
        # El texto plano se deriva siempre del HTML saneado: es la fuente de búsqueda y offsets.
        html, texto = richtext.sanear(html)
        _html_set(conexion, doc, numero, html)
        detalle["formato"] = True
    elif texto is not None:
        _html_set(conexion, doc, numero, None)  # solo texto: el formato guardado ya no encaja
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


def localizar(doc: dict, numero: int, textos: list[str]) -> list[dict | None]:
    png = imagen_pagina(doc, numero)
    pdf = None
    if doc["mime_type"] == "application/pdf" and not storage.existe(
            f"{doc['id']}/reescaneo_{numero}.png"):
        pdf = _original(doc)
    return [ocr.localizar(png, pdf, numero, t) for t in textos]


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
    _html_set(conexion, doc, numero, None)  # texto nuevo: el formato anterior ya no encaja
    conexion.execute(SQL["version_meta_set"], {"id": doc["v_id"], "ruta": ["paginas", str(numero)],
                                               "valor": json.dumps(_meta_pagina(r))})
    conexion.execute(SQL["pagina_actualizar"], {"documento_id": doc["id"], "numero": numero,
                                                **_pagina_bd(r)})
    audit.registrar(conexion, "PAGINA_REESCANEADA" if fichero else "PAGINA_RELEIDA",
                    request=request, usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                    entidad_id=doc["id"], detalle={"pagina": numero, "estado": r["estado"],
                                                   "contraste": r["contraste"]})
    return {"type": "page", **r}
