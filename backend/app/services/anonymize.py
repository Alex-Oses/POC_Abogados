"""Detección con Presidio (0006) y sustituciones (formas de la maqueta).

Configuración «mejorada» de `investigacion/presidio/benchmark.py` (docs/presidio.md §6):
patrones propios para matrícula, catastral, dirección, teléfono y DNI con puntos; nombres en
mayúsculas; sin personas jurídicas, municipios ni instituciones.
"""

import re
from functools import lru_cache

from psycopg import Connection

from app.core.config import settings
from app.core.errors import AppError
from app.db.queries import SQL
from app.services import audit
from app.services.documents import nueva_version

CONSONANTES = "BCDFGHJKLMNPRSTVWXYZ"
# Entidad de Presidio → código de `categorias_sensibles` (V11).
MAPA = {"ES_NIF": "DNI_NIE", "ES_NIE": "DNI_NIE", "PERSON": "NOMBRE_PERSONA",
        "PHONE_NUMBER": "TELEFONO", "EMAIL_ADDRESS": "EMAIL", "DIRECCION": "DIRECCION",
        "LOCATION": "DIRECCION", "IBAN_CODE": "IBAN", "MATRICULA": "MATRICULA",
        "ES_REF_CATASTRAL": "REF_CATASTRAL", "IP_ADDRESS": "IP", "NUSS": "NUSS"}
IGNORAR = ["DNI", "NIE", "FALLO", "Testigo", "ANTECEDENTES", "HECHO", "SENTENCIA", "TRIBUNAL",
           "JUSTICIA", "JUTJAT", "Magistrado-Juez", "Ilmo", "ESTIMAR", "ESTIMO", "IBAN", "IRPF",
           "NIF", "Don", "Doña"]
# shortcut: lista corta de municipios; en producción, el nomenclátor completo de Catalunya.
MUNICIPIOS = {"Tarragona", "Reus", "Valls", "El Vendrell", "Tortosa", "Girona", "Barcelona",
              "Lleida", "Madrid"}
INSTITUCION_RX = re.compile(r"(?:La\s)?(?:Ley|Llei|Audiencia|Audiència|Juzgado|Jutjat|Colegio|"
                            r"Col·legi|Tribunal|Agencia|Agència|Seguridad|Seguretat|Ayuntamiento)\b")
EMPRESA_RX = re.compile(r"[A-ZÀ-Ú][\wÀ-ÿ·]+(?:\s[A-ZÀ-Ú][\wÀ-ÿ·]+)*,\s*S\.[LA]\.")
MAYUS_RX = re.compile(r"\b[A-ZÀ-Ú·]{2,}(?:\s+[A-ZÀ-Ú·]+)+\b")

# Forma de la maqueta → accion_aplicada (V15).
MODOS = {"censurar": "censurar", "borrar": "eliminado", "tachar": "tachado",
         "etiqueta": "etiqueta", "seudonimo": "pseudonimizado", "iniciales": "iniciales"}


@lru_cache
def motor():
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_analyzer.predefined_recognizers import (
        EmailRecognizer,
        EsNieRecognizer,
        EsNifRecognizer,
        IbanRecognizer,
        IpRecognizer,
        PhoneRecognizer,
        SpacyRecognizer,
    )

    nlp = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "es", "model_name": settings.spacy_model}]}).create_engine()
    reg = RecognizerRegistry(supported_languages=["es"])
    for rec in (EsNifRecognizer(supported_language="es"), EsNieRecognizer(supported_language="es"),
                IbanRecognizer(supported_language="es"), EmailRecognizer(supported_language="es"),
                IpRecognizer(supported_language="es"),
                PhoneRecognizer(supported_language="es", supported_regions=("ES",)),
                SpacyRecognizer(supported_language="es", supported_entities=["PERSON", "LOCATION"])):
        reg.add_recognizer(rec)

    def patron(entidad, rx, score=0.85):
        reg.add_recognizer(PatternRecognizer(supported_entity=entidad, supported_language="es",
                                             patterns=[Pattern(entidad, rx, score)]))

    patron("ES_REF_CATASTRAL", r"\b\d{7}[A-Z]{2}\d{4}[A-Z]\d{4}[A-Z]{2}\b")
    patron("MATRICULA", rf"\b\d{{4}}[\s-]?[{CONSONANTES}]{{3}}\b")
    patron("PHONE_NUMBER", r"(?:\+34\s?)?\b[6789]\d{2}(?:\s?\d{2}){3}\b|\b[6789]\d{2}\s?\d{3}\s?\d{3}\b", 0.6)
    patron("ES_NIF", r"\b\d{1,2}\.\d{3}\.\d{3}-?[A-Z]\b", 0.7)
    patron("NUSS", r"\b\d{2}/\d{8}/\d{2}\b", 0.8)
    patron("DIRECCION",
           r"(?i)\b(?:calle|c/|c\.|avenida|avda\.|plaza|paseo|carrer|pla[çc]a|rambla|passeig)\s[^,\n]{2,40}"
           r"(?:,?\s*(?:n\.?º|núm\.?)?\s*\d+(?![.\d]))?(?:,\s*\d\.º\s*\d\.ª)?(?:,\s*\d{5})?"
           r"(?:,?\s*(?:de\s)?[A-ZÀ-Ú][\wÀ-ÿ'·]*(?:\s[A-ZÀ-Ú][\wÀ-ÿ'·]*)?)?")
    return AnalyzerEngine(registry=reg, nlp_engine=nlp, supported_languages=["es"])


