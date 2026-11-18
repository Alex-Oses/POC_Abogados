# Reglas de negocio

- **Estado**: borrador de trabajo · 18/11/2026
- **Para qué**: una sola lista con las **43 reglas numeradas** del proyecto (20 de usuarios, 23 de aprobación), para leerlas seguidas y **editar a mano lo que no convenza**.
- **De dónde salen**: `usuarios.md` y `aprobacion.md`, en esta misma carpeta. Allí está el detalle y su contexto; aquí, la regla en una frase.
- **Cómo se mantiene**: si cambias una regla aquí, se traslada al fichero de origen y al contrato en el mismo PR. Este fichero no puede quedarse por delante de los otros dos.
- **No incluye**: payloads ni códigos HTTP (`docs/api/endpoints.md`), la composición del PDF (`docs/export/pdf.md`) ni el esquema (`V14`/`V15`).
- **Lo marcado `(propuesta)`** todavía no está aceptado; lo demás son decisiones cerradas en su fichero.

## Índice

### Usuarios

| ID | Regla | Estado |
|---|---|---|
| U-01 | Varios roles por usuario | propuesta (0012) |
| U-02 | El permiso se comprueba en el servidor | cerrada |
| U-03 | Propiedad del recurso | cerrada |
| U-04 | El estado de la cuenta es explícito | cerrada |
| U-05 | Alta por SSO | propuesta (0009/0012) |
| U-06 | El primer admin se siembra | cerrada |
| U-07 | Sin invitación con SSO | propuesta |
| U-08 | La baja no borra | cerrada |
| U-09 | Cambio de roles con efecto inmediato | cerrada |
| U-10 | El servidor hashea, el cliente nunca | cerrada |
| U-11 | Política de contraseña mínima | cerrada |
| U-12 | Recuperación con enlace de un solo uso | cerrada |
| U-13 | Cambio de contraseña revoca sesiones | cerrada |
| U-14 | Bloqueo progresivo | cerrada |
| U-15 | Login indistinguible | cerrada |
| U-16 | Token opaco, no JWT | cerrada |
| U-17 | Máximo 3 sesiones | cerrada |
| U-18 | Caducidad de sesión | cerrada |
| U-19 | Cuándo se revoca una sesión | cerrada |
| U-20 | Logout es revocación, no borrado | cerrada |

### Aprobación

| ID | Regla | Estado |
|---|---|---|
| A-01 | El estado lo escribe el servidor | cerrada |
| A-02 | Los estados transitorios vuelven atrás | cerrada |
| A-03 | Solo se anonimiza texto existente | cerrada |
| A-04 | Una sola revisión abierta por documento | cerrada |
| A-05 | Cola con toma atómica | cerrada |
| A-06 | Un revisor puede saltarse la cola | cerrada |
| A-07 | Nadie revisa lo suyo | cerrada |
| A-08 | La asignación es visible | cerrada |
| A-09 | No se aprueba con anotaciones pendientes | cerrada |
| A-10 | El revisor corrige, no reescribe | cerrada |
| A-11 | Cada decisión queda firmada | cerrada |
| A-12 | El rechazo no es el final | cerrada |
| A-13 | Motivo obligatorio al rechazar | cerrada |
| A-14 | `devuelto` no mata el documento | cerrada |
| A-15 | Doble firma solo en categorías especiales | cerrada |
| A-16 | Exportar es una acción explícita | cerrada |
| A-17 | Solo se exporta lo aprobado | cerrada |
| A-18 | Lo exportado es inmutable | cerrada |
| A-19 | Aprobar congela | cerrada |
| A-20 | 48 h laborables con aviso a las 24 h | cerrada |
| A-21 | El expediente no caduca | cerrada |
| A-22 | Los plazos no cambian el estado solos | cerrada |
| A-23 | Cierre optimista | cerrada |

---

## Usuarios

**U-01 · Varios roles por usuario** *(propuesta, 0012)*
Los roles viven en `usuarios_roles (usuario_id, rol)` (N:M) y el permiso es la **unión**. Hay tres roles: `transcriptor`, `revisor` y `admin`. El `supervisor` se elimina y sus funciones pasan al revisor.

**U-02 · El permiso se comprueba en el servidor, siempre.**
Los roles se releen de `usuarios_roles` en cada petición; el token no arrastra los roles con los que se emitió.

**U-03 · Propiedad del recurso.**
El transcriptor solo ve y opera sobre documentos con `creado_por = usuario_id`. El revisor ve todos. El admin no ve contenido de documentos, solo metadatos.

