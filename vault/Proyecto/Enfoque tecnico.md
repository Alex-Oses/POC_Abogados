# Enfoque técnico del backend

- **Para**: entrega del viernes 27/11/2026 (ver [[Equipo]])
- **Estado**: **propuesta** · 17/11/2026
- **Autor**: @ia-opencode-ruben
- **Qué es**: cómo se construye y por qué el **backend** (la API que sostiene el contrato). No cubre la arquitectura del sistema ni el ETL: eso lo lleva @Yaser y se documenta aparte. El detalle de cada ruta está en [`docs/api/endpoints.md`](../../docs/api/endpoints.md), las reglas en [`docs/reglas/`](../../docs/reglas/) y el modelo de datos lo cierra @Marina en [[Modelo de datos]].

## 1. Alcance

El backend es el servicio que **expone las 40 rutas del contrato, guarda el estado y decide quién puede hacer qué**. No hace OCR, ni anonimización, ni compone el PDF: pide esas transformaciones, espera el resultado y lo persiste con sus permisos y su rastro.

Esa frontera no es burocracia. Si el backend hiciera el OCR, una subida tendría la API bloqueada dos minutos por documento y cualquier fallo de la GPU tumbaría también la consulta de un expediente ya aprobado.

## 2. Frontera con el ETL

| Quién | Qué es suyo |
|---|---|
| **Backend** (@Rubén) | Contrato HTTP, sesiones y permisos, máquina de estados del documento, transacciones, auditoría, encolado de lo largo, idempotencia del export, forma de los errores |
| **ETL** (@Yaser) | Recorrido del dato: extracción y OCR, layout, anonimización, composición del PDF, semáforo de calidad y sus métricas |
| **Base de datos** (@Marina) | Esquema, migraciones y lo que se guarda de cada paso |

Lo que cruza la frontera son **datos** (fichero, estructura, anotaciones), nunca estado: el ETL no escribe en las tablas del contrato ni decide si un documento se puede exportar. Se conectan por las rutas `/transform/*`, `/anonymize` y `/export`, que el backend expone y delega.

Puntos a cerrar con @Yaser antes de escribir código (no los decido yo):

- Quién escribe `bloques_layout` y `anotaciones_entidad`: hoy el contrato se lo atribuye a `/transform/*`, y eso es esquema de @Marina.
- Formato del resultado intermedio (estructura del PDF, anotaciones) y quién lo versiona.
- Reintentos: qué transformación es idempotente y cuál no, y qué pasa si el ETL falla a mitad.

## 3. Stack

**Python 3.12 + FastAPI + SQL explícito** ([[0008-stack-backend]], Propuesta).

| Por qué | Qué se descartó |
|---|---|
| Las tres piezas caras ya son Python (OCR, Presidio, PDF): un runtime, un CI y sin contrato interno HTTP. El cuello de botella es la GPU, no el lenguaje | **C# + ASP.NET Core**: obliga a un sidecar Python para Presidio y el PDF, un segundo runtime y un contrato interno |
| SQL explícito: el modelo usa `JSONB`, particiones, índices parciales y consultas de informe | **ORM**: estorba más de lo que ahorra en ese modelo |
| Un solo despliegue | **Microservicios**: un Colegio, un servidor y una persona en backend |

## 4. El contrato

40 rutas REST y JSON bajo `/api/v1`, en kebab-case, sin barra final ni extensiones. `application/json` (subidas `multipart/form-data`), `Authorization: Bearer <token>`.

| Convención | Valor |
|---|---|
| Errores | `{"error": {"code": "...", "message": "..."}}`; `code` estable, `message` para la persona |
| Paginación | `?page=1&limit=20` |
| Fechas | ISO 8601 en UTC |
| Cierres | `If-Match` obligatorio (ver §6) |
| Versión | Global en la ruta; solo sube ante un cambio incompatible |

Los payloads y códigos de cada ruta viven en el contrato; aquí solo va lo que condiciona la implementación.

## 5. Sesiones y permisos

- **Token opaco revocable**, no JWT: con JWT no se puede cerrar una sesión antes de que caduque, y el contrato exige cerrarlas al cambiar contraseña o rol.
- Contraseñas con **Argon2id**; máximo **3 sesiones** por usuario; sin autoregistro (alta por invitación del admin).
- Cuatro roles: transcriptor (T), revisor (R), supervisor (S), admin (A). El transcriptor solo ve lo suyo; revisor y supervisor ven todo.
- El `401` **no revela si el email existe**: misma respuesta y mismo tiempo para usuario inexistente y contraseña mala.
- Identidad definitiva pendiente de [[0009-identidad]] (SSO del ICAT + admin local de emergencia). Si sale SSO, esta sección pierde el login por contraseña pero no los roles ni las sesiones.

