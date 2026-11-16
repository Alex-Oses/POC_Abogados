# 2026-11-16 — @ia-opencode-ruben

## Hecho

- Contrato HTTP v1 completo en [docs/api/endpoints.md](../../docs/api/endpoints.md): 40 rutas, roles, payloads, códigos y qué escribe cada una.
- Reglas de negocio en [docs/reglas/usuarios.md](../../docs/reglas/usuarios.md) y [docs/reglas/aprobacion.md](../../docs/reglas/aprobacion.md); el contrato solo cita el nombre de la regla, sin números sueltos.
- `vault/Proyecto/API.md` pasa a índice y apunta al detalle; `vault/Inicio.md` recoge las dos carpetas nuevas.
- Decisión [[0005-reglas-usuarios-y-aprobacion]] en estado **Propuesta** con las 7 reglas cerradas.
- Diseño del PDF final en [docs/export/pdf.md](../../docs/export/pdf.md): la estructura de cada versión se guarda como JSON y el PDF se reconstruye desde ahí con el texto ya anonimizado, sin píxeles del original. Decisión [[0006-generacion-pdf-final]] en **Propuesta**. Estimado: menos de 1,5 s para 100 páginas.

## Siguiente

- Revisar el PR de la rama `docs/aprobacion-usuarios-endpoints` y pasar 0005 a Aceptada si procede.
- Implementar el PDF final por fases (estructura, render, tablas, hash e idempotencia); la tarea está en el tablero.
- Encajar en `docs/architecture/` las columnas que citan las reglas (`tokens_usuario`, `revisiones.en_cola`, `asignado_a`, `fecha_limite`, `documentos.pendiente_visto_bueno`, `visto_bueno_*`, `hash_export`). Fuera de este PR.

## Bloqueos / preguntas

- [[0004-anonimizacion-antes-o-despues-de-revision]] sigue en Propuesta y el flujo de aprobación depende de ella.
- El tablero mantiene abierto si el OCR es síncrono o por página; el contrato lo da por síncrono.
- Plazo legal de conservación tras la baja: sin decidir; no se purga nada mientras tanto.
- Word y PDF/A quedan fuera del alcance del PDF final; falta saber si el ICAT los exige por contrato.
- La retícula original del PDF depende de que el OCR devuelva cajas, y hoy PaddleOCR-VL por Ollama devuelve solo texto. Mientras siga así, el export va en modo secuencial (una columna, mismo orden y jerarquía).
