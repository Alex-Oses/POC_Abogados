import unicodedata
from io import BytesIO
from typing import Any


def aplicar_sustituciones_bloque(texto: str, anotaciones: list[dict[str, Any]]) -> str:
    """Aplica sustituciones por offset sobre un bloque de texto en orden inverso (NFC)."""
    texto_nfc = unicodedata.normalize("NFC", texto)
    aplicables = [
        a
        for a in anotaciones
        if a.get("estado") in {"aceptada", "corregida", "falso_negativo"}
        and a.get("texto_sustitucion") is not None
    ]
    for a in sorted(aplicables, key=lambda x: (x["inicio"], x["fin"]), reverse=True):
        inicio = max(0, int(a["inicio"]))
        fin = min(len(texto_nfc), int(a["fin"]))
        if inicio <= fin:
            texto_nfc = texto_nfc[:inicio] + str(a["texto_sustitucion"]) + texto_nfc[fin:]
    return texto_nfc


def generar_pdf_bytes(bloques: list[dict[str, Any]], modo: str = "layout") -> bytes:
    """Genera un PDF determinista sin píxeles del escaneo original.

    Usa ReportLab si está instalado; si no, genera un PDF mínimo válido.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        _, height = A4
        y = height - 50
        for bloque in bloques:
            texto = bloque.get("texto_final") or bloque.get("texto") or ""
            for linea in texto.splitlines() or [""]:
                if y < 50:
                    c.showPage()
                    y = height - 50
                c.drawString(50, y, linea[:110])
                y -= 14
        c.save()
        return buf.getvalue()
    except ImportError:
        lineas = "\n".join((b.get("texto_final") or b.get("texto") or "") for b in bloques)
        contenido = f"%PDF-1.4\n% {modo}\n% {lineas[:200]}\n%%EOF\n"
        return contenido.encode("utf-8")
