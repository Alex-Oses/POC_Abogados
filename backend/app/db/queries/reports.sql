-- name: doc_bloquear
SELECT id, estado, nombre_original FROM documentos WHERE id = %(id)s FOR UPDATE;

-- name: version_final_doc
SELECT id, numero_version, ruta_pdf, metadatos_proceso
  FROM versiones_documento
 WHERE documento_id = %(documento_id)s AND tipo_version = 'final_aprobado'
 ORDER BY numero_version DESC LIMIT 1;

-- name: version_pdf_set
UPDATE versiones_documento
   SET ruta_pdf = %(ruta)s,
       metadatos_proceso = jsonb_set(metadatos_proceso, '{hash_export}', to_jsonb(%(hash)s::text), true)
 WHERE id = %(id)s;

-- name: doc_exportado
UPDATE documentos
   SET estado = 'exportado', exportado_en = now(), cerrado_en = now(), actualizado_en = now()
 WHERE id = %(id)s;

-- name: config_valor
SELECT valor FROM configuracion_sistema WHERE clave = %(clave)s;

-- name: informe_resumen
-- Agregados reales del mes en curso (UTC).
SELECT
  (SELECT COALESCE(SUM(num_paginas), 0) FROM documentos
    WHERE estado <> 'eliminado' AND creado_en >= date_trunc('month', now())) AS paginas_mes,
  (SELECT COUNT(*) FROM documentos
    WHERE estado <> 'eliminado' AND creado_en >= date_trunc('month', now())) AS documentos_mes,
  (SELECT AVG(tiempo_revision_seg)::int FROM revisiones
    WHERE finalizado_en >= date_trunc('month', now())) AS tiempo_medio_revision_seg,
  (SELECT COUNT(*) FROM auditoria
    WHERE evento = 'PAGINA_REESCANEADA' AND creado_en >= date_trunc('month', now())) AS paginas_reescaneadas,
  (SELECT COUNT(*) FROM auditoria
    WHERE evento = 'JG_ENVIADO' AND creado_en >= date_trunc('month', now())) AS jg_enviados,
  (SELECT COUNT(*) FROM documentos
    WHERE estado = 'exportado' AND exportado_en >= date_trunc('month', now())) AS exportados_mes,
  (SELECT COALESCE(json_object_agg(estado, n), '{}') FROM
     (SELECT estado, COUNT(*) AS n FROM documentos GROUP BY estado) e) AS documentos_por_estado;
