# Anonimización en local con Presidio

- **Estado**: primera prueba hecha
- **Responsable**: @Alex
- **Coste (deuda técnica)**: ~1 h de prueba guiada por IA. Pendiente lo de abajo.
- **Prueba reproducible**: `investigacion/presidio/prueba_es.py` (texto jurídico ficticio en castellano)

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

## Riesgo detectado: coordenadas para tapar la imagen

PaddleOCR-VL por Ollama (prompt `OCR:`) devuelve **solo texto, sin posiciones**. Para borrar datos de la imagen del PDF hacen falta las cajas de cada palabra, y el contrato de `docs/api/endpoints.md` (`/blocks`, campo `bbox`) también las espera. Pregunta abierta a @Rubén en el [[Tablero]]. Opciones:

1. **Exportar un PDF nuevo generado desde el texto anonimizado**, sin la imagen original (es lo que ya propone `/transform/build` en la [[API]]). Es lo más simple y elimina el riesgo de dejar datos en la imagen. Recomendado para el POC.
2. Sacar las cajas con un segundo OCR (Tesseract o PaddleOCR clásico) y alinearlas con el texto. Es más fiel al original, pero hay dos OCR que pueden no coincidir.

## Siguiente

- [ ] Probar `es_core_news_lg` y un modelo transformer (y `ca_core_news_*` para el catalán).
- [ ] Lista de palabras a ignorar (FALLO, DNI, Testigo…) y regla «S.L./S.A. → empresa».
- [ ] Patrones para dirección completa (calle + número + CP), matrícula y NSS.
- [ ] Decidir la opción 1 o 2 de la imagen (afecta a [[0004-anonimizacion-antes-o-despues-de-revision]]).
