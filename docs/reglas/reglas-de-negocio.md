# Reglas de negocio

- **Estado**: borrador de trabajo · 18/11/2026
- **Para qué**: una sola lista con las **36 reglas vigentes** del proyecto (14 de usuarios, 22 de aprobación), para leerlas seguidas y **editar a mano lo que no convenza**. Hay 9 retiradas, al final.
- **De dónde salen**: `usuarios.md` y `aprobacion.md`, en esta misma carpeta. Allí está el detalle y su contexto; aquí, la regla en una frase.
- **Cómo se mantiene**: si cambias una regla aquí, se traslada al fichero de origen y al contrato en el mismo PR. Este fichero no puede quedarse por delante de los otros dos.
- **No incluye**: payloads ni códigos HTTP (`docs/api/endpoints.md`), la composición del PDF (`docs/export/pdf.md`) ni el esquema (`V14`/`V15`).
- **Lo marcado `(propuesta)` o `(en pausa)`** todavía no está aceptado; lo demás son decisiones cerradas en su fichero.

## Índice

### Usuarios

| ID | Regla | Estado |
|---|---|---|
| U-01 | Varios roles por usuario | propuesta (0012) |
| U-02 | El permiso se comprueba en el servidor | cerrada |
| U-03 | Propiedad del recurso (solo transcriptor puro) | cerrada |
| U-04 | El estado de la cuenta es explícito | cerrada |
| U-05 | Alta por SSO | propuesta (0009/0012) |
| U-06 | El primer admin se siembra | cerrada |
| U-08 | La baja no borra | cerrada |
| U-09 | Cambio de roles con efecto inmediato | cerrada |
| U-16 | Token opaco, no JWT | cerrada |
| U-17 | Máximo 3 sesiones | cerrada |
| U-18 | Caducidad de sesión | cerrada |
| U-19 | Cuándo se revoca una sesión | cerrada |
| U-20 | Logout es revocación, no borrado | cerrada |
| U-21 | La credencial del admin de desarrollo no vive en el repo | cerrada |

### Aprobación

| ID | Regla | Estado |
|---|---|---|
| A-01 | El estado lo escribe el servidor | cerrada |
| A-02 | Los estados transitorios vuelven atrás | cerrada |
| A-03 | Solo se anonimiza texto existente | cerrada |
| A-04 | Una sola revisión abierta por documento | cerrada |
| A-05 | Cola con toma atómica | cerrada |
| A-06 | El revisor elige de la cola | propuesta |
| A-08 | La asignación es visible | cerrada |
| A-09 | No se aprueba con anotaciones pendientes | cerrada |
| A-10 | El revisor corrige, no reescribe | cerrada |
| A-11 | Cada decisión queda firmada | cerrada |
| A-12 | El rechazo no es el final | cerrada |
| A-13 | Motivo obligatorio al rechazar | cerrada |
| A-14 | `devuelto` no mata el documento | cerrada |
| A-15 | Doble firma solo en categorías especiales | en pausa |
| A-16 | Exportar es una acción explícita | cerrada |
| A-17 | Solo se exporta lo aprobado | cerrada |
| A-18 | Lo exportado es inmutable | cerrada |
| A-19 | Aprobar congela | cerrada |
| A-21 | El expediente no caduca | cerrada |
| A-22 | Los plazos no cambian el estado solos | sin efecto |
| A-23 | Cierre optimista | cerrada |
| A-24 | Doble transcripción y comparación | cerrada |

---

## Usuarios

**U-01 · Varios roles por usuario** *(propuesta, 0012)*
Los roles viven en `usuarios_roles (usuario_id, rol)` (N:M) y el permiso es la **unión**. Hay tres roles: `transcriptor`, `revisor` y `admin`. El `supervisor` se elimina y sus funciones pasan al revisor.

**U-02 · El permiso se comprueba en el servidor, siempre.**
Los roles se releen de `usuarios_roles` en cada petición; el token no arrastra los roles con los que se emitió.

**U-03 · Propiedad del recurso (solo transcriptor puro).**
Quien tiene **únicamente** el rol de transcriptor solo ve y opera sobre documentos con `creado_por = usuario_id`. En cuanto tiene también el rol de revisor, ve y revisa todos los documentos, aunque haya subido alguno. El admin no ve contenido de documentos, solo metadatos.

