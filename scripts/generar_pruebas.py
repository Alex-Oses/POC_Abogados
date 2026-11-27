"""Genera documentos de prueba variados en pruebas/ (todo ficticio, AGENTS.md: nunca datos reales).

Uso:  backend/.venv/Scripts/python scripts/generar_pruebas.py      (Linux: backend/.venv/bin/python)

DNI con letra válida pero inventados; IBAN con formato español de ejemplo.
Sin PyMuPDF (AGPL): se compone con ReportLab y se rasteriza con pypdfium2.
"""

import io
import random
from pathlib import Path

from PIL import Image, ImageFilter

SALIDA = Path(__file__).resolve().parents[1] / "pruebas"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

DNI = "Documento Nacional de Identidad\nNombre: Laura Martín Soler\nDNI 87654321X\nNacimiento: 01/02/1985"
PADRON = ("Volante de empadronamiento\nPadrón municipal de Tarragona\n"
          "Domicilio: calle Ficticia 12, 43001 Tarragona\nConviven 3 personas en el domicilio")
IRPF = "Declaración IRPF modelo 100 ejercicio 2025\nBase imponible general 14.250,75\nCuota líquida 1.020,00"
BIENES = "Certificado de bienes\nRegistro de la propiedad de Tarragona\nSin titularidad catastral a su nombre"
JUZGADO = ("Juzgado de Primera Instancia 3 de Tarragona\nProcedimiento ordinario nº 456/2026\n"
           "Cédula de notificación a Laura Martín Soler, domiciliada en calle Ficticia 12, Tarragona")
CONTRATO = ("Contrato de arrendamiento de vivienda\nReunidos de una parte Pere Vidal Roca, DNI 11111111H,\n"
            "y de otra Laura Martín Soler, DNI 87654321X.\nLas partes acuerdan la cláusula primera:\n"
            "renta mensual de 650,00 euros, que se ingresará en la cuenta ES91 2100 0418 4502 0005 1332.\n"
            "Teléfono de contacto 600 123 456 · correo laura.ficticia@example.com")
CATALAN = ("SOL·LICITUD DE JUSTÍCIA GRATUÏTA\nNom: Jordi Ficticio Puig\nDNI 12345678Z\n"
           "Ingressos: 9.800 EUR\nDomicili a carrer Major 7, Reus")


def nomina(mes: str) -> str:
    return (f"Nómina {mes} 2026\nRecibo de salarios de Laura Martín Soler\n"
            "Total devengado 1.350,00\nLíquido a percibir 1.187,40")


def _pdf_bytes(paginas: list[str], color=(0.0, 0.0, 0.0)) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    alto = A4[1]
    for texto in paginas:
        lienzo.setFillColorRGB(*color)
        y = alto - 90
        for linea in texto.split("\n"):
            lienzo.drawString(72, y, linea)
            y -= 16
        lienzo.showPage()
    lienzo.save()
    return buffer.getvalue()


def pdf(nombre: str, paginas: list[str], color=(0.0, 0.0, 0.0)) -> None:
    (SALIDA / nombre).write_bytes(_pdf_bytes(paginas, color))


def _rasterizar(datos: bytes, dpi: int = 150) -> Image.Image:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(datos)
    try:
        return doc[0].render(scale=dpi / 72).to_pil().convert("L")
    finally:
        doc.close()


def imagen(texto: str, *, girar=0.0, ruido=0, desenfoque=0.0, gris=0) -> Image.Image:
    """Renderiza el texto y lo «escanea»: giro, ruido y desenfoque como un escáner barato."""
    img = _rasterizar(_pdf_bytes([texto], (gris / 255,) * 3))
    if ruido:
        rnd = random.Random(7)
        px = img.load()
        for _ in range(img.width * img.height * ruido // 100):
            x, y = rnd.randrange(img.width), rnd.randrange(img.height)
            px[x, y] = rnd.choice((0, 255))
    if desenfoque:
        img = img.filter(ImageFilter.GaussianBlur(desenfoque))
    return img.rotate(girar, expand=True, fillcolor=255) if girar else img


def pdf_escaneado(nombre: str, imagenes: list[Image.Image]) -> None:
    """PDF solo imagen, sin capa de texto (como un escáner real)."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer)
    for img in imagenes:
        b = io.BytesIO()
        img.convert("RGB").save(b, "PNG")
        b.seek(0)
        ancho = img.width * 72 / 150
        alto = img.height * 72 / 150
        lienzo.setPageSize((ancho, alto))
        lienzo.drawImage(ImageReader(b), 0, 0, width=ancho, height=alto)
        lienzo.showPage()
    lienzo.save()
    (SALIDA / nombre).write_bytes(buffer.getvalue())


def main() -> None:
    SALIDA.mkdir(exist_ok=True)
    pdf("01_dni.pdf", [DNI])
    pdf("02_nomina_enero.pdf", [nomina("enero")])
    pdf("03_padron.pdf", [PADRON])
    pdf("04_irpf.pdf", [IRPF])
    pdf("05_notificacion_juzgado.pdf", [JUZGADO])
    pdf("06_contrato_datos_personales.pdf", [CONTRATO])
    pdf("07_solicitud_catalan.pdf", [CATALAN])
    # Justicia gratuita completa: todos los requeridos y 12 nóminas.
    pdf("08_expediente_jg_completo.pdf", [DNI, PADRON, IRPF, BIENES, JUZGADO] + [nomina(m) for m in MESES])
    # Incompleto: faltan bienes y 9 nóminas.
    pdf("09_expediente_jg_incompleto.pdf", [DNI, PADRON, IRPF, JUZGADO] + [nomina(m) for m in MESES[:3]])
    # Página casi blanca: el semáforo la marca ilegible.
    pdf("10_pagina_ilegible.pdf", [DNI, BIENES], color=(0.93, 0.93, 0.93))
    pdf("11_largo_20_paginas.pdf", [f"Página {i} del expediente 456/2026\n{CONTRATO}" for i in range(1, 21)])
    # Escaneos sin capa de texto: limpio, torcido con ruido y muy degradado.
    pdf_escaneado("12_escaneo_limpio.pdf", [imagen(JUZGADO)])
    pdf_escaneado("13_escaneo_torcido_ruido.pdf", [imagen(CONTRATO, girar=2.5, ruido=2)])
    pdf_escaneado("14_escaneo_degradado.pdf", [imagen(DNI, desenfoque=2.2, ruido=6, gris=150)])
    imagen(PADRON, girar=-1.5, ruido=1).save(SALIDA / "15_padron_foto.jpg", quality=70)
    imagen(DNI).save(SALIDA / "16_dni.png")
    (SALIDA / "17_no_es_pdf.pdf").write_bytes(b"esto no es un PDF")  # debe rechazarse (415)
    print(f"{len(list(SALIDA.iterdir()))} ficheros en {SALIDA}")


if __name__ == "__main__":
    main()
