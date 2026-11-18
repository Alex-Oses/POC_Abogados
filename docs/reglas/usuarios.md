# Usuarios — ciclo de vida, roles y sesiones

**Estado:** propuesta; roles e identidad en revisión por [[0012-identidad-y-roles]] (18/11/2026).
**Contrato HTTP:** `docs/api/endpoints.md` (aquí solo se referencian rutas, no se redefinen).
**Modelo de datos:** `docs/architecture/` (migraciones Flyway).

## 1. Alcance

Quién puede entrar, qué puede hacer y cómo se le retira el acceso. No describe payloads ni códigos de estado: eso está en el contrato.

## 2. Roles

| Rol | Para quién | Alcance |
| --- | --- | --- |
| `transcriptor` | Personal que digitaliza expedientes | Sus propios documentos |
| `revisor` | Abogado que valida la anonimización | Todos los documentos en revisión, asignación, visto bueno y auditoría |
| `admin` | Sistemas | Usuarios y roles, reglas, categorías y configuración |

**Regla U-01 — varios roles por usuario (propuesto, [[0012-identidad-y-roles]]).** Los roles viven en `usuarios_roles (usuario_id, rol)` (N:M) y el permiso es la **unión**. `usuarios.rol` desaparece. Hay tres roles: `transcriptor`, `revisor` y `admin`; **el supervisor se elimina** y sus funciones pasan al revisor.

*Riesgo asumido:* un rol único obligaba a cuentas duplicadas cuando la misma persona sube, revisa y administra. Con roles múltiples, A-07 (nadie revisa lo suyo) y A-15 (otro revisor firma) son las que mantienen la separación de funciones.

**Regla U-02 — el permiso se comprueba en el servidor, siempre.** Los roles se releen de `usuarios_roles` en cada petición; el token no arrastra los roles con los que se emitió.

## 3. Matriz de capacidades

| Capacidad | transcriptor | revisor | admin |
| --- | --- | --- | --- |
| Subir documentos | sí | — | — |
| Ver sus documentos | sí | sí (todos) | — |
| Lanzar anonimización | sí | sí | — |
| Revisar anotaciones | — | sí | — |
| Cerrar revisión | — | sí | — |
| Asignar y reasignar | — | sí | — |
| Visto bueno final | — | otro revisor, no quien cerró | — |
| Exportar aprobado | sus documentos | sí | — |
| Reglas y categorías | — | — | sí |
| Usuarios y roles | — | — | sí |
| Auditoría | — | lectura | lectura |
| Configuración del sistema | — | — | sí |

**Regla U-03 — propiedad del recurso.** El transcriptor solo ve y opera sobre documentos con `creado_por = usuario_id`. El revisor ve todos; el admin no ve contenido de documentos, solo metadatos.

## 4. Ciclo de vida de la cuenta

```text
invitado → activo → bloqueado → activo
              └──→ baja (irreversible)
```

| Estado | Quién lo provoca | Efecto |
| --- | --- | --- |
| `invitado` | Solo camino local de desarrollo | Tiene token de invitación; no puede iniciar sesión hasta fijar contraseña. Con SSO no se usa |
| `activo` | Acepta la invitación (o reset de contraseña) | Acceso completo |
| `bloqueado` | Admin, o 10 intentos fallidos | Login denegado; sesiones revocadas |
| `baja` | Admin | Login denegado; datos conservados según plazo legal |

**Regla U-04 — el estado es explícito.** `usuarios.estado` sustituye al booleano `activo`. Con un booleano no se distingue «invitado» de «bloqueado», y la auditoría no puede explicar por qué alguien no entra.

**Regla U-05 — alta por SSO (propuesta en [[0009-identidad]] y [[0012-identidad-y-roles]]).** No hay autoregistro, ni invitación, ni contraseñas de usuario. El primer acceso con SSO crea la ficha en `activo` y **sin roles**; un admin le asigna los suyos y hasta entonces no ve documentos. El administrador de desarrollo se siembra por migración o variable de entorno.

**Regla U-06 — el primer admin se siembra.** El admin de desarrollo se crea por migración o variable de entorno, nunca por endpoint público. Sin esta regla, el sistema no arranca. No se despliega en producción.

**Regla U-07 — sin invitación con SSO.** Con SSO no hay token de invitación: U-07 queda sin efecto. Si el piloto vuelve a cuentas locales, se recupera la validez de 72 h (`configuracion_sistema.invitacion_ttl_horas`).

**Regla U-08 — la baja no borra.** Se marca `estado = baja` y `eliminado_en`. Las anotaciones, revisiones y auditoría siguen apuntando al usuario; un `DELETE` real rompería la trazabilidad.

**Regla U-09 — cambio de roles con efecto inmediato.** Al cambiar los roles de un usuario se revocan todas sus sesiones abiertas. Si no, sigue operando con los roles anteriores hasta que caduque el token.

