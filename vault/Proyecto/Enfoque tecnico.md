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

**Reabierto el 20/11**: [[0014-stack-backend-c-sharp-java-python]] compara C#, Java y Python. La razón principal de 0008 (un solo lenguaje con el OCR y Presidio) deja de valer porque el ETL queda fuera del backend (§2). Mientras 0014 no se cierre, aquí se describe la opción Python, que es la que está escrita en [[Estructura del backend (Python)]]; las de [[Estructura del backend (CSharp)]] y [[Estructura del backend (Java)]] ya están escritas para comparar. Cómo se escriben las consultas se cerró el 23/11: **SQL directo** con el driver y un mapeador fino ([[0013-consultas-sql-o-sqlalchemy-core]]).

| Por qué (opción Python) | Qué se descartó |
|---|---|
| Las tres piezas caras ya son Python (OCR, Presidio, PDF): un runtime, un CI y sin contrato interno HTTP. El cuello de botella es la GPU, no el lenguaje | **C# + ASP.NET Core**: pedía un sidecar Python para Presidio y el PDF. Con el ETL fuera, ese coste desaparece y queda solo «otro runtime» |
| SQL explícito: el modelo usa `JSONB`, particiones, índices parciales y consultas de informe | **ORM**: estorba más de lo que ahorra en ese modelo |
| Un solo despliegue | **Microservicios**: un Colegio, un servidor y una persona en backend |

## 4. El contrato

40 rutas REST y JSON bajo `/api/v1`, en kebab-case, sin barra final ni extensiones. `application/json` (subidas `multipart/form-data`), `Authorization: Bearer <token>`.

| Convención | Valor                                                                                     |
| ---------- | ----------------------------------------------------------------------------------------- |
| Errores    | `{"error": {"code": "...", "message": "..."}}`; `code` estable, `message` para la persona |
| Paginación | `?page=1&limit=20`                                                                        |
| Fechas     | ISO 8601 en UTC                                                                           |
| Cierres    | `If-Match` obligatorio (ver §6)                                                           |
| Versión    | Global en la ruta; solo sube ante un cambio incompatible                                  |

Los payloads y códigos de cada ruta viven en el contrato; aquí solo va lo que condiciona la implementación.

## 5. Sesiones, roles y permisos

**Entrada por SSO del ICAT** ([[0009-identidad]], Propuesta). El backend **no gestiona cuentas**: no hay invitación, ni alta manual, ni contraseñas, ni proveedor de correo. El proveedor valida a la persona y devuelve su identificador (`sub`); el backend busca o crea la ficha y abre sesión.

| Qué | Cómo |
|---|---|
| Primer acceso | Se crea la ficha con `sub`, nombre y email, **sin roles**; hasta que un admin le asigne uno, solo ve un aviso |
| Único login local | **Una cuenta de admin, solo para desarrollo y pruebas**, sembrada por variable de entorno (U-21): no se versiona ni se despliega en producción |
| Sesión | Token opaco revocable (no JWT), **3 a la vez**, 1 h con renovación, 12 h máximo; se revoca al cambiar roles, bloquear o dar de baja |
| Roles | Tabla `usuarios_roles (usuario_id, rol)`: **un usuario puede tener varios**; el permiso es la unión. Tres valores con `CHECK` |
| Comprobación | Los roles se releen en cada petición: el token no arrastra rol |
| Sin permiso | Sin sesión `401`; con sesión pero sin permiso `403`, o `404` si además el recurso no es suyo |

Los tres roles son **transcriptor, revisor y admin**. **El supervisor desaparece** y sus funciones pasan al revisor: asignar y reasignar (A-06), liberar o devolver el visto bueno (A-15, en pausa), reabrir un aprobado (A-19) y consultar la auditoría.

La doble firma queda **en pausa** (18/11): A-07 (nadie revisa lo suyo) se retira y A-15 (otro revisor firma) se para, así que hoy un revisor puede cerrar un documento que subió él. Si se retoman, el visto bueno vuelve a exigir un revisor distinto de quien cerró.

