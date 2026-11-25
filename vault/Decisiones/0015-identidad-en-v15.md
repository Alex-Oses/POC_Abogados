# 0015 · Identidad (B1): el SQL de 0012 va al final de `V15`

- **Estado**: Aceptada (2026-11-23, @Rubén)
- **Fecha**: 2026-11-23
- **Autor**: @ia-opencode-ruben
- **Se decide con**: @Rubén (backend), @Marina (BD)
- **Votos**: @Rubén (backend), 2026-11-23: **editar `V15`** y meter la identidad completa; `@Marina` no revisa la bóveda, así que su conformidad se recoge fuera. @Rubén (backend), 2026-11-23: **adelante**, con la condición de que el modelo lógico-relacional se mantenga intacto y coherente.

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

### Condición: el modelo lógico-relacional no cambia

Lo que se mueve es dónde vive la identidad, no la estructura del modelo. Se conservan la PK de `usuarios`, las FK de `revisiones`, `documentos`, `versiones_documento` y `auditoria`, la historia (quien firmó queda firmado) y todas las tablas que no son de identidad. Las dos tablas nuevas cuelgan de `usuarios` con `ON DELETE CASCADE`.

El orden de implementación importa, porque hay dependencias reales:

1. **Soltar `v_metricas_revisor` antes** de retirar `rol`/`activo`: usa `u.rol` y `u.activo`, y un `DROP COLUMN` con la vista viva falla. Se recrea después con `EXISTS (usuarios_roles)` y `estado = 'activo'`.
2. **Reemplazar la función del trigger de revisor** en el mismo cambio: lee `usuarios.rol` y pasa a `NOT EXISTS` sobre `usuarios_roles`.
3. `idx_usuarios_rol_activo` cae con las columnas; no hace falta borrarlo antes.
4. **No se tocan** `revisiones`, `documentos`, `versiones_documento`, `anotaciones_entidad`, `auditoria` ni los seeds.

Se considera implementada cuando `flyway migrate` funciona desde cero, `views.sql` y `triggers.sql` no mencionan `rol`/`activo`, y `data-dictionary.md` tiene `usuarios_roles` y las columnas nuevas.

Esto decide **dónde** y aplica el modelo aceptado en [[0012-identidad-y-roles]]. @Kevin y @Alex pueden dejar constancia de conformidad por Teams, pero sus votos no bloquean la implementación.

## Consecuencias

- **La BD sigue siendo `V1`-`V15`.** Ni `V13` ni `V16`; el hueco se queda.
- **Hay que recrear la base de desarrollo**: `V15` ya está aplicada y Flyway guarda su *checksum*. No hay datos reales, solo seeds, así que es `flyway clean` + `migrate` (o borrar el esquema y volver a migrar). Si alguien la aplicó fuera de desarrollo, `flyway repair` no basta: el esquema cambia.
- **`V15` deja de ser solo flujo de revisión y export.** Su nombre miente un poco; se acepta antes que abrir una migración nueva con otro número.
- Los cambios en `views.sql`, `triggers.sql` y `data-dictionary.md` se aplicaron el 24/11 junto con esta implementación.
- **Riesgo asumido**: si el ICAT tarda en dar el registro OIDC, la tabla `usuarios` ya tendrá el hueco (`sso_subject`) y el admin de desarrollo funcionará mientras tanto.

## Qué falta

- Validarlo desde cero en desarrollo: `flyway clean` + `migrate`, comprobar la vista y el trigger, y revisar el diccionario de datos.
- La conformidad de @Kevin y @Alex en [[0012-identidad-y-roles]], que se recogerá por Teams sin bloquear la implementación ya aceptada por @Rubén.
- El registro de la aplicación OIDC en el ICAT, que es lo único que no depende del equipo.
