-- name: listar_documentos
SELECT id, titulo, estado, creado_por, creado_en, actualizado_en, exportado_en
FROM documentos
WHERE estado <> 'eliminado'
ORDER BY actualizado_en DESC
LIMIT %(limit)s OFFSET %(offset)s;

-- name: contar_documentos
SELECT count(*) AS total
FROM documentos
WHERE estado <> 'eliminado';

-- name: obtener_documento
SELECT id, titulo, estado, creado_por, creado_en, actualizado_en, exportado_en
FROM documentos
WHERE id = %(id)s AND estado <> 'eliminado';

-- name: crear_documento
INSERT INTO documentos (titulo, estado, creado_por)
VALUES (%(titulo)s, %(estado)s, %(creado_por)s)
RETURNING id, titulo, estado, creado_por, creado_en, actualizado_en, exportado_en;

-- name: eliminar_documento_logico
UPDATE documentos
SET estado = 'eliminado', actualizado_en = now()
WHERE id = %(id)s AND estado <> 'eliminado'
RETURNING id;

-- name: listar_paginas_documento
SELECT id, documento_id, numero_pagina, semaforo, avisos
FROM paginas_documento
WHERE documento_id = %(documento_id)s
ORDER BY numero_pagina ASC;

-- name: insertar_pagina_documento
INSERT INTO paginas_documento (documento_id, numero_pagina, semaforo, avisos)
VALUES (%(documento_id)s, %(numero_pagina)s, %(semaforo)s, %(avisos)s)
RETURNING id, documento_id, numero_pagina, semaforo, avisos;

-- name: listar_versiones_documento
SELECT id, documento_id, numero_version, es_actual, texto_contenido, metadatos_proceso, creado_en
FROM versiones_documento
WHERE documento_id = %(documento_id)s
ORDER BY numero_version DESC;

-- name: obtener_version_por_numero
SELECT id, documento_id, numero_version, es_actual, texto_contenido, metadatos_proceso, creado_en
FROM versiones_documento
WHERE documento_id = %(documento_id)s AND numero_version = %(numero_version)s;

-- name: obtener_version_actual
SELECT id, documento_id, numero_version, es_actual, texto_contenido, metadatos_proceso, creado_en
FROM versiones_documento
WHERE documento_id = %(documento_id)s AND es_actual = true;

-- name: crear_version_documento
INSERT INTO versiones_documento (documento_id, texto_contenido, metadatos_proceso)
VALUES (%(documento_id)s, %(texto_contenido)s, %(metadatos_proceso)s)
RETURNING id, documento_id, numero_version, es_actual, texto_contenido, metadatos_proceso, creado_en;

-- name: listar_bloques_version
SELECT id, version_id, pagina, orden, tipo, texto, bbox
FROM bloques_layout
WHERE version_id = %(version_id)s
ORDER BY pagina ASC, orden ASC;

-- name: insertar_bloque_layout
INSERT INTO bloques_layout (version_id, pagina, orden, tipo, texto, bbox)
VALUES (%(version_id)s, %(pagina)s, %(orden)s, %(tipo)s, %(texto)s, %(bbox)s)
RETURNING id, version_id, pagina, orden, tipo, texto, bbox;

-- name: marcar_documento_exportado
UPDATE documentos
SET exportado_en = now(), actualizado_en = now()
WHERE id = %(id)s
RETURNING id, exportado_en;
