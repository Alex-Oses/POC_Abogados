# 2026-11-18 — @ia-opencode-maga369

## Hecho

- **Un solo diagrama ER.** Retirados el «Diagrama propuesto» de [[0010-modelo-de-datos]] y `docs/architecture/diagrama-bbdd-borrador.png` (el borrador del esquema `V1`). El vigente es [[Modelo de datos]], reescrito hoy: 13 tablas, sin `TOKENS_USUARIO`, con `PAGINAS_DOCUMENTO`, `clave_cifrado`, `revisiones.documento_id`, el enum de 8 acciones de `accion_aplicada` y `expira_en`/`ultimo_uso_en` en `sesiones_usuario`. Se van también las secciones «Diferencias con 0010» del 17/11, que comparaban contra el diagrama viejo.
- **Reglas de negocio implementadas.** [`docs/reglas/reglas-de-negocio.md`](../docs/reglas/reglas-de-negocio.md) con el texto de @Marina: 36 vigentes, 9 retiradas y la tabla «Cambios pedidos». Es el fichero que se edita a mano; `usuarios.md` y `aprobacion.md` siguen siendo el origen.
- **Roles en tabla, no en columna** (decisión de @Marina, 18/11). `USUARIOS_ROLES (usuario_id, rol)` sustituye a `usuarios.roles TEXT[]` en todo lo que lo citaba: [[0012-identidad-y-roles]] (decisión, coste, SQL, `views.sql` y `triggers.sql`), [[0005-reglas-usuarios-y-aprobacion]], [[0011-ajustes-al-modelo-de-marina]], [[Enfoque tecnico]], [[Coherencia]] (B1), `docs/reglas/usuarios.md`, `docs/pendientes.md`, [[Modelo de datos]] y el [[Tablero]].
- **README de arquitectura**: deja de citar `er-diagram.md`, que nunca existió, y apunta al diagrama de la bóveda.
- **Tablero**: quitado el «PR #28 pendiente de merge» (mergeado el 17/11), quitada la línea duplicada de [[Enfoque tecnico]], retirada la pregunta ya contestada a @Marina y puestas en Hecho las tareas de hoy.

## Siguiente

- `V13` con `usuarios_roles`, `estado`, `sso_subject`, `sesiones_usuario` y sin `tokens_usuario`, cuando [[0009-identidad]] y [[0012-identidad-y-roles]] estén aceptadas.
- `V16` con el dueño del hash del PDF, si B8 se cierra por la versión.
- `GET /documents/{id}/pages`: sin él, `paginas_documento` sigue sin lector.

## Bloqueos / preguntas

- **@Rubén**: los roles pasan a tabla por decisión de @Marina. El SQL de 0012 ya usa `usuarios_roles` y el trigger y la vista pasan a `EXISTS`; si ves coste en `v_metricas_revisor`, dilo antes de escribir `V13`. La pregunta está en el [[Tablero]].
- **0012 sigue en Propuesta**: faltan @Kevin y @Alex; @Marina ha decidido el almacenamiento de roles, no el resto del documento.
- **`docs/pendientes.md` §1 contradice a 0012** en `password_cambiado_en`, `intentos_fallidos`, `bloqueado_hasta` y `ultimo_acceso`: la tabla los da a `usuarios` y 0012 dice que no se crean. No lo he tocado porque no es de esta tarea.
- **Sin ejecutar en PostgreSQL**: Docker no arranca en este equipo; el SQL de 0012 está revisado a mano, no probado.
