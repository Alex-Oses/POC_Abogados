# Aprobación — estados, asignación y cierre

**Estado:** propuesta con decisiones cerradas (16/11/2026).
**Contrato HTTP:** `docs/api/endpoints.md` (aquí solo se referencian rutas, no se redefinen).
**Modelo de datos:** `docs/architecture/` (migraciones Flyway).

## 1. Alcance

Desde que un documento termina el OCR hasta que se convierte en un PDF aprobado e inmutable. Quién revisa, qué se considera terminado, qué pasa si se rechaza y quién puede liberar el resultado.

## 2. Máquina de estados del documento

```text
pendiente → ocr_procesando → ocr_completado → anonimizando → en_revision

en_revision
  ├─ rechazado ──reopen──→ en_revision (numero_intento + 1)
  ├─ aprobado                                          (riesgo normal)
  └─ pendiente_visto_bueno ──visto bueno──→ aprobado   (categoría especial)

aprobado ──export──→ exportado
```

| Desde | Hasta | Quién | Regla |
| --- | --- | --- | --- |
| `pendiente` | `ocr_procesando` | sistema | A-01 |
| `ocr_procesando` | `ocr_completado` | sistema | A-02 |
| `ocr_procesando` | `pendiente` | sistema (fallo) | A-02 |
| `ocr_completado` | `anonimizando` | transcriptor, revisor | A-03 |
| `anonimizando` | `en_revision` | sistema | A-03 |
| `en_revision` | `pendiente_visto_bueno` | sistema, si `requiere_visto_bueno` | A-15 |
| `en_revision` | `aprobado` | revisor | A-09 |
| `pendiente_visto_bueno` | `aprobado` | supervisor | A-15 |
| `pendiente_visto_bueno` | `en_revision` | supervisor (con motivo) | A-15 |
| `en_revision` | `rechazado` | revisor | A-13 |
| `rechazado` | `en_revision` | revisor, supervisor | A-12 |
| `aprobado` | `exportado` | supervisor, transcriptor dueño | A-16 |

**Regla A-01 — el estado lo escribe el servidor.** El cliente nunca envía `estado`; solo dispara acciones. Un `PATCH` con `estado` en el cuerpo se rechaza.

**Regla A-02 — los estados transitorios vuelven atrás.** Si el OCR o la anonimización fallan, el documento regresa al estado anterior y el error queda en `auditoria`. Nunca se queda colgado en `ocr_procesando`.

**Regla A-03 — solo se anonimiza texto existente.** Sin versión `ocr_texto` no hay nada que anonimizar (`422`).

## 3. Estados de la revisión

`revisiones.estado` es independiente de `documentos.estado`: una revisión cerrada no cambia el documento por sí sola.

| Estado | Significa | Efecto en el documento |
| --- | --- | --- |
| `en_cola` | Creada, sin revisor asignado | `en_revision` |
| `en_proceso` | Tomada por un revisor | `en_revision` |
| `aprobado` | Decisión del revisor | `aprobado`, o `pendiente_visto_bueno` si A-15 |
| `rechazado_con_cambios` | Corregible | `rechazado`, crea versión `revisado_humano` |
| `devuelto` | Transitorio: no es revisable (falta texto, escaneo ilegible) | Se queda `en_revision` y la fila vuelve a `en_cola` |

**Regla A-04 — una sola revisión abierta por documento.** Se considera abierta si está en `en_cola` o `en_proceso`. Un nuevo intento devuelve `409`; `numero_intento` se incrementa al crear la siguiente.

## 4. Asignación

**Regla A-05 — cola con toma atómica (decidido).** `POST /documents/{id}/reviews` crea la revisión en `en_cola` y **sin** `asignado_a`. El revisor la toma con `POST /reviews/{id}/claim`, que rellena `asignado_a` y `asignado_en` y pasa la revisión a `en_proceso`.

La toma es un `UPDATE ... WHERE estado = 'en_cola'` de una sola sentencia. Si dos revisores pulsan a la vez, uno recibe `409` y su vista se recarga. Asignar leyendo primero y escribiendo después es como se acaba con dos dueños del mismo expediente.

*Por qué cola y no reparto automático:* con un equipo pequeño el reparto round-robin solo añade una pieza que mantener. Se migra cuando el volumen haga que la cola se atasque, y para entonces `asignado_a` ya existe.

**Regla A-06 — el supervisor puede saltarse la cola.** `PATCH /reviews/{id}/assign` fija `asignado_a` directamente sobre una revisión `en_cola` o reasigna una `en_proceso`. Para expedientes delicados. La reasignación queda en `auditoria` con el motivo.

