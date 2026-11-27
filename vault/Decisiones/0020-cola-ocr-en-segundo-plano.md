# 0017 · Cola de OCR en segundo plano, página a página

- **Estado**: Propuesta
- **Fecha**: 2026-11-26
- **Autor**: @ia-claude-alex

## Contexto

El OCR real tarda entre 10 y 20 segundos por página. Hasta ahora `POST /transform/document` leía todo el documento dentro de la petición y guardaba las páginas al final. Mientras tanto no se podía revisar nada, y si se cerraba la pestaña o se reiniciaba el servidor se perdía el trabajo. Queremos revisar la página 1 en cuanto está leída y dejar PDF largos transcribiéndose de noche. Cierra la tarea del tablero «Decidir si el OCR es síncrono o por página asíncrona».

## Decisión

- El OCR es **asíncrono y por página**. La subida guarda el original, deja el documento en `pendiente` y responde `202` al momento.
- La cola es la propia tabla `documentos`, sin Redis ni Celery: `pendiente` con `metadatos_extras.ocr` (modo pedido) y sin `ocr.error`. No cambia el esquema (V1..V15).
- Un hilo dentro del backend (`OCR_WORKERS=1`, porque el cuello de botella es el modelo) toma el más antiguo con `FOR UPDATE SKIP LOCKED` y lo pasa a `ocr_procesando`. Cada página se confirma en su propia transacción: fila de `paginas_documento`, bloque de la versión `ocr_texto`, avisos con caja, diferencias y contraste.
- Estados: `pendiente` = en cola, `ocr_procesando` = leyendo, `ocr_completado` = terminado. Si falla o se cancela, el documento vuelve a `pendiente` con `ocr.error` (`OCR_FALLIDO` o `CANCELADO`), se audita y la cola sigue con el siguiente.
- Al arrancar, lo que quedó en `ocr_procesando` vuelve a la cola y sigue desde la última página guardada.
- Las páginas ya guardadas se pueden editar, validar, releer y localizar mientras el resto sigue en cola. Las que faltan dan `409 PAGINA_EN_PROCESO`.
- El NDJSON se mantiene para el frontend actual, pero ahora lee la BD cada segundo. Hay además `GET /documents/{id}/progress`, `GET /documents/{id}/stream` y `POST /documents/{id}/cancel` (ver `docs/api/endpoints.md` §11).

## Consecuencias

- La subida ya no bloquea, y un reinicio no pierde las páginas leídas.
- La reanudación supone **un solo proceso backend**. Con varias réplicas habría que añadir un latido por worker antes de devolver documentos a la cola.
- Si el servidor se apaga a mitad de una página, esa página se vuelve a leer al arrancar.
- El frontend tiene que aceptar documentos en `pendiente`/`ocr_procesando` como abribles y usar `pages_done` y `queue_position`.

> Renumerada de `0017` a `0020` el 27/11/2026: el PR #52 usó `0017` para [[0017-particionado-auditoria]] y `0018` para [[0018-mariadb-segunda-opcion]].