## 5. Contraseñas

Con SSO ([[0009-identidad]]), esta sección solo aplica al **admin de desarrollo**: no hay contraseñas de usuario.

**Regla U-10 — el servidor hashea, el cliente nunca.** Argon2id con sal por usuario. La contraseña viaja en claro dentro de TLS y no se registra en logs.

**Regla U-11 — política mínima.** 12 caracteres, sin exigir composición artificial (mayúsculas y símbolos obligatorios producen contraseñas peores). Opcional: rechazo contra listas de contraseñas comprometidas.

**Regla U-12 — recuperación con enlace de un solo uso.** Token de 32 bytes guardado **hasheado**, caducidad 30 minutos, un uso. Al consumirse se revocan todas las sesiones del usuario. Es el mismo mecanismo que la invitación, con distinto `tipo` en `tokens_usuario`.

**Regla U-13 — cambio de contraseña revoca sesiones.** Incluido el cambio hecho por el propio usuario.

**Regla U-14 — bloqueo progresivo.** 5 intentos fallidos en 15 minutos → `429`. 10 acumulados → `estado = bloqueado` y aviso al admin. El contador se reinicia con un login correcto.

**Regla U-15 — respuesta de login indistinguible.** Mismo mensaje y mismo tiempo de respuesta para «email inexistente» y «contraseña incorrecta».

## 6. Sesiones

**Regla U-16 — token opaco, no JWT.** `sesiones_usuario` guarda `token_hash`, `expira_en` y `revocado_en`; con eso la revocación es inmediata. Un JWT sin estado obligaría a mantener además una lista negra, que es la misma consulta a base de datos con más piezas.

**Regla U-17 — máximo 3 sesiones simultáneas (decidido).** Al crear la cuarta se revoca la más antigua por `creado_en`. Cambiar de dispositivo no debería obligar a cerrar sesión en los demás, pero 20 sesiones abiertas sí son un agujero.

**Regla U-18 — caducidad.** Acceso 1 hora; renovación mientras haya actividad y la cuenta siga `activo`. Máximo absoluto 12 horas por sesión.

**Regla U-19 — revocación.** Se revoca al: cambiar contraseña, cambiar los roles, bloquear o dar de baja al usuario, superar el límite de sesiones y cuando el admin fuerza el cierre. Toda revocación se escribe en `auditoria`.

**Regla U-20 — logout es revocación, no borrado.** `revocado_en`, nunca `DELETE`: la sesión forma parte de la auditoría.

## 7. Lo que falta en el esquema

| Necesidad | Columna o tabla | Regla |
| --- | --- | --- |
| Estado real de la cuenta | `usuarios.estado` (sustituye a `activo`) | U-04 |
| Identidad del proveedor | `usuarios.sso_subject` (único) | U-05 |
| Roles, varios por usuario | tabla `usuarios_roles`: `usuario_id`, `rol` (`transcriptor`\|`revisor`\|`admin`), PK compuesta | U-01 |
| Motivo de la baja | `usuarios.motivo_baja` | U-08 |
| Fecha del último cambio de contraseña | `usuarios.password_cambiado_en` (solo admin de desarrollo) | U-13 |
| Tokens de un solo uso | tabla `tokens_usuario`: **solo camino local de desarrollo**; en producción no se usa (no hay invitación ni reset) | U-05, U-12 |
| Orden de antigüedad de sesiones | `sesiones_usuario.creado_en` (ya existe) | U-17 |

Nada de esta tabla está todavía en `docs/architecture/`: son columnas propuestas, pendientes de bajar al modelo en `V13`.

## 8. Endpoints

Todos están ya en `docs/api/endpoints.md`, que es el dueño de los payloads.

`POST /user/register` se elimina del contrato. Con SSO, las rutas de invitación y contraseña quedan como **camino del admin de desarrollo**; el usuario real entra por el callback SSO, que el contrato aún no tiene ([[0009-identidad]]).

```text
POST   /admin/users                  alta por SSO o siembra del admin de desarrollo
POST   /user/invitation/accept       solo camino local de desarrollo
POST   /user/password/change         solo admin de desarrollo
POST   /user/password/reset          solo admin de desarrollo
POST   /user/password/reset/confirm  solo admin de desarrollo
DELETE /admin/users/{id}/sessions  revocar todas las sesiones
GET    /user/me
POST   /user/login                   solo admin de desarrollo
POST   /user/logout
GET    /admin/users?rol=&estado=
PATCH  /admin/users/{id}
```

**Decisiones cerradas:** U-05 (alta por SSO, propuesta en 0009/0012), U-17 (3 sesiones). **Abierta:** U-01, roles múltiples ([[0012-identidad-y-roles]]).

**Pendiente de negocio (no bloquea):** plazo legal de conservación tras la baja.
