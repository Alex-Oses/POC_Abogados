# 0012 · Identidad y roles: SSO, tres roles y roles múltiples

- **Estado**: Propuesta
- **Fecha**: 2026-11-18
- **Autor**: @ia-opencode-ruben (a petición de @Rubén)
- **Se decide con**: @Rubén (backend), @Marina (BD, decide el modelo), @Kevin (despliegue), @Alex (frontend/OCR)
- **Votos**: @Rubén (backend), 2026-11-18: **SSO sin gestión de cuentas, tres roles y roles múltiples**. Faltan @Marina, @Kevin y @Alex.

## Contexto

Tres piezas estaban decididas por separado y no encajan entre sí:

- [[0009-identidad]] propone SSO **más un admin local de emergencia**, y el contrato implementa contraseñas con invitación.
- [[0005-reglas-usuarios-y-aprobacion]] fija **un rol por usuario** (`usuarios.rol`) y cuatro roles, con `supervisor` para asignar, dar el visto bueno y reabrir.
- [[0011-ajustes-al-modelo-de-marina]] acaba de aceptar `V14` y `V15`; `V13` (identidad) sigue sin escribir porque espera a 0009. [[0010-modelo-de-datos]] cierra con `usuarios.rol` de un solo valor.

@Rubén cambia el criterio el 18/11: **el producto no gestiona cuentas**. Entra quien el ICAT diga, y el software solo guarda qué puede hacer cada persona. Eso deja `V13` como el único sitio donde el cambio sale gratis: la migración no existe todavía.

## Decisión

1. **SSO del ICAT como única entrada.** No hay invitación, ni alta manual, ni contraseñas de usuario, ni proveedor de correo. El proveedor valida y devuelve `sub`; el backend busca o crea la ficha y abre sesión.
2. **Un único login local: el admin de desarrollo.** Sembrado por migración o variable de entorno, con contraseña fuerte, **no se despliega en producción**. Sirve para pruebas y para arrancar el sistema sin depender del ICAT.
3. **Tres roles**: `transcriptor`, `revisor`, `admin`. **El supervisor desaparece** y sus funciones pasan al revisor: asignar y reasignar (A-06), liberar o devolver el visto bueno (A-15), reabrir un aprobado (A-19), recibir avisos de plazo (A-20) y consultar la auditoría.
4. **Varios roles por usuario** en `usuarios_roles (usuario_id, rol)`: el permiso es la **unión** de los roles. `usuarios.rol` desaparece.
5. **La doble firma sigue siendo doble**: el visto bueno lo libera un revisor **distinto** de quien cerró la revisión y de quien subió el documento (A-15 + A-07). Si no, con tres roles la firma sería un clic del mismo revisor.
6. **La primera entrada crea la ficha sin roles.** Un usuario sin roles no ve documentos; un admin le asigna los suyos. No hay alta previa ni invitación que esperar.

## Lo que cambia en la base de datos

Sobre lo aceptado en 0011. **Todo lo estructural cabe en `V13`**, que todavía no está escrita; lo demás son textos y un trigger.

| Dónde | Qué cambia | Coste |
|---|---|---|
| `V1__create_usuarios.sql` | La columna `usuarios.rol` y su `CHECK` con cuatro valores se retiran en `V13`, no en `V1` (V1-V12 no se tocan) | nulo: una migración que aún no existe |
| `V13` (sin escribir) | Entra `usuarios_roles (usuario_id UUID, rol VARCHAR(20), PRIMARY KEY (usuario_id, rol))` con `CHECK (rol IN ('transcriptor','revisor','admin'))`; entra `usuarios.sso_subject` único; `usuarios.password_hash` queda opcional y solo lo usa el admin de desarrollo; **`tokens_usuario` no se usa en producción** (no hay invitación ni reset; si se mantiene el alta local para pruebas, la tabla existe solo para esas cuentas); se mantiene `sesiones_usuario` | ~1 hora de SQL, dentro de la migración que ya estaba pendiente |
| `V15__flujo_revision_y_export.sql` | **Ningún cambio estructural.** `visto_bueno_por` ya es un FK a `usuarios` y no comprueba rol. Solo dos comentarios y la descripción de `revision_aviso_horas` dicen «supervisor» → «revisor» | 3 líneas de texto |
| `triggers.sql` (validación de revisor) | `(SELECT rol FROM usuarios ...)` deja de existir. Pasa a `EXISTS (SELECT 1 FROM usuarios_roles WHERE usuario_id = NEW.asignado_a AND rol = 'revisor')` | ~5 líneas; lo firma @Marina |
| `views.sql` (`v_metricas_revisor`) | Filtra por `u.rol = 'revisor' AND u.activo`, dos columnas que `V13` retira o sustituye. Pasa a `JOIN usuarios_roles` y `u.estado = 'activo'` | ~3 líneas; lo firma @Marina |
| `data-dictionary.md` | La fila `rol` de `usuarios` sale; entra `usuarios_roles` y `sso_subject` | texto |
| Seeds | No hay ningún `INSERT INTO usuarios` en las migraciones: el admin inicial ya se creaba fuera. No hay datos que migrar | nulo |