**Regla A-07 — nadie revisa lo suyo.** Si `asignado_a` coincide con el `creado_por` del documento, la toma y la asignación se rechazan. Con rol único (U-01) casi no puede pasar; si algún día hay roles múltiples, esta es la regla que evita el conflicto de interés.

**Regla A-08 — la asignación es visible.** El revisor ve la cola completa y solo puede editar las revisiones que tiene en `en_proceso`. El supervisor ve quién tiene qué y desde cuándo.

## 5. Revisión por anotaciones

**Regla A-09 — no se aprueba con anotaciones pendientes (decidido).** Para cerrar en `aprobado`, toda anotación de la versión debe tener `decision_revisor` distinto de nulo. Si queda alguna, `422` con la lista de `anotacion_id` pendientes.

No hay casilla de «revisado el resto»: es exactamente la clase de atajo que convierte una revisión en un trámite. Si negocio la pide, se implementa como campo explícito `revisado_resto` del cierre y se firma en `auditoria`, nunca como un «aprobar igualmente».

**Regla A-10 — el revisor puede corregir, no reescribir.** Cambiar `accion_aplicada`, `texto_sustitucion` y la decisión sí. Cambiar el texto transcrito no: eso exige volver a procesar y crear versión nueva.

**Regla A-11 — cada decisión queda firmada.** `revisado_por` y `revisado_en` son obligatorios; el revisor no puede modificarlos a mano. Solo se modifica una anotación mientras la revisión está `en_proceso`: cerrada la revisión, el `PATCH` devuelve `409`.

## 6. Rechazo y reentrada

**Regla A-12 — el rechazo no es el final.** `rechazado_con_cambios` crea la versión `revisado_humano` y deja el documento en `rechazado`. Desde ahí, `POST /documents/{id}/reopen` genera una nueva versión `anonimizado_ia` aplicando la regla vigente, crea una revisión nueva en `en_cola` con `numero_intento + 1` y devuelve el documento a `en_revision`.

Sin esa reentrada, un documento rechazado se queda muerto: era el hueco más grande del diseño anterior.

**Regla A-13 — el motivo es obligatorio al rechazar.** `comentario_general` no puede ir vacío en `rechazado_con_cambios` ni en `devuelto`.

**Regla A-14 — `devuelto` no mata el documento.** Un documento ilegible no es un rechazo: vuelve a `en_cola` para que otro revisor lo mire. `devuelto` es transitorio: se escribe con su motivo y la fila vuelve a `en_cola` en la misma transacción, así que el estado persistido que se ve es `en_cola`. Tras dos devoluciones para la misma versión, el supervisor recibe el aviso y decide si se reescanea.

## 7. Visto bueno y exportación

**Regla A-15 — doble firma solo en categorías especiales (decidido).** Al cerrar la revisión, el servidor calcula `requiere_visto_bueno` y lo persiste: es cierto si la versión lleva alguna anotación cuya categoría tenga `rgpd_especial = true`, es decir, datos del art. 9-10 RGPD (salud, menores, violencia, discapacidad, condenas, origen racial, religión, sindicato, orientación sexual, biométricos y genéticos). El admin controla el conjunto marcando o desmarcando `rgpd_especial` en `categorias_sensibles`: el alta o baja de una categoría no exige desplegar.

`nivel_riesgo` **no** decide esto. Gradúa cuánto esfuerzo de detección y revisión pide una categoría, y casi todos los identificadores directos (DNI, nombre, dirección, IBAN) están en `alto`: usarlo aquí mandaba a doble firma cualquier expediente y vaciaba la regla.

Si negocio quiere un conjunto propio, independiente del art. 9, se añade `categorias_sensibles.requiere_doble_firma` y esta regla pasa a leer esa columna. No se construye hasta que se pida; queda anotado en [vault/Proyecto/Coherencia.md](../../vault/Proyecto/Coherencia.md).

Se guarda el valor calculado, no se recalcula después: la regla que se aplicó en ese momento es la que debe poder auditarse.

- `requiere_visto_bueno = false` → el documento pasa directo a `aprobado`.
- `requiere_visto_bueno = true` → pasa a `pendiente_visto_bueno`. El supervisor lo libera con `POST /documents/{id}/visto-bueno`, que rellena `visto_bueno_por` y `visto_bueno_en` y deja el documento en `aprobado`.

El visto bueno no es una segunda revisión: el supervisor no re-anota, solo firma o devuelve a `en_revision` con motivo.

**Regla A-16 — exportar es una acción explícita.** `POST /documents/{id}/export` genera el PDF definitivo, calcula su hash y pasa el documento a `exportado`. No se exporta al vuelo desde el visor: un PDF descargado sin dejar rastro no es un expediente. `POST /transform/build` sigue siendo la vista previa con formato, no el cierre del expediente.

**Regla A-17 — solo se exporta lo aprobado.** `409` en cualquier otro estado, incluido `pendiente_visto_bueno`.

