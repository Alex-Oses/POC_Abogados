-- views.sql
-- Vistas listas para consumo por API (Backend/Frontend)
-- Ejecutar DESPUÉS de V10__create_indexes.sql

-- ============================================================
-- 1. Documento con su versión actual + métricas rápidas
-- ============================================================
CREATE OR REPLACE VIEW v_documento_actual AS
SELECT
    d.id                          AS documento_id,
    d.nombre_original,
    d.hash_sha256,
    d.mime_type,
    d.tamano_bytes,
    d.estado                      AS documento_estado,
    d.metadatos_extras,
    d.creado_en                   AS documento_creado_en,
    d.creado_por                  AS documento_creado_por,
    u.email                       AS creado_por_email,
    -- Versión actual (la más alta)
    vd.id                         AS version_id,
    vd.numero_version,
    vd.tipo_version,
    vd.contenido_texto,
    vd.contenido_html,
    vd.ruta_pdf,
    vd.motor_ocr,
    vd.modelo_ia,
    vd.confianza_promedio,
    vd.metadatos_proceso,
    vd.creado_en                  AS version_creado_en,
    -- Conteos para UI
    COALESCE(a.pendientes, 0)     AS entidades_pendientes_revision,
    COALESCE(a.confirmadas, 0)    AS entidades_confirmadas,
    COALESCE(a.total, 0)          AS entidades_total,
    -- Última revisión
    r.estado                      AS revision_estado,
    r.numero_intento              AS revision_intento,
    r.finalizado_en               AS revision_finalizado_en,
    r.asignado_a                  AS revision_asignado_a
FROM documentos d
JOIN usuarios u ON u.id = d.creado_por
JOIN LATERAL (
    SELECT *
    FROM versiones_documento vd2
    WHERE vd2.documento_id = d.id
    ORDER BY vd2.numero_version DESC
    LIMIT 1
) vd ON true
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) FILTER (WHERE accion_aplicada = 'pendiente_revision') AS pendientes,
        COUNT(*) FILTER (WHERE accion_aplicada IN ('tachado','pseudonimizado','eliminado','mantenido')) AS confirmadas,
        COUNT(*) AS total
    FROM anotaciones_entidad ae
    WHERE ae.version_id = vd.id
) a ON true
LEFT JOIN LATERAL (
    SELECT *
    FROM revisiones r2
    WHERE r2.version_id = vd.id
    ORDER BY r2.numero_intento DESC
    LIMIT 1
) r ON true;

COMMENT ON VIEW v_documento_actual IS 'Documento + versión actual + conteo entidades + última revisión (para listado y detalle)';


-- ============================================================
-- 2. Cola de trabajo del revisor (entidades pendientes)
-- ============================================================
CREATE OR REPLACE VIEW v_entidades_pendientes_revision AS
SELECT
    ae.id                         AS anotacion_id,
    ae.version_id,
    vd.documento_id,
    d.nombre_original             AS documento_nombre,
    d.estado                      AS documento_estado,
    ae.categoria_id,
    cs.codigo                     AS categoria_codigo,
    cs.nombre                     AS categoria_nombre,
    cs.nivel_riesgo               AS categoria_riesgo,
    cs.rgpd_especial              AS categoria_rgpd_especial,
    ae.inicio_offset,
    ae.fin_offset,
    ae.texto_original,
    ae.texto_sustitucion,
    ae.confianza_deteccion,
    ae.motor_deteccion,
    ae.pagina_numero,
    ae.bbox_x, ae.bbox_y, ae.bbox_ancho, ae.bbox_alto,
    ae.creado_en                  AS detectado_en,
    -- Contexto para UI (snippet alrededor)
    SUBSTRING(vd.contenido_texto FROM GREATEST(1, ae.inicio_offset - 80) FOR 200) AS contexto_texto
FROM anotaciones_entidad ae
JOIN versiones_documento vd ON vd.id = ae.version_id
JOIN documentos d ON d.id = vd.documento_id
JOIN categorias_sensibles cs ON cs.id = ae.categoria_id
WHERE ae.accion_aplicada = 'pendiente_revision'
  AND d.estado IN ('en_revision', 'anonimizando')
ORDER BY
    cs.nivel_riesgo DESC,          -- Alto riesgo primero
    ae.confianza_deteccion ASC,    -- Menor confianza primero (más dudosas)
    d.creado_en ASC;               -- FIFO

COMMENT ON VIEW v_entidades_pendientes_revision IS 'Cola priorizada para el revisor: riesgo alto + baja confianza + antigüedad';


