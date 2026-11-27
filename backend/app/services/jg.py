"""Comprobación orientativa de la documentación de justicia gratuita.

AGENTS.md: la herramienta no decide; solo orienta. La decisión es de la Comisión.
Clasifica cada página por palabras clave y extrae datos con expresiones regulares.
"""

import json
import re
import unicodedata

from psycopg import Connection

from app.core import storage
from app.core.errors import AppError
from app.db.queries import SQL
from app.services import audit, ocr

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
# Orden importa: la primera regla que casa gana. Palabras sin acentos y en minúscula.
TIPOS = [
    ("irpf", "Declaración de IRPF", ["irpf", "renta de las personas fisicas", "base imponible", "modelo 100"]),
    ("nomina", "Nóminas (12 meses)", ["nomina", "recibo de salarios", "liquido a percibir", "total devengado"]),
    ("empadronamiento", "Certificado de empadronamiento", ["empadronamiento", "padron municipal", "volante de empadronamiento"]),
    ("certificado_bienes", "Certificado de bienes", ["certificado de bienes", "catastro", "titularidad catastral", "indice de bienes", "registro de la propiedad"]),
    ("notificacion_juzgado", "Notificación del juzgado", ["juzgado", "diligencia", "cedula de notificacion", "procedimiento", "autos"]),
    ("contrato", "Contrato", ["contrato de", "arrendamiento", "las partes", "clausula"]),
    ("dni", "DNI / NIE", ["documento nacional de identidad", "dni", "nie", "permiso de residencia"]),
]
REQUERIDOS = ["dni", "empadronamiento", "nomina", "irpf", "certificado_bienes", "notificacion_juzgado"]
LETRAS = "TRWAGMYFPDXBNJZSQVHLCKE"
DNI_RX = re.compile(r"\b([XYZ]?)[\s.]?(\d{1,2}\.?\d{3}\.?\d{3})[\s-]?([A-Z])\b")


def _plano(texto: str) -> str:
    sin = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin.lower()


def dni_valido(prefijo: str, numero: str, letra: str) -> bool:
    cifras = numero.replace(".", "")
    if prefijo:
        cifras = str("XYZ".index(prefijo)) + cifras
    return cifras.isdigit() and LETRAS[int(cifras) % 23] == letra


def clasificar(texto: str) -> str | None:
    plano = _plano(texto)
    for codigo, _, claves in TIPOS:
        if any(re.search(rf"\b{re.escape(c)}\b", plano) for c in claves):
            return codigo
    return None


def _importe(valor: str) -> float:
    return float(valor.replace(".", "").replace(",", "."))


def extraer(textos: dict[int, str], tipos: dict[int, str | None]) -> dict:
    todo = "\n".join(textos.values())
    datos: dict = {"solicitante": None, "dni": None, "dni_valido": None, "ingresos_anuales": None,
                   "miembros_unidad_familiar": None, "procedimiento": None, "domicilio": None}
    nombre = re.search(r"(?:\b(?:D\.|Dña\.|Don|Doña)\s+|(?i:solicitante|sol·licitant|nombre y apellidos|nom i cognoms|nombre|nom)\s*:\s*)"
                       r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de\s+|del\s+|la\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,4})",
                       todo)
    if nombre:
        datos["solicitante"] = nombre.group(1)
    dni = DNI_RX.search(todo)
    if dni:
        datos["dni"] = "".join(dni.groups()).replace(".", "")
        datos["dni_valido"] = dni_valido(*dni.groups())
    irpf = "\n".join(t for n, t in textos.items() if tipos.get(n) == "irpf")
    base = re.search(r"base\s+imponible\s+general[^\d]{0,40}([\d.]+,\d{2})", irpf, re.IGNORECASE) or \
        re.search(r"base\s+imponible[^\d]{0,40}([\d.]+,\d{2})", irpf, re.IGNORECASE)
    # Sin IRPF: una línea «Ingresos/Ingressos: 9.000 EUR» en cualquier página (ES o CA).
    base = base or re.search(r"\bingres(?:os|sos)(?:\s+anual(?:es|s))?\s*:?\s*([\d.]+(?:,\d{2})?)", todo,
                             re.IGNORECASE)
    if base:
        datos["ingresos_anuales"] = _importe(base.group(1))
    padron = "\n".join(t for n, t in textos.items() if tipos.get(n) == "empadronamiento")
    if padron:
        explicito = re.search(r"(\d+)\s+(?:personas|habitantes|miembros)", padron, re.IGNORECASE)
        datos["miembros_unidad_familiar"] = (
            int(explicito.group(1)) if explicito
            else len({m.group(0) for m in DNI_RX.finditer(padron)}) or None)
    proc = re.search(r"((?:procedimiento|juicio|autos)[^\n]{0,60}?(?:n\.?º|núm\.?)\s*\d+/\d{2,4})",
                     todo, re.IGNORECASE)
    if proc:
        datos["procedimiento"] = proc.group(1).strip()
    dom = re.search(r"domicili(?:o|ado|ada)\s+(?:en\s+)?([^\n.]{5,90})", todo, re.IGNORECASE) or \
        re.search(r"\b((?:calle|c/|avenida|avda\.|plaza|paseo|carrer|rambla)\s[^\n]{3,80})", todo, re.IGNORECASE)
    if dom:
        datos["domicilio"] = dom.group(1).strip(" ,")
    return datos