## 6. Transacciones y concurrencia

Es donde el backend justifica su existencia:

| Regla | Cómo |
|---|---|
| Una petición, una transacción | O se guarda el cambio y su fila de auditoría, o no se guarda ninguno |
| Cierres sin pisarse | Aprobar, dar el visto bueno y exportar exigen `If-Match` con la versión que se leyó. Si otro la cambió, `409` y se recarga |
| Export idempotente | Dos exportaciones del mismo texto dan el mismo SHA-256 y no duplican versión |
| Sin dudas, sin export | Una anotación sin decisión devuelve error, nunca un PDF |
| Nada se borra | Anulación y reapertura son estados; el original cifrado se conserva ([[0004-anonimizacion-antes-o-despues-de-revision]], Aceptada) |

Dueño del hash del PDF (B8) sigue abierto: `documentos` o `versiones_documento`. Hasta que se cierre, el export no se implementa.

## 7. Lo que tarda

El contrato hoy es **síncrono**: `POST /transform/document` responde `201` cuando el OCR ya está hecho. Eso es aceptable con un documento pequeño y una GPU libre; no lo es con un PDF de 100 páginas y dos subidas a la vez.

Si el OCR pasa a ser por página (I5, abierto), el backend necesita estado de la tarea y una ruta de consulta. **No lo he decidido**: cambia el contrato y depende del ETL.

## 8. Auditoría

Cada acción se registra en `auditoria` (V8) con su anterior **encadenada por hash**, particionada por mes: quién, qué, cuándo, sobre qué documento y desde dónde. Incluye el uso del admin de emergencia. La escritura va en la misma transacción que la acción: si no se puede auditar, no se hace.

Los logs de aplicación no sustituyen a esta tabla: se rotan y se pierden; no sirven como prueba.

## 9. Errores

| Código | Cuándo |
|---|---|
| `400` / `413` / `415` | Petición mal formada, fichero demasiado grande, tipo no admitido |
| `401` / `403` | Sin sesión válida / con sesión pero sin permiso |
| `404` | No existe o no es tuyo: mismo código, para no revelar qué hay |
| `409` | La versión cambió desde que la leíste (`If-Match`) |
| `422` | El OCR no produjo texto |
| `500` | Fallo interno, con `code` estable y sin datos personales en el mensaje |

## 10. Cómo se comprueba

Cada promesa del backend tiene su prueba; si no la tiene, no es una promesa:

| Promesa | Cómo se comprueba |
|---|---|
| El contrato se cumple | Una prueba por ruta: código, forma del JSON y efecto en base de datos |
| Los permisos no se saltan | Prueba de cada rol contra cada ruta: lo que no toca da `403` o `404`, nunca datos |
| Los cierres no se pisan | Dos `PATCH` con el mismo `If-Match`: el segundo da `409` |
| El export es idempotente | Dos ejecuciones seguidas dan el mismo SHA-256 y una sola versión |
| No se exporta con dudas | Una anotación sin decisión devuelve error, no PDF |
| Todo queda auditado | Tras cada operación existe su fila, con el hash anterior correcto |
| El `401` no filtra | Email inexistente y contraseña mala dan la misma respuesta |

## 11. Qué no está decidido

| Abierto | Quién | Qué bloquea |
|---|---|---|
| [[0008-stack-backend]] | @Marina, @Kevin, @Alex | El primer endpoint |
| [[0009-identidad]] | @Kevin, @Marina, @Alex + registro OIDC del ICAT (1-2 semanas de terceros) | Alta de usuarios y tabla de identidad |
| Modelo de datos ([[0010-modelo-de-datos]]) | @Marina | La migración `V13`-`V15` |
| Dueño del hash del PDF (B8) | @Rubén | El export idempotente |
| OCR síncrono o por página (I5) | sin dueño | La forma de las rutas de OCR |
| Frontera fina con el ETL (§2) | @Rubén y @Yaser | Quién escribe bloques y anotaciones |

Fuera de este documento: la arquitectura del sistema y el ETL (@Yaser), el frontend (@Alex) y el modelo de datos (@Marina). El plan de fases está en [[Propuesta ICAT]] y los bloqueantes, con su impacto, en [[Coherencia]].
