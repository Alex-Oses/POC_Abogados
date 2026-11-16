"""Prueba de Presidio en local con un texto jurídico en castellano (datos ficticios).

Uso:
  pip install presidio-analyzer presidio-anonymizer
  python -m spacy download es_core_news_md
  python investigacion/presidio/prueba_es.py
"""
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

TEXTO = (
    "Procedimiento ordinario 1014/2019. Magistrado-Juez: Ilmo. Sr. D. Fernando Ruiz Calvo. "
    "Por la representación procesal de D. Raúl Gómez Cañizares, con DNI 22633920B y domicilio en "
    "calle Mayor, n.º 112, 43003 Tarragona, se presentó demanda. Testigo: Ana Pérez Soler, con NIE X1234567L. "
    "La actora aporta correo raul.gomez@ejemplo.com y teléfono 612 345 678, y solicita el pago en la cuenta "
    "ES91 2100 0418 4502 0005 1332. El vehículo matrícula 4821 KLM fue retirado. "
    "Referencia catastral 1973060DF9313N0001XY. FALLO: se condena a Construcciones Levante, S.L. al pago de las costas."
)

# Lo que un revisor anonimizaría (según la propuesta). La empresa NO, porque CENDOJ solo anonimiza personas físicas.
ESPERADO = {
    "Fernando Ruiz Calvo": "PERSON", "Raúl Gómez Cañizares": "PERSON", "Ana Pérez Soler": "PERSON",
    "22633920B": "ES_NIF", "X1234567L": "ES_NIE", "raul.gomez@ejemplo.com": "EMAIL_ADDRESS",
    "612 345 678": "PHONE_NUMBER", "ES91 2100 0418 4502 0005 1332": "IBAN_CODE",
    "1973060DF9313N0001XY": "ES_REF_CATASTRAL", "calle Mayor, n.º 112": "LOCATION",
}

nlp = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "es", "model_name": "es_core_news_md"}],
}).create_engine()

registry = RecognizerRegistry(supported_languages=["es"])
registry.load_predefined_recognizers(languages=["es"], nlp_engine=nlp)
# Presidio no trae estos dos para España: se añaden con un patrón.
registry.add_recognizer(PatternRecognizer(
    supported_entity="ES_REF_CATASTRAL", supported_language="es",
    patterns=[Pattern("catastral", r"\b\d{7}[A-Z]{2}\d{4}[A-Z]\d{4}[A-Z]{2}\b", 0.9)]))
registry.add_recognizer(PatternRecognizer(
    supported_entity="PHONE_NUMBER", supported_language="es",
    patterns=[Pattern("movil_es", r"\b[6789]\d{2}[ ]?\d{3}[ ]?\d{3}\b", 0.6)],
    context=["teléfono", "móvil", "tel"]))

analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp, supported_languages=["es"])
resultados = analyzer.analyze(text=TEXTO, language="es")

print("Detectado:")
for r in sorted(resultados, key=lambda r: r.start):
    print(f"  {r.entity_type:<18} {r.score:.2f}  {TEXTO[r.start:r.end]}")

detectados = {TEXTO[r.start:r.end] for r in resultados}
acertados = [t for t in ESPERADO if any(t in d or d in t for d in detectados)]
print(f"\nCobertura: {len(acertados)}/{len(ESPERADO)}")
print("No detectado:", [t for t in ESPERADO if t not in acertados])
print("Falsos positivos:", sorted(d for d in detectados if not any(d in t or t in d for t in ESPERADO)))

anon = AnonymizerEngine().anonymize(
    text=TEXTO, analyzer_results=resultados,
    operators={"DEFAULT": OperatorConfig("replace", {"new_value": "[DATO]"}),
               "PERSON": OperatorConfig("replace", {"new_value": "[PERSONA]"})})
print("\nAnonimizado (modo etiqueta):\n" + anon.text)
