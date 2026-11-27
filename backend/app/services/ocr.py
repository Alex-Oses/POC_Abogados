"""OCR con PaddleOCR-VL por Ollama (0001). Lógica traída de `ocr_web_app.py`.

Trabaja con bytes en memoria: ninguna página del original queda en claro en disco.
"""

import base64
import difflib
import io
import json
import re
import threading
import time
import urllib.request

from app.core.config import settings
from app.core.logging import log

DPI = 150
_MOCK = ("Don Juan Pérez García, con DNI 12345678Z y domicilio en Barcelona, "
         "solicita justicia gratuita. IBAN ES91 2100 0418 4502 0005 1332.")


def _pdfium(datos: bytes):
    """PDF abierto con pypdfium2 (Apache-2.0/BSD-3): PDFium no impone la AGPL de PyMuPDF."""
    import pypdfium2 as pdfium

    return pdfium.PdfDocument(datos)


def _png_de(pagina, escala: float) -> tuple[bytes, int, int]:
    pil = pagina.render(scale=escala).to_pil()
    salida = io.BytesIO()
    pil.save(salida, "PNG")
    return salida.getvalue(), pil.width, pil.height


def _capa(pagina) -> str:
    textpage = pagina.get_textpage()
    try:
        return textpage.get_text_range()
    finally:
        textpage.close()


def _imagen(datos: bytes) -> dict:
    """JPG/PNG sueltos: una sola página, sin capa de texto, convertida a PNG."""
    from PIL import Image

    with Image.open(io.BytesIO(datos)) as im:
        ancho, alto = im.size
        salida = io.BytesIO()
        im.convert("RGB").save(salida, "PNG")
    return {"png": salida.getvalue(), "ancho": ancho, "alto": alto, "capa": ""}


def renderizar(datos: bytes, mime: str) -> list[dict]:
    """Una entrada por página: PNG a 150 dpi, tamaño en píxeles y capa de texto (si hay)."""
    if mime != "application/pdf":
        return [_imagen(datos)]
    doc = _pdfium(datos)
    paginas = []
    try:
        for indice in range(len(doc)):
            pagina = doc[indice]
            png, ancho, alto = _png_de(pagina, DPI / 72)
            paginas.append({"png": png, "ancho": ancho, "alto": alto, "capa": _capa(pagina)})
    finally:
        doc.close()
    return paginas


def contar(datos: bytes, mime: str) -> int:
    if mime != "application/pdf":
        return 1
    doc = _pdfium(datos)
    try:
        return len(doc)
    finally:
        doc.close()


def una_pagina(datos: bytes, mime: str, numero: int) -> dict:
    """Como `renderizar`, pero solo la página `numero` (la cola no carga todo el PDF en PNG)."""
    if mime != "application/pdf":
        if numero != 1:
            raise IndexError("La imagen tiene una sola página")
        return _imagen(datos)
    doc = _pdfium(datos)
    try:
        pagina = doc[numero - 1]
        png, ancho, alto = _png_de(pagina, DPI / 72)
        return {"png": png, "ancho": ancho, "alto": alto, "capa": _capa(pagina)}
    finally:
        doc.close()


def png_pagina(datos: bytes, mime: str, numero: int) -> bytes:
    if mime != "application/pdf":
        return _imagen(datos)["png"] if numero == 1 else b""
    doc = _pdfium(datos)
    try:
        if not 1 <= numero <= len(doc):
            return b""
        return _png_de(doc[numero - 1], DPI / 72)[0]
    finally:
        doc.close()


def contraste(png: bytes) -> int:
    """Distancia entre la tinta (percentil 0,05 %) y el papel (99,5 %), 0-255."""
    from PIL import Image

    hist = Image.open(io.BytesIO(png)).convert("L").histogram()
    total = sum(hist)
    acc, lo, hi = 0, None, 255
    for nivel, n in enumerate(hist):
        acc += n
        if lo is None and acc >= total * 0.0005:
            lo = nivel
        if acc >= total * 0.995:
            hi = nivel
            break
    return int(hi - (lo or 0))