**U-04 · El estado de la cuenta es explícito.**
`usuarios.estado` sustituye al booleano `activo`: `activo`, `bloqueado` o `baja`. Con un booleano no se distingue «invitado» de «bloqueado» y la auditoría no puede explicar por qué alguien no entra.

**U-05 · Alta por SSO** *(propuesta, 0009/0012)*
No hay autoregistro, ni invitación, ni contraseñas de usuario. El primer acceso con SSO crea la ficha en `activo` y **sin roles**; un admin le asigna los suyos y hasta entonces no ve documentos.

**U-06 · El primer admin se siembra.**
El admin de desarrollo se crea por migración o variable de entorno, nunca por endpoint público. Sin esta regla el sistema no arranca. No se despliega en producción.

**U-07 · Sin invitación con SSO.** *(propuesta)*
Con SSO no hay token de invitación. Si el piloto vuelve a cuentas locales, se recupera la validez de 72 h.

**U-08 · La baja no borra.**
Se marca `estado = baja` y `eliminado_en`. Las anotaciones, revisiones y auditoría siguen apuntando al usuario; un `DELETE` real rompería la trazabilidad.

**U-09 · Cambio de roles con efecto inmediato.**
Al cambiar los roles de un usuario se revocan todas sus sesiones abiertas.

**U-10 · El servidor hashea, el cliente nunca.** *(solo admin de desarrollo)*
Argon2id con sal por usuario. La contraseña viaja en claro dentro de TLS y no se registra en logs.

**U-11 · Política mínima de contraseña.** *(solo admin de desarrollo)*
12 caracteres, sin exigir mayúsculas ni símbolos: la composición artificial produce contraseñas peores.

**U-12 · Recuperación con enlace de un solo uso.** *(solo admin de desarrollo)*
Token de 32 bytes guardado hasheado, caducidad 30 minutos, un uso. Al consumirse se revocan todas las sesiones.

**U-13 · Cambio de contraseña revoca sesiones.** *(solo admin de desarrollo)*
Incluido el cambio hecho por el propio usuario.

**U-14 · Bloqueo progresivo.** *(solo admin de desarrollo)*
5 intentos fallidos en 15 minutos → `429`. 10 acumulados → `estado = bloqueado` y aviso al admin. El contador se reinicia con un login correcto.

**U-15 · Login indistinguible.** *(solo admin de desarrollo)*
Mismo mensaje y mismo tiempo de respuesta para «email inexistente» y «contraseña incorrecta».

**U-16 · Token opaco, no JWT.**
`sesiones_usuario` guarda `token_hash`, `expira_en` y `revocado_en`: la revocación es inmediata, sin lista negra.

**U-17 · Máximo 3 sesiones simultáneas.** *(cerrada)*
Al crear la cuarta se revoca la más antigua por `creado_en`.

**U-18 · Caducidad de sesión.**
Acceso 1 hora, renovación mientras haya actividad y la cuenta siga `activo`. Máximo absoluto 12 horas por sesión.

**U-19 · Cuándo se revoca una sesión.**
Al cambiar contraseña, cambiar los roles, bloquear o dar de baja, superar el límite de sesiones y cuando el admin fuerza el cierre. Toda revocación va a `auditoria`.

**U-20 · Logout es revocación, no borrado.**
Se escribe `revocado_en`, nunca `DELETE`: la sesión forma parte de la auditoría.

---

## Aprobación

**A-01 · El estado lo escribe el servidor.**
El cliente nunca envía `estado`; solo dispara acciones. Un `PATCH` con `estado` en el cuerpo se rechaza.

**A-02 · Los estados transitorios vuelven atrás.**
Si el OCR o la anonimización fallan, el documento regresa al estado anterior y el error queda en `auditoria`. Nunca se queda colgado en `ocr_procesando`.

**A-03 · Solo se anonimiza texto existente.**
Sin versión `ocr_texto` no hay nada que anonimizar (`422`).

**A-04 · Una sola revisión abierta por documento.**
Se considera abierta si está en `en_cola` o `en_proceso`. Un nuevo intento devuelve `409`; `numero_intento` se incrementa al crear la siguiente.

**A-05 · Cola con toma atómica.** *(cerrada)*
La revisión nace `en_cola` y sin `asignado_a`. El revisor la toma con `POST /reviews/{id}/claim`, que rellena `asignado_a` y `asignado_en` en un solo `UPDATE ... WHERE estado = 'en_cola'`. Si dos pulsan a la vez, uno recibe `409`.

**A-06 · Un revisor puede saltarse la cola.**
`PATCH /reviews/{id}/assign` fija `asignado_a` sobre una revisión en cola o reasigna una en proceso. La reasignación queda en `auditoria` con el motivo.

