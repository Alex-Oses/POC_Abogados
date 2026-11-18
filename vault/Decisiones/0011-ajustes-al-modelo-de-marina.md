# 0011 · Ajustes al modelo de @Marina: qué sobra, qué falta y dónde va cada cosa

- **Estado**: Aceptada (2026-11-17, @Marina)
- **Fecha**: 2026-11-17
- **Autor**: @ia-opencode-maga369
- **Quién decide**: @Marina. Su [[Modelo de datos]] es la fuente de verdad; esto solo responde a las preguntas de [[0010-modelo-de-datos]] y baja el modelo a SQL.
- **Votos**: @Marina acepta los once puntos y las cinco respuestas el 2026-11-17. @Rubén sigue debiendo **B8** (dueño del hash del PDF) y la confirmación de `GET /documents/{id}/pages`; ninguna de las dos entra en lo aceptado.

## Contexto

[[0010-modelo-de-datos]] dejó el modelo de @Marina como válido y seis preguntas abiertas. Este documento las contesta, revisa los tres puntos que no encajaban y las ocho columnas que podían sobrar, y entrega las migraciones `V14` (estructura, se puede aplicar ya) y `V15` (flujo, espera a 0005).

Regla que se ha seguido al revisar la lista de 0010: **si no hay regla, respuesta del contrato ni código que lea una columna, se dice y se quita**; si la lee algo, se queda aunque 0010 propusiera lo contrario.

## Los once puntos

| # | Punto | Se propone | Motivo en una línea | A quién afecta |
|---|---|---|---|---|
| 1 | `documentos.expira_en` | **Quitar** | A-21 dice que el expediente no caduca; el TTL de 24 h es de los temporales del OCR, que no son filas de `documentos` | Contrato: nada (no lo devuelve). Regla A-21: la deja implementable sin `404` |
| 2 | `documentos.retencion_hasta` | **Quitar** | Ninguna regla ni respuesta lo lee; se calcula de `configuracion_sistema.retencion_documentos_meses` + `creado_en` cuando U-08 fije el plazo | Nada; se pierde una consulta directa que hoy nadie hace |
| 3 | `documentos.cerrado_en` | **Se queda** | 0010 se equivoca: A-19 lo nombra y el contrato §10 dice que lo escribe el export | Contrato §10 y regla A-19 |
| 4 | `auditoria.hash_actual` | **Quitar** | En tabla particionada el `UNIQUE` debe incluir la clave de partición y, sin trigger que lo calcule, valdría `NULL` siempre; la cadena ya se verifica con `hash_anterior` (V8) | Nada. Si se quiere integridad real: trigger y **sin** `UNIQUE` |
| 5 | `auditoria.entidad_clave` | **Quitar** | Solo la usarían los eventos `CONFIG_*` y ningún contrato la devuelve; la clave cabe en `detalle->>'clave'` | Nada; la auditoría de configuración se consulta por `detalle` |
| 6 | `bloques_layout.pagina_ancho` | **Se queda** | El contrato §4 lo devuelve por bloque (`pagina.ancho`); moverlo a `paginas_documento` obliga a `join` y se rompe si una versión se re-renderiza a otro dpi | Contrato §4 |
| 7 | `bloques_layout.pagina_alto` | **Se queda** | Mismo motivo que el anterior | Contrato §4 |
| 8 | `bloques_layout.forma` | **Se queda** | El contrato §4 dice que con `quad`/`poly` se usa `puntos` en lugar del `bbox`: sin `forma` no se sabe cuál leer | Contrato §4 |
| 9 | `bloques_layout.puntos` | **Se queda** | Es lo único que guarda el polígono; el `bbox` es solo su caja envolvente | Contrato §4 |
| 10 | `revisiones.revisor_id` | **Quitar** (se renombra a `asignado_a`) | Si significa «quien cerró», no lo lee ningún endpoint ni regla: el cierre queda en `auditoria` y en `versiones_documento.creado_por`; mantener las dos invita a que discrepen | `views.sql` (`v_metricas_revisor`, `v_documento_actual`) y `triggers.sql` |
| 11 | `revisiones.asignado_a` | **Se queda** y absorbe a `revisor_id` | Es la única columna de responsabilidad: la leen A-05, A-06 y el contrato §6 | Contrato §6 |

Sobre el punto 10: el renombrado es `ALTER TABLE revisiones RENAME COLUMN revisor_id TO asignado_a`, sin pérdida de datos, y quita el `NOT NULL` porque la revisión nace en cola sin dueño (A-05).

