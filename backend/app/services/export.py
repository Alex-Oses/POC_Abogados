"""PDF final reconstruido desde el texto (0007, docs/export/pdf.md, modo secuencial).

Ningún píxel del original: lienzo nuevo con ReportLab y el texto ya sustituido.
`invariant=1` hace el PDF determinista, así el hash es reproducible.
"""

import hashlib
import io
from xml.sax.saxutils import escape

from psycopg import Connection

from app.core import storage
from app.core.errors import AppError
from app.db.queries import SQL
from app.services import audit, richtext

AVISO_TACHADO = "Documento NO anonimizado: tachado solo para revisión interna"


def _relleno(texto: str, caracter: str) -> str:
    """Tantos `caracter` como ocupe `texto` en Helvetica 10 (BodyText): el original no entra al PDF."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    ancho = stringWidth(texto, "Helvetica", 10)
    return caracter * max(1, round(ancho / stringWidth(caracter, "Helvetica", 10)))


def marcar(contenido: str, anotaciones: list[dict]) -> tuple[str, bool]:
    """Marcado de ReportLab de un bloque con cada forma como en la vista previa.
    censurar/borrar dibujan relleno del mismo ancho: los caracteres originales no se escriben."""
    salida, pos, tachado = [], 0, False
    for a in sorted(anotaciones, key=lambda a: a["inicio_offset"]):
        if a["decision_revisor"] == "falso_positivo" or a["accion_aplicada"] == "mantenido":
            continue
        # Solapes: se recorta a lo que queda sin tratar. Descartar la anotación dejaría
        # texto original a la vista en el PDF (A-09), así que nunca se salta un tramo.
        inicio, fin = max(a["inicio_offset"], pos), a["fin_offset"]
        if inicio >= fin:
            continue
        original = contenido[inicio:fin].replace("\n", " ")
        accion = a["accion_aplicada"]
        if accion == "censurar":
            trozo = f'<font color="#3A3A3A" backColor="#3A3A3A">{_relleno(original, chr(0xA0))}</font>'
        elif accion == "eliminado":
            trozo = f'<font color="#C8C8C8">{_relleno(original, chr(0xA6))}</font>'  # ¦ rayado claro
        elif accion == "tachado":
            tachado = True
            trozo = f'<font backColor="#E6E6E6"><strike>{escape(original)}</strike></font>'
        else:  # etiqueta, pseudonimizado, iniciales
            nuevo = (a["texto_sustitucion"] or "").replace("\n", " ") or "█"
            trozo = f'<font color="#FFFFFF" backColor="#4A4A4A">&nbsp;{escape(nuevo)}&nbsp;</font>'
        salida += [escape(contenido[pos:inicio]), trozo]
        pos = fin
    salida.append(escape(contenido[pos:]))
    return "".join(salida), tachado


def paginas_marcadas(conexion: Connection, version_id, bloques_version_id) -> tuple[list[str], bool]:
    """Como `anonymize.texto_plano`, pero en marcado con las formas de la maqueta."""
    anotaciones = conexion.execute(SQL["anotaciones_para_aplicar"],
                                   {"version_id": version_id}).fetchall()
    bloques = conexion.execute(SQL["bloques_version"], {
        "version_id": bloques_version_id, "pagina": None, "limit": 100000, "offset": 0}).fetchall()
    paginas: dict[int, list[str]] = {}
    hay_tachado = False
    for b in bloques:
        marcado, tachado = marcar(b["contenido"], [a for a in anotaciones if a["bloque_id"] == b["id"]])
        hay_tachado |= tachado
        paginas.setdefault(b["pagina_numero"], []).append(marcado)
    return ["\n\n".join(v) for _, v in sorted(paginas.items())], hay_tachado


def _config(conexion: Connection, clave: str, defecto):
    fila = conexion.execute(SQL["config_valor"], {"clave": clave}).fetchone()
    return fila["valor"] if fila else defecto


def componer(paginas: list[str], marca_agua: bool, htmls: dict | None = None,
             tachado: bool = False) -> bytes:
    """`htmls` ({"n": html saneado}) solo sin anonimizar: las sustituciones van sobre offsets del
    texto plano, así que el PDF anonimizado sale sin formato. `paginas` ya viene en marcado
    de ReportLab (`marcar`)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

    estilo = getSampleStyleSheet()["BodyText"]
    salida = io.BytesIO()

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        if marca_agua:
            canvas.drawString(70, 815, "ANONIMIZADO - CONFIDENCIAL")
        canvas.drawRightString(525, 30, str(documento.page))
        canvas.restoreState()

    # Metadatos limpios: sin autor, título ni fechas reales.
    doc = SimpleDocTemplate(salida, pagesize=A4, invariant=1, title="", author="", subject="",
                            creator="", producer="", leftMargin=70.9, rightMargin=70.9)
    historia = []
    if tachado:
        historia.append(Paragraph(f'<font color="#B00020"><b>{AVISO_TACHADO}</b></font>', estilo))
    for i, texto in enumerate(paginas or [""]):
        if i:
            historia.append(PageBreak())
        if (htmls or {}).get(str(i + 1)):
            marcado, mayor = richtext.a_reportlab(htmls[str(i + 1)])
            propio = ParagraphStyle("rico", parent=estilo, leading=max(estilo.leading, mayor * 1.2))
            try:
                historia.append(Paragraph(marcado, propio))
                continue
            except ValueError:  # marcado que ReportLab no acepta: la página sale en texto plano
                pass
        for parrafo in texto.split("\n\n"):
            # El texto que no cabe pasa a la página siguiente: no se corta.
            historia.append(Paragraph(parrafo.replace("\n", "<br/>") or "&nbsp;", estilo))
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()


