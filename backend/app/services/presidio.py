import re
from functools import lru_cache
from typing import Any

from app.core.config import settings

# Categorías iniciales de anonimización en el backend (Presidio local)
CATEGORIAS_ANONIMIZACION: dict[str, str] = {
    "PERSON": "[NOMBRE]",
    "DNI_NIE": "[DNI/NIE]",
    "EMAIL_ADDRESS": "[EMAIL]",
    "PHONE_NUMBER": "[TELEFONO]",
    "LOCATION": "[DIRECCION]",
    "IBAN_CODE": "[IBAN]",
}

_PATRONES_FALLBACK: list[tuple[str, re.Pattern[str]]] = [
    ("DNI_NIE", re.compile(r"\b(?:[XYZ]\d{7}|\d{8})[-\s]?[A-HJ-NP-TV-Z]\b", re.IGNORECASE)),
    ("EMAIL_ADDRESS", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("IBAN_CODE", re.compile(r"\bES\d{2}(?:[\s-]?\d{4}){5}\b", re.IGNORECASE)),
    ("PHONE_NUMBER", re.compile(r"(?:\+34[\s-]?)?\b[6789]\d{2}(?:[\s-]?\d{3}){2}\b")),
]


CONSONANTES = "BCDFGHJKLMNPRSTVWXYZ"
# Entidades del registro propio → categorías iniciales de este módulo.
_A_CATEGORIA = {"ES_NIF": "DNI_NIE", "ES_NIE": "DNI_NIE"}


@lru_cache(maxsize=1)
def cargar_analyzer() -> Any | None:
    """AnalyzerEngine de Presidio, o None si Presidio/spaCy no están instalados.

    Registro «mejorado» medido en `investigacion/presidio/benchmark.py` (docs/presidio.md §6):
    NIF/NIE con letra de control, IBAN, correo, IP, teléfono ES, PERSON/LOCATION de spaCy y
    patrones propios (catastral, matrícula, teléfono, NIF con puntos, NUSS, dirección).
    """
    try:
        from presidio_analyzer import (
            AnalyzerEngine,
            Pattern,
            PatternRecognizer,
            RecognizerRegistry,
        )
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
    except ImportError:
        return None

    try:
        nlp = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "es", "model_name": settings.spacy_model}]}).create_engine()
    except Exception:  # noqa: BLE001 - sin modelo de spaCy se usa el fallback por regex
        return None
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


def detectar_entidades_presidio(texto: str, idioma: str = "es") -> list[dict[str, Any]]:
    """Detecta las 6 categorías iniciales de datos personales en el propio backend.

    Categorías: Nombre y apellidos (PERSON), DNI/NIE (DNI_NIE),
    Correo electrónico (EMAIL_ADDRESS), Teléfono (PHONE_NUMBER),
    Dirección (LOCATION) e IBAN (IBAN_CODE).
    """
    if not texto:
        return []

    analyzer = cargar_analyzer()
    if analyzer is not None:
        resultados = analyzer.analyze(text=texto, language=idioma)
        hallazgos = []
        for res in sorted(resultados, key=lambda r: r.start):
            tipo = _A_CATEGORIA.get(res.entity_type, res.entity_type)
            if tipo in CATEGORIAS_ANONIMIZACION:
                hallazgos.append({
                    "tipo": tipo,
                    "inicio": res.start,
                    "fin": res.end,
                    "texto_original": texto[res.start : res.end],
                    "texto_sustitucion": CATEGORIAS_ANONIMIZACION[tipo],
                    "confianza": res.score,
                })
        return hallazgos

    # Fallback determinista por regex cuando Presidio/spaCy no están instalados
    hallazgos: list[dict[str, Any]] = []
    for tipo, patron in _PATRONES_FALLBACK:
        for match in patron.finditer(texto):
            hallazgos.append(
                {
                    "tipo": tipo,
                    "inicio": match.start(),
                    "fin": match.end(),
                    "texto_original": match.group(0),
                    "texto_sustitucion": CATEGORIAS_ANONIMIZACION[tipo],
                    "confianza": 0.75,
                }
            )
    return sorted(hallazgos, key=lambda item: item["inicio"])
