# API REST — Contrato completo

**Responsable:** Rubén
**Estado:** propuesta, sujeta a cambios
**Base de datos:** `docs/architecture/` (migraciones Flyway)
**Reglas de negocio:** `docs/reglas/usuarios.md` y `docs/reglas/aprobacion.md`. Este documento solo define rutas, payloads y códigos: donde una regla aplique, se cita el nombre de la regla, no su número.
**Generación del PDF:** `docs/export/pdf.md`.

## Convenciones

- **Prefijo:** `{url}/api/v1`. La versión afecta a toda la API.
- **Formato:** JSON (`application/json`), salvo subida de ficheros (`multipart/form-data`) y descarga de PDF (`application/pdf`).
- **Auth:** `Authorization: Bearer <token>`. Token revocable guardado como hash en `sesiones_usuario`.
- **Paginación:** `?page=1&limit=20`. Respuesta `{ "items": [], "page": 1, "limit": 20, "total": 0 }`.
- **Nombres de campo:** `snake_case`, idénticos a las columnas.
- **Fechas:** ISO 8601 en UTC (`2026-11-16T10:00:00Z`).
- **Errores:** misma forma siempre.
- **Idempotencia:** todo `POST` que crea recursos acepta `Idempotency-Key` opcional.
- **Concurrencia:** los cierres exigen `If-Match` con el `updated_at` leído; si no coincide, `409`.

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "La sesión no existe o ha caducado"
  }
}
```

| Código | Uso |
| --- | --- |
| `200` | Correcto |
| `201` | Recurso creado |
| `202` | Aceptado, procesándose |
| `400` | Petición mal formada |
| `401` | Sin token o inválido |
| `403` | Sin permisos para el recurso |
| `404` | No existe |
| `409` | Conflicto (email duplicado, documento ya en revisión, revisión tomada por otro) |
| `410` | Token caducado o ya usado |
| `413` | Fichero demasiado grande |
| `415` | Formato no soportado |
| `422` | Petición correcta pero no procesable (anotaciones pendientes, sin texto, falta motivo) |
| `429` | Límite de peticiones |
| `500` | Fallo interno |

## Roles

`transcriptor` (T), `revisor` (R), `admin` (A). Un usuario puede tener **varios roles** en `usuarios_roles`; el permiso es la unión. **El rol `supervisor` se elimina** y sus funciones pasan al revisor ([[0012-identidad-y-roles]], propuesta).

Los roles se releen de `usuarios_roles` en cada petición: un token no arrastra los roles con los que se emitió. Las rutas marcadas `público` son las únicas que no exigen `Authorization`.

## Resumen

| Método | Ruta | Roles | Tablas |
| --- | --- | --- | --- |
| `POST` | `/api/v1/user/invitation/accept` | público | `usuarios`, `tokens_usuario` |
| `POST` | `/api/v1/user/login` | público | `usuarios`, `sesiones_usuario` |
| `POST` | `/api/v1/user/logout` | todos | `sesiones_usuario` |
| `GET` | `/api/v1/user/me` | todos | `usuarios` |
| `POST` | `/api/v1/user/password/change` | todos | `usuarios`, `sesiones_usuario` |
| `POST` | `/api/v1/user/password/reset` | público | `usuarios`, `tokens_usuario` |
| `POST` | `/api/v1/user/password/reset/confirm` | público | `usuarios`, `tokens_usuario`, `sesiones_usuario` |
| `GET` | `/api/v1/admin/users` | A, S | `usuarios` |
| `POST` | `/api/v1/admin/users` | A | `usuarios`, `tokens_usuario` |
| `PATCH` | `/api/v1/admin/users/{id}` | A | `usuarios`, `sesiones_usuario` |
| `DELETE` | `/api/v1/admin/users/{id}/sessions` | A | `sesiones_usuario` |
| `POST` | `/api/v1/transform/document` | T | `documentos`, `versiones_documento`, `bloques_layout` |
| `POST` | `/api/v1/transform/plain-text` | T, R | `versiones_documento` |
| `POST` | `/api/v1/transform/build` | T, R | `versiones_documento` |
| `GET` | `/api/v1/documents` | T, R, S | `documentos` |
| `GET` | `/api/v1/documents/{id}` | T, R, S | `documentos`, `versiones_documento` |
| `DELETE` | `/api/v1/documents/{id}` | T (dueño), A | `documentos` |
| `GET` | `/api/v1/documents/{id}/versions` | R, S | `versiones_documento` |
| `GET` | `/api/v1/documents/{id}/versions/{numero_version}` | R, S | `versiones_documento` |
| `GET` | `/api/v1/documents/{id}/versions/{numero_version}/blocks` | R, S | `bloques_layout` |
| `POST` | `/api/v1/documents/{id}/anonymize` | T, R | `versiones_documento`, `anotaciones_entidad`, `reglas_anonimizacion` |
| `GET` | `/api/v1/documents/{id}/annotations` | R | `anotaciones_entidad` |
| `PATCH` | `/api/v1/annotations/{id}` | R | `anotaciones_entidad` |
| `GET` | `/api/v1/reviews` | R, S | `revisiones` |
| `POST` | `/api/v1/documents/{id}/reviews` | R | `revisiones`, `documentos` |
| `POST` | `/api/v1/reviews/{id}/claim` | R | `revisiones` |
| `PATCH` | `/api/v1/reviews/{id}/assign` | R | `revisiones` |
| `PATCH` | `/api/v1/reviews/{id}` | R | `revisiones`, `versiones_documento`, `documentos`, `anotaciones_entidad` |
| `POST` | `/api/v1/documents/{id}/reopen` | R, S | `documentos`, `versiones_documento`, `revisiones` |
| `POST` | `/api/v1/documents/{id}/sign-off` | R | `documentos` |
| `POST` | `/api/v1/documents/{id}/export` | T (dueño), S | `documentos`, `versiones_documento` |
| `GET` | `/api/v1/rules` | A | `reglas_anonimizacion`, `regla_categorias` |
| `POST` | `/api/v1/rules` | A | `reglas_anonimizacion`, `regla_categorias` |
| `PATCH` | `/api/v1/rules/{id}` | A | `reglas_anonimizacion`, `regla_categorias` |
| `GET` | `/api/v1/categories` | A | `categorias_sensibles` |
| `POST` | `/api/v1/categories` | A | `categorias_sensibles` |
| `PATCH` | `/api/v1/categories/{id}` | A | `categorias_sensibles` |
| `GET` | `/api/v1/audit` | R, A | `auditoria` |
| `GET` | `/api/v1/config` | A | `configuracion_sistema` |
| `PUT` | `/api/v1/config/{clave}` | A | `configuracion_sistema` |

---

## 1. Autenticación

Con SSO ([[0009-identidad]], propuesta), el camino normal es el del ICAT: no hay alta, invitación ni contraseñas de usuario. Las siete rutas de esta sección quedan como **camino del admin de desarrollo** y el callback SSO es una ruta nueva, aún sin escribir ([[0012-identidad-y-roles]]).

No hay autoregistro. En el camino local, la cuenta la crea el admin y se activa con el token de invitación.

### `POST /user/invitation/accept`

Fija la contraseña y activa la cuenta. Es el único camino de `invitado` a `activo`.

```json
{ "token": "token-en-claro-del-email", "password": "contraseña" }
```

`200` → `{ "id": "uuid", "email": "...", "roles": ["transcriptor"] }`.

Errores: `400` si la contraseña no cumple la política, `404` si el token no existe, `410` si ha caducado o ya se usó.

El token se guarda hasheado en `tokens_usuario` (`tipo = invitacion`). Al consumirlo se marca `usado_en` y no se puede reutilizar.

### `POST /user/login`

Devuelve el token y lo guarda hasheado en `sesiones_usuario`.

```json
{ "email": "correo@electronico.com", "password": "contraseña" }
```

`200` → `{ "access_token": "...", "token_type": "Bearer", "expires_in": 3600 }`.

Errores: `401` genérico (no distingue email inexistente de contraseña incorrecta), `403` si la cuenta está `invitado` o `bloqueado`, `429` tras N intentos.

Con la cuarta sesión simultánea se revoca la más antigua: el login responde `200` y la sesión desalojada recibe `401` en su siguiente petición.

### `POST /user/logout`

`204`. Marca `revocado_en` en la sesión actual.

### `GET /user/me`

`200` → `{ "id", "nombre", "apellidos", "email", "roles", "estado" }`.

### `POST /user/password/change`

Autenticado. Cambia la contraseña y revoca todas las sesiones del usuario, incluida la actual.

```json
{ "password_actual": "contraseña", "password_nueva": "contraseña-nueva" }
```

`204`. Errores: `400` si la nueva no cumple la política, `401` si la actual no coincide.

### `POST /user/password/reset`

Público. Envía el enlace de recuperación. Responde siempre `202`, exista o no el email: no se puede usar para enumerar cuentas.

```json
{ "email": "correo@electronico.com" }
```

`202` → `{ "mensaje": "Si la cuenta existe, se ha enviado un correo" }`.

### `POST /user/password/reset/confirm`

Público. Consume el token (`tipo = reset`), fija la contraseña y revoca todas las sesiones.

```json
{ "token": "token-en-claro-del-email", "password": "contraseña-nueva" }
```

`204`. Errores: `400` (política), `404` (token inexistente), `410` (caducado o usado).

---

## 2. Usuarios (administración)

### `GET /admin/users?rol=&estado=&page=`

Listado paginado. `estado` filtra por `invitado|activo|bloqueado|baja`.

`200` → `{ "items": [ { "id", "email", "nombre", "apellidos", "roles", "estado", "ultimo_acceso" } ], "page", "limit", "total" }`.

### `POST /admin/users`

Alta por invitación. Crea la cuenta en `estado = invitado`, sin contraseña, y envía el token de un solo uso.

```json
{ "nombre": "nombre", "apellidos": "apellidos", "email": "correo@electronico.com", "roles": ["revisor"] }
```

`201` → `{ "id": "uuid", "email": "...", "roles": ["revisor"], "estado": "invitado", "expira_en": "2026-11-19T10:00:00Z" }`.

Errores: `409` si el email ya existe (comparación en minúsculas). El token solo viaja en el correo, nunca en la respuesta.

Reenviar la invitación es el mismo `POST` sobre un email ya existente en estado `invitado`: devuelve `200` y emite un token nuevo, invalidando el anterior.

### `PATCH /admin/users/{id}`

```json
{ "roles": ["revisor"], "estado": "bloqueado", "motivo_baja": null }
```

`200`. Reglas:

- Cambiar `rol` o pasar a `bloqueado`/`baja` revoca todas las sesiones del usuario.
- `estado = baja` es irreversible y exige `motivo_baja`. No borra filas: rellena `eliminado_en`.
- `estado = activo` sobre un `bloqueado` desbloquea y reinicia `intentos_fallidos`.

Todo cambio se registra en `auditoria`.

### `DELETE /admin/users/{id}/sessions`

Cierra todas las sesiones abiertas de un usuario.

`204`. Idempotente: si no había sesiones, también `204`. No toca la contraseña ni el estado de la cuenta.

---

## 3. Documentos y OCR

### `POST /transform/document`

Sube el documento, guarda el fichero **cifrado** y ejecuta OCR y layout con PaddleOCR-VL. Crea:

- 1 fila en `documentos`, con el original cifrado
- versión `original` (sin texto)
- versión `ocr_texto` con una fila por bloque en `bloques_layout`

**Aquí no se anonimiza** (decisión 0004): el original cifrado se conserva para la revisión y la anonimización se aplica al construir la versión que va a revisión y al exportar.

**Petición** (`multipart/form-data`): `file` (PDF, JPG, PNG; máx. 20 MB).

`201` → `{ "id": "uuid", "num_paginas": 3, "estado": "ocr_completado" }`.

Errores: `400`, `413`, `415`. `422` si el OCR no produce texto.

### `POST /transform/plain-text`

Texto de la versión vigente (`es_actual = true`), sin formato.

```json
{ "id": "uuid" }
```

`200` → `{ "result": "texto plano transformado" }`.

Errores: `404` si el documento no existe.

### `POST /transform/build`

PDF maquetado de la versión vigente. Es vista previa: **no** cierra el expediente ni marca `exportado`. Se compone desde la estructura guardada, sin píxeles del original ([docs/export/pdf.md](../export/pdf.md)).

```json
{ "id": "uuid" }
```

`200` → binario, `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="documento.pdf"`.

Errores: `404` si el documento no existe, `500` si falla la generación.

### `GET /documents?estado=&page=&limit=`

Lista documentos. El transcriptor ve solo los suyos; el revisor ve todos.

`200` → `{ "items": [ { "id", "nombre_original", "estado", "num_paginas", "creado_en" } ], ... }`.

### `GET /documents/{id}`

`200` → documento + `version_actual`:

```json
{
  "id": "uuid",
  "nombre_original": "escritura.pdf",
  "mime_type": "application/pdf",
  "num_paginas": 3,
  "estado": "ocr_completado",
  "creado_en": "2026-11-16T10:00:00Z",
  "version_actual": {
    "id": "uuid",
    "numero_version": 2,
    "tipo_version": "ocr_texto",
    "pipeline_version": "v1.6",
    "confianza_layout_promedio": 0.973
  }
}
```

### `DELETE /documents/{id}`

`204`. Borrado lógico (`eliminado_en`). No borra las versiones ni la auditoría.

---

## 4. Versiones y bloques

### `GET /documents/{id}/versions`

`200` → `{ "items": [ { "numero_version", "tipo_version", "motor_ocr", "pipeline_version", "creado_en" } ] }`.

### `GET /documents/{id}/versions/{numero_version}`

`200` → la versión completa, incluido `contenido_texto` y `contenido_html`.

### `GET /documents/{id}/versions/{numero_version}/blocks?page=`

Lo que pinta el visor. Una entrada por fila de `bloques_layout`.

```json
{
  "items": [
    {
      "id": "uuid",
      "pagina_numero": 1,
      "orden_lectura": 3,
      "etiqueta": "text",
      "confianza": 0.984,
      "forma": "rect",
      "bbox": { "x": 389.1, "y": 200.3, "ancho": 353.6, "alto": 95.3 },
      "pagina": { "ancho": 1600, "alto": 2200 },
      "contenido": "Yo, Juan Pérez, con DNI 12345678Z..."
    }
  ],
  "page": 1,
  "limit": 100,
  "total": 42
}
```

Las coordenadas están en píxeles de la página renderizada. Para `forma = "quad"` o `"poly"` se usa `puntos` en lugar de `bbox`.

---

## 5. Anonimización y anotaciones

### `POST /documents/{id}/anonymize`

Aplica una regla sobre la versión vigente y crea una versión `anonimizado_ia` con sus anotaciones.

Es el paso que prepara la revisión: el documento pasa a `anonimizando` y, al terminar, a `en_revision` con `anonimizado_ia` como versión vigente ([aprobacion.md](../reglas/aprobacion.md), A-03). El original cifrado no se toca: lo que se anonimiza es la copia que revisa el revisor y la que se exporta.

```json
{ "regla_id": "uuid" }
```

`201` → `{ "version_id": "uuid", "numero_version": 3, "anotaciones": 27 }`.

Errores: `404` si el documento o la regla no existen, `409` si ya hay un proceso en curso, `422` si no hay texto que anonimizar.

### `GET /documents/{id}/annotations?version=&categoria=&pendientes=true`

`200` → `{ "items": [ { "id", "bloque_id", "categoria", "inicio_offset", "fin_offset", "texto_original", "accion_aplicada", "confianza_deteccion", "decision_revisor" } ] }`.

Los offsets son índices de carácter dentro de `bloques_layout.contenido`.

### `PATCH /annotations/{id}`

Decisión del revisor sobre una entidad detectada.

```json
{
  "accion_aplicada": "pseudonimizado",
  "texto_sustitucion": "[NOMBRE_1]",
  "decision_revisor": "modificado",
  "observaciones_revisor": "El DNI estaba partido en dos líneas"
}
```

`200`. Rellena `revisado_por` y `revisado_en`. Cada cambio se audita.

---

## 6. Revisión

### `GET /reviews?estado=&asignado_a=me&page=`

Cola de trabajo. `estado=en_cola` devuelve lo que nadie ha tomado; `asignado_a=me` lo que tengo yo.

`200` → `{ "items": [ { "id", "documento_id", "numero_intento", "estado", "asignado_a", "fecha_limite", "creado_en" } ] }`.

### `POST /documents/{id}/reviews`

Abre una revisión sobre la versión vigente. Nace en `en_cola` y **sin** revisor asignado: se toma después con `claim`. El documento pasa a `en_revision`.

`201` → `{ "id": "uuid", "numero_intento": 1, "estado": "en_cola", "fecha_limite": "2026-11-18T17:00:00Z" }`.

`fecha_limite` se calcula al crear, con `configuracion_sistema.calendario_laboral`.

Errores: `409` si ya hay una revisión abierta o el documento no está anonimizado, `422` si no hay versión `anonimizado_ia`.

### `POST /reviews/{id}/claim`

Toma la revisión de la cola. Rellena `asignado_a` y `asignado_en`, y pasa la revisión a `en_proceso`.

`200` → `{ "id", "estado": "en_proceso", "asignado_a", "asignado_en", "fecha_limite" }`.

Errores: `409` si otro revisor la tomó primero o la revisión no está `en_cola`; `403` si el documento lo subió el propio revisor.

La toma es un único `UPDATE ... WHERE estado = 'en_cola'`: no usa `If-Match` y no puede dejar dos dueños.

### `PATCH /reviews/{id}/assign`

Cualquier revisor. Asigna una revisión en cola o reasigna una en proceso. **Excepción, no norma**: A-06 propone que el revisor elija libremente de la cola; si se confirma, la ruta desaparece.

```json
{ "asignado_a": "uuid", "comentario": "Expediente delicado" }
```

`200`. `asignado_a: null` la devuelve a la cola. La reasignación de una revisión `en_proceso` exige `comentario` y queda en `auditoria`.

Errores: `403` si el destino es el `creado_por` del documento, `409` si la revisión ya está cerrada.

### `PATCH /reviews/{id}`

Cierra la revisión. Exige `If-Match` con el `updated_at` que devolvió la última lectura.

```json
{ "estado": "aprobado", "comentario_general": "Correcto" }
```

Efectos según `estado`:

| `estado` | Versión creada | `documentos.estado` |
| --- | --- | --- |
| `aprobado` | `final_aprobado` con `es_actual = true` | `aprobado`, o `pendiente_visto_bueno` si `requiere_visto_bueno` |
| `rechazado_con_cambios` | `revisado_humano` | `rechazado` |
| `devuelto` | ninguna | `en_revision`, la revisión vuelve a `en_cola` |

`200` → `{ "id", "estado", "documento_estado", "requiere_visto_bueno" }`. Rellena `finalizado_en` y `tiempo_revision_seg`.

Errores:

- `422` con la lista de `anotacion_id` si quedan anotaciones pendientes y se intenta aprobar.
- `422` si faltan `comentario_general` en `rechazado_con_cambios` o `devuelto`.
- `409` si `If-Match` no coincide con el `updated_at` actual (otro revisor cerró antes), o si la revisión no está `en_proceso`.

### `POST /documents/{id}/reopen`

Devuelve un documento rechazado al circuito. Crea una versión `anonimizado_ia` nueva con la regla vigente, una revisión nueva en `en_cola` con `numero_intento + 1` y deja el documento en `en_revision`.

```json
{ "comentario": "Se corrige el escaneo de la página 3" }
```

`201` → `{ "version_id": "uuid", "numero_version": 5, "revision_id": "uuid", "numero_intento": 2 }`.

Errores: `409` si el documento no está `rechazado`, `422` si no hay texto que anonimizar.

### `POST /documents/{id}/sign-off`

Cualquier revisor, **salvo quien cerró la revisión**. Libera un documento en `pendiente_visto_bueno`. No crea versión: `final_aprobado` ya se creó al aprobar el revisor.

**En pausa con A-15** (18/11): mientras la doble firma esté parada, `requiere_visto_bueno` es siempre `false` y esta ruta no se usa. Se conserva en el contrato para no reescribirlo si se retoma.

```json
{ "comentario": "Firmado" }
```

`200` → `{ "id", "estado": "aprobado", "visto_bueno_por", "visto_bueno_en" }`.

Errores: `409` si el documento no está en `pendiente_visto_bueno`.

### `POST /documents/{id}/export`

Cierra el expediente. Genera el PDF definitivo desde la versión aprobada (ya anonimizada), guarda `hash_export` y `exportado_en`, y pasa el documento a `exportado`.

`200` → binario, `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="documento.pdf"` y cabecera `X-Document-Hash` con el SHA-256.

Errores: `409` si el documento no está `aprobado`.

Un documento ya exportado devuelve el mismo PDF y el mismo hash: la operación es idempotente y no reescribe nada. Cómo se genera: [docs/export/pdf.md](../export/pdf.md).

---

## 7. Reglas y categorías

### `GET /rules?activa=`

`200` → reglas con sus categorías:

```json
{
  "items": [
    {
      "id": "uuid",
      "codigo": "rgpd_basico",
      "version": 2,
      "nombre": "RGPD básico",
      "activa": true,
      "categorias": [
        { "categoria_id": "uuid", "codigo": "dni", "configuracion": {} }
      ]
    }
  ]
}
```

### `POST /rules`

Crea una regla nueva. Si el `codigo` ya existe, genera la siguiente `version` en lugar de sobrescribir.

```json
{
  "codigo": "rgpd_basico",
  "nombre": "RGPD básico",
  "descripcion": "DNI, nombre, dirección",
  "categorias": [
    { "categoria_id": "uuid", "configuracion": { "accion": "pseudonimizado" } }
  ]
}
```

`201`. Errores: `409` si ya hay una regla activa con ese `codigo` y no se pide versión nueva.

### `PATCH /rules/{id}`

Activa o desactiva, o cambia nombre y configuración. `200`.

### `GET /categories?activa=`

`200` → `{ "items": [ { "id", "codigo", "nombre", "regex_patron", "prioridad", "nivel_riesgo", "rgpd_especial", "activa" } ] }`.

### `POST /categories`

```json
{
  "codigo": "dni",
  "nombre": "DNI",
  "regex_patron": "\\b\\d{8}[A-Z]\\b",
  "prioridad": 10,
  "nivel_riesgo": "alto",
  "rgpd_especial": true
}
```

`201`. Errores: `400` si la expresión regular no compila, `409` si el código existe.

### `PATCH /categories/{id}`

`200`. Desactivar no borra: las anotaciones históricas la siguen referenciando.

---

## 8. Auditoría y configuración

### `GET /audit?entidad_tipo=&entidad_id=&usuario_id=&desde=&hasta=&page=`

Solo lectura. `200` → `{ "items": [ { "id", "evento", "entidad_tipo", "entidad_id", "usuario_id", "ip_origen", "creado_en", "detalle" } ] }`.

### `GET /config`

`200` → `{ "items": [ { "clave", "valor", "descripcion", "actualizado_en" } ] }`.

### `PUT /config/{clave}`

```json
{ "valor": { "max_upload_mb": 20 }, "descripcion": "Límite de subida" }
```

`200`. Crea o actualiza y audita el cambio.

---

## 9. Máquina de estados de `documentos.estado`

```text
pendiente → ocr_procesando → ocr_completado → anonimizando → en_revision