**Lo que no hay que tocar:** `revisiones.asignado_a`, `documentos.visto_bueno_por`, `documentos.visto_bueno_en` y `auditoria` no dependen del rol. El cambio de rol no reescribe filas históricas: quien firmó queda firmado.

## Lo que cambia fuera de la base de datos

| Dónde | Qué |
|---|---|
| **Contrato** | Bloque de roles (tres, varios por usuario), columna de roles de 4 rutas (`assign`, `sign-off`, `audit`), payloads de `/admin/users` (`rol` → `roles`) y los textos que dicen «supervisor». Las siete rutas de contraseña e invitación quedan como camino del admin de desarrollo, no del usuario real |
| **Reglas U** | U-01 (rol único), U-02 (releer de `usuarios`), U-03 y U-09; U-19 gana «cambio de roles» |
| **Reglas A** | A-06, A-07, A-08, A-14, A-15, A-19 y A-20: de supervisor a revisor, con la firma de otro revisor |
| [[0005-reglas-usuarios-y-aprobacion]] | Reglas 1, 2, 4 y 6 |
| [[0009-identidad]] | La opción 3 pasa de «admin de emergencia» a «admin de desarrollo»; `tokens_usuario` sale del todo |
| [[Enfoque tecnico]] | §5 y §11: SSO, tres roles, varios roles y su efecto en el modelo |

## Por qué así

- **SSO y no cuentas locales**: mantener contraseñas, política, bloqueos y SMTP es trabajo que no da valor y multiplica los sitios donde se filtra una credencial. El ICAT ya tiene la identidad.
- **Tres roles y no cuatro**: `supervisor` era una persona, no un permiso. Con roles múltiples, quien supervisa es un revisor con el mismo permiso; lo que no puede es firmar dos veces el mismo expediente.
- **N:M y no un rol único**: en un despacho de dos o tres personas la misma persona sube, revisa y administra. El rol único obligaba a cuentas duplicadas o a renunciar a la separación de funciones.

## Coste y riesgos

- **Riesgo asumido (SSO)**: si el tenant del ICAT cae o retira el permiso, **nadie entra**, ni a consultar lo aprobado. El admin local no se despliega en producción a propósito: es una puerta de desarrollo, no una de emergencia. Si negocio quiere emergencia real, es la opción 3 original y hay que decirlo.
- **Dependencia externa**: el registro OIDC del ICAT son 1-2 semanas de terceros y solo lo puede pedir una persona.
- **@Marina decide el modelo**: `usuarios_roles`, `sso_subject` y la retirada de `tokens_usuario` cambian su diagrama aceptado. Esta propuesta no las aplica: las deja escritas para que ella las acepte o las corrija.
- **Doble firma con tres roles**: si el equipo prefiere que cualquier revisor pueda firmar su propio cierre, A-15 pierde el sentido y hay que decirlo; no se cambia por la puerta de atrás.

## Qué falta

- Votos de @Marina, @Kevin y @Alex a este documento y a [[0009-identidad]].
- Que @Marina acepte el cambio de modelo y escriba `V13` con `usuarios_roles` y sin `tokens_usuario`.
- Pedir al ICAT el registro de la aplicación OIDC.