def detectar(texto: str) -> list[dict]:
    """Entidades sin solapes: [{inicio, fin, entidad, score}] ordenadas por posición."""
    if not texto.strip():
        return []
    leido = MAYUS_RX.sub(lambda m: m.group().title(), texto)  # mismas posiciones
    res = sorted(motor().analyze(text=leido, language="es", allow_list=IGNORAR),
                 key=lambda x: x.start)
    unidos = []
    for x in res:  # «Jordi Puig i Serra»: el modelo corta en la «i»
        p = unidos[-1] if unidos else None
        if p and p.entity_type == x.entity_type == "PERSON" and texto[p.end:x.start].lower() in (" i ", " y "):
            p.end = x.end
        else:
            unidos.append(x)
    for x in unidos:  # el modelo a veces arrastra la línea siguiente: se corta en el salto
        salto = texto.find("\n", x.start, x.end)
        if salto > x.start and x.entity_type in ("PERSON", "LOCATION"):
            x.end = salto
    empresas = [(m.start(), m.end()) for m in EMPRESA_RX.finditer(texto)]
    candidatos = [
        x for x in unidos
        if x.entity_type in MAPA
        and not (x.entity_type == "LOCATION" and (texto[x.start:x.end] in MUNICIPIOS
                                                  or INSTITUCION_RX.match(texto, x.start)))
        and not any(x.start < e and b < x.end for b, e in empresas)]
    # Solapes: gana la de mayor puntuación y, a igualdad, la más larga.
    candidatos.sort(key=lambda x: (-x.score, -(x.end - x.start)))
    elegidos: list = []
    for x in candidatos:
        if all(x.end <= y.start or x.start >= y.end for y in elegidos):
            elegidos.append(x)
    return [{"inicio": x.start, "fin": x.end, "entidad": x.entity_type,
             "score": round(min(max(x.score, 0), 1), 3)} for x in sorted(elegidos, key=lambda x: x.start)]


def sustitucion(accion: str, texto: str, codigo: str, seudonimos: dict) -> str | None:
    if accion in ("censurar", "tachado"):
        return "█" * len(texto)
    if accion == "eliminado":
        return ""
    if accion == "etiqueta":
        return f"[{codigo}]"
    if accion == "iniciales":
        return " ".join(p[0].upper() + "." for p in texto.split() if p[0].isalpha()) or "█"
    if accion == "pseudonimizado":
        # La misma persona recibe siempre la misma letra en todo el documento.
        clave = (codigo, " ".join(texto.lower().split()))
        if clave not in seudonimos:
            n = sum(1 for c, _ in seudonimos if c == codigo)
            seudonimos[clave] = (f"Persona {chr(65 + n % 26)}{'' if n < 26 else n // 26}"
                                 if codigo == "NOMBRE_PERSONA" else f"[{codigo} {n + 1}]")
        return seudonimos[clave]
    return None  # mantenido


def aplicar(contenido: str, anotaciones: list[dict]) -> str:
    """Texto de salida de un bloque: nunca deja visible el origen de una entidad sustituida."""
    for a in sorted(anotaciones, key=lambda a: a["inicio_offset"], reverse=True):
        if a["decision_revisor"] == "falso_positivo" or a["accion_aplicada"] == "mantenido":
            continue
        nuevo = a["texto_sustitucion"]
        if nuevo is None:
            nuevo = "█" * (a["fin_offset"] - a["inicio_offset"])
        contenido = contenido[:a["inicio_offset"]] + nuevo + contenido[a["fin_offset"]:]
    return contenido