en_revision
  ├─ rechazado ──POST /documents/{id}/reopen──→ en_revision
  ├─ aprobado                                              (requiere_visto_bueno = false)
  └─ pendiente_visto_bueno ──POST /documents/{id}/sign-off──→ aprobado

aprobado ──POST /documents/{id}/export──→ exportado
```

- `ocr_procesando` y `anonimizando` son transitorios: si el proceso falla, el documento vuelve al estado anterior y se registra en `auditoria`.
- `pendiente_visto_bueno` solo existe si la versión tiene alguna anotación de una categoría con `rgpd_especial = true`.
- `exportado` lo marca únicamente `POST /documents/{id}/export`. `POST /transform/build` es vista previa y no cambia estados.
- `aprobado` está congelado: no admite versiones nuevas salvo reapertura explícita de un revisor.
- Ningún endpoint permite saltarse un estado; el `409` lo impide.

## 10. Qué endpoint escribe qué

| Acción | Escribe |
| --- | --- |
| Alta por invitación | `usuarios` (`invitado`), `tokens_usuario` |
| Aceptar invitación / reset | `usuarios`, `tokens_usuario`, `sesiones_usuario` |
| Login / logout | `sesiones_usuario` |
| Cambio de rol, bloqueo o baja | `usuarios`, `sesiones_usuario` |
| Revocar sesiones | `sesiones_usuario` |
| Subida + OCR | `documentos`, `versiones_documento` (2), `bloques_layout` |
| Anonimizar | `versiones_documento` (1), `anotaciones_entidad` (N) |
| Revisar anotación | `anotaciones_entidad` |
| Abrir revisión | `revisiones` (`en_cola`), `documentos` |
| Tomar o asignar revisión | `revisiones` |
| Cerrar revisión | `revisiones`, `versiones_documento`, `documentos` |
| Reabrir rechazado | `documentos`, `versiones_documento`, `revisiones` |
| Visto bueno | `documentos` (`visto_bueno_por`, `visto_bueno_en`) |
| Exportar | `documentos` (`hash_export`, `exportado_en`, `cerrado_en`) |
| Reglas / categorías | `reglas_anonimizacion`, `regla_categorias`, `categorias_sensibles` |
| Configuración | `configuracion_sistema` |
| Todo lo anterior | `auditoria` (una fila por cambio) |
