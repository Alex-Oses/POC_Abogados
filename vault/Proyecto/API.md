# API v1 (borrador)

Fuente: *Endpoints · Diseño de la API* (06/11/2026).

## Convenciones

- Prefijo `{url}/api/v1`; versión global, solo sube ante cambios incompatibles.
- Rutas en kebab-case, sin barra final ni extensiones.
- `Content-Type: application/json` (subidas: `multipart/form-data`); `Authorization: Bearer <token>`.
- Errores: `{"error": {"code": "SESSION_NOT_FOUND", "message": "..."}}`. `code` es estable.

## Endpoints

| Método | Ruta | Entrada | Salida |
|---|---|---|---|
| POST | `/transform/document` | `file` (PDF/JPG/PNG, ≤ 20 MB) | `201 {"id"}` · 400/413/415 |
| POST | `/transform/plain-text` | `{"id"}` | `200 {"result": "texto"}` · 404 |
| POST | `/transform/build` | `{"id"}` | `200` PDF (`attachment`) · 404/500 |
| POST | `/user/register` | `name, surnames, email, password (≥ 12)` | `201` · 400/409 |
| POST | `/user/login` | `email, password` | `200 {"access_token", "token_type": "Bearer", "expires_in": 3600}` · 401/429 |

## Flujo

Subir → OCR + anonimización en servidor → sesión con `id` → pedir texto o PDF → la sesión caduca a las 24 h (404).

## Seguridad

TLS obligatorio · contraseña con hash y sal (el cliente no hashea) · tokens cortos firmados · límite de intentos por IP y cuenta · validación del tipo real del fichero · nada sensible en logs · 401 no distingue email inexistente de contraseña errónea.

## Lo que puede cambiar el diseño

- **OCR por página en paralelo**: la API pasaría a asíncrona, devolviendo IDs por página.
- **Base de datos** sin decidir en este documento (ya hay borrador: [[Base de datos]]).
- **Formato**: si se trabaja con `.docx` en lugar de PDF.
- Ver [[0004-anonimizacion-antes-o-despues-de-revision]].