def leer(png: bytes, temperatura: float = 0, capa: str = "") -> tuple[float, str]:
    if settings.ocr_mock:
        time.sleep(settings.ocr_mock_delay)  # simula la lentitud del modelo en pruebas
        # Sin modelo: se usa la capa de texto del PDF si existe, para probar con contenido real.
        texto = capa.strip() or _MOCK
        if temperatura > 0:
            texto = texto.replace("domicilio", "domicilo").replace("solicita", "solicito")
        return 0.05, texto
    cuerpo = {
        "model": settings.ocr_model,
        "prompt": "OCR:",
        "images": [base64.b64encode(png).decode()],
        "stream": False,
        "options": {"temperature": temperatura, "num_ctx": 4096, "repeat_penalty": 1.05,
                    "num_predict": 1500},
    }
    inicio = time.time()
    peticion = urllib.request.Request(settings.ollama_url + "/api/generate",
                                      json.dumps(cuerpo).encode(),
                                      {"Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=300) as r:
        respuesta = json.loads(r.read())
    return time.time() - inicio, respuesta.get("response", "").strip()


def variante(png: bytes) -> bytes:
    """Misma página preparada de otra forma para la segunda lectura."""
    from PIL import Image, ImageOps

    im = Image.open(io.BytesIO(png)).convert("L")
    im = im.resize((int(im.width * 1.35), int(im.height * 1.35)), Image.LANCZOS)
    salida = io.BytesIO()
    ImageOps.autocontrast(im, cutoff=1).save(salida, "PNG")
    return salida.getvalue()


_LINEAS: dict[str, list] = {}  # shortcut: caché en memoria por hash de la imagen; se pierde al reiniciar
_CANDADO = threading.Lock()  # una sola pasada de RapidOCR a la vez; quien llega después espera y reutiliza


def _lineas(png: bytes) -> list:
    import hashlib

    clave = hashlib.sha256(png).hexdigest()
    if clave not in _LINEAS:
        with _CANDADO:
            if clave not in _LINEAS:
                from rapidocr_onnxruntime import RapidOCR

                _LINEAS[clave] = RapidOCR()(png)[0] or []
    return _LINEAS[clave]


def calentar(png: bytes) -> None:
    """Precalcula en segundo plano las líneas de RapidOCR de un escaneo (recuadro instantáneo)."""
    def tarea():
        try:
            _lineas(png)
        except Exception:  # noqa: BLE001 - sin caché, `locate` lo calcula al pedirlo
            log.warning("rapidocr_precalculo_fallido")
    threading.Thread(target=tarea, daemon=True).start()


def localizar(png: bytes, pdf: bytes | None, numero: int, texto: str) -> dict | None:
    """Caja en píxeles de `texto` en la página: capa de texto del PDF o, en escaneos,
    líneas de RapidOCR (PaddleOCR-VL no da coordenadas) con la palabra situada por proporción."""
    texto = texto.strip()
    if not texto:
        return None
    if pdf:
        caja = cajas(pdf, numero, [[texto] + texto.split()], DPI / 72)[0]
        if caja:
            return caja
    lineas = _lineas(png)
    norm = lambda x: re.sub(r"\W", "", x).lower()  # RapidOCR junta palabras
    buscados = [norm(texto)] + [norm(w) for w in texto.split() if len(norm(w)) >= 3]
    for buscado in filter(None, buscados):
        for puntos, linea, _conf in lineas:
            n = norm(linea)
            i = n.find(buscado)
            if i < 0:
                continue
            xs, ys = [p[0] for p in puntos], [p[1] for p in puntos]
            x0, x1 = min(xs), max(xs)
            a, b = i / len(n), (i + len(buscado)) / len(n)
            return {"x": round(x0 + (x1 - x0) * a, 1), "y": round(min(ys), 1),
                    "ancho": round((x1 - x0) * (b - a), 1), "alto": round(max(ys) - min(ys), 1)}
    return None


def diferencias(a: str, b: str) -> list[dict]:
    """Trozos del primer texto marcando los que no coinciden con la segunda lectura."""
    ta = re.findall(r"\S+\s*", a)
    tb = re.findall(r"\S+\s*", b)
    ka = [t.strip() for t in ta]
    kb = [t.strip() for t in tb]
    unidos: list[dict] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ka, b=kb).get_opcodes():
        t = "".join(ta[i1:i2])
        otro = "" if tag == "equal" else " ".join(kb[j1:j2])
        diff = tag != "equal"
        if unidos and unidos[-1]["diff"] == diff:
            unidos[-1]["t"] += t
            if diff:
                unidos[-1]["other"] = (unidos[-1]["other"] + " " + otro).strip()
        else:
            unidos.append({"t": t, "diff": diff, "other": otro})
    return [s for s in unidos if s["t"]]


def _caja_texto(textpage, buscado: str, alto_pt: float, escala: float) -> dict | None:
    """Caja en píxeles del primer `buscado` en la capa de texto (coordenadas PDF: origen abajo)."""
    texto = textpage.get_text_range()
    inicio = texto.lower().find(buscado.lower())
    if inicio < 0:
        return None
    fin = min(inicio + len(buscado) - 1, max(textpage.count_chars() - 1, 0))
    x0, y0, x1, y1 = textpage.get_charbox(inicio)
    x2, y2, x3, y3 = textpage.get_charbox(fin)
    izq, der = min(x0, x2), max(x1, x3)
    abajo, arriba = min(y0, y2), max(y1, y3)
    return {"x": round(izq * escala, 1), "y": round((alto_pt - arriba) * escala, 1),
            "ancho": round((der - izq) * escala, 1), "alto": round((arriba - abajo) * escala, 1)}


def cajas(pdf: bytes | None, numero: int, candidatos: list[list[str]], escala: float):
    """Caja en píxeles de la página renderizada de cada duda, si el PDF tiene capa de texto."""
    if not pdf:
        return [None] * len(candidatos)
    try:
        doc = _pdfium(pdf)
        try:
            pagina = doc[numero - 1]
            alto_pt = pagina.get_height()
            textpage = pagina.get_textpage()
            try:
                salida = []
                for lista in candidatos:
                    caja = next((c for c in (_caja_texto(textpage, texto, alto_pt, escala)
                                             for texto in lista if texto) if c), None)
                    salida.append(caja)
                return salida
            finally:
                textpage.close()
        finally:
            doc.close()
    except Exception:  # noqa: BLE001 - sin caja el aviso sigue valiendo
        return [None] * len(candidatos)


def procesar_pagina(pagina: dict, numero: int, doble: bool, pdf: bytes | None) -> dict:
    """Semáforo de calidad, OCR y, en doble lectura (A-24), las diferencias con su caja."""
    c = contraste(pagina["png"])
    legible = c >= settings.contraste_minimo
    t, texto, diff = 0.0, "", None
    avisos: list[dict] = []
    escaneo = legible and not pagina["capa"].strip()
    if escaneo:
        calentar(pagina["png"])  # en paralelo con el modelo: no frena el flujo
    if legible:  # página mala: el modelo inventaría texto, así que no se lee
        t, texto = leer(pagina["png"], 0, pagina["capa"])
        if doble:
            # A-24: la segunda lectura es independiente: otra imagen (más resolución, gris y
            # contraste estirado). Con la misma imagen el modelo repite la lectura palabra a palabra.
            t2, texto2 = leer(variante(pagina["png"]), 0.3, pagina["capa"])
            t += t2
            diff = diferencias(texto, texto2)
            dudas = [s for s in diff if s["diff"]]
            rects = cajas(pdf, numero, [s["t"].split() + s["other"].split() for s in dudas],
                          DPI / 72)
            for s, rect in zip(dudas, rects, strict=True):
                if not rect and escaneo:  # sin capa de texto: líneas de RapidOCR (ya calentadas)
                    try:
                        rect = (localizar(pagina["png"], None, numero, s["t"])
                                or localizar(pagina["png"], None, numero, s["other"]))
                    except Exception:  # noqa: BLE001 - sin caja el aviso sigue valiendo
                        rect = None
                aviso = {"tipo": "doble_lectura",
                         "mensaje": f"Lectura dudosa: «{s['t'].strip()}» / «{s['other']}»"}
                if rect:
                    aviso["bbox"] = rect
                avisos.append(aviso)
    else:
        avisos.append({"tipo": "contraste_bajo",
                       "mensaje": f"Contraste {c} < {settings.contraste_minimo}: volver a escanear"})
    estado = "ilegible" if not legible else ("revisar" if avisos else "ok")
    return {"numero": numero, "contraste": c, "estado": estado, "leida_ocr": legible,
            "texto": texto, "diferencias": diff, "avisos": avisos, "tiempo": round(t, 2),
            "ancho": pagina["ancho"], "alto": pagina["alto"]}