**A-07 · Nadie revisa lo suyo.**
Si `asignado_a` coincide con el `creado_por` del documento, la toma y la asignación se rechazan.

**A-08 · La asignación es visible.**
El revisor ve la cola completa, solo edita lo que tiene en `en_proceso`, y ve quién tiene qué y desde cuándo.

**A-09 · No se aprueba con anotaciones pendientes.** *(cerrada)*
Toda anotación de la versión debe tener `decision_revisor`. Si queda alguna, `422` con la lista de `anotacion_id`. No hay casilla de «revisado el resto».

**A-10 · El revisor corrige, no reescribe.**
Puede cambiar `accion_aplicada`, `texto_sustitucion` y la decisión. Cambiar el texto transcrito exige volver a procesar y crear versión nueva.

**A-11 · Cada decisión queda firmada.**
`revisado_por` y `revisado_en` son obligatorios y no se editan a mano. Solo se modifica una anotación mientras la revisión está `en_proceso`; cerrada, el `PATCH` da `409`.

**A-12 · El rechazo no es el final.**
`rechazado_con_cambios` crea la versión `revisado_humano` y deja el documento en `rechazado`. `POST /documents/{id}/reopen` genera una versión `anonimizado_ia` nueva, una revisión en `en_cola` con `numero_intento + 1` y devuelve el documento a `en_revision`.

**A-13 · Motivo obligatorio al rechazar.**
`comentario_general` no puede ir vacío en `rechazado_con_cambios` ni en `devuelto`.

**A-14 · `devuelto` no mata el documento.**
Un documento ilegible no es un rechazo: vuelve a `en_cola` en la misma transacción, con su motivo. Tras dos devoluciones de la misma versión, los revisores reciben el aviso y deciden si se reescanea.

**A-15 · Doble firma solo en categorías especiales.** *(cerrada)*
Al cerrar la revisión, el servidor calcula y guarda `requiere_visto_bueno`: cierto si la versión tiene alguna anotación de una categoría con `rgpd_especial = true` (art. 9-10 RGPD). `nivel_riesgo` no interviene.
Si es cierto, el documento pasa a `pendiente_visto_bueno` y lo libera con `POST /documents/{id}/sign-off` **un revisor distinto del que cerró la revisión**, que rellena `visto_bueno_por` y `visto_bueno_en`. No re-anota: firma o devuelve a `en_revision` con motivo.

**A-16 · Exportar es una acción explícita.**
`POST /documents/{id}/export` genera el PDF definitivo, calcula su hash y pasa el documento a `exportado`. `POST /transform/build` es solo vista previa y no cierra el expediente.

**A-17 · Solo se exporta lo aprobado.**
`409` en cualquier otro estado, incluido `pendiente_visto_bueno`.

**A-18 · Lo exportado es inmutable.**
Se guardan `hash_export` y `exportado_en`; si el documento se reabre, el hash anterior se conserva. Sobrescribir el PDF de un expediente cerrado es lo que una auditoría no perdona.

**A-19 · Aprobar congela.**
Tras `aprobado` no se crean versiones nuevas salvo reapertura explícita de un revisor, que rellena `cerrado_en`. Queda en `auditoria` quién reabrió y por qué.

**A-20 · 48 h laborables con aviso a las 24 h.** *(cerrada)*
Al crear la revisión se calcula `fecha_limite` sumando `revision_plazo_horas` (48) horas laborables. Al cruzar las 24 sin decisión se rellena `aviso_24h_enviado_en` y se notifica al revisor asignado y, si sigue en cola, a los revisores. Laborable = L-V 09:00-18:00 menos los festivos de `configuracion_sistema`.

**A-21 · El expediente no caduca.**
No hay plazo sobre el documento. El TTL (24 h) es solo de los ficheros temporales del OCR; el original cifrado tampoco caduca mientras el expediente exista.

**A-22 · Los plazos no cambian el estado solos.**
Un documento vencido sigue `en_revision`; el vencimiento genera aviso, no una transición silenciosa.

**A-23 · Cierre optimista.**
`PATCH /reviews/{id}` exige `If-Match` con el `updated_at` de la revisión. Si otro la cerró primero, `409` y se recarga. La toma de la cola (A-05) no usa `If-Match`: la resuelve el `WHERE estado = 'en_cola'`.

---

## Cambios pedidos

Para anotar lo que no convence, sin tocar las reglas de arriba. Formato: `- [ ] ID — qué cambiar y por qué`.

- [ ] _(pendiente)_