**U-04 · El estado de la cuenta es explícito.**
`usuarios.estado` sustituye al booleano `activo`: `activo`, `bloqueado` o `baja`. Con un booleano no se distingue «invitado» de «bloqueado» y la auditoría no puede explicar por qué alguien no entra.

**U-05 · Alta por SSO** *(propuesta, 0009/0012)*
No hay autoregistro, ni invitación, ni contraseñas de usuario. El primer acceso con SSO crea la ficha en `activo` y **sin roles**; un admin le asigna los suyos y hasta entonces no ve documentos.

**U-06 · El primer admin se siembra.**
El admin de desarrollo se crea por migración o variable de entorno, nunca por endpoint público. Sin esta regla el sistema no arranca. No se despliega en producción.

**U-08 · La baja no borra.**
Se marca `estado = baja` y `eliminado_en`. Las anotaciones, revisiones y auditoría siguen apuntando al usuario; un `DELETE` real rompería la trazabilidad.

**U-09 · Cambio de roles con efecto inmediato.**
Al cambiar los roles de un usuario se revocan todas sus sesiones abiertas.

*U-10 a U-15, retiradas el 18/11.* El admin de desarrollo deja de tener reglamento propio; su credencial queda en U-21. Los números no se reutilizan.

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

**U-21 · La credencial del admin de desarrollo no vive en el repo.**
Se siembra por variable de entorno, no se versiona y **no se despliega en producción**. El admin local funciona igual que antes (login y cambio de contraseña); lo que desaparece es el reglamento sobre cómo se gestiona su contraseña.

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

**A-06 · El revisor elige de la cola.** *(propuesta)*
El revisor toma de la cola el documento que quiere (`claim`); no se asigna de oficio a una persona. La asignación directa queda como excepción para un encargo concreto, no como norma. Si se confirma que sobra, `PATCH /reviews/{id}/assign` desaparece del contrato.

**A-08 · La asignación es visible.**
El revisor ve la cola completa, solo edita lo que tiene en `en_proceso`, y ve quién tiene qué y desde cuándo.

**A-09 · No se aprueba con anotaciones pendientes.** *(cerrada)*
Toda anotación de la versión debe tener `decision_revisor`. Si queda alguna, `422` con la lista de `anotacion_id`. No hay casilla de «revisado el resto».

**A-10 · El revisor corrige, no reescribe.**
Puede cambiar `accion_aplicada`, `texto_sustitucion` y la decisión. Cambiar el texto transcrito exige volver a procesar y crear versión nueva.

**A-11 · Cada decisión queda firmada.**
`revisado_por` y `revisado_en` son obligatorios y no se editan a mano. Solo se modifica una anotación mientras la revisión está `en_proceso`; cerrada, el `PATCH` da `409`.

**A-12 · El rechazo no es el final.**
`rechazado_con_cambios` crea la versión `revisado_humano` y deja el documento en `rechazado`. `POST /documents/{id}/reopen` genera una versión `anonimizado_ia` nueva, una revisión en `en_cola` con `numero_intento + 1` y devuelve el documento a `en_revision`. También acepta un `aprobado`, con `comentario` (A-19).

**A-13 · Motivo obligatorio al rechazar.**
`comentario_general` no puede ir vacío en `rechazado_con_cambios` ni en `devuelto`.

**A-14 · `devuelto` no mata el documento.**
Un documento ilegible no es un rechazo: vuelve a `en_cola` en la misma transacción, con su motivo. Tras dos devoluciones de la misma versión, los revisores reciben el aviso y deciden si se reescanea.

**A-15 · Doble firma solo en categorías especiales.** *(en pausa)*
En pausa por decisión de @Rubén (18/11): exige identificar los datos del art. 9-10 y montar una segunda firma, y ahora mismo complica más de lo que aporta. Mientras siga en pausa, `requiere_visto_bueno` se queda siempre en `false` y ningún documento entra en `pendiente_visto_bueno`.

