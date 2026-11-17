# Usuarios — ciclo de vida, roles y sesiones

**Estado:** propuesta con decisiones cerradas (16/11/2026).
**Contrato HTTP:** `docs/api/endpoints.md` (aquí solo se referencian rutas, no se redefinen).
**Modelo de datos:** `docs/architecture/` (migraciones Flyway).

## 1. Alcance

Quién puede entrar, qué puede hacer y cómo se le retira el acceso. No describe payloads ni códigos de estado: eso está en el contrato.

## 2. Roles

| Rol | Para quién | Alcance |
| --- | --- | --- |
| `transcriptor` | Personal que digitaliza expedientes | Sus propios documentos |
| `revisor` | Abogado que valida la anonimización | Todos los documentos en revisión |
| `supervisor` | Responsable del despacho | Lectura completa y visto bueno final |
| `admin` | Sistemas | Usuarios, reglas, categorías y configuración |

**Regla U-01 — un rol por usuario (decidido).** `usuarios.rol` es un valor único. Es suficiente para separar funciones y evita la tabla N:M.

*Riesgo asumido:* en un despacho de dos o tres personas no habrá nadie que solo revise. Si eso ocurre, la migración es `usuarios_roles` y afecta a la matriz de permisos y a la regla A-06 de `docs/reglas/aprobacion.md`. No se construye hasta que duela.

**Regla U-02 — el permiso se comprueba en el servidor, siempre.** El rol se relee de `usuarios` en cada petición; el token no arrastra el rol con el que se emitió.

## 3. Matriz de capacidades

| Capacidad | transcriptor | revisor | supervisor | admin |
| --- | --- | --- | --- | --- |
| Subir documentos | sí | — | — | — |
| Ver sus documentos | sí | sí (todos) | sí (todos) | — |
| Lanzar anonimización | sí | sí | — | — |
| Revisar anotaciones | — | sí | — | — |
| Cerrar revisión | — | sí | — | — |
| Visto bueno final | — | — | sí | — |
| Exportar aprobado | sus documentos | — | sí | — |
| Reglas y categorías | — | — | lectura | sí |
| Usuarios y sesiones | — | — | lectura | sí |
| Auditoría | — | — | sí | sí |
| Configuración del sistema | — | — | — | sí |

**Regla U-03 — propiedad del recurso.** El transcriptor solo ve y opera sobre documentos con `creado_por = usuario_id`. El revisor y el supervisor ven todos; el admin no ve contenido de documentos, solo metadatos.

## 4. Ciclo de vida de la cuenta

```text
invitado → activo → bloqueado → activo
              └──→ baja (irreversible)
```

| Estado | Quién lo provoca | Efecto |
| --- | --- | --- |
| `invitado` | Admin crea la cuenta | Tiene token de invitación; no puede iniciar sesión hasta fijar contraseña |
| `activo` | Acepta la invitación (o reset de contraseña) | Acceso completo |
| `bloqueado` | Admin, o 10 intentos fallidos | Login denegado; sesiones revocadas |
| `baja` | Admin | Login denegado; datos conservados según plazo legal |

**Regla U-04 — el estado es explícito.** `usuarios.estado` sustituye al booleano `activo`. Con un booleano no se distingue «invitado» de «bloqueado», y la auditoría no puede explicar por qué alguien no entra.

**Regla U-05 — solo por invitación (decidido).** No hay autoregistro. El admin crea la cuenta en estado `invitado`, el sistema envía un token de un solo uso al email y el usuario fija su contraseña con ese token. El autoregistro abierto es un agujero en un producto legal: cualquiera con la URL se crea una cuenta.

**Regla U-06 — el primer admin se siembra.** El admin inicial se crea por migración o variable de entorno, nunca por endpoint público. Sin esta regla, el sistema no arranca.

**Regla U-07 — la invitación caduca.** Token de un solo uso, validez 72 h (`configuracion_sistema.invitacion_ttl_horas`). Caducado, el admin reenvía una nueva.

**Regla U-08 — la baja no borra.** Se marca `estado = baja` y `eliminado_en`. Las anotaciones, revisiones y auditoría siguen apuntando al usuario; un `DELETE` real rompería la trazabilidad.

**Regla U-09 — cambio de rol con efecto inmediato.** Al cambiar `rol` se revocan todas las sesiones abiertas del usuario. Si no, sigue operando con el rol anterior hasta que caduque el token.

## 5. Contraseñas

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

**Regla U-19 — revocación.** Se revoca al: cambiar contraseña, cambiar rol, bloquear o dar de baja al usuario, superar el límite de sesiones y cuando el admin fuerza el cierre. Toda revocación se escribe en `auditoria`.

**Regla U-20 — logout es revocación, no borrado.** `revocado_en`, nunca `DELETE`: la sesión forma parte de la auditoría.

## 7. Lo que falta en el esquema

| Necesidad | Columna o tabla | Regla |
| --- | --- | --- |
| Estado real de la cuenta | `usuarios.estado` (sustituye a `activo`) | U-04 |
| Motivo de la baja | `usuarios.motivo_baja` | U-08 |
| Fecha del último cambio de contraseña | `usuarios.password_cambiado_en` | U-13 |
| Tokens de un solo uso | tabla `tokens_usuario`: `usuario_id`, `tipo` (`invitacion`\|`reset`), `token_hash`, `expira_en`, `usado_en` | U-05, U-12 |
| Orden de antigüedad de sesiones | `sesiones_usuario.creado_en` (ya existe) | U-17 |

`usuarios_roles` **no** se crea (U-01). Nada de esta tabla está todavía en `docs/architecture/`: son columnas propuestas, pendientes de bajar al modelo.

## 8. Endpoints

Todos están ya en `docs/api/endpoints.md`, que es el dueño de los payloads.

`POST /user/register` se elimina del contrato: el alta pasa por `POST /admin/users` y la aceptación por `POST /user/invitation/accept`.

```text
POST   /admin/users                  alta por invitación
POST   /user/invitation/accept       fijar contraseña con token de invitación
POST   /user/password/change
POST   /user/password/reset
POST   /user/password/reset/confirm
DELETE /admin/users/{id}/sessions  revocar todas las sesiones
GET    /user/me
POST   /user/login
POST   /user/logout
GET    /admin/users?rol=&estado=
PATCH  /admin/users/{id}
```

**Decisiones cerradas:** U-01 (rol único), U-05 (solo invitación), U-17 (3 sesiones).

**Pendiente de negocio (no bloquea):** plazo legal de conservación tras la baja.
