# 0005 — Reglas de usuarios y flujo de aprobación

- **Estado**: Propuesta
- **Fecha**: 2026-11-16
- **Autor**: @ia-opencode-ruben

## Contexto

El contrato de la API tenía 5 rutas y no decía nada de quién puede entrar, cómo se retira el acceso, quién revisa ni cuándo un documento se considera cerrado. Se han escrito dos documentos de reglas, con payloads delegados al contrato:

- [docs/reglas/usuarios.md](../../docs/reglas/usuarios.md): ciclo de vida de la cuenta, roles, contraseñas, sesiones (U-01 a U-20).
- [docs/reglas/aprobacion.md](../../docs/reglas/aprobacion.md): máquina de estados, cola de revisión, rechazo y reentrada, visto bueno, plazos (A-01 a A-23).
- [docs/api/endpoints.md](../../docs/api/endpoints.md): las 40 rutas que implementan lo anterior.

## Decisión

Se cierran estas reglas, que son las que cambian el contrato y el modelo:

1. **Un rol por usuario** (`usuarios.rol`), sin tabla N:M.
2. **Alta solo por invitación** del admin: no hay autoregistro. La cuenta nace `invitado` y se activa con un token de un solo uso.
3. **Máximo 3 sesiones simultáneas**; la cuarta revoca la más antigua.
4. **Cola de revisión**: la revisión nace `en_cola` sin revisor; `claim` la toma de forma atómica y el supervisor puede asignar o reasignar.
5. **No se aprueba con anotaciones pendientes.** Sin casilla de «revisado el resto».
6. **Doble firma solo en categorías especiales**: si la versión tiene alguna anotación de una categoría con `rgpd_especial = true` (art. 9-10 RGPD), el documento pasa por `pendiente_visto_bueno` y lo libera el supervisor. `nivel_riesgo` no interviene: casi todos los identificadores directos están en `alto` y la regla dejaría de ser excepcional.
7. **Plazo de 48 h laborables con aviso a las 24 h**, con calendario L-V 09:00-18:00 y festivos en `configuracion_sistema`.

## Consecuencias

- El contrato pasa de 5 a 40 rutas; `/user/register` desaparece.
- Hacen falta columnas y una tabla que hoy no están en `docs/architecture/` (`tokens_usuario`, `revisiones.en_cola`/`asignado_a`/`fecha_limite`, `documentos.pendiente_visto_bueno`/`visto_bueno_*`/`hash_export`). **No se toca el modelo en este PR**: el encaje queda pendiente y se decidirá aparte.
- Depende de [[0004-anonimizacion-antes-o-despues-de-revision]]: el flujo asume que se conserva el original y se anonimiza antes de la revisión.
- Queda abierto el plazo legal de conservación tras la baja; mientras no exista, no se purga nada.
