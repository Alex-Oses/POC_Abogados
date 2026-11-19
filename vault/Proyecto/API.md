# API v1

Contrato completo: [docs/api/endpoints.md](../../docs/api/endpoints.md). Esta nota es el índice; los payloads, códigos y efectos viven allí. Reglas de negocio: [docs/reglas/usuarios.md](../../docs/reglas/usuarios.md) y [docs/reglas/aprobacion.md](../../docs/reglas/aprobacion.md).

Estado: propuesta (16/11/2026), 40 rutas. Sustituye al borrador de 5 rutas del 06/11/2026.

## Convenciones

- Prefijo `{url}/api/v1`; versión global, solo sube ante cambios incompatibles.
- Rutas en kebab-case, sin barra final ni extensiones.
- `Content-Type: application/json` (subidas: `multipart/form-data`); `Authorization: Bearer <token>`.
- Errores: `{"error": {"code": "...", "message": "..."}}`. `code` es estable.
- Paginación `?page=1&limit=20`; fechas ISO 8601 en UTC; `If-Match` en los cierres.

## Bloques

| Bloque | Rutas | Para qué |
|---|---|---|
| Autenticación | 6 | SSO, login/logout, `me` y cambio de contraseña del admin de desarrollo |
| Usuarios | 3 | Listado, `PATCH` de roles/estado, revocar sesiones |
| OCR | 3 | Subir, texto plano y PDF de vista previa |
| Documentos y versiones | 8 | Listado, detalle, páginas, original, baja lógica, versiones y bloques de layout |
| Anonimización | 3 | Lanzar el proceso, listar anotaciones, decidir cada una |
| Revisión | 5 | Cola, abrir, tomar, asignar y cerrar |
| Cierre | 3 | Reapertura, visto bueno (en pausa con A-15) y exportación con hash |
| Reglas y categorías | 6 | Catálogo de anonimización |
| Auditoría y configuración | 3 | Consulta y parámetros globales |

## Flujo

Subir → OCR y layout → anonimizar → revisión en cola → (visto bueno de otro revisor si hay datos de categorías especiales, art. 9-10; **en pausa con A-15**) → exportar PDF con hash.

## Seguridad

TLS obligatorio; SSO del ICAT y una única contraseña local, la del admin de desarrollo (Argon2id en servidor); token opaco revocable (no JWT), máximo 3 sesiones; `401` que no distingue email inexistente de contraseña errónea; sin autoregistro; nada sensible en logs.

## Lo que puede cambiar el diseño

- [[0004-anonimizacion-antes-o-despues-de-revision]]: el contrato asume que se guarda el original y se anonimiza después.
- OCR síncrono o por página asíncrona: aquí es síncrono (tarea en el tablero).
- Las reglas citan columnas que aún no están en [docs/architecture](../../docs/architecture/README.md); ver [[0005-reglas-usuarios-y-aprobacion]].