## Lo que faltaba y no estaba en la lista

| Qué | Por qué | Quién lo lee |
|---|---|---|
| `revisiones.documento_id` | A-04 prohíbe **dos revisiones abiertas por documento**, no por versión; sin la columna no hay índice que lo impida | A-04 y el `409` de `POST /documents/{id}/reviews` |
| `revisiones.actualizado_en` | Es el `If-Match` del cierre | A-23 y contrato §6 |
| `categorias_sensibles.prioridad` | El contrato ya la devuelve y no existía como columna | Contrato §7 |
| `revision_plazo_horas`, `revision_aviso_horas`, `calendario_laboral` | A-20 los nombra y no estaban sembrados; sin ellos el plazo acaba como constante en el código | A-20 |
| `documentos.clave_cifrado` | 0004 está **Aceptada** y el modelo solo tenía `ruta_almacenamiento` | 0004 |
| `documentos.eliminado_en` | `DELETE /documents/{id}` es borrado lógico y el modelo no lo tenía en el esquema | Contrato §3 y H3 |
| `UNIQUE (creado_por, hash_sha256)` parcial | El único global de V3 impide que dos personas suban el mismo PDF; se excluye lo borrado para poder volver a subirlo | Modelo de @Marina; I-7 de 0010 |

**Dos excepciones a la regla del lector**, dichas para que no parezcan un descuido: `bloques_layout.calidad_semaforo` y `paginas_documento.leida_ocr` no los devuelve hoy ningún endpoint. Se quedan porque el OCR los escribe al procesar y el modelo de @Marina los pide; el semáforo que sí se pinta en la maqueta es el de la página (`contraste` + `estado`). Si se prefiere cero columnas sin lector, se quitan esas dos y `V14` sigue en pie.

## Las cinco preguntas abiertas de 0010

**1. Geometría.** Se queda como está: **píxeles de la página renderizada** y `pagina_ancho`/`pagina_alto` en el propio bloque. Con `forma = quad|poly` se usa `puntos`, en las **mismas unidades** y con el mismo tamaño de página; el `bbox` se guarda siempre porque es el que sirve para filtrar por zona y para el `hit-test` del visor. No se normaliza a 0-1: PaddleOCR-VL devuelve `coordinate` en píxeles, normalizar pierde precisión y obliga a recalcular si cambia el dpi del render. Precisión: `DECIMAL(10,2)`, que es 0,01 px.

**2. `revisiones`.** `asignado_a` es «quien la tiene» (A-05/A-06) y `revisor_id` sobra: «quien la cerró» ya está en `auditoria` (`REVISION_APROBADA`/`REVISION_RECHAZADA` con `usuario_id`) y en `versiones_documento.creado_por` de la versión que crea el cierre. A-04 se implementa con `documento_id` + índice parcial único sobre `en_cola`/`en_proceso`.

**3. Tabla de páginas.** **Entra.** B5 y la maqueta la exigen (contraste < 80 → no se transcribe), y `num_paginas` ya lo devuelve el contrato. Aviso: hoy **no hay endpoint que la lea**; el contrato tiene que ganar `GET /documents/{id}/pages` y eso queda como tarea en el [[Tablero]]. Se añade ahora porque el OCR debe escribir el contraste al procesar, y eso no se puede inventar después.

**4. `seudonimos`.** **No se crea en el piloto.** La consistencia dentro de un documento se consigue con un mapa determinista al generar la versión (`hash(categoria_id || texto_normalizado)` → etiqueta numerada) y el resultado ya se guarda en `anotaciones_entidad.texto_sustitucion`; ninguna regla ni endpoint lee una tabla de seudónimos. Si negocio mantiene la promesa de la maqueta («taula de pseudònims xifrada i separada»), la tabla sería `seudonimos (documento_id, entidad_hash, etiqueta, creado_en)` con `UNIQUE (documento_id, entidad_hash)`, cifrada en reposo: decisión nueva y ~1 día. Recomendación: cambiar el texto de la maqueta (I2) y dejar la tabla para Fase 2.

**5. Clave del cifrado.** Ni KMS ni clave en la fila: `documentos.clave_cifrado VARCHAR(100)` guarda el **identificador de la clave** (versión de KEK) de un gestor local; el material vive fuera de la base de datos (fichero con permisos `0600` o keyring del sistema). Motivo: un KMS en cloud contradice que todo el POC sea local, y guardar la clave en la fila la filtra con un `SELECT *`. Cifrado por sobre: una DEK por documento, cifrada con la KEK.

