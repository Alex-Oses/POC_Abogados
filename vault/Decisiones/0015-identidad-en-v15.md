# 0015 · Identidad (B1): el SQL de 0012 va al final de `V15`

- **Estado**: Aceptada (2026-11-23, @Rubén)
- **Fecha**: 2026-11-23
- **Autor**: @ia-opencode-ruben
- **Se decide con**: @Rubén (backend), @Marina (BD)
- **Votos**: @Rubén (backend), 2026-11-23: **editar `V15`** y meter la identidad completa; `@Marina` no revisa la bóveda, así que su conformidad se recoge fuera.

## Contexto

[[0012-identidad-y-roles]] necesita dos tablas y cinco columnas que no existen: `usuarios_roles`, `sesiones_usuario`, `usuarios.estado`, `usuarios.sso_subject` y `usuarios.password_hash`, más la retirada de `usuarios.rol` y `usuarios.activo`. Es el bloqueante **B1** de [[Coherencia]].

El problema no es el diseño: es dónde va. La BD (`V1`-`V15`) se cerró el 19/11 y no se escriben `V13` ni `V16`; el hueco de `V13` es intencional. 0012 se escribió cuando `V13` aún no existía, con el argumento de que «el cambio sale gratis». Ese argumento ya no vale.

Tres salidas, y dos se descartaron:

| Opción | Qué cuesta | Por qué no |
|---|---|---|
| Implementar sobre `rol`/`activo` | 0 | Un rol por usuario, sin revocación de sesión y sin `sso_subject`; contradice 0012, U-16 a U-20 y el revisor que también transcribe. Se rehace en cuanto el piloto sea real |
| Dejar la identidad fuera del piloto | 0 | La demo se enseña, pero no se puede defender «quién puede qué» ni la auditoría por persona |
| **Editar `V15`** *(elegida)* | Recrear la BD de desarrollo | Mantiene 0012 entero y la BD sigue siendo `V1`-`V15` |

## Decisión

**El SQL de 0012 se añade al final de `V15__flujo_revision_y_export.sql`**, no a una migración nueva. En concreto, en este orden:

1. `usuarios_roles (usuario_id, rol)` con FK, `CHECK` de tres roles y PK compuesta; fuera `usuarios.rol`.
2. `usuarios.estado` (`activo`/`bloqueado`/`baja`), `motivo_baja` y `eliminado_en`; fuera `usuarios.activo`.
3. `usuarios.sso_subject TEXT UNIQUE` y `usuarios.password_hash TEXT` (nulo; solo el admin de desarrollo).
4. `sesiones_usuario` con `token_hash`, `expira_en`, `revocado_en`, `ip` y `user_agent`.
5. Índices: fuera `idx_usuarios_rol_activo`; entran `(estado)` y `usuarios_roles (rol)`.

El SQL exacto y los cambios de `views.sql` y `triggers.sql` están en [[0012-identidad-y-roles]], sección «Para @Marina». No se copian aquí para que exista una sola versión.

Esto decide **dónde**, no **qué**: 0012 sigue en Propuesta hasta que la voten @Kevin y @Alex.

## Consecuencias

- **La BD sigue siendo `V1`-`V15`.** Ni `V13` ni `V16`; el hueco se queda.
- **Hay que recrear la base de desarrollo**: `V15` ya está aplicada y Flyway guarda su *checksum*. No hay datos reales, solo seeds, así que es `flyway clean` + `migrate` (o borrar el esquema y volver a migrar). Si alguien la aplicó fuera de desarrollo, `flyway repair` no basta: el esquema cambia.
- **`V15` deja de ser solo flujo de revisión y export.** Su nombre miente un poco; se acepta antes que abrir una migración nueva con otro número.
- Los cambios en `views.sql`, `triggers.sql` y `data-dictionary.md` se hacen al implementar, no en esta decisión.
- **Riesgo asumido**: si el ICAT tarda en dar el registro OIDC, la tabla `usuarios` ya tendrá el hueco (`sso_subject`) y el admin de desarrollo funcionará mientras tanto.

## Qué falta

- Implementarlo: tarea en el [[Tablero]] (editar `V15`, la vista, el trigger y el diccionario de datos). No es trabajo de esta nota.
- Los votos de @Kevin y @Alex en [[0012-identidad-y-roles]].
- El registro de la aplicación OIDC en el ICAT, que es lo único que no depende del equipo.
