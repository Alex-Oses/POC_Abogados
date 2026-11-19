# 0005 — Reglas de usuarios y flujo de aprobación

- **Estado**: Aceptada (2026-11-19, @Rubén)
- **Fecha**: 2026-11-16
- **Autor**: @ia-opencode-ruben

## Contexto

El contrato de la API tenía 5 rutas y no decía nada de quién puede entrar, cómo se retira el acceso, quién revisa ni cuándo un documento se considera cerrado. Se han escrito dos documentos de reglas, con payloads delegados al contrato:

- [docs/reglas/usuarios.md](../../docs/reglas/usuarios.md): ciclo de vida de la cuenta, roles, contraseñas, sesiones (U-01 a U-20).
- [docs/reglas/aprobacion.md](../../docs/reglas/aprobacion.md): máquina de estados, cola de revisión, rechazo y reentrada, visto bueno, plazos (A-01 a A-23).
- [docs/api/endpoints.md](../../docs/api/endpoints.md): las 40 rutas que implementan lo anterior.

## Decisión

Se cierran estas reglas, que son las que cambian el contrato y el modelo:

1. **Roles múltiples por usuario en la tabla `usuarios_roles (usuario_id, rol)`**: el permiso es la unión ([[0012-identidad-y-roles]]). Tres roles: `transcriptor`, `revisor` y `admin`; el supervisor desaparece y sus funciones pasan al revisor.
2. **Alta por SSO**: la ficha se crea al primer acceso y un admin le asigna los roles. No hay autoregistro, ni invitación, ni contraseñas de usuario; solo el admin de desarrollo tiene credencial local ([[0009-identidad]]).
3. **Máximo 3 sesiones simultáneas**; la cuarta revoca la más antigua.
4. **Cola de revisión libre**: la revisión nace `en_cola` y el revisor toma el documento que quiere con `claim`; no se asigna de oficio. La asignación directa queda como excepción (propuesta de @Rubén, 18/11).
5. **No se aprueba con anotaciones pendientes.** Sin casilla de «revisado el resto».
6. **Doble firma: en pausa** (18/11). Exige identificar datos del art. 9-10 y montar una segunda firma; @Rubén la deja parada. Mientras dure, `requiere_visto_bueno` se queda en `false`.
7. ~~Plazo de 48 h laborables con aviso a las 24 h~~ **Retirada** (18/11): el piloto no lleva plazos.

## Consecuencias

- El contrato pasa de 5 a 40 rutas; `/user/register` desaparece. Con SSO, las rutas de invitación y contraseña quedan como camino del admin de desarrollo ([[0012-identidad-y-roles]]).
- Hacen falta columnas que hoy no están en `docs/architecture/` (`roles`, `estado`, `sso_subject`, `motivo_baja`, `revisiones.asignado_a` ya está en `V15`, `documentos.requiere_visto_bueno`/`hash_export`) y la tabla `sesiones_usuario` (sesión propia, decidida el 18/11). **No se toca el modelo en este PR**: el encaje queda pendiente y se decidirá aparte.
- Depende de [[0004-anonimizacion-antes-o-despues-de-revision]]: el flujo asume que se conserva el original y se anonimiza antes de la revisión.
- Queda abierto el plazo legal de conservación tras la baja; mientras no exista, no se purga nada.
