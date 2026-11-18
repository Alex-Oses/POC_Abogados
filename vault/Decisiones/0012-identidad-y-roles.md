# 0012 · Identidad y roles: SSO, tres roles y roles múltiples

- **Estado**: Propuesta
- **Fecha**: 2026-11-18
- **Autor**: @ia-opencode-ruben (a petición de @Rubén)
- **Se decide con**: @Rubén (backend), @Marina (BD, decide el modelo), @Kevin (despliegue), @Alex (frontend/OCR)
- **Votos**: @Rubén (backend), 2026-11-18: **SSO sin gestión de cuentas, tres roles, roles múltiples y sin tablas nuevas para los roles**. Faltan @Marina, @Kevin y @Alex.

## Contexto

Tres piezas estaban decididas por separado y no encajan entre sí:

- [[0009-identidad]] propone SSO **más un admin local de emergencia**, y el contrato implementa contraseñas con invitación.
- [[0005-reglas-usuarios-y-aprobacion]] fija **un rol por usuario** (`usuarios.rol`) y cuatro roles, con `supervisor` para asignar, dar el visto bueno y reabrir.
- [[0011-ajustes-al-modelo-de-marina]] acaba de aceptar `V14` y `V15`; `V13` (identidad) sigue sin escribir porque espera a 0009. [[0010-modelo-de-datos]] cierra con `usuarios.rol` de un solo valor.

@Rubén cambia el criterio el 18/11: **el producto no gestiona cuentas**. Entra quien el ICAT diga, y el software solo guarda qué puede hacer cada persona. Eso deja `V13` como el único sitio donde el cambio sale gratis: la migración no existe todavía.

## Decisión

1. **SSO del ICAT como única entrada.** No hay invitación, ni alta manual, ni contraseñas de usuario, ni proveedor de correo. El proveedor valida y devuelve `sub`; el backend busca o crea la ficha y abre sesión.
2. **Un único login local: el admin de desarrollo.** Sembrado por variable de entorno, con contraseña fuerte, **no se despliega en producción** (U-21). Sirve para pruebas y para arrancar el sistema sin depender del ICAT.
3. **Tres roles**: `transcriptor`, `revisor`, `admin`. **El supervisor desaparece** y sus funciones pasan al revisor: asignar y reasignar (A-06), liberar o devolver el visto bueno (A-15, en pausa), reabrir un aprobado (A-19) y consultar la auditoría.
4. **Varios roles por usuario en una columna**, `usuarios.roles TEXT[]`: el permiso es la **unión** de los roles. **`usuarios.rol` desaparece y no se crea ninguna tabla de roles.**
5. **La doble firma queda en pausa** (18/11): A-07 (nadie revisa lo suyo) se retira y A-15 (otro revisor firma) se para. Consecuencia asumida: hoy un revisor puede revisar y cerrar un documento que subió él.
6. **La primera entrada crea la ficha sin roles.** Un usuario sin roles no ve documentos; un admin le asigna los suyos. No hay alta previa ni invitación que esperar.

## Lo que cambia en la base de datos

Sobre lo aceptado en 0011. **Todo lo estructural cabe en `V13`**, que todavía no está escrita. **Ninguna tabla nueva para los roles.**

| Dónde | Qué cambia | Coste |
|---|---|---|
| `V1__create_usuarios.sql` | `usuarios.rol` y su `CHECK` de cuatro valores se retiran en `V13`, no en `V1` (V1-V12 no se tocan) | nulo: una migración que aún no existe |
| `V13` · roles | Entra `usuarios.roles TEXT[] NOT NULL DEFAULT '{}'` con `CHECK (roles <@ ARRAY['transcriptor','revisor','admin'])` y un índice GIN. Sale `rol` | 4 líneas |
| `V13` · identidad | Entra `usuarios.sso_subject TEXT UNIQUE`; `usuarios.password_hash` pasa a opcional (solo lo usa el admin de desarrollo) | 2 líneas |
| `V13` · cuenta | Entra `usuarios.estado` (`activo`/`bloqueado`/`baja`) y sale `activo` (U-04); entran `motivo_baja` y `eliminado_en` (U-08) | 3 líneas |
| `V13` · índices | `idx_usuarios_rol_activo (rol, activo)` se cae con las columnas viejas; entra `(estado)` + GIN `(roles)` | 2 líneas |
| `V13` · sesiones | **Única tabla candidata**: `sesiones_usuario` (ver abajo) | 1 tabla, y solo si se elige la opción B |
| `V15__flujo_revision_y_export.sql` | **Ningún cambio estructural.** `visto_bueno_por` ya es un FK a `usuarios` y no comprueba rol. Solo dos comentarios dicen «supervisor» → «revisor» | 2 líneas de texto |
| `triggers.sql` (validación de revisor) | `(SELECT rol FROM usuarios ...)` pasa a `(SELECT 'revisor' = ANY(roles) FROM usuarios WHERE id = NEW.asignado_a)` | 2 líneas; lo firma @Marina |
| `views.sql` (`v_metricas_revisor`) | `u.rol = 'revisor' AND u.activo` pasa a `'revisor' = ANY(u.roles) AND u.estado = 'activo'` | 2 líneas; lo firma @Marina |
| `data-dictionary.md` | La fila `rol` sale; entran `roles`, `estado`, `sso_subject` | texto |
| Seeds | No hay ningún `INSERT INTO usuarios` en las migraciones: el admin inicial ya se creaba fuera. No hay datos que migrar | nulo |