-- ============================================================
-- 3. Métricas por revisor (productividad, calidad)
-- ============================================================
CREATE OR REPLACE VIEW v_metricas_revisor AS
SELECT
    u.id                          AS revisor_id,
    u.nombre_completo             AS revisor_nombre,
    u.email                       AS revisor_email,
    COUNT(DISTINCT r.id)          AS revisiones_totales,
    COUNT(DISTINCT r.id) FILTER (WHERE r.estado = 'aprobado') AS revisiones_aprobadas,
    COUNT(DISTINCT r.id) FILTER (WHERE r.estado = 'rechazado_con_cambios') AS revisiones_rechazadas,
    AVG(r.tiempo_revision_seg)    AS tiempo_medio_seg,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY r.tiempo_revision_seg) AS tiempo_mediano_seg,
    -- Entidades procesadas
    COUNT(ae.id)                  AS entidades_revisadas,
    COUNT(ae.id) FILTER (WHERE ae.decision_revisor = 'confirmado') AS entidades_confirmadas,
    COUNT(ae.id) FILTER (WHERE ae.decision_revisor = 'modificado') AS entidades_modificadas,
    COUNT(ae.id) FILTER (WHERE ae.decision_revisor = 'falso_positivo') AS falsos_positivos,
    COUNT(ae.id) FILTER (WHERE ae.decision_revisor = 'falso_negativo') AS falsos_negativos,
    -- Calidad
    CASE WHEN COUNT(ae.id) > 0
         THEN ROUND(100.0 * COUNT(ae.id) FILTER (WHERE ae.decision_revisor = 'confirmado') / COUNT(ae.id), 1)
         ELSE 0 END               AS pct_confirmado,
    MAX(r.finalizado_en)          AS ultima_revision
FROM usuarios u
LEFT JOIN revisiones r ON r.asignado_a = u.id
LEFT JOIN anotaciones_entidad ae ON ae.revisado_por = u.id
WHERE EXISTS (
    SELECT 1
    FROM usuarios_roles ur
    WHERE ur.usuario_id = u.id
      AND ur.rol = 'revisor'
) AND u.estado = 'activo'
GROUP BY u.id, u.nombre_completo, u.email
ORDER BY revisiones_totales DESC;

COMMENT ON VIEW v_metricas_revisor IS 'KPIs por revisor: volumen, velocidad, calidad (para dashboard supervisor)';


-- ============================================================
-- 4. Dashboard global: documentos por estado + tiempos
-- ============================================================
CREATE OR REPLACE VIEW v_dashboard_estados AS
SELECT
    estado,
    COUNT(*)                      AS total_documentos,
    AVG(EXTRACT(EPOCH FROM (actualizado_en - creado_en))/3600) AS horas_media_estado,
    MIN(creado_en)                AS mas_antiguo,
    MAX(creado_en)                AS mas_reciente
FROM documentos
GROUP BY estado
ORDER BY
    CASE estado
        WHEN 'pendiente' THEN 1
        WHEN 'ocr_procesando' THEN 2
        WHEN 'ocr_completado' THEN 3
        WHEN 'anonimizando' THEN 4
        WHEN 'en_revision' THEN 5
        WHEN 'aprobado' THEN 6
        WHEN 'rechazado' THEN 7
        WHEN 'exportado' THEN 8
        ELSE 9 END;

COMMENT ON VIEW v_dashboard_estados IS 'Resumen global para panel admin: cuellos de botella por estado';


-- ============================================================
-- 5. Detalle entidad para diff UI (antes/después)
-- ============================================================
CREATE OR REPLACE VIEW v_entidad_detalle_diff AS
SELECT
    ae.id,
    ae.version_id,
    ae.categoria_id,
    cs.codigo AS categoria_codigo,
    cs.nombre AS categoria_nombre,
    ae.inicio_offset,
    ae.fin_offset,
    ae.texto_original,
    ae.texto_sustitucion,
    ae.accion_aplicada,
    ae.confianza_deteccion,
    ae.motor_deteccion,
    ae.revisado_por,
    ae.revisado_en,
    ae.decision_revisor,
    ae.observaciones_revisor,
    -- Versión original (tipo_version='ocr_texto') para comparar
    v_orig.contenido_texto AS texto_original_completo,
    v_orig.numero_version AS version_ocr_numero
FROM anotaciones_entidad ae
JOIN categorias_sensibles cs ON cs.id = ae.categoria_id
JOIN versiones_documento vd ON vd.id = ae.version_id
JOIN LATERAL (
    SELECT contenido_texto, numero_version
    FROM versiones_documento v2
    WHERE v2.documento_id = vd.documento_id
      AND v2.tipo_version = 'ocr_texto'
    ORDER BY v2.numero_version DESC
    LIMIT 1
) v_orig ON true;

COMMENT ON VIEW v_entidad_detalle_diff IS 'Para componente UI diff: muestra entidad con texto OCR original completo';