def anonimizar(conexion: Connection, doc: dict, regla_id, modo: str, usuario: dict, request,
               estados: tuple = ("ocr_completado",)) -> dict:
    if doc["estado"] not in estados:
        raise AppError("ESTADO_INVALIDO", "Solo se anonimiza un documento con OCR completado", 409)
    # Siempre desde la última transcripción: en una reapertura la vigente es otra.
    origen = conexion.execute(
        "SELECT id FROM versiones_documento WHERE documento_id = %(d)s AND tipo_version = 'ocr_texto' "
        "ORDER BY numero_version DESC LIMIT 1", {"d": doc["id"]}).fetchone()
    if not origen:
        raise AppError("SIN_TEXTO", "No hay transcripción que anonimizar", 422)
    accion = MODOS.get(modo)
    if not accion:
        raise AppError("VALIDACION", f"modo debe ser uno de {sorted(MODOS)}", 400)
    if regla_id:
        if not conexion.execute(SQL["regla_por_id"], {"id": regla_id}).fetchone():
            raise AppError("REGLA_NO_ENCONTRADA", "La regla no existe", 404)
        categorias = conexion.execute(SQL["categorias_de_regla"], {"regla_id": regla_id}).fetchall()
    else:
        # Sin reglas sembradas en V1..V15: se usan todas las categorías activas.
        categorias = conexion.execute(SQL["categorias_listar"], {"activa": True}).fetchall()
    por_codigo = {c["codigo"]: c for c in categorias}

    version = nueva_version(conexion, doc["id"], "anonimizado_ia", usuario["usuario_id"],
                            regla_id=regla_id, modelo_ia=f"presidio+{settings.spacy_model}",
                            meta={"modo": modo, "version_origen": str(origen["id"])})
    bloques = conexion.execute(SQL["bloques_copiar"],
                               {"origen": origen["id"], "destino": version["id"]}).fetchall()
    conexion.execute(SQL["version_texto_recalcular"], {"id": version["id"]})
    if not any(b["contenido"].strip() for b in bloques):
        raise AppError("SIN_TEXTO", "No hay texto que anonimizar", 422)

    detectadas = {b["id"]: detectar(b["contenido"]) for b in bloques}
    # Un dato visto en una página se marca en todas sus apariciones: el NER no siempre
    # lo reconoce en cada contexto (cabeceras, mayúsculas).
    vistos = {b["contenido"][e["inicio"]:e["fin"]]: e["entidad"]
              for b in bloques for e in detectadas[b["id"]] if e["fin"] - e["inicio"] >= 4}
    for b in bloques:
        for valor, entidad in vistos.items():
            for m in re.finditer(re.escape(valor), b["contenido"]):
                if all(m.end() <= e["inicio"] or m.start() >= e["fin"] for e in detectadas[b["id"]]):
                    detectadas[b["id"]].append({"inicio": m.start(), "fin": m.end(),
                                                "entidad": entidad, "score": 0.5})

    seudonimos: dict = {}
    total = 0
    for bloque in bloques:
        for e in detectadas[bloque["id"]]:
            categoria = por_codigo.get(MAPA[e["entidad"]])
            if not categoria:
                continue
            texto = bloque["contenido"][e["inicio"]:e["fin"]]
            conexion.execute(SQL["anotacion_insertar"], {
                "version_id": version["id"], "bloque_id": bloque["id"],
                "categoria_id": categoria["id"], "inicio": e["inicio"], "fin": e["fin"],
                "texto": texto, "pagina": bloque["pagina_numero"], "accion": accion,
                "sustitucion": sustitucion(accion, texto, categoria["codigo"], seudonimos),
                "confianza": e["score"], "motor": "presidio", "regla_id": regla_id,
                "decision": None, "revisado_por": None})
            total += 1
    conexion.execute(SQL["doc_estado"], {"id": doc["id"], "estado": "en_revision"})
    audit.registrar(conexion, "ANONIMIZACION_IA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="documento", entidad_id=doc["id"],
                    detalle={"version_id": str(version["id"]), "anotaciones": total, "modo": modo,
                             "regla_id": str(regla_id) if regla_id else None})
    return {"version_id": version["id"], "numero_version": version["numero_version"],
            "anotaciones": total}


def _revision_abierta(conexion: Connection, version_id) -> None:
    if not conexion.execute(SQL["revision_en_proceso_version"], {"version_id": version_id}).fetchone():
        raise AppError("REVISION_NO_EN_PROCESO",
                       "La revisión de esta versión no está en proceso", 409)


