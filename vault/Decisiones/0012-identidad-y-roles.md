# 0012 · Identidad y roles: SSO, tres roles y roles múltiples

- **Estado**: Propuesta
- **Fecha**: 2026-11-18
- **Autor**: @ia-opencode-ruben (a petición de @Rubén)
- **Se decide con**: @Rubén (backend), @Marina (BD, decide el modelo), @Kevin (despliegue), @Alex (frontend/OCR)
- **Votos**: @Rubén (backend), 2026-11-18: **SSO sin gestión de cuentas, tres roles, roles múltiples y sesión propia en `sesiones_usuario`**. @Marina (BD, decide el modelo), 2026-11-18: **los roles van en tabla `usuarios_roles` (N:M), no en columna**; el resto de la propuesta, sin cambios. @Rubén (backend), 2026-11-20: **confirma la tabla `usuarios_roles` de @Marina y no ve problema en el `JOIN`/`EXISTS` de `v_metricas_revisor` ni en el trigger de revisor**. Faltan @Kevin y @Alex.

## Contexto

Tres piezas estaban decididas por separado y no encajan entre sí:

- [[0009-identidad]] propone SSO **más un admin local de emergencia**, y el contrato implementa contraseñas con invitación.
- [[0005-reglas-usuarios-y-aprobacion]] fija **un rol por usuario** (`usuarios.rol`) y cuatro roles, con `supervisor` para asignar, dar el visto bueno y reabrir.
- [[0011-ajustes-al-modelo-de-marina]] acaba de aceptar `V14` y `V15`; `V13` (identidad) sigue sin escribir porque espera a 0009. [[0010-modelo-de-datos]] cierra con `usuarios.rol` de un solo valor.

@Rubén cambia el criterio el 18/11: **el producto no gestiona cuentas**. Entra quien el ICAT diga, y el software solo guarda qué puede hacer cada persona. En ese momento el cambio salía gratis porque `V13` no existía; el 23/11 se cerró que va al final de `V15` editada ([[0015-identidad-en-v15]]), sin abrir migración nueva.

## Decisión

1. **SSO del ICAT como única entrada.** No hay invitación, ni alta manual, ni contraseñas de usuario, ni proveedor de correo. El proveedor valida y devuelve `sub`; el backend busca o crea la ficha y abre sesión.
2. **Un único login local: el admin de desarrollo.** Sembrado por variable de entorno, con contraseña fuerte, **no se despliega en producción** (U-21). Sirve para pruebas y para arrancar el sistema sin depender del ICAT.
3. **Tres roles**: `transcriptor`, `revisor`, `admin`. **El supervisor desaparece** y sus funciones pasan al revisor: asignar y reasignar (A-06), liberar o devolver el visto bueno (A-15, en pausa), reabrir un aprobado (A-19) y consultar la auditoría.
4. **Varios roles por usuario en una tabla**, `usuarios_roles (usuario_id, rol)`: el permiso es la **unión** de los roles. **`usuarios.rol` desaparece.** La clave es el par (`usuario_id`, `rol`), con FK a `usuarios` y `CHECK` de los tres valores; sin columnas de más, el «quién y cuándo» va a `auditoria`.
5. **La doble firma queda en pausa** (18/11): A-07 (nadie revisa lo suyo) se retira y A-15 (otro revisor firma) se para. Consecuencia asumida: hoy un revisor puede revisar y cerrar un documento que subió él.
6. **La primera entrada crea la ficha sin roles.** Un usuario sin roles no ve documentos; un admin le asigna los suyos. No hay alta previa ni invitación que esperar.
7. **La sesión es nuestra** (18/11, @Rubén): token opaco revocable, 3 a la vez, 1 h con renovación y 12 h máximo, revocado al cambiar roles, bloquear o dar de baja. Se guarda en `sesiones_usuario`, una de las **dos tablas nuevas** de `V15` (editada, [[0015-identidad-en-v15]]).

## Lo que cambia en la base de datos

Sobre lo aceptado en 0011. **Todo lo estructural cabe al final de `V15` (editada)**, porque `V13` no existe ni se va a escribir ([[0015-identidad-en-v15]]). **Dos tablas nuevas: `usuarios_roles` (decisión de @Marina) y `sesiones_usuario`.**

