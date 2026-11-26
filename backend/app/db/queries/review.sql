-- name: listar_anotaciones_version
SELECT id, version_id, bloque_id, categoria_id, inicio, fin, texto_original, texto_sustitucion, estado
FROM anotaciones_entidad
WHERE version_id = %(version_id)s
ORDER BY inicio ASC;

-- name: insertar_anotacion
INSERT INTO anotaciones_entidad (
    version_id, bloque_id, categoria_id, inicio, fin, texto_original, texto_sustitucion, estado
)
VALUES (
    %(version_id)s, %(bloque_id)s, %(categoria_id)s, %(inicio)s, %(fin)s,
    %(texto_original)s, %(texto_sustitucion)s, %(estado)s
)
RETURNING id, version_id, bloque_id, categoria_id, inicio, fin, texto_original, texto_sustitucion, estado;

-- name: actualizar_anotacion
UPDATE anotaciones_entidad
SET estado = %(estado)s,
    texto_sustitucion = COALESCE(%(texto_sustitucion)s, texto_sustitucion)
WHERE id = %(id)s
RETURNING id, version_id, bloque_id, categoria_id, inicio, fin, texto_original, texto_sustitucion, estado;

-- name: contar_anotaciones_pendientes
SELECT count(*) AS total
FROM anotaciones_entidad
WHERE version_id = %(version_id)s AND estado = 'pendiente';

-- name: listar_revisiones
SELECT id, documento_id, revisor_id, estado, motivo, creado_en, actualizado_en
FROM revisiones
ORDER BY creado_en DESC
LIMIT %(limit)s OFFSET %(offset)s;

-- name: contar_revisiones
SELECT count(*) AS total
FROM revisiones;

-- name: obtener_revision
SELECT id, documento_id, revisor_id, estado, motivo, creado_en, actualizado_en
FROM revisiones
WHERE id = %(id)s;

-- name: crear_revision
INSERT INTO revisiones (documento_id, revisor_id, estado)
VALUES (%(documento_id)s, %(revisor_id)s, %(estado)s)
RETURNING id, documento_id, revisor_id, estado, motivo, creado_en, actualizado_en;

-- name: reclamar_revision
UPDATE revisiones
SET revisor_id = %(revisor_id)s, estado = 'en_curso', actualizado_en = now()
WHERE id = %(id)s AND revisor_id IS NULL AND estado = 'pendiente'
RETURNING id, documento_id, revisor_id, estado, motivo, creado_en, actualizado_en;

-- name: asignar_revision
UPDATE revisiones
SET revisor_id = %(revisor_id)s, estado = 'en_curso', actualizado_en = now()
WHERE id = %(id)s
RETURNING id, documento_id, revisor_id, estado, motivo, creado_en, actualizado_en;

-- name: cerrar_revision
UPDATE revisiones
SET estado = %(estado)s, motivo = %(motivo)s, actualizado_en = now()
WHERE id = %(id)s
RETURNING id, documento_id, revisor_id, estado, motivo, creado_en, actualizado_en;

-- name: actualizar_estado_documento
UPDATE documentos
SET estado = %(estado)s, actualizado_en = now()
WHERE id = %(id)s
RETURNING id, titulo, estado, creado_por, creado_en, actualizado_en, exportado_en;
