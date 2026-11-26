-- name: revision_abierta_doc
SELECT id FROM revisiones WHERE documento_id = %(documento_id)s AND estado IN ('en_cola', 'en_proceso');

-- name: revision_abrir
INSERT INTO revisiones (version_id, documento_id, estado, numero_intento, actualizado_en)
SELECT %(version_id)s, %(documento_id)s, 'en_cola', COALESCE(MAX(numero_intento), 0) + 1, now()
  FROM revisiones WHERE documento_id = %(documento_id)s
RETURNING id, numero_intento, estado, actualizado_en;

-- name: revisiones_listar
SELECT r.id, r.documento_id, d.nombre_original, r.version_id, r.numero_intento, r.estado,
       r.asignado_a, r.asignado_en, r.creado_en, r.actualizado_en, COUNT(*) OVER () AS total
  FROM revisiones r JOIN documentos d ON d.id = r.documento_id
 WHERE (%(estado)s::text IS NULL OR r.estado = %(estado)s)
   AND (%(asignado_a)s::uuid IS NULL OR r.asignado_a = %(asignado_a)s)
   AND d.estado <> 'eliminado'
 ORDER BY r.creado_en
 LIMIT %(limit)s OFFSET %(offset)s;

-- name: revision_tomar
-- A-05: un único UPDATE; dos revisores a la vez no pueden quedar los dos.
UPDATE revisiones
   SET estado = 'en_proceso', asignado_a = %(usuario_id)s, asignado_en = now(), actualizado_en = now()
 WHERE id = %(id)s AND estado = 'en_cola'
RETURNING id, estado, asignado_a, asignado_en, actualizado_en;

-- name: revision_por_id
SELECT id, documento_id, version_id, estado, asignado_a, numero_intento, actualizado_en
  FROM revisiones WHERE id = %(id)s;

-- name: revision_cerrar
-- A-23: cierre optimista con el actualizado_en leído (If-Match).
UPDATE revisiones
   SET estado = %(estado)s, comentario_general = %(comentario)s, finalizado_en = now(),
       tiempo_revision_seg = GREATEST(0, EXTRACT(EPOCH FROM now() - COALESCE(asignado_en, creado_en)))::int,
       actualizado_en = now()
 WHERE id = %(id)s AND estado = 'en_proceso' AND actualizado_en = %(if_match)s::timestamptz
RETURNING id, estado, finalizado_en, tiempo_revision_seg;

-- name: revision_devolver
UPDATE revisiones
   SET estado = 'en_cola', asignado_a = NULL, asignado_en = NULL,
       comentario_general = %(comentario)s, actualizado_en = now()
 WHERE id = %(id)s AND estado = 'en_proceso' AND actualizado_en = %(if_match)s::timestamptz
RETURNING id, estado;

-- name: revision_aprobada_doc
SELECT version_id FROM revisiones
 WHERE documento_id = %(documento_id)s AND estado = 'aprobado'
 ORDER BY numero_intento DESC LIMIT 1;