| Dónde | Qué cambia | Coste |
|---|---|---|
| `V1__create_usuarios.sql` | `usuarios.rol` y su `CHECK` de cuatro valores se retiran al final de `V15` editada, no en `V1` (V1-V14 no se tocan) | nulo: unas líneas al final de `V15` |
| `V15` · roles | Entra `usuarios_roles (usuario_id, rol)` con FK a `usuarios`, `CHECK (rol IN ('transcriptor','revisor','admin'))` y `PRIMARY KEY (usuario_id, rol)`. Sale `usuarios.rol` | 1 tabla |
| `V15` · identidad | Entra `usuarios.sso_subject TEXT UNIQUE` y `usuarios.password_hash TEXT` (nuevo y nulo: solo lo usa el admin de desarrollo) | 2 líneas |
| `V15` · cuenta | Entra `usuarios.estado` (`activo`/`bloqueado`/`baja`) y sale `activo` (U-04); entran `motivo_baja` y `eliminado_en` (U-08) | 3 líneas |
| `V15` · índices | `idx_usuarios_rol_activo (rol, activo)` se cae con las columnas viejas; entra `(estado)` y un índice por `usuarios_roles (rol)` para listar revisores | 2 líneas |
| `V15` · sesiones | Entra `sesiones_usuario` (decisión de @Rubén, 18/11): `usuario_id`, `token_hash`, `creado_en`, `expira_en`, `revocado_en`, `ip`, `user_agent` | 1 tabla |
| `V15__flujo_revision_y_export.sql` | **Aquí va todo lo anterior, al final del fichero** ([[0015-identidad-en-v15]]). Además, `visto_bueno_por` ya es un FK a `usuarios` y no comprueba rol; dos comentarios dicen «supervisor» → «revisor» | lo de las filas de arriba, más 2 líneas de texto |
| `triggers.sql` (validación de revisor) | `(SELECT rol FROM usuarios ...)` pasa a `NOT EXISTS (SELECT 1 FROM usuarios_roles WHERE usuario_id = NEW.asignado_a AND rol = 'revisor')` | 2 líneas; lo firma @Marina |
| `views.sql` (`v_metricas_revisor`) | `u.rol = 'revisor' AND u.activo` pasa a `EXISTS (... usuarios_roles ... rol = 'revisor') AND u.estado = 'activo'` | 2 líneas; lo firma @Marina |
| `data-dictionary.md` | La fila `rol` sale; entra la tabla `usuarios_roles` y, en `usuarios`, `estado` y `sso_subject` | texto |
| Seeds | No hay ningún `INSERT INTO usuarios` en las migraciones: el admin inicial ya se creaba fuera. No hay datos que migrar | nulo |

**Lo que no hay que tocar:** `revisiones.asignado_a`, `documentos.visto_bueno_por`, `documentos.visto_bueno_en` y `auditoria` no dependen del rol. El cambio de rol no reescribe filas históricas: quien firmó queda firmado.

### Por qué una tabla y no una columna de roles

| | `usuarios.roles TEXT[]` *(descartada)* | **`usuarios_roles` (N:M)** *(elegida por @Marina, 18/11)* |
|---|---|---|
| Cambio en la BD | 1 columna + 1 `CHECK` + 1 índice GIN | 1 tabla + `JOIN` en trigger y vista |
| Integridad | `CHECK` contra tres valores fijos | FK al usuario + `CHECK` de tres valores |
| Consulta | `'revisor' = ANY(roles)` | `JOIN` o `EXISTS` |
| Añadir un rol | Reescribir el `CHECK` de la columna | Un valor más en el `CHECK` de `rol` |
| Metadato del par (quién lo dio, cuándo) | No; va a `auditoria` | Tampoco hoy: la tabla solo tiene el par. Se puede añadir sin cambiar de forma |

@Marina decide el modelo y elige la tabla el 18/11: el rol pasa a ser una **fila** con FK al usuario, y el catálogo de tres valores se valida en `usuarios_roles.rol`. El coste son dos tablas nuevas en `V15` en vez de una y un `JOIN` en la vista de métricas y en el trigger de revisor; a cambio, el rol deja de ser un tipo especial (`TEXT[]`) y un cuarto rol, o colgar del par quién lo asignó, no obliga a cambiar el tipo de una columna.

### La tabla de sesiones: `sesiones_usuario`