**Regla A-18 — lo exportado es inmutable.** Se guarda `hash_export` y `exportado_en`; si el documento se reabre, el hash anterior se conserva. Sobrescribir el PDF de un expediente cerrado es exactamente lo que una auditoría no perdona.

**Regla A-19 — aprobar congela.** Tras `aprobado` no se crean versiones nuevas salvo reapertura explícita del supervisor, que rellena `cerrado_en` al reabrir. Queda en `auditoria` quién reabrió y por qué.

Cómo se compone el PDF (estructura guardada, reconstrucción sin píxeles del original y determinismo del hash): [docs/export/pdf.md](../export/pdf.md).

## 8. Plazos

**Regla A-20 — 48 h laborables con aviso a las 24 h (decidido).** Al crear la revisión se calcula `revisiones.fecha_limite` sumando `revision_plazo_horas` (48) horas laborables. Al cruzar `revision_aviso_horas` (24) sin decisión se rellena `aviso_24h_enviado_en` y se notifica al revisor asignado y, si la revisión sigue `en_cola`, al supervisor.

Qué es laborable sale de `configuracion_sistema.calendario_laboral`: lunes a viernes, 09:00-18:00, más la lista de `festivos` en formato ISO. Con la lista vacía no se descuenta ningún festivo, y el plazo saldrá largo en Semana Santa o Navidad; es el primer valor que hay que cargar al desplegar.

A las 48 h vencidas no cambia nada por sí solo: el supervisor recibe el aviso y reasigna con A-06.

**Regla A-21 — la sesión de OCR caduca.** `documentos.expira_en` (propuesta: 24 h). Pasado el plazo, los endpoints de texto y PDF devuelven `404` y hay que volver a subir.

**Regla A-22 — los plazos no cambian el estado solos.** Un documento vencido sigue `en_revision`; el vencimiento genera aviso, no una transición automática silenciosa.

## 9. Concurrencia

**Regla A-23 — cierre optimista.** `PATCH /reviews/{id}` exige `If-Match` con el `updated_at` de la revisión. Si otro revisor la cerró primero, `409` y se recarga. Sin esto, dos cierres simultáneos crean dos versiones `final_aprobado`.

La toma de la cola (A-05) no depende de `If-Match`: la resuelve el `WHERE estado = 'en_cola'` de la propia sentencia.

## 10. Lo que falta en el esquema

| Necesidad | Columna o tabla | Regla |
| --- | --- | --- |
| Revisor asignado | `revisiones.asignado_a` (FK `usuarios`, nulo en `en_cola`) | A-05 |
| Cuándo se tomó | `revisiones.asignado_en` | A-05 |
| Plazo | `revisiones.fecha_limite` | A-20 |
| Aviso de 24 h ya enviado | `revisiones.aviso_24h_enviado_en` | A-20 |
| Doble firma aplicable | `documentos.requiere_visto_bueno` (booleano persistido) | A-15 |
| Firmante del visto bueno | `documentos.visto_bueno_por`, `documentos.visto_bueno_en` | A-15 |
| Estado nuevo | `documentos.estado` gana `pendiente_visto_bueno` | A-15 |
| Cierre del expediente | `documentos.cerrado_en` | A-19 |
| Hash del PDF exportado | `documentos.hash_export` | A-18 |
| Fecha de exportación | `documentos.exportado_en` | A-18 |

`revisiones.estado` gana `en_cola` (A-04, A-05).

## 11. Endpoints

Todos están ya en `docs/api/endpoints.md`, que es el dueño de los payloads. Aquí solo queda la referencia.

```text
GET    /reviews?estado=en_cola      cola de trabajo
POST   /reviews/{id}/claim          tomar de la cola (atómico)
PATCH  /reviews/{id}/assign         asignar o reasignar (supervisor)
POST   /documents/{id}/reviews      abrir revisión (nace en_cola)
PATCH  /reviews/{id}                cerrar revisión (If-Match)
POST   /documents/{id}/reopen       rechazado → en_revision, nueva versión
POST   /documents/{id}/visto-bueno  pendiente_visto_bueno → aprobado (supervisor)
POST   /documents/{id}/export       aprobado → exportado, con hash
```

**Decisiones cerradas:** A-05 (cola), A-09 (no aprobar con pendientes), A-15 (doble firma solo en categorías especiales, art. 9-10), A-20 (48 h + aviso 24 h). Las columnas que estas reglas necesitan y que todavía no están en `docs/architecture/` se listan en la sección 10; bajarlas al modelo está pendiente de decisión.

**Único pendiente de negocio:** plazo legal de conservación tras la baja (U-08). No bloquea la construcción: mientras no haya plazo, `eliminado_en` se guarda y no se purga nada.
