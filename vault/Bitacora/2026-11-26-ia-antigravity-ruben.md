---
fecha: 2026-11-26
autor: "@ia-antigravity-ruben"
tarea: Presidio en backend Python
---

## Qué hice

- Separé `integrations/etl.py` en dos módulos con responsabilidades claras:
  - `integrations/ocr.py` → cliente HTTP del servicio OCR externo (PaddleOCR-VL, URL en `OCR_SERVICE_URL`)
  - `services/presidio.py` → Presidio corre **en el propio backend Python**; no hay ETL para esto
- Implementé las **6 categorías iniciales** de anonimización:
  | Entidad Presidio | Sustitución |
  |---|---|
  | PERSON | [NOMBRE] |
  | DNI_NIE | [DNI/NIE] |
  | EMAIL_ADDRESS | [EMAIL] |
  | PHONE_NUMBER | [TELEFONO] |
  | LOCATION | [DIRECCION] |
  | IBAN_CODE | [IBAN] |
- Añadí reconocedor personalizado para DNI/NIE (regex con letra de control)
- Fallback determinista por regex cuando spaCy/Presidio no están instalados (útil en CI sin modelo)
- `services/anonymize.py` importa ahora de `services/presidio` en lugar de `integrations/etl`
- 4 tests en verde (`test_routes_loaded`, `test_presidio`)

## Decisiones

- Presidio se ejecuta en proceso (no como servicio separado) → latencia mínima, sin dependencia de red adicional
- El modelo spaCy recomendado es `es_core_news_lg` (configurado en `_cargar_analyzer`); si no está, el fallback es funcional para las categorías sin semántica (DNI, Email, IBAN, Teléfono)
- OCR sigue siendo externo (servicio PaddleOCR-VL), la URL se configura por `OCR_SERVICE_URL`

## Pendiente

- Instalar `presidio-analyzer`, `presidio-anonymizer` y `es_core_news_lg` en el entorno de producción
- Ajustar umbral de confianza (`score_threshold`) y lista de palabras a ignorar · ver [[Anonimizacion con Presidio]]
- Validación de IBAN con checksum y DNI con letra de control (tarea en tablero)