**Lo que no hay que tocar:** `revisiones.asignado_a`, `documentos.visto_bueno_por`, `documentos.visto_bueno_en` y `auditoria` no dependen del rol. El cambio de rol no reescribe filas históricas: quien firmó queda firmado.

### Por qué una columna y no una tabla de roles

| | `usuarios.roles TEXT[]` | `usuarios_roles` (N:M) |
|---|---|---|
| Cambio en la BD | 1 columna + 1 `CHECK` + 1 índice | 1 tabla + `JOIN` en trigger y vista |
| Integridad | `CHECK` contra tres valores fijos | FK contra un catálogo de roles |
| Consulta | `'revisor' = ANY(roles)` | `JOIN` o `EXISTS` |
| Metadato del par (quién lo dio, cuándo) | No; va a `auditoria` | Sí |

Con tres roles fijos y una decena de usuarios, la tabla no compra nada: el `CHECK` ya impide un rol inventado y no hay nada que colgar del par usuario-rol que no sea auditoría. **Cuándo migrar a tabla**: si los roles pasan a definirlos el cliente, dejan de ser un conjunto cerrado o hace falta historiar asignaciones en la propia tabla. Entonces será una migración pequeña con datos, y se hará con razón.

### La única tabla que queda: `sesiones_usuario`

Ninguna columna sustituye a una tabla de sesiones: U-16 (token opaco revocable), U-17 (tope de 3 dispositivos) y U-20 (logout como revocación) son estado en servidor. Hay dos salidas y la decisión es de @Rubén y @Kevin:

| Opción | Tablas nuevas | Qué se pierde |
|---|---|---|
| **A. Delegar la sesión en el token del ICAT** | **0** | No hay tope de dispositivos ni «cerrar sesión en todas partes» desde el panel; se retiran U-16 a U-20 |
| **B. Sesión propia en `sesiones_usuario`** | **1** | Nada; es lo que ya está escrito en 0005 y 0010 |

A es defendible porque **U-02 ya obliga a releer el rol en cada petición**, así que cambiar los roles surte efecto inmediato sin revocar nada, que es lo único que U-09 protegía. El tope de 3 y el logout global son comodidad, no seguridad. **Recomendación para el piloto: A**; si el cliente quiere control de sesiones, B.

### Lo que ya no hay que crear

`tokens_usuario` **no se crea**: al retirar U-10 a U-15 no hay invitación ni reset gobernados por token, y la contraseña del admin de desarrollo se cambia cambiando la variable de entorno (U-21). Tampoco hace falta nada por A-15 (en pausa: las columnas de `V15` se quedan sin usar) ni por A-20 (retirada: `fecha_limite` y `aviso_24h_enviado_en` existen y se quedan vacías).

## Lo que cambia fuera de la base de datos

| Dónde | Qué |
|---|---|
| **Contrato** | Bloque de roles (tres, varios por usuario), columna de roles de 4 rutas (`assign`, `sign-off`, `audit`), payloads de `/admin/users` (`rol` → `roles`), fuera `fecha_limite` (A-20) y los `403` de A-07. Las rutas de contraseña quedan como bloque de desarrollo y entran `GET /auth/sso/login` y `/auth/sso/callback` como propuesta |
| **Reglas U** | U-01 (varios roles), U-02 (releer de la base de datos), U-03 y U-09; U-19 gana «cambio de roles»; **U-10 a U-15 se retiran** y su contenido queda en U-21 |
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
- **@Marina decide el modelo**: `roles`, `estado`, `sso_subject` y la retirada de `tokens_usuario` cambian su diagrama aceptado. Esta propuesta no las aplica: las deja escritas para que ella las acepte o las corrija.
- **La columna no tiene catálogo**: si mañana los roles los define el cliente, hay que migrar a tabla. Es el precio de ahorrarse una tabla hoy.
- **Doble firma con tres roles**: si el equipo prefiere que cualquier revisor pueda firmar su propio cierre, A-15 pierde el sentido y hay que decirlo; no se cambia por la puerta de atrás.

## Qué falta

- Decidir entre **A (cero tablas, sin U-16 a U-20)** y **B (`sesiones_usuario`)**.
- Votos de @Marina, @Kevin y @Alex a este documento y a [[0009-identidad]].
- Que @Marina acepte el cambio de modelo (`roles`, `estado`, `sso_subject`, sin `tokens_usuario`) y escriba `V13`.
- Pedir al ICAT el registro de la aplicación OIDC.