Consecuencia para el modelo de @Marina: `usuarios.rol` sale y entra la **tabla `usuarios_roles`**; entra `usuarios.sso_subject` y `tokens_usuario` no se crea (no hay invitaciones ni reset, U-10 a U-15 retiradas). `usuarios.estado` se queda. **Las tablas nuevas son `usuarios_roles` y `sesiones_usuario`** (opción B, 18/11): la sesión es de la aplicación ([[0012-identidad-y-roles]]).

El contrato de autenticación ya tiene el camino de producción: `GET /auth/sso/login` y `GET /auth/sso/callback`, marcadas como propuesta. Las rutas de contraseña quedan como bloque del admin local de desarrollo; la invitación y el reset se retiraron (U-10 a U-15). El callback no se implementa hasta que 0009 se acepte y el ICAT registre la aplicación OIDC.

He dejado el contrato de autenticación como está a propósito: sus rutas de contraseña pasan a ser el camino del admin local de desarrollo, y el callback SSO es una ruta nueva. Esa parte no se escribe hasta que 0009 se acepte y el ICAT registre la aplicación OIDC.

## 6. Transacciones y concurrencia

Es donde el backend justifica su existencia:

| Regla | Cómo |
|---|---|
| Una petición, una transacción | O se guarda el cambio y su fila de auditoría, o no se guarda ninguno |
| Cierres sin pisarse | Cerrar la revisión exige `If-Match` con el `actualizado_en` leído (A-23). Si otro la cambió, `409` y se recarga. La toma de la cola no usa `If-Match`: es un `UPDATE ... WHERE estado = 'en_cola'` (A-05) |
| Export idempotente | Dos exportaciones del mismo texto dan el mismo SHA-256 y no duplican versión |
| Sin dudas, sin export | Una anotación sin decisión devuelve error, nunca un PDF |
| Nada se borra | Anulación y reapertura son estados; el original cifrado se conserva ([[0004-anonimizacion-antes-o-despues-de-revision]], Aceptada) |

Dueño del hash del PDF (B8) sigue abierto: `documentos` o `versiones_documento`. Hasta que se cierre, el export no se implementa.

## 7. Lo que tarda

El contrato hoy es **síncrono**: `POST /transform/document` responde `201` cuando el OCR ya está hecho. Eso es aceptable con un documento pequeño y una GPU libre; no lo es con un PDF de 100 páginas y dos subidas a la vez.

Si el OCR pasa a ser por página (I5, abierto), el backend necesita estado de la tarea y una ruta de consulta. **No lo he decidido**: cambia el contrato y depende del ETL.

## 8. Auditoría

Cada acción se registra en `auditoria` (V8) con su anterior **encadenada por hash**, particionada por mes: quién, qué, cuándo, sobre qué documento y desde dónde. Incluye el uso del admin de desarrollo. La escritura va en la misma transacción que la acción: si no se puede auditar, no se hace.

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
| Roles y permisos | Un transcriptor puro solo ve lo suyo; el mismo usuario con revisor ve todo, y el permiso se recalcula al cambiarle los roles en caliente |

## 11. Qué no está decidido

| Abierto | Quién | Qué bloquea |
|---|---|---|
| ~~[[0008-stack-backend]]~~ **Reabierta (20/11)**: [[0014-stack-backend-c-sharp-java-python]] compara C#, Java y Python | — | — |
| [[0009-identidad]]: SSO sin gestión de cuentas, admin local solo en desarrollo | @Kevin, @Marina, @Alex + registro OIDC del ICAT (1-2 semanas de terceros) | El login real y la primera ruta con permisos |
| Modelo de datos ([[0010-modelo-de-datos]]): `usuarios_roles` (tabla N:M, decisión de @Marina) y sin `tokens_usuario` | @Marina | La migración `V13` |
| Sesión propia en `sesiones_usuario` ([[0012-identidad-y-roles]]) | @Rubén, @Kevin | `V13`: la otra tabla nueva |
| Dueño del hash del PDF (B8) | @Rubén | El export idempotente |
| OCR síncrono o por página (I5) | sin dueño | La forma de las rutas de OCR |
| Frontera fina con el ETL (§2) | @Rubén y @Yaser | Quién escribe bloques y anotaciones |

Fuera de este documento: la arquitectura del sistema y el ETL (@Yaser), el frontend (@Alex) y el modelo de datos (@Marina). El plan de fases está en [[Propuesta ICAT]] y los bloqueantes, con su impacto, en [[Coherencia]].
