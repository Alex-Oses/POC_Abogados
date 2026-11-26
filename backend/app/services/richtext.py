"""Texto con formato por página: saneado con lista blanca y paso a marcado de ReportLab.

El texto plano derivado del HTML sigue siendo la fuente para búsqueda, JG y offsets de Presidio.
"""

import re
from html import escape
from html.parser import HTMLParser

ETIQUETAS = {"p", "div", "br", "b", "strong", "i", "em", "u", "s", "mark", "span", "font"}
BLOQUES = {"p", "div"}
DESCARTAR = {"script", "style", "template", "iframe", "object", "embed", "svg", "math",
             "noscript", "textarea", "title", "head"}  # su contenido tampoco se conserva
FUENTES = {"georgia": "Times-Roman", "times new roman": "Times-Roman", "arial": "Helvetica",
           "verdana": "Helvetica", "courier new": "Courier", "roboto": "Helvetica"}
_COLOR = re.compile(r"#[0-9a-f]{3}|#[0-9a-f]{6}|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)")
_TAMANO = re.compile(r"(\d{1,2}(?:\.\d+)?)(px|pt)")
_TAMANO_FONT = {"1": 8, "2": 10, "3": 12, "4": 14, "5": 18, "6": 24, "7": 36}  # execCommand


def _fuente(valor: str) -> str | None:
    for nombre in valor.split(","):
        nombre = nombre.strip().strip("'\"").lower()
        if nombre in FUENTES:
            return nombre
    return None


def _estilo(css: str) -> dict:
    """Solo las propiedades y valores permitidos; lo demás (url(), expression...) se descarta."""
    salida = {}
    for decl in css.split(";"):
        prop, _, valor = decl.partition(":")
        prop, valor = prop.strip().lower(), valor.strip().lower()
        tamano = _TAMANO.fullmatch(valor)
        if prop == "font-family" and _fuente(valor):
            salida[prop] = _fuente(valor)
        elif ((prop == "font-size" and tamano and 8 <= float(tamano[1]) <= 48)
              or (prop in ("color", "background-color") and _COLOR.fullmatch(valor))
              or (prop == "text-decoration" and valor in ("underline", "line-through"))
              or (prop == "font-weight" and valor in ("bold", "700"))
              or (prop == "font-style" and valor == "italic")):
            salida[prop] = valor
    return salida


class _Saneador(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.html: list[str] = []
        self.texto: list[str] = []
        self.pila: list[str] = []
        self.ignorar = 0

    def _salto(self):
        if self.texto and not self.texto[-1].endswith("\n"):
            self.texto.append("\n")

    def handle_starttag(self, tag, attrs):
        if tag in DESCARTAR:
            self.ignorar += 1
            return
        if self.ignorar or tag not in ETIQUETAS:
            return
        if tag in BLOQUES:
            self._salto()
        if tag == "br":
            self.texto.append("\n")
            self.html.append("<br>")
            return
        partes = []
        for nombre, valor in attrs:
            valor = (valor or "").strip()
            if nombre == "style" and (css := _estilo(valor)):
                partes.append('style="' + escape("; ".join(f"{k}: {v}" for k, v in css.items())) + '"')
            elif tag == "font" and nombre == "face" and _fuente(valor):
                partes.append(f'face="{escape(_fuente(valor))}"')
            elif tag == "font" and nombre == "size" and valor in _TAMANO_FONT:
                partes.append(f'size="{valor}"')
            elif tag == "font" and nombre == "color" and _COLOR.fullmatch(valor.lower()):
                partes.append(f'color="{escape(valor.lower())}"')
        self.html.append(f"<{tag}{''.join(' ' + p for p in partes)}>")
        self.pila.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in DESCARTAR:
            return  # <script/> no abre nada
        self.handle_starttag(tag, attrs)
        if tag != "br" and self.pila and self.pila[-1] == tag:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in DESCARTAR:
            self.ignorar = max(0, self.ignorar - 1)
            return
        if self.ignorar or tag not in self.pila:
            return
        while self.pila:  # cierra también lo que quedó abierto dentro
            abierta = self.pila.pop()
            self.html.append(f"</{abierta}>")
            if abierta == tag:
                break
        if tag in BLOQUES:
            self._salto()

    def handle_data(self, data):
        if not self.ignorar:
            self.html.append(escape(data, quote=False))
            self.texto.append(data)


def sanear(html: str) -> tuple[str, str]:
    """(html saneado, texto plano con saltos de línea)."""
    s = _Saneador()
    s.feed(html)
    s.close()
    s.html.extend(f"</{t}>" for t in reversed(s.pila))
    return "".join(s.html), "".join(s.texto).rstrip("\n")


# --- ReportLab -----------------------------------------------------------------------------

def _hex(color: str) -> str:
    if color.startswith("rgb"):
        r, g, b = (min(int(n), 255) for n in re.findall(r"\d+", color))
        return f"#{r:02x}{g:02x}{b:02x}"
    return color


class _ReportLab(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.cierres: list[str] = []
        self.mayor = 0.0

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.out.append("<br/>")
            return
        if tag in BLOQUES:
            if self.out and not self.out[-1].endswith("<br/>"):
                self.out.append("<br/>")
            self.cierres.append("")
            return
        abre, cierra = [], []
        simples = {"b": "b", "strong": "b", "i": "i", "em": "i", "u": "u", "s": "strike"}
        if tag in simples:
            abre.append(f"<{simples[tag]}>")
            cierra.insert(0, f"</{simples[tag]}>")
        a = dict(attrs)
        css = _estilo(a.get("style", ""))
        font = {}
        if fuente := css.get("font-family") or (_fuente(a.get("face", "")) if tag == "font" else None):
            font["face"] = FUENTES[fuente]
        if m := _TAMANO.fullmatch(css.get("font-size", "")):
            font["size"] = float(m[1]) * (0.75 if m[2] == "px" else 1)
        elif tag == "font" and a.get("size") in _TAMANO_FONT:
            font["size"] = _TAMANO_FONT[a["size"]]
        color = css.get("color") or (a.get("color", "") if tag == "font" else "")
        if _COLOR.fullmatch(color.lower()):
            font["color"] = _hex(color.lower())
        if fondo := css.get("background-color"):
            font["backColor"] = _hex(fondo)
        elif tag == "mark":
            font["backColor"] = "#ffff00"
        if font:
            self.mayor = max(self.mayor, font.get("size", 0))
            abre.append("<font " + " ".join(f'{k}="{v}"' for k, v in font.items()) + ">")
            cierra.insert(0, "</font>")
        for decl, (o, c) in (("font-weight", ("<b>", "</b>")), ("font-style", ("<i>", "</i>"))):
            if decl in css:
                abre.append(o)
                cierra.insert(0, c)
        deco = css.get("text-decoration")
        if deco:
            t = "u" if deco == "underline" else "strike"
            abre.append(f"<{t}>")
            cierra.insert(0, f"</{t}>")
        self.out.append("".join(abre))
        self.cierres.append("".join(cierra))

    def handle_endtag(self, tag):
        if tag != "br" and self.cierres:
            self.out.append(self.cierres.pop())

    def handle_data(self, data):
        self.out.append(escape(data, quote=False))


def a_reportlab(html_saneado: str) -> tuple[str, float]:
    """Marcado de Paragraph para una página y el mayor tamaño de letra usado (para el interlineado)."""
    p = _ReportLab()
    p.feed(html_saneado)
    p.close()
    return "".join(p.out) or "&nbsp;", p.mayor
