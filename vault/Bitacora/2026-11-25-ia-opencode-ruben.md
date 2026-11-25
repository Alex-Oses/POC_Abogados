# 2026-11-25 · @ia-opencode-ruben

## Hecho

- Corregidos los desajustes del PDF final (P1-P12): offsets por bloque con FK compuesta por versión, texto de origen sin sustituciones materializadas, `falso_negativo` obligado a sustituir, export sin sobrescritura, bloqueo y escritura atómica, estructura perezosa y regenerable, tablas y Unicode NFC.
- Aclarado que PaddleOCR-VL 1.6 solo devuelve texto: la geometría sale de la capa del PDF, de un detector de layout o de un bloque sintético por página. Corregidas 0007 y 0011.
- Alineados `pdf.md`, `endpoints.md`, `aprobacion.md`, `data-dictionary.md`, `views.sql`, `pendientes.md`, `Coherencia.md` y el registro (E-21, E-25, E-52).
- `V15` añade la FK compuesta `(bloque_id, version_id)` y el único `(id, version_id)` en `bloques_layout`.
- `trg_version_auto_number` mantiene `es_actual`: la versión insertada pasa a ser la vigente, para que `v_documento_actual` no se quede en la anterior.

## Siguiente

- Validar `V15` y las vistas contra PostgreSQL 16 desde cero; sigue sin haber Docker ni `psql` en este equipo.
- Implementar el export en `backend/` con las pruebas 1-13 de `pdf.md`.

## Bloqueos / preguntas

- E-51 sigue bloqueado: los `bbox_*` legacy de `anotaciones_entidad` requieren decisión de @Marina. No se leen en el export.
