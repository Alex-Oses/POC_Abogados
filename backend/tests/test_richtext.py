"""Saneado del texto con formato y formas del PDF exportado (sin BD)."""

from app.services import export, richtext


def _texto_pdf(datos: bytes) -> str:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(datos)
    try:
        textpage = doc[0].get_textpage()
        try:
            return textpage.get_text_range()
        finally:
            textpage.close()
    finally:
        doc.close()


def test_sanear_quita_xss():
    sucio = ('<p style="color:#ff0000;background:url(javascript:alert(1));font-family:Arial">Hola'
             '<img src=x onerror="alert(1)"><script>alert(2)</script>'
             '<a href="javascript:alert(3)" class="c" data-x="1">enlace</a></p>'
             '<div onclick="x()" style="background-color:url(javascript:a)">otra</div>')
    html, texto = richtext.sanear(sucio)
    for veneno in ("img", "onerror", "script", "alert(2)", "javascript", "href", "<a", "class",
                   "data-x", "onclick", "url("):
        assert veneno not in html, veneno
    assert html == '<p style="color: #ff0000; font-family: arial">Holaenlace</p><div>otra</div>'
    assert texto == "Holaenlace\notra"


def test_sanear_formato_y_texto():
    html, texto = richtext.sanear('a<div><b>b</b><br></div><div><font face="Georgia" size="5" '
                                  'color="#00f" onmouseover="x">c</font></div><u>&lt;d&gt;')
    assert html == ('a<div><b>b</b><br></div><div><font face="georgia" size="5" color="#00f">c'
                    '</font></div><u>&lt;d&gt;</u>')
    assert texto == "a\nb\nc\n<d>"  # el <br> final de un div es el relleno del navegador
    marcado, mayor = richtext.a_reportlab(html)
    assert '<font face="Times-Roman" size="18" color="#00f">' in marcado and mayor == 18
    assert export.componer(["x"], False, {"1": html}).startswith(b"%PDF")


def test_pdf_censurar_y_borrar_sin_original():
    contenido = "Don Juan Pérez García, DNI 12345678Z, vive en Reus."
    notas = [{"inicio_offset": 4, "fin_offset": 21, "accion_aplicada": "censurar"},
             {"inicio_offset": 27, "fin_offset": 36, "accion_aplicada": "eliminado"}]
    for n in notas:
        n |= {"decision_revisor": "confirmado", "texto_sustitucion": None}
    marcado, tachado = export.marcar(contenido, notas)
    pdf = export.componer([marcado], True)
    texto = _texto_pdf(pdf)
    assert not tachado and "vive en Reus" in texto
    for original in ("Juan", "Pérez", "García", "12345678Z"):
        assert original not in texto and original.encode() not in pdf


def test_pdf_tachado_avisa():
    nota = {"inicio_offset": 0, "fin_offset": 4, "accion_aplicada": "tachado",
            "decision_revisor": "confirmado", "texto_sustitucion": None}
    marcado, tachado = export.marcar("Juan vive", [nota])
    pdf = export.componer([marcado], False, tachado=tachado)
    texto = _texto_pdf(pdf)
    assert tachado and export.AVISO_TACHADO in texto and "Juan" in texto