def comprobar(conexion: Connection, doc: dict, usuario: dict, request) -> dict:
    origen = conexion.execute(
        "SELECT id FROM versiones_documento WHERE documento_id = %(d)s AND tipo_version = 'ocr_texto' "
        "ORDER BY numero_version DESC LIMIT 1", {"d": doc["id"]}).fetchone()
    if not origen:
        raise AppError("SIN_TEXTO", "El documento no tiene transcripción", 422)
    bloques = conexion.execute(SQL["bloques_version"], {"version_id": origen["id"], "pagina": None,
                                                        "limit": 100000, "offset": 0}).fetchall()
    estados = {p["numero"]: p["estado"] for p in conexion.execute(
        "SELECT numero, estado FROM paginas_documento WHERE documento_id = %(d)s", {"d": doc["id"]})}
    textos: dict[int, str] = {}
    for b in bloques:
        textos[b["pagina_numero"]] = textos.get(b["pagina_numero"], "") + "\n" + b["contenido"]

    # Página ilegible: no se transcribió, pero la capa de texto del PDF puede decir qué es.
    capas: dict[int, str] = {}
    if doc["mime_type"] == "application/pdf" and "ilegible" in estados.values():
        paginas = ocr.renderizar(storage.leer(doc["ruta_almacenamiento"]), "application/pdf")
        capas = {i: p["capa"] for i, p in enumerate(paginas, 1)}
    tipos = {n: clasificar(t) for n, t in textos.items() if t.strip()}
    tipos_ilegibles = {n: clasificar(capas.get(n, "")) for n, e in estados.items() if e == "ilegible"}

    documentos = []
    for codigo, nombre, _ in TIPOS:
        paginas = sorted(n for n, t in tipos.items() if t == codigo)
        ilegibles = sorted(n for n, t in tipos_ilegibles.items() if t == codigo)
        if paginas:
            estado = "presente"
        elif ilegibles:
            estado = "ilegible"
        else:
            estado = "falta"
        entrada = {"tipo": codigo, "nombre": nombre, "requerido": codigo in REQUERIDOS,
                   "estado": estado, "paginas": paginas, "paginas_ilegibles": ilegibles}
        if codigo == "nomina" and paginas:
            meses = sorted({m for n in paginas for m in MESES if m in _plano(textos[n])},
                           key=MESES.index)
            entrada["meses"] = meses
            if len(meses) < 12:
                entrada["estado"] = "incompleto"
                entrada["detalle"] = f"{len(meses)} de 12 meses"
        if entrada["requerido"] or paginas:
            documentos.append(entrada)
    faltan = [d["nombre"] for d in documentos
              if d["requerido"] and d["estado"] in ("falta", "ilegible", "incompleto")]
    resultado = {
        "orientativo": True,
        "aviso": "Orientativo, no vinculante: la decisión es de la Comisión.",
        "documentos": documentos,
        "paginas_sin_clasificar": sorted(n for n in textos if n not in tipos and textos[n].strip()),
        "paginas_ilegibles": sorted(n for n, e in estados.items() if e == "ilegible"),
        "datos": extraer(textos, tipos),
        "completo": not faltan,
        "requerimiento": None if not faltan else (
            "Para continuar con la solicitud de asistencia jurídica gratuita, le rogamos que aporte "
            "la siguiente documentación: " + "; ".join(faltan) + "."),
    }
    conexion.execute(SQL["doc_meta_set"], {"id": doc["id"], "ruta": ["justicia_gratuita"],
                                           "valor": json.dumps(resultado, ensure_ascii=False)})
    audit.registrar(conexion, "JG_COMPROBADO", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="documento", entidad_id=doc["id"],
                    detalle={"completo": resultado["completo"], "faltan": faltan})
    return resultado


def enviar(conexion: Connection, doc: dict, usuario: dict, request) -> dict:
    jg = (doc["metadatos_extras"] or {}).get("justicia_gratuita")
    if not jg:
        raise AppError("JG_SIN_COMPROBAR", "Primero hay que comprobar la documentación", 409)
    fila = conexion.execute("UPDATE documentos SET metadatos_extras = jsonb_set(metadatos_extras, "
                            "'{justicia_gratuita,enviado_en}', to_jsonb(now())) WHERE id = %(id)s "
                            "RETURNING metadatos_extras->'justicia_gratuita'->>'enviado_en' AS enviado_en",
                            {"id": doc["id"]}).fetchone()
    audit.registrar(conexion, "JG_ENVIADO", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="documento", entidad_id=doc["id"],
                    detalle={"completo": jg.get("completo")})
    return {"id": doc["id"], "enviado_en": fila["enviado_en"]}
