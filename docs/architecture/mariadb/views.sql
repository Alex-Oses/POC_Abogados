-- MariaDB 11.4+ · equivalente de ../views.sql
-- Ejecutar DESPUÉS de las migraciones V1–V15 y de los índices.
-- Sin JOIN LATERAL: se sustituye por tablas derivadas con ROW_NUMBER().
-- Sin COUNT(*) FILTER: se sustituye por SUM(CASE WHEN ...).
-- Sin PERCENTILE_CONT: mediana calculada con ROW_NUMBER() sobre la propia muestra.

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
    vd.id                         AS version_id,
    vd.numero_version,
    vd.tipo_version,
    vd.contenido_texto,
    vd.contenido_html,
    vd.ruta_pdf,
    vd.motor_ocr,
    vd.modelo_ia,
    vd.confianza_layout_promedio,
    vd.metadatos_proceso,
    vd.version_creado_en,
    COALESCE(a.pendientes, 0)     AS entidades_pendientes_revision,
    COALESCE(a.confirmadas, 0)    AS entidades_confirmadas,
    COALESCE(a.total, 0)          AS entidades_total,
    r.estado                      AS revision_estado,
    r.numero_intento              AS revision_intento,
    r.finalizado_en               AS revision_finalizado_en,
    r.asignado_a                  AS revision_asignado_a
FROM documentos d
JOIN usuarios u ON u.id = d.creado_por
JOIN (
    SELECT id, documento_id, numero_version, tipo_version,
           contenido_texto, contenido_html, ruta_pdf, motor_ocr, modelo_ia,
           confianza_layout_promedio, metadatos_proceso,
           creado_en AS version_creado_en,
           ROW_NUMBER() OVER (PARTITION BY documento_id
                              ORDER BY numero_version DESC, id DESC) AS rn
      FROM versiones_documento
     WHERE es_actual
) vd ON vd.documento_id = d.id AND vd.rn = 1
LEFT JOIN (
    SELECT version_id,
           SUM(CASE WHEN accion_aplicada = 'pendiente_revision' THEN 1 ELSE 0 END) AS pendientes,
           SUM(CASE WHEN accion_aplicada IN ('tachado','pseudonimizado','eliminado','mantenido')
                    THEN 1 ELSE 0 END) AS confirmadas,
           COUNT(*) AS total
      FROM anotaciones_entidad
     GROUP BY version_id
) a ON a.version_id = vd.id
LEFT JOIN (
    SELECT version_id, estado, numero_intento, finalizado_en, asignado_a,
           ROW_NUMBER() OVER (PARTITION BY version_id
                              ORDER BY numero_intento DESC) AS rn
      FROM revisiones
) r ON r.version_id = vd.id AND r.rn = 1;

-- ============================================================
-- 2. Cola de trabajo del revisor (entidades pendientes)
-- ============================================================
CREATE OR REPLACE VIEW v_entidades_pendientes_revision AS
SELECT
    ae.id                         AS anotacion_id,
    ae.version_id,
    ae.bloque_id,
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
    bl.pagina_numero,
    ae.creado_en                  AS detectado_en,
    SUBSTRING(bl.contenido FROM GREATEST(1, ae.inicio_offset - 80) FOR 200) AS contexto_texto
FROM anotaciones_entidad ae
JOIN bloques_layout bl ON bl.id = ae.bloque_id
JOIN versiones_documento vd ON vd.id = ae.version_id
JOIN documentos d ON d.id = vd.documento_id
JOIN categorias_sensibles cs ON cs.id = ae.categoria_id
WHERE ae.accion_aplicada = 'pendiente_revision'
  AND d.estado IN ('en_revision', 'anonimizando')
ORDER BY
    cs.nivel_riesgo DESC,
    ae.confianza_deteccion ASC,
    d.creado_en ASC;

-- ============================================================
-- 3. Métricas por revisor (productividad, calidad)
-- ============================================================
CREATE OR REPLACE VIEW v_metricas_revisor AS
SELECT
    u.id                          AS revisor_id,
    CONCAT_WS(' ', u.nombre, u.apellidos) AS revisor_nombre,
    u.email                       AS revisor_email,
    COUNT(DISTINCT r.id)          AS revisiones_totales,
    COUNT(DISTINCT CASE WHEN r.estado = 'aprobado' THEN r.id END) AS revisiones_aprobadas,
    COUNT(DISTINCT CASE WHEN r.estado = 'rechazado_con_cambios' THEN r.id END) AS revisiones_rechazadas,
    AVG(r.tiempo_revision_seg)    AS tiempo_medio_seg,
    MAX(med.tiempo_mediano_seg)   AS tiempo_mediano_seg,
    COUNT(ae.id)                  AS entidades_revisadas,
    SUM(CASE WHEN ae.decision_revisor = 'confirmado' THEN 1 ELSE 0 END) AS entidades_confirmadas,
    SUM(CASE WHEN ae.decision_revisor = 'modificado' THEN 1 ELSE 0 END) AS entidades_modificadas,
    SUM(CASE WHEN ae.decision_revisor = 'falso_positivo' THEN 1 ELSE 0 END) AS falsos_positivos,
    SUM(CASE WHEN ae.decision_revisor = 'falso_negativo' THEN 1 ELSE 0 END) AS falsos_negativos,
    CASE WHEN COUNT(ae.id) > 0
         THEN ROUND(100.0 * SUM(CASE WHEN ae.decision_revisor = 'confirmado' THEN 1 ELSE 0 END)
                    / COUNT(ae.id), 1)
         ELSE 0 END               AS pct_confirmado,
    MAX(r.finalizado_en)          AS ultima_revision
FROM usuarios u
LEFT JOIN revisiones r ON r.asignado_a = u.id
LEFT JOIN anotaciones_entidad ae ON ae.revisado_por = u.id
LEFT JOIN (
    SELECT asignado_a, AVG(tiempo) AS tiempo_mediano_seg
      FROM (
        SELECT asignado_a,
               tiempo_revision_seg AS tiempo,
               ROW_NUMBER() OVER (PARTITION BY asignado_a ORDER BY tiempo_revision_seg) AS rn,
               COUNT(*) OVER (PARTITION BY asignado_a) AS cnt
          FROM revisiones
         WHERE tiempo_revision_seg IS NOT NULL
    ) x
     WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
     GROUP BY asignado_a
) med ON med.asignado_a = u.id
WHERE EXISTS (
    SELECT 1
      FROM usuarios_roles ur
     WHERE ur.usuario_id = u.id
       AND ur.rol = 'revisor'
) AND u.estado = 'activo'
GROUP BY u.id, u.nombre, u.apellidos, u.email
ORDER BY revisiones_totales DESC;

-- ============================================================
-- 4. Dashboard global: documentos por estado + tiempos
-- ============================================================
CREATE OR REPLACE VIEW v_dashboard_estados AS
SELECT
    estado,
    COUNT(*)                      AS total_documentos,
    AVG(TIMESTAMPDIFF(SECOND, creado_en, actualizado_en) / 3600) AS horas_media_estado,
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

-- ============================================================
-- 5. Detalle entidad para diff UI (antes/después)
-- ============================================================
CREATE OR REPLACE VIEW v_entidad_detalle_diff AS
SELECT
    ae.id,
    ae.version_id,
    ae.bloque_id,
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
    bl.contenido AS texto_bloque,
    bl.pagina_numero
FROM anotaciones_entidad ae
JOIN categorias_sensibles cs ON cs.id = ae.categoria_id
JOIN bloques_layout bl ON bl.id = ae.bloque_id;