Ninguna columna sustituye a una tabla de sesiones: U-16 (token opaco revocable), U-17 (tope de 3 dispositivos) y U-20 (logout como revocación) son estado en servidor. **Decidido por @Rubén el 18/11: la sesión es nuestra, opción B.** Se queda lo que ya estaba escrito en [[0005-reglas-usuarios-y-aprobacion]] y [[0010-modelo-de-datos]] y U-16 a U-20 siguen vigentes.

| Opción | Tablas nuevas de sesión | Qué se pierde |
|---|---|---|
| **B. Sesión propia en `sesiones_usuario`** *(elegida)* | **1** | Nada: tope de 3 dispositivos, «cerrar sesión en todas partes» y revocación al cambiar roles, bloquear o dar de baja |
| A. Delegar la sesión en el token del ICAT *(descartada)* | 0 | Tope de dispositivos y logout remoto; habría que retirar U-16 a U-20 |

A habría ahorrado la tabla, pero **U-02 ya obliga a releer los roles en cada petición**, así que lo único que la tabla compra es control de sesiones, y el equipo lo quiere: con SSO, cerrar sesión en el ICAT no cierra la nuestra. El `CREATE TABLE` está en el bloque de abajo.

### Lo que ya no hay que crear

`tokens_usuario` **no se crea**: al retirar U-10 a U-15 no hay invitación ni reset gobernados por token, y la contraseña del admin de desarrollo se cambia cambiando la variable de entorno (U-21). Tampoco hace falta nada por A-15 (en pausa: las columnas de `V15` se quedan sin usar) ni por A-20 (retirada: `fecha_limite` y `aviso_24h_enviado_en` existen y se quedan vacías).

### Para @Marina: el SQL de `V15`

Esto es todo lo que habría que añadir al final de `V15`: **dos tablas nuevas y el resto columnas** ([[0015-identidad-en-v15]]). Se aplica sobre el `usuarios` que deja `V1` (`rol`, `activo`, `creado_en`, `actualizado_en`) y no toca `V1`-`V14`:

```sql
-- 1. Roles: una tabla N:M en lugar de una columna (decisión de @Marina, 18/11)
ALTER TABLE usuarios DROP COLUMN rol;

CREATE TABLE usuarios_roles (
    usuario_id UUID NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    rol        TEXT NOT NULL CHECK (rol IN ('transcriptor','revisor','admin')),
    PRIMARY KEY (usuario_id, rol)
);

-- 2. Cuenta: tres estados en lugar de un booleano
ALTER TABLE usuarios DROP COLUMN activo;
ALTER TABLE usuarios ADD COLUMN estado TEXT NOT NULL DEFAULT 'activo'
  CHECK (estado IN ('activo','bloqueado','baja'));
ALTER TABLE usuarios ADD COLUMN motivo_baja  TEXT;
ALTER TABLE usuarios ADD COLUMN eliminado_en TIMESTAMPTZ;

-- 3. Identidad del ICAT y credencial del admin de desarrollo
ALTER TABLE usuarios ADD COLUMN sso_subject   TEXT UNIQUE;
ALTER TABLE usuarios ADD COLUMN password_hash TEXT;   -- nulo: solo lo usa el admin de desarrollo

-- 4. Índices: el viejo se cae con las columnas que quita
DROP INDEX IF EXISTS idx_usuarios_rol_activo;   -- cae sola con `rol`/`activo`; IF EXISTS para reintentos
CREATE INDEX idx_usuarios_estado ON usuarios (estado);
CREATE INDEX idx_usuarios_roles_rol ON usuarios_roles (rol);

-- 5. Sesión propia (opción B, decidida por @Rubén el 18/11): la segunda tabla nueva
CREATE TABLE sesiones_usuario (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  UUID NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_en   TIMESTAMPTZ NOT NULL,
    revocado_en TIMESTAMPTZ,
    ip          INET,
    user_agent  TEXT
);
CREATE INDEX idx_sesiones_usuario_usuario ON sesiones_usuario (usuario_id, creado_en DESC);
```

Y dos cambios de texto en ficheros que ya existen:

```sql
-- views.sql, v_metricas_revisor
WHERE EXISTS (
    SELECT 1 FROM usuarios_roles ur
    WHERE ur.usuario_id = u.id AND ur.rol = 'revisor'
) AND u.estado = 'activo'

-- triggers.sql, validación de revisor
AND NOT EXISTS (
    SELECT 1 FROM usuarios_roles
    WHERE usuario_id = NEW.asignado_a AND rol = 'revisor'
)
```

**No hay que crear:** `tokens_usuario`, `password_cambiado_en`, `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso`. Ninguna regla vigente los pide; si el login local del admin necesita límite de intentos, es una columna y se añade entonces.

**Las tablas nuevas son dos: `usuarios_roles` y `sesiones_usuario`**, con las columnas de los bloques de SQL de arriba.

## Lo que cambia fuera de la base de datos

| Dónde | Qué |
|---|---|
| **Contrato** | Bloque de roles (tres, varios por usuario), campo de roles de 4 rutas (`assign`, `sign-off`, `audit`), payloads de `/admin/users` (`rol` → `roles`), fuera `fecha_limite` (A-20) y los `403` de A-07. Las rutas de contraseña quedan como bloque de desarrollo y entran `GET /auth/sso/login` y `/auth/sso/callback` como propuesta |
| **Reglas U** | U-01 (varios roles en `usuarios_roles`), U-02 (releer de `usuarios_roles`), U-03 y U-09; U-19 gana «cambio de roles»; **U-10 a U-15 se retiran** y su contenido queda en U-21 |
| **Reglas A** | A-06 pasa a cola libre; A-08, A-14, A-15 y A-19 pasan de supervisor a revisor. A-07 y A-20 se retiran (18/11) |
| [[0005-reglas-usuarios-y-aprobacion]] | Reglas 1, 2, 4 y 6 |
| [[0009-identidad]] | La opción 3 pasa de «admin de emergencia» a «admin de desarrollo»; `tokens_usuario` sale del todo |
| [[Enfoque tecnico]] | §5 y §11: SSO, tres roles, varios roles y su efecto en el modelo |

## Por qué así

- **SSO y no cuentas locales**: mantener contraseñas, política, bloqueos y SMTP es trabajo que no da valor y multiplica los sitios donde se filtra una credencial. El ICAT ya tiene la identidad.
- **Tres roles y no cuatro**: `supervisor` era una persona, no un permiso. Con roles múltiples, quien supervisa es un revisor con el mismo permiso; lo que no puede es firmar dos veces el mismo expediente.
- **Varios roles y no uno**: en un despacho de dos o tres personas la misma persona sube, revisa y administra. El rol único obligaba a cuentas duplicadas o a renunciar a la separación de funciones.

## Coste y riesgos

- **Riesgo asumido (SSO)**: si el tenant del ICAT cae o retira el permiso, **nadie entra**, ni a consultar lo aprobado. El admin local no se despliega en producción a propósito: es una puerta de desarrollo, no una de emergencia. Si negocio quiere emergencia real, es la opción 3 original y hay que decirlo.
- **Dependencia externa**: el registro OIDC del ICAT son 1-2 semanas de terceros y solo lo puede pedir una persona.
- **@Marina decide el modelo**: `usuarios_roles`, `estado`, `sso_subject` y la retirada de `tokens_usuario` cambian su diagrama del 17/11. Los roles ya los decidió el 18/11 (tabla); el resto queda escrito para que lo acepte o lo corrija.
- **La tabla no valida el rol contra un catálogo**: el `CHECK` fija tres valores. Si mañana los define el cliente, se sustituye por una tabla `roles` con FK, sin tocar el resto.
- **Doble firma con tres roles**: si el equipo prefiere que cualquier revisor pueda firmar su propio cierre, A-15 pierde el sentido y hay que decirlo; no se cambia por la puerta de atrás.

## Qué falta

- Decidido: **B**, sesión propia en `sesiones_usuario` (18/11). U-16 a U-20 siguen vigentes.
- Decidido: **roles en tabla `usuarios_roles`** (@Marina, 18/11).
- Votos de @Kevin y @Alex a este documento y a [[0009-identidad]]; falta que @Rubén confirme el cambio de los roles a tabla.
- Que @Marina acepte el resto del cambio de modelo (`estado`, `sso_subject`, sin `tokens_usuario`): el SQL de la sección «Para @Marina» va al final de `V15` ([[0015-identidad-en-v15]]).
- Pedir al ICAT el registro de la aplicación OIDC.
