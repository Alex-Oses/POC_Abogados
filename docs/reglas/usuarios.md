# Usuarios — ciclo de vida, roles y sesiones

**Estado:** propuesta; roles e identidad en revisión por [[0012-identidad-y-roles]] (18/11/2026).
**Lista completa para revisar:** [`reglas-de-negocio.md`](reglas-de-negocio.md) (U-01 a U-21 y A-01 a A-24 en un solo fichero).
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

**Regla U-01 — varios roles por usuario (propuesto, [[0012-identidad-y-roles]]).** Los roles viven en una **columna `usuarios.roles`** (`TEXT[]`, sin tabla N:M) y el permiso es la **unión**. `usuarios.rol` desaparece. Hay tres roles: `transcriptor`, `revisor` y `admin`; **el supervisor se elimina** y sus funciones pasan al revisor.

*Riesgo asumido:* un rol único obligaba a cuentas duplicadas cuando la misma persona sube, revisa y administra. Con roles múltiples, la separación de funciones ya no la da el rol: la darían A-07 (nadie revisa lo suyo) y A-15 (otro revisor firma), ambas retiradas o en pausa, así que hoy un revisor puede revisar y cerrar un documento que subió él.

**Regla U-02 — el permiso se comprueba en el servidor, siempre.** Los roles se releen de la base de datos en cada petición; el token no arrastra los roles con los que se emitió.

## 3. Matriz de capacidades

| Capacidad | transcriptor | revisor | admin |
| --- | --- | --- | --- |
| Subir documentos | sí | — | — |
| Ver sus documentos | sí | sí (todos) | — |
| Lanzar anonimización | sí | sí | — |
| Revisar anotaciones | — | sí | — |
| Cerrar revisión | — | sí | — |
| Asignar y reasignar | — | sí | — |
| Visto bueno final | — | en pausa (A-15) | — |
| Exportar aprobado | sus documentos | sí | — |
| Reglas y categorías | — | — | sí |
| Usuarios y roles | — | — | sí |
| Auditoría | — | lectura | lectura |
| Configuración del sistema | — | — | sí |

**Regla U-03 — propiedad del recurso (solo transcriptor puro).** Quien tiene **únicamente** el rol de transcriptor solo ve y opera sobre documentos con `creado_por = usuario_id`. Si además es revisor, ve y revisa todos, aunque haya subido alguno. El admin no ve contenido de documentos, solo metadatos.

## 4. Ciclo de vida de la cuenta

```text
activo → bloqueado → activo
   └──→ baja (irreversible)
```

| Estado | Quién lo provoca | Efecto |
| --- | --- | --- |
| `activo` | Primer acceso con SSO; el admin de desarrollo se siembra ya activo | Acceso completo |
| `bloqueado` | Admin, o N intentos fallidos (solo login local) | Login denegado; sesiones revocadas |
| `baja` | Admin | Login denegado; datos conservados según plazo legal |

**Regla U-04 — el estado es explícito.** `usuarios.estado` sustituye al booleano `activo`. Con un booleano no se distingue «bloqueado» de «baja», y la auditoría no puede explicar por qué alguien no entra.

**Regla U-05 — alta por SSO (propuesta en [[0009-identidad]] y [[0012-identidad-y-roles]]).** No hay autoregistro, ni invitación, ni contraseñas de usuario. El primer acceso con SSO crea la ficha en `activo` y **sin roles**; un admin le asigna los suyos y hasta entonces no ve documentos. El administrador de desarrollo se siembra por variable de entorno (U-21).

**Regla U-06 — el primer admin se siembra.** El admin de desarrollo se crea por variable de entorno, nunca por endpoint público. Sin esta regla, el sistema no arranca. No se despliega en producción (U-21).

**Regla U-08 — la baja no borra.** Se marca `estado = baja` y `eliminado_en`. Las anotaciones, revisiones y auditoría siguen apuntando al usuario; un `DELETE` real rompería la trazabilidad.

U-07 (validez de 72 h de la invitación) se retira el 18/11: con SSO no hay invitación. El número no se reutiliza.

**Regla U-09 — cambio de roles con efecto inmediato.** Al cambiar los roles de un usuario se revocan todas sus sesiones abiertas. Si no, sigue operando con los roles anteriores hasta que caduque el token.

## 5. Contraseñas

Con SSO ([[0009-identidad]]), esta sección ya solo mira al **admin de desarrollo**: no hay contraseñas de usuario. U-10 a U-15 se retiran el 18/11; el admin local sigue funcionando igual, pero deja de tener reglamento propio.

**Regla U-21 — la credencial del admin de desarrollo no vive en el repo.** Se siembra por variable de entorno, no se versiona y **no se despliega en producción**. El admin local funciona igual que antes (login y cambio de contraseña); lo que desaparece es el reglamento sobre cómo se gestiona su contraseña y, con U-10 a U-15, el reset por correo. El hash, la política, el bloqueo por intentos y el mensaje de error se quedan en el código como están.

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
| Roles, varios por usuario | `usuarios.roles TEXT[]` con `CHECK (roles <@ ARRAY['transcriptor','revisor','admin'])` e índice GIN (columna, no tabla) | U-01 |
| Motivo de la baja | `usuarios.motivo_baja` | U-08 |
| Fecha del último cambio de contraseña | `usuarios.password_cambiado_en` (solo admin de desarrollo, sin regla propia) | — |
| Tokens de un solo uso | **no se crea `tokens_usuario`**: U-10 a U-15 retiradas (18/11); la credencial del admin de desarrollo viene de entorno (U-21) | — |
| Orden de antigüedad de sesiones | `sesiones_usuario.creado_en`, **solo si no se delega la sesión en el ICAT** | U-17 |

Nada de esta tabla está todavía en `docs/architecture/`: son columnas propuestas, pendientes de bajar al modelo en `V13`.

## 8. Endpoints

Todos están ya en `docs/api/endpoints.md`, que es el dueño de los payloads.

`POST /user/register` se elimina del contrato. Con SSO, las rutas de contraseña quedan como **camino del admin de desarrollo** y la invitación y el reset se retiran (U-10 a U-15); el usuario real entra por el callback SSO, que el contrato aún no tiene ([[0009-identidad]]).

```text
GET    /auth/sso/login               propuesta: único camino de producción
GET    /auth/sso/callback            propuesta: crea la ficha sin roles
POST   /user/password/change         solo admin de desarrollo
DELETE /admin/users/{id}/sessions  revocar todas las sesiones
GET    /user/me
POST   /user/login                   solo admin de desarrollo
POST   /user/logout
GET    /admin/users?roles=&estado=
PATCH  /admin/users/{id}
```

**Decisiones cerradas:** U-05 (alta por SSO, propuesta en 0009/0012), U-17 (3 sesiones). **Abierta:** U-01, roles múltiples ([[0012-identidad-y-roles]]).

**Pendiente de negocio (no bloquea):** plazo legal de conservación tras la baja.
