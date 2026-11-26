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
from app.services import audit
from app.services.anonymize import texto_plano


def _config(conexion: Connection, clave: str, defecto):
    fila = conexion.execute(SQL["config_valor"], {"clave": clave}).fetchone()
    return fila["valor"] if fila else defecto


def componer(paginas: list[str], marca_agua: bool) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
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
    for i, texto in enumerate(paginas or [""]):
        if i:
            historia.append(PageBreak())
        for parrafo in texto.split("\n\n"):
            # El texto que no cabe pasa a la página siguiente: no se corta.
            historia.append(Paragraph(escape(parrafo).replace("\n", "<br/>") or "&nbsp;", estilo))
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()


def vista_previa(conexion: Connection, doc: dict) -> bytes:
    """`POST /transform/build`: la vigente, sin cambiar estados."""
    version_id = doc["v_id"]
    bloques_de = version_id
    if doc["v_tipo"] == "final_aprobado":
        bloques_de = doc["v_meta"]["version_revisada_id"]
        version_id = bloques_de
    return componer(texto_plano(conexion, version_id, bloques_de),
                    bool(_config(conexion, "pdf_export_incluir_marcas_agua", True)))


def exportar(conexion: Connection, documento_id, usuario: dict, request) -> tuple[bytes, str, str]:
    doc = conexion.execute(SQL["doc_bloquear"], {"id": documento_id}).fetchone()
    if not doc or doc["estado"] == "eliminado":
        raise AppError("DOCUMENTO_NO_ENCONTRADO", "El documento no existe", 404)
    if doc["estado"] not in ("aprobado", "exportado"):
        raise AppError("ESTADO_INVALIDO", "Solo se exporta un documento aprobado (A-17)", 409)
    final = conexion.execute(SQL["version_final_doc"], {"documento_id": documento_id}).fetchone()
    if not final:
        raise AppError("ESTADO_INVALIDO", "No hay versión final aprobada", 409)
    nombre = doc["nombre_original"].rsplit(".", 1)[0] + "_anonimizado.pdf"
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
    pdf = componer(texto_plano(conexion, revisada, revisada),
                   bool(_config(conexion, "pdf_export_incluir_marcas_agua", True)))
    huella = hashlib.sha256(pdf).hexdigest()
    ruta = f"{documento_id}/v{final['numero_version']}.pdf"
    storage.guardar(ruta, pdf, cifrar=False)  # el PDF ya está anonimizado
    conexion.execute(SQL["version_pdf_set"], {"id": final["id"], "ruta": ruta, "hash": huella})
    conexion.execute(SQL["doc_exportado"], {"id": documento_id})
    audit.registrar(conexion, "PDF_EXPORTADO", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="documento", entidad_id=documento_id,
                    detalle={"version_id": str(final["id"]), "hash": huella, "bytes": len(pdf)})
    return pdf, huella, nombre