**6. `citext` o `lower(email)`.** `lower(email)` con índice único funcional, `varchar` como está. `citext` exige `CREATE EXTENSION citext` (superusuario) y no aporta nada que el índice no dé. Va en `V13`: `CREATE UNIQUE INDEX uq_usuarios_email_lower ON usuarios (lower(email));` y se puede quitar el `UNIQUE` de la columna.

## Orden de las migraciones

| # | Contenido | ¿Se puede escribir ya? |
|---|---|---|
| `V13` | Identidad: `usuarios.roles`, `estado`, `sso_subject`; `sesiones_usuario` (única tabla nueva); `tokens_usuario` no se crea | **No**: espera [[0009-identidad]] y [[0012-identidad-y-roles]]. Es el único sitio donde esperar sale gratis |
| `V14` | Estructura: `bloques_layout`, `paginas_documento`, `num_paginas` | **Sí.** Escrita y sin dependencias; desbloquea OCR, semáforo y PDF |
| `V15` | Flujo: estados, visto bueno, `revisiones`, `anotaciones_entidad.bloque_id`, seeds H6/H8 | **Sí, salvo el hash**: espera a que se acepte [[0005-reglas-usuarios-y-aprobacion]] |
| `V16` | Hash del PDF (B8): `versiones_documento.hash_export` + `exportado_en` o las dos en `documentos`, **un solo dueño** | No: espera B8 |

Ninguna toca `V1`-`V12` ni borra tablas. `V15` **renombra** una columna (`revisor_id` → `asignado_a`), y lo dice en el fichero.

`V14` se puede aplicar hoy porque no depende de identidad, de las reglas ni de B8. `V15` espera a 0005, pero su contenido ya está escrito para que la revisión de @Rubén sea sobre SQL y no sobre una idea.

## Anexo del 18/11: qué deja de usarse

No cambia nada de lo aceptado, pero dos reglas que `V15` bajó al modelo se han movido:

- **A-20 retirada**: `revisiones.fecha_limite` y `revisiones.aviso_24h_enviado_en` existen y **se quedan sin uso**; los seeds `revision_plazo_horas`, `revision_aviso_horas` y `calendario_laboral` también. No se borran: quitar columnas es otra migración y no urge.
- **A-15 en pausa**: `documentos.requiere_visto_bueno` se queda siempre en `false` y ningún documento pasa a `pendiente_visto_bueno`. Las columnas y el estado ya están en `V15`.

Lo que sí cambia de fondo es la identidad: ver [[0012-identidad-y-roles]], que deja `V13` en estas columnas y **sin tabla de roles**.

## Fuera de lo aceptado: el hash del PDF (B8)

**Esto no forma parte de la decisión aceptada.** Es una recomendación para que la decida @Rubén con 0007 delante: **el dueño es la versión**. El PDF se genera por versión, y al reabrir un aprobado el hash anterior tiene que sobrevivir; si el dueño es `documentos`, la reapertura lo pisa o lo duplica. `documentos` se quedaría con `estado` y `exportado_en`; el contrato §6 y §10 tendrían que dejar de devolver `documentos.hash_export`, que es un cambio de documentación, no de código.

## Consecuencias

- `views.sql`: `v_documento_actual` y `v_metricas_revisor` pasan a `asignado_a` (hecho en este PR).
- `triggers.sql`: la validación de rol admite `NULL` (la revisión nace sin dueño), el `If-Match` de `revisiones` gana su trigger de `actualizado_en`, y el trigger de estados ya no escribe en `NEW.estado` (esa columna no existe: era un fallo que habría saltado al primer cierre).
- Contrato: falta `GET /documents/{id}/pages` (B5); y, cuando se cierre B8, dejar de devolver `hash_export` desde `documentos`.
- La maqueta: el texto de la tabla de seudónimos (I2) y el semáforo por página ya tienen modelo.

## Preguntas para el equipo

- **@Rubén**: B8, ¿versión o documento? Y confirmar `GET /documents/{id}/pages` en el contrato. Son las dos únicas cosas que 0011 deja abiertas.
- **@Marina**: aceptado el 2026-11-17. Los puntos 1, 2, 4, 5, 10 y 11 quedan como están escritos, sin correcciones.
- **@Alex, @Kevin**: el voto de [[0009-identidad]] es lo único que separa `V13` de estar escrita.
