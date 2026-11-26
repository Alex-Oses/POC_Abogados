import re
from functools import lru_cache
from typing import Any

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


@lru_cache(maxsize=1)
def _cargar_analyzer() -> Any | None:
    """Inicializa Presidio AnalyzerEngine si está instalado en el entorno."""
    try:
        from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
        from presidio_analyzer.nlp_engine import NlpEngineProvider
    except ImportError:
        return None

    try:
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "es", "model_name": "es_core_news_lg"}],
            }
        )
        nlp_engine = provider.create_engine()
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["es"])
    except Exception:
        return None

    dni_recognizer = PatternRecognizer(
        supported_entity="DNI_NIE",
        supported_language="es",
        patterns=[
            Pattern(
                name="dni_nie_es",
                regex=r"\b(?:[XYZ]\d{7}|\d{8})[-\s]?[A-HJ-NP-TV-Z]\b",
                score=0.85,
            )
        ],
    )
    analyzer.registry.add_recognizer(dni_recognizer)
    return analyzer


def detectar_entidades_presidio(texto: str, idioma: str = "es") -> list[dict[str, Any]]:
    """Detecta las 6 categorías iniciales de datos personales en el propio backend.

    Categorías: Nombre y apellidos (PERSON), DNI/NIE (DNI_NIE),
    Correo electrónico (EMAIL_ADDRESS), Teléfono (PHONE_NUMBER),
    Dirección (LOCATION) e IBAN (IBAN_CODE).
    """
    if not texto:
        return []

    analyzer = _cargar_analyzer()
    if analyzer is not None:
        resultados = analyzer.analyze(
            text=texto,
            language=idioma,
            entities=list(CATEGORIAS_ANONIMIZACION.keys()),
        )
        return [
            {
                "tipo": res.entity_type,
                "inicio": res.start,
                "fin": res.end,
                "texto_original": texto[res.start : res.end],
                "texto_sustitucion": CATEGORIAS_ANONIMIZACION.get(res.entity_type, "[ANONIMIZADO]"),
                "confianza": res.score,
            }
            for res in sorted(resultados, key=lambda r: r.start)
        ]

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
