-- name: doc_por_hash
-- V15: el hash es único por creador y excluye lo eliminado.
SELECT id FROM documentos
 WHERE creado_por = %(creado_por)s AND hash_sha256 = %(hash)s AND estado <> 'eliminado';

-- name: doc_insertar
-- 0017: entra en cola (`pendiente`); `metadatos_extras.ocr` guarda el modo pedido.
INSERT INTO documentos (nombre_original, hash_sha256, mime_type, tamano_bytes,
                        ruta_almacenamiento, estado, creado_por, clave_cifrado, num_paginas,
                        metadatos_extras)
VALUES (%(nombre)s, %(hash)s, %(mime)s, %(tamano)s, %(ruta)s, 'pendiente',
        %(creado_por)s, %(clave)s, %(num_paginas)s, %(meta)s::jsonb)
RETURNING id;

-- name: cola_tomar
-- 0017: el más antiguo en cola. SKIP LOCKED: dos workers nunca toman el mismo.
-- En cola = `pendiente` con `ocr` en metadatos y sin `ocr.error` (fallido o cancelado).
UPDATE documentos SET estado = 'ocr_procesando', actualizado_en = now()
 WHERE id = (SELECT id FROM documentos
              WHERE estado = 'pendiente' AND metadatos_extras ? 'ocr'
                AND NOT metadatos_extras -> 'ocr' ? 'error'
              ORDER BY creado_en, id
              LIMIT 1 FOR UPDATE SKIP LOCKED)
RETURNING id, mime_type, ruta_almacenamiento, num_paginas, creado_por, metadatos_extras;

-- name: cola_reanudar
-- Al arrancar: lo que quedó a medias (caída o reinicio) vuelve a la cola y se reanuda.
-- shortcut: supone un solo proceso backend; con varios, añadir un latido por worker.
UPDATE documentos SET estado = 'pendiente'
 WHERE estado = 'ocr_procesando' AND metadatos_extras ? 'ocr'
RETURNING id;

-- name: cola_huerfanos
-- Subidos antes de la cola (sin `ocr` en metadatos): no se pueden reanudar. Quedan como fallidos
-- para que la bandeja ofrezca volver a subirlos en vez de «transcribiendo» para siempre.
UPDATE documentos
   SET estado = 'pendiente', actualizado_en = now(),
       metadatos_extras = metadatos_extras || jsonb_build_object('ocr', jsonb_build_object(
           'error', 'Transcripción interrumpida: vuelve a subir el documento'))
 WHERE estado = 'ocr_procesando' AND NOT metadatos_extras ? 'ocr'
RETURNING id;

-- name: doc_progreso
SELECT d.estado, d.num_paginas, d.creado_en, d.metadatos_extras -> 'ocr' AS ocr,
       (SELECT count(*) FROM paginas_documento p WHERE p.documento_id = d.id) AS pages_done,
       CASE WHEN d.estado = 'pendiente' AND d.metadatos_extras ? 'ocr'
                 AND NOT d.metadatos_extras -> 'ocr' ? 'error'
            THEN (SELECT count(*) FROM documentos c
                   WHERE c.estado = 'pendiente' AND c.metadatos_extras ? 'ocr'
                     AND NOT c.metadatos_extras -> 'ocr' ? 'error'
                     AND (c.creado_en, c.id) <= (d.creado_en, d.id))
       END AS queue_position
  FROM documentos d
 WHERE d.id = %(id)s;

-- name: doc_estado
UPDATE documentos SET estado = %(estado)s, actualizado_en = now() WHERE id = %(id)s;

-- name: doc_fin_ocr
UPDATE documentos
   SET estado = 'ocr_completado', num_paginas = %(num_paginas)s, actualizado_en = now()
 WHERE id = %(id)s;

-- name: doc_meta_set
-- Nunca reemplaza el objeto entero: solo la clave indicada.
UPDATE documentos
   SET metadatos_extras = jsonb_set(metadatos_extras, %(ruta)s::text[], %(valor)s::jsonb, true),
       actualizado_en = now()
 WHERE id = %(id)s;

-- name: doc_eliminar
UPDATE documentos SET estado = 'eliminado', eliminado_en = now(), actualizado_en = now()
 WHERE id = %(id)s AND estado <> 'eliminado';

-- name: doc_por_id
SELECT d.id, d.nombre_original, d.mime_type, d.num_paginas, d.estado, d.creado_en,
       d.actualizado_en, d.creado_por, d.ruta_almacenamiento, d.tamano_bytes,
       d.metadatos_extras, d.exportado_en, d.requiere_visto_bueno,
       v.id AS v_id, v.numero_version AS v_numero, v.tipo_version AS v_tipo,
       v.confianza_layout_promedio AS v_confianza, v.metadatos_proceso AS v_meta,
       COALESCE(d.metadatos_extras ->> 'subido_por', concat_ws(' ', u.nombre, u.apellidos)) AS subido_por
  FROM documentos d
  LEFT JOIN versiones_documento v ON v.documento_id = d.id AND v.es_actual
  LEFT JOIN usuarios u ON u.id = d.creado_por
 WHERE d.id = %(id)s AND d.estado <> 'eliminado';