def vista_previa(conexion: Connection, doc: dict) -> bytes:
    """`POST /transform/build`: la vigente, sin cambiar estados."""
    version_id = doc["v_id"]
    bloques_de = version_id
    if doc["v_tipo"] == "final_aprobado":
        bloques_de = doc["v_meta"]["version_revisada_id"]
        version_id = bloques_de
    htmls = (doc["v_meta"] or {}).get("paginas_html") if doc["v_tipo"] == "ocr_texto" else None
    paginas, tachado = paginas_marcadas(conexion, version_id, bloques_de)
    return componer(paginas, bool(_config(conexion, "pdf_export_incluir_marcas_agua", True)),
                    htmls, tachado)


def exportar(conexion: Connection, documento_id, usuario: dict, request) -> tuple[bytes, str, str]:
    doc = conexion.execute(SQL["doc_bloquear"], {"id": documento_id}).fetchone()
    if not doc or doc["estado"] == "eliminado":
        raise AppError("DOCUMENTO_NO_ENCONTRADO", "El documento no existe", 404)
    if doc["estado"] not in ("aprobado", "exportado"):
        raise AppError("ESTADO_INVALIDO", "Solo se exporta un documento aprobado (A-17)", 409)
    final = conexion.execute(SQL["version_final_doc"], {"documento_id": documento_id}).fetchone()
    if not final:
        raise AppError("ESTADO_INVALIDO", "No hay versión final aprobada", 409)
    nombre = doc["nombre_original"].rsplit(".", 1)[0] + "_anon.pdf"
    huella = final["metadatos_proceso"].get("hash_export")

    if doc["estado"] == "exportado" and final["ruta_pdf"] and huella:
        # A-18: idempotente; nunca se regenera sobre la misma versión.
        try:
            pdf = storage.leer(final["ruta_pdf"], cifrado=False)
        except AppError as error:
            raise AppError("EXPORT_INTEGRITY", "Falta el PDF exportado", 500) from error
        if hashlib.sha256(pdf).hexdigest() != huella:
            raise AppError("EXPORT_INTEGRITY", "El PDF exportado no supera la integridad", 500)
        return pdf, huella, nombre

    revisada = final["metadatos_proceso"]["version_revisada_id"]
    pendientes = conexion.execute(SQL["anotaciones_pendientes"], {"version_id": revisada}).fetchall()
    if pendientes:
        raise AppError("ANOTACIONES_PENDIENTES", "Hay anotaciones sin decisión o sin bloque", 422)
    paginas, tachado = paginas_marcadas(conexion, revisada, revisada)
    pdf = componer(paginas, bool(_config(conexion, "pdf_export_incluir_marcas_agua", True)),
                   tachado=tachado)
    huella = hashlib.sha256(pdf).hexdigest()
    ruta = f"{documento_id}/v{final['numero_version']}.pdf"
    storage.guardar(ruta, pdf, cifrar=False)  # el PDF ya está anonimizado
    conexion.execute(SQL["version_pdf_set"], {"id": final["id"], "ruta": ruta, "hash": huella})
    conexion.execute(SQL["doc_exportado"], {"id": documento_id})
    audit.registrar(conexion, "PDF_EXPORTADO", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="documento", entidad_id=documento_id,
                    detalle={"version_id": str(final["id"]), "hash": huella, "bytes": len(pdf)})
    return pdf, huella, nombre


def transcrito(conexion: Connection, doc: dict, usuario: dict, request) -> tuple[bytes, str]:
    """PDF de la última transcripción, sin anonimizar y con el formato de la página.
    No se guarda: contiene datos personales y se genera al pedirlo."""
    if doc["estado"] in ("pendiente", "ocr_procesando"):
        raise AppError("ESTADO_INVALIDO", "La transcripción aún no ha terminado", 409)
    ocr = conexion.execute(SQL["version_ocr_ultima"], {"documento_id": doc["id"]}).fetchone()
    if not ocr:
        raise AppError("SIN_TEXTO", "No hay transcripción", 422)
    # Sin anotaciones: la versión OCR no tiene; paginas_marcadas solo escapa el texto.
    paginas, _ = paginas_marcadas(conexion, ocr["id"], ocr["id"])
    pdf = componer(paginas, False, (ocr["metadatos_proceso"] or {}).get("paginas_html"))
    audit.registrar(conexion, "PDF_TRANSCRITO_EXPORTADO", request=request,
                    usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                    entidad_id=doc["id"], detalle={"version_id": str(ocr["id"]), "bytes": len(pdf)})
    return pdf, doc["nombre_original"].rsplit(".", 1)[0] + "_trans.pdf"
