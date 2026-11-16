# 2026-11-16 — @ia-opencode-ruben

## Hecho

- Contrato HTTP v1 completo en [docs/api/endpoints.md](../../docs/api/endpoints.md): 40 rutas, roles, payloads, códigos y qué escribe cada una.
- Reglas de negocio en [docs/reglas/usuarios.md](../../docs/reglas/usuarios.md) y [docs/reglas/aprobacion.md](../../docs/reglas/aprobacion.md); el contrato solo cita el nombre de la regla, sin números sueltos.
- `vault/Proyecto/API.md` pasa a índice y apunta al detalle; `vault/Inicio.md` recoge las dos carpetas nuevas.
- Decisión [[0005-reglas-usuarios-y-aprobacion]] en estado **Propuesta** con las 7 reglas cerradas.

## Siguiente

- Revisar el PR de la rama `docs/aprobacion-usuarios-endpoints` y pasar 0005 a Aceptada si procede.
- Encajar en `docs/architecture/` las columnas que citan las reglas (`tokens_usuario`, `revisiones.en_cola`, `asignado_a`, `fecha_limite`, `documentos.pendiente_visto_bueno`, `visto_bueno_*`, `hash_export`). Fuera de este PR.

## Bloqueos / preguntas

- [[0004-anonimizacion-antes-o-despues-de-revision]] sigue en Propuesta y el flujo de aprobación depende de ella.
- El tablero mantiene abierto si el OCR es síncrono o por página; el contrato lo da por síncrono.
- Plazo legal de conservación tras la baja: sin decidir; no se purga nada mientras tanto.