-- name: docs_listar
-- Bandeja y archivo. `q` busca en el texto de la versión vigente (texto completo, español)
-- y en el nombre. `solo_de` limita al creador (el transcriptor ve solo lo suyo).
SELECT d.id, d.nombre_original, d.estado, d.num_paginas, d.creado_en, d.actualizado_en,
       d.exportado_en,
       COALESCE(d.metadatos_extras ->> 'subido_por', concat_ws(' ', u.nombre, u.apellidos)) AS subido_por,
       d.metadatos_extras -> 'ocr' ->> 'modo' AS modo_ocr,
       (SELECT count(*) FROM paginas_documento p
         WHERE p.documento_id = d.id AND p.estado = 'revisar') AS paginas_revisar,
       (SELECT count(*) FROM paginas_documento p
         WHERE p.documento_id = d.id AND p.estado = 'ilegible') AS paginas_ilegibles,
       (SELECT count(*) FROM paginas_documento p WHERE p.documento_id = d.id) AS pages_done,
       CASE WHEN d.estado = 'pendiente' AND d.metadatos_extras ? 'ocr'
                 AND NOT d.metadatos_extras -> 'ocr' ? 'error'
            THEN (SELECT count(*) FROM documentos c
                   WHERE c.estado = 'pendiente' AND c.metadatos_extras ? 'ocr'
                     AND NOT c.metadatos_extras -> 'ocr' ? 'error'
                     AND (c.creado_en, c.id) <= (d.creado_en, d.id))
       END AS queue_position,
       -- shortcut: sin fragmento en exportados porque contenido_texto no está anonimizado;
       -- cuando se guarde el texto sustituido, sacar el fragmento de ahí.
       CASE WHEN %(q)s::text IS NULL OR d.estado = 'exportado' THEN NULL
            ELSE ts_headline('spanish', coalesce(v.contenido_texto, ''),
                             plainto_tsquery('spanish', %(q)s),
                             'MaxWords=25, MinWords=8, MaxFragments=2')
       END AS fragmento,
       COUNT(*) OVER () AS total
  FROM documentos d
  LEFT JOIN versiones_documento v ON v.documento_id = d.id AND v.es_actual
  LEFT JOIN usuarios u ON u.id = d.creado_por
 WHERE d.estado <> 'eliminado'
   AND (%(estado)s::text IS NULL OR d.estado = %(estado)s)
   AND (%(solo_de)s::uuid IS NULL OR d.creado_por = %(solo_de)s)
   AND (%(q)s::text IS NULL
        OR to_tsvector('spanish', coalesce(v.contenido_texto, ''))
           @@ plainto_tsquery('spanish', %(q)s)
        OR d.nombre_original ILIKE '%%' || %(q)s || '%%')
 ORDER BY d.creado_en DESC
 LIMIT %(limit)s OFFSET %(offset)s;

-- name: version_desmarcar
-- Sin triggers.sql (no aplica en PG16) el backend mantiene `es_actual` y la numeración.
UPDATE versiones_documento SET es_actual = false
 WHERE documento_id = %(documento_id)s AND es_actual;

-- name: version_insertar
INSERT INTO versiones_documento (documento_id, numero_version, tipo_version, contenido_texto,
                                 motor_ocr, modelo_ia, confianza_layout_promedio,
                                 metadatos_proceso, creado_por, pipeline_version, regla_id,
                                 es_actual)
SELECT %(documento_id)s, COALESCE(MAX(numero_version), 0) + 1, %(tipo)s, %(texto)s,
       %(motor_ocr)s, %(modelo_ia)s, %(confianza)s, %(meta)s::jsonb, %(creado_por)s,
       %(pipeline)s, %(regla_id)s, true
  FROM versiones_documento WHERE documento_id = %(documento_id)s
RETURNING id, numero_version;

-- name: version_meta_set
UPDATE versiones_documento
   SET metadatos_proceso = jsonb_set(metadatos_proceso, %(ruta)s::text[], %(valor)s::jsonb, true)
 WHERE id = %(id)s;

-- name: version_texto_recalcular
UPDATE versiones_documento
   SET contenido_texto = (SELECT string_agg(contenido, E'\n\n' ORDER BY pagina_numero, orden_lectura)
                            FROM bloques_layout WHERE version_id = %(id)s)
 WHERE id = %(id)s;