Si se retoma: al cerrar la revisión, el servidor calcula y guarda `requiere_visto_bueno` (cierto si hay alguna anotación de una categoría con `rgpd_especial = true`; `nivel_riesgo` no interviene). El documento pasa a `pendiente_visto_bueno` y lo libera con `POST /documents/{id}/sign-off` **un revisor distinto del que cerró**, que rellena `visto_bueno_por` y `visto_bueno_en`. No re-anota: firma o devuelve a `en_revision` con motivo.

**A-16 · Exportar es una acción explícita.**
`POST /documents/{id}/export` genera el PDF definitivo, calcula su hash y pasa el documento a `exportado`. `POST /transform/build` es solo vista previa y no cierra el expediente.

**A-17 · Solo se exporta lo aprobado.**
`409` en cualquier otro estado, incluido `pendiente_visto_bueno`.

**A-18 · Lo exportado es inmutable.**
El hash SHA-256 va en la versión exportada (`versiones_documento.metadatos_proceso->>'hash_export'`) y la fecha en `documentos.exportado_en`. Si el documento se reabre, la versión anterior conserva su hash y el PDF nuevo nace en otra versión. Sobrescribir el PDF de un expediente cerrado es lo que una auditoría no perdona.

**A-19 · Aprobar congela.**
Tras `aprobado` no se crean versiones nuevas salvo reapertura explícita de un revisor, que exige `comentario` y devuelve el documento a `en_revision` con una revisión nueva. `cerrado_en` lo escribe el export. Queda en `auditoria` quién reabrió y por qué.

**A-21 · El expediente no caduca.**
No hay plazo sobre el documento. El TTL (24 h) es solo de los ficheros temporales del OCR; el original cifrado tampoco caduca mientras el expediente exista.

**A-22 · Los plazos no cambian el estado solos.** *(sin efecto)*
Sin A-20 no hay vencimiento ni aviso. Se conserva por si vuelve un plazo, pero hoy no se implementa nada.

**A-23 · Cierre optimista.**
`PATCH /reviews/{id}` exige `If-Match` con el `actualizado_en` de la revisión. Si otro la cerró primero, `409` y se recarga. La toma de la cola (A-05) no usa `If-Match`: la resuelve el `WHERE estado = 'en_cola'`.

**A-24 · Doble transcripción y comparación.** *(decidida, 19/11)*
Cada documento se transcribe dos veces; se muestran al revisor una de las dos lecturas y **se marcan como aviso las diferencias** con la otra, para que solo se revisen los puntos donde no coinciden.

No hace falta esquema nuevo: la segunda lectura y su diff van en `versiones_documento.metadatos_proceso` (`segunda_lectura`, `diferencias`) y los avisos se pintan desde `paginas_documento.avisos` con `tipo = "doble_lectura"`.

Coste: duplica el OCR (~1.375 pág/h en vez de ~2.750 con la RTX 3050).

---

## Reglas retiradas (18/11/2026)

Se conservan los números para no reutilizarlos; no se renumeran las demás.

| ID | Qué era | Por qué se retira |
|---|---|---|
| U-07 | Validez de 72 h de la invitación | Con SSO no hay invitación. @Rubén la elimina |
| U-10 | El servidor hashea, el cliente nunca | El admin de desarrollo deja de tener reglamento propio. Queda U-21 |
| U-11 | Política de contraseña mínima | Ídem: una sola regla para el admin local |
| U-12 | Recuperación con enlace de un solo uso | Ídem: la ruta sigue existiendo, sin regla que la gobierne |
| U-13 | Cambio de contraseña revoca sesiones | Ídem |
| U-14 | Bloqueo progresivo | Ídem |
| U-15 | Login indistinguible | Ídem |
| A-07 | Nadie revisa lo suyo | @Rubén la elimina. Consecuencia dicha: un revisor puede cerrar un documento que subió él |
| A-20 | 48 h laborables con aviso a las 24 h | @Rubén la elimina: el piloto no lleva plazos |

---

## Cambios pedidos

Para anotar lo que no convence, sin tocar las reglas de arriba. Formato: `- [ ] ID — qué cambiar y por qué`.

- [ ] _(pendiente)_ )