def decidir(conexion: Connection, anotacion_id, cambios: dict, usuario: dict, request) -> dict:
    fila = conexion.execute(SQL["anotacion_por_id"], {"id": anotacion_id}).fetchone()
    if not fila:
        raise AppError("ANOTACION_NO_ENCONTRADA", "La anotación no existe", 404)
    _revision_abierta(conexion, fila["version_id"])
    decision = cambios.get("decision_revisor")
    accion = cambios.get("accion_aplicada") or fila["accion_aplicada"]
    actual = conexion.execute(
        "SELECT texto_sustitucion, texto_original, observaciones_revisor, c.codigo "
        "FROM anotaciones_entidad a JOIN categorias_sensibles c ON c.id = a.categoria_id "
        "WHERE a.id = %(id)s", {"id": anotacion_id}).fetchone()
    sust = cambios.get("texto_sustitucion")
    if sust is None and "accion_aplicada" in cambios:
        sust = sustitucion(accion, actual["texto_original"], actual["codigo"], {})
    if sust is None:
        sust = actual["texto_sustitucion"]
    if decision in ("confirmado", "modificado", "falso_negativo") and sust is None and accion != "mantenido":
        raise AppError("SUSTITUCION_REQUERIDA", "Esta decisión exige texto_sustitucion", 422)
    conexion.execute(SQL["anotacion_actualizar"], {
        "id": anotacion_id, "accion": accion, "sustitucion": sust, "decision": decision,
        "observaciones": cambios.get("observaciones_revisor", actual["observaciones_revisor"]),
        "revisado_por": usuario["usuario_id"]})
    audit.registrar(conexion, "ENTIDAD_REVISADA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="anotacion", entidad_id=anotacion_id,
                    detalle={"decision": decision, "accion": accion})
    return {"id": anotacion_id, "accion_aplicada": accion, "texto_sustitucion": sust,
            "decision_revisor": decision}


def crear_manual(conexion: Connection, doc: dict, datos: dict, usuario: dict, request) -> dict:
    """Falso negativo: el revisor marca un dato que el detector no vio."""
    if doc["v_tipo"] != "anonimizado_ia":
        raise AppError("ESTADO_INVALIDO", "El documento no está anonimizado", 409)
    _revision_abierta(conexion, doc["v_id"])
    bloque = conexion.execute(
        "SELECT id, pagina_numero, contenido FROM bloques_layout WHERE id = %(id)s AND version_id = %(v)s",
        {"id": datos["bloque_id"], "v": doc["v_id"]}).fetchone()
    if not bloque:
        raise AppError("BLOQUE_NO_ENCONTRADO", "El bloque no es de la versión vigente", 404)
    if not 0 <= datos["inicio_offset"] < datos["fin_offset"] <= len(bloque["contenido"]):
        raise AppError("VALIDACION", "Offsets fuera del bloque", 400)
    categoria = conexion.execute("SELECT codigo FROM categorias_sensibles WHERE id = %(id)s",
                                 {"id": datos["categoria_id"]}).fetchone()
    if not categoria:
        raise AppError("CATEGORIA_NO_ENCONTRADA", "La categoría no existe", 404)
    texto = bloque["contenido"][datos["inicio_offset"]:datos["fin_offset"]]
    accion = datos.get("accion_aplicada") or "censurar"
    sust = datos.get("texto_sustitucion") or sustitucion(accion, texto, categoria["codigo"], {})
    fila = conexion.execute(SQL["anotacion_insertar"], {
        "version_id": doc["v_id"], "bloque_id": bloque["id"], "categoria_id": datos["categoria_id"],
        "inicio": datos["inicio_offset"], "fin": datos["fin_offset"], "texto": texto,
        "pagina": bloque["pagina_numero"], "accion": accion, "sustitucion": sust,
        "confianza": 1, "motor": "manual", "regla_id": None, "decision": "falso_negativo",
        "revisado_por": usuario["usuario_id"]}).fetchone()
    audit.registrar(conexion, "ENTIDAD_ANADIDA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="anotacion", entidad_id=fila["id"],
                    detalle={"categoria": categoria["codigo"], "accion": accion})
    return {"id": fila["id"], "texto_sustitucion": sust}


def texto_plano(conexion: Connection, version_id, bloques_version_id) -> list[str]:
    """Texto de salida por página, con las decisiones aplicadas."""
    anotaciones = conexion.execute(SQL["anotaciones_para_aplicar"],
                                   {"version_id": version_id}).fetchall()
    bloques = conexion.execute(SQL["bloques_version"], {
        "version_id": bloques_version_id, "pagina": None, "limit": 100000, "offset": 0}).fetchall()
    paginas: dict[int, list[str]] = {}
    for b in bloques:
        propias = [a for a in anotaciones if a["bloque_id"] == b["id"]]
        paginas.setdefault(b["pagina_numero"], []).append(aplicar(b["contenido"], propias))
    return ["\n\n".join(v) for _, v in sorted(paginas.items())]

