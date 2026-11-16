# Anonimización en local con Presidio

- **Estado**: investigado; informe completo con mediciones
- **Responsable**: @Alex
- **Coste (deuda técnica)**: ~1 h la primera prueba + ~3 h el banco de pruebas (13 configuraciones, 150 documentos ficticios por idioma y corpus de validación aparte).
- **Documentación y rendimiento**: [`docs/presidio.md`](../../docs/presidio.md) (también en PDF)
- **Pruebas reproducibles**: `investigacion/presidio/prueba_es.py` (texto corto) y `investigacion/presidio/benchmark.py` (corpus y mediciones)

## Qué es

[Presidio](https://presidio.dataprivacystack.org/) (Microsoft, código abierto, Python) detecta datos personales (*analyzer*) y los transforma (*anonymizer*). Funciona 100 % en local: spaCy para nombres y lugares + patrones con validación para identificadores.

## Qué trae ya para nuestro caso

| Necesidad (ver [[Propuesta ICAT]]) | Presidio |
|---|---|
| DNI / NIE / pasaporte | `ES_NIF`, `ES_NIE` (patrón + letra de control), `ES_PASSPORT` |
| IBAN | `IBAN_CODE` (dígito de control) |
| Correo, teléfono | `EMAIL_ADDRESS`, `PHONE_NUMBER` |
| Nombres, lugares, empresas | `PERSON`, `LOCATION`, `ORGANIZATION` vía spaCy `es_core_news_*` |
| Formas: censurar, etiqueta, seudónimo, iniciales | Operadores `redact`, `replace`, `mask`, `hash`, `encrypt` y `custom` (función propia) |
| Seudónimo reversible y cifrado | `encrypt` + `DeanonymizeEngine` con `decrypt` |
| Firmas y datos en la imagen | `presidio-image-redactor`, pero necesita las coordenadas de cada palabra (usa Tesseract) |

## Resultado de la prueba (spaCy `es_core_news_md`)

**Cobertura 10/10** de los datos esperados, con **6 falsos positivos**:

- Perfectos (puntuación 1,0): DNI, NIE, IBAN, correo, teléfono y referencia catastral (con un patrón propio).
- Nombres de persona: los 3 detectados.
- Direcciones: **parcial**. Detecta «calle Mayor» y «Tarragona», pero se le escapan «n.º 112» y el código postal «43003».
- Falsos positivos: «DNI», «Testigo», «FALLO» y «KLM» se toman por personas, lugares o empresas. «Construcciones Levante, S.L.» se clasifica como lugar, así que se anonimizaría aunque, según el CENDOJ, las personas jurídicas no se anonimizan.
- Matrículas: no las detecta (hace falta un patrón).

## Conclusión

Sirve como motor de detección local. Los identificadores con dígito de control son fiables; el reconocimiento de nombres y lugares necesita ajuste y **siempre** revisión humana, que la propuesta ya exige.

## Resultado medido (150 sentencias ficticias por idioma)

Castellano con `es_core_news_md`, contando el dato **tapado del todo**:

| | De serie | Configuración «mejorada» |
|---|---|---|
| Datos cubiertos | 71,2 % | 100 % (94,4 % con corpus de validación) |
| Precisión | 62,8 % | 98,8 % |
| Texto inocente tapado por página | 6,3 | 0,17 |
| Tiempo / memoria | — | 65 ms/página · 339 MB |

Catalán (`ca_core_news_md`): 96,7 % en el corpus de ajuste y 88,9 % en el de validación. Con un **4 % de errores de OCR**, el castellano baja al 89 %: la anonimización no puede fiarse de un OCR malo, de ahí el semáforo de calidad. El modelo `lg` no mejora al `md` y ocupa 2,6 veces más. Detalle y desglose por tipo de dato en [`docs/presidio.md`](../../docs/presidio.md).

## Riesgo detectado: coordenadas para tapar la imagen

PaddleOCR-VL por Ollama (prompt `OCR:`) devuelve **solo texto, sin posiciones**. La decisión [[0006-generacion-pdf-final]] ya resuelve la exportación sin ellas: se reconstruye un PDF nuevo desde la estructura guardada, con el texto anonimizado, y `origen_geometria` admite los dos modos. Queda la pregunta al contrato: `GET /blocks` pide un `bbox` por bloque y hoy nada puede rellenarlo. Ver [[Tablero]] § Preguntas abiertas.

## Siguiente

- [x] Probar `es_core_news_lg` (no mejora al `md`) y el modelo catalán.
- [x] Lista de palabras a ignorar y regla «S.L./S.A. → empresa».
- [x] Patrones para dirección completa, matrícula y referencia catastral.
- [x] Nombres en mayúsculas y catalanes con «i».
- [ ] Repetir la medición con 100-200 páginas reales anonimizadas del Colegio (fase 0 de la propuesta).
- [ ] Mover la configuración «mejorada» al backend, con la lista de excepciones versionada.
- [ ] Cerrar [[0004-anonimizacion-antes-o-despues-de-revision]]: la revisión humana necesita el original durante el proceso.