-- name: versiones_listar
SELECT numero_version, tipo_version, motor_ocr, confianza_layout_promedio, creado_en, es_actual
  FROM versiones_documento WHERE documento_id = %(documento_id)s ORDER BY numero_version;

-- name: version_por_numero
SELECT id, documento_id, numero_version, tipo_version, contenido_texto, contenido_html,
       ruta_pdf, motor_ocr, modelo_ia, confianza_layout_promedio, metadatos_proceso,
       pipeline_version, regla_id, es_actual, creado_en
  FROM versiones_documento
 WHERE documento_id = %(documento_id)s AND numero_version = %(numero)s;

-- name: bloque_insertar
INSERT INTO bloques_layout (version_id, pagina_numero, orden_lectura, etiqueta, confianza,
                            bbox_x, bbox_y, bbox_ancho, bbox_alto, pagina_ancho, pagina_alto,
                            contenido, calidad_semaforo)
VALUES (%(version_id)s, %(pagina)s, 0, 'text', NULL, 0, 0, %(ancho)s, %(alto)s, %(ancho)s,
        %(alto)s, %(contenido)s, %(semaforo)s);

-- name: bloques_copiar
INSERT INTO bloques_layout (version_id, pagina_numero, orden_lectura, etiqueta, confianza, forma,
                            bbox_x, bbox_y, bbox_ancho, bbox_alto, pagina_ancho, pagina_alto,
                            puntos, contenido, calidad_semaforo)
SELECT %(destino)s, pagina_numero, orden_lectura, etiqueta, confianza, forma, bbox_x, bbox_y,
       bbox_ancho, bbox_alto, pagina_ancho, pagina_alto, puntos, contenido, calidad_semaforo
  FROM bloques_layout WHERE version_id = %(origen)s
RETURNING id, pagina_numero, orden_lectura, contenido;

-- name: bloques_version
SELECT id, pagina_numero, orden_lectura, etiqueta, confianza, forma, bbox_x, bbox_y, bbox_ancho,
       bbox_alto, pagina_ancho, pagina_alto, puntos, contenido, calidad_semaforo,
       COUNT(*) OVER () AS total
  FROM bloques_layout
 WHERE version_id = %(version_id)s
   AND (%(pagina)s::int IS NULL OR pagina_numero = %(pagina)s)
 ORDER BY pagina_numero, orden_lectura
 LIMIT %(limit)s OFFSET %(offset)s;

-- name: bloque_de_pagina
SELECT id, contenido FROM bloques_layout
 WHERE version_id = %(version_id)s AND pagina_numero = %(pagina)s
 ORDER BY orden_lectura LIMIT 1;

-- name: bloque_actualizar
UPDATE bloques_layout SET contenido = %(contenido)s, calidad_semaforo = %(semaforo)s
 WHERE id = %(id)s;

-- name: pagina_insertar
INSERT INTO paginas_documento (documento_id, numero, contraste, estado, avisos, leida_ocr)
VALUES (%(documento_id)s, %(numero)s, %(contraste)s, %(estado)s, %(avisos)s::jsonb, %(leida)s);

-- name: pagina_actualizar
UPDATE paginas_documento
   SET contraste = %(contraste)s, estado = %(estado)s, avisos = %(avisos)s::jsonb,
       leida_ocr = %(leida)s
 WHERE documento_id = %(documento_id)s AND numero = %(numero)s;

-- name: paginas_numeros
SELECT numero FROM paginas_documento WHERE documento_id = %(documento_id)s;

-- name: paginas_listar
SELECT p.numero, p.contraste, p.estado, p.avisos, p.leida_ocr,
       (SELECT b.contenido FROM bloques_layout b
         WHERE b.version_id = %(version_id)s AND b.pagina_numero = p.numero
         ORDER BY b.orden_lectura LIMIT 1) AS texto
  FROM paginas_documento p
 WHERE p.documento_id = %(documento_id)s
 ORDER BY p.numero;

-- name: usuario_por_nombre
-- SharePoint: la carpeta lleva el nombre de la persona; si coincide con un usuario activo, el
-- documento es suyo (lo ve en su bandeja).
SELECT u.id AS usuario_id, u.nombre, u.apellidos
  FROM usuarios u
 WHERE u.estado = 'activo'
   AND lower(%(nombre)s) IN (lower(concat_ws(' ', u.nombre, u.apellidos)), lower(u.nombre))
 ORDER BY u.creado_en
 LIMIT 1;

-- name: version_ocr_ultima
SELECT id, metadatos_proceso FROM versiones_documento
 WHERE documento_id = %(documento_id)s AND tipo_version = 'ocr_texto'
 ORDER BY numero_version DESC LIMIT 1;
