"""OCR con PaddleOCR-VL por Ollama (0001). Lógica traída de `ocr_web_app.py`.

Trabaja con bytes en memoria: ninguna página del original queda en claro en disco.
"""

import base64
import difflib
import io
import json
import re
import time
import urllib.request

from app.core.config import settings

DPI = 150
_MOCK = ("Don Juan Pérez García, con DNI 12345678Z y domicilio en Barcelona, "
         "solicita justicia gratuita. IBAN ES91 2100 0418 4502 0005 1332.")


def renderizar(datos: bytes, mime: str) -> list[dict]:
    """Una entrada por página: PNG a 150 dpi, tamaño en píxeles y capa de texto (si hay)."""
    import pymupdf as fitz

    if mime == "application/pdf":
        doc = fitz.open(stream=datos, filetype="pdf")
    else:
        doc = fitz.open(stream=datos, filetype=mime.split("/")[1])
    paginas = []
    for pagina in doc:
        pix = pagina.get_pixmap(dpi=DPI)
        capa = pagina.get_text() if mime == "application/pdf" else ""
        paginas.append({"png": pix.tobytes("png"), "ancho": pix.width, "alto": pix.height,
                        "capa": capa})
    doc.close()
    return paginas


def png_pagina(datos: bytes, mime: str, numero: int) -> bytes:
    import pymupdf as fitz

    tipo = "pdf" if mime == "application/pdf" else mime.split("/")[1]
    doc = fitz.open(stream=datos, filetype=tipo)
    if not 1 <= numero <= len(doc):
        doc.close()
        return b""
    png = doc[numero - 1].get_pixmap(dpi=DPI).tobytes("png")
    doc.close()
    return png


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
    import hashlib

    clave = hashlib.sha256(png).hexdigest()
    if clave not in _LINEAS:
        from rapidocr_onnxruntime import RapidOCR

        _LINEAS[clave] = RapidOCR()(png)[0] or []
    norm = lambda x: re.sub(r"\W", "", x).lower()  # RapidOCR junta palabras
    buscados = [norm(texto)] + [norm(w) for w in texto.split() if len(norm(w)) >= 3]
    for buscado in filter(None, buscados):
        for puntos, linea, _conf in _LINEAS[clave]:
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


def cajas(pdf: bytes | None, numero: int, candidatos: list[list[str]], escala: float):
    """Caja en píxeles de la página renderizada de cada duda, si el PDF tiene capa de texto."""
    if not pdf:
        return [None] * len(candidatos)
    try:
        import pymupdf as fitz

        doc = fitz.open(stream=pdf, filetype="pdf")
        pagina = doc[numero - 1]
        salida = []
        for lista in candidatos:
            rect = next((h[0] for c in lista if c for h in [pagina.search_for(c)] if h), None)
            salida.append(None if rect is None else {
                "x": round(rect.x0 * escala, 1), "y": round(rect.y0 * escala, 1),
                "ancho": round(rect.width * escala, 1), "alto": round(rect.height * escala, 1)})
        doc.close()
        return salida
    except Exception:  # noqa: BLE001 - sin caja el aviso sigue valiendo
        return [None] * len(candidatos)


def procesar_pagina(pagina: dict, numero: int, doble: bool, pdf: bytes | None) -> dict:
    """Semáforo de calidad, OCR y, en doble lectura (A-24), las diferencias con su caja."""
    c = contraste(pagina["png"])
    legible = c >= settings.contraste_minimo
    t, texto, diff = 0.0, "", None
    avisos: list[dict] = []
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
