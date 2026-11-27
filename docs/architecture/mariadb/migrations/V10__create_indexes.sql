-- MariaDB 11.4+ · equivalente de migrations/V10__create_indexes.sql
-- MariaDB no tiene índices parciales ni de expresión: los sustituimos por columnas
-- generadas PERSISTENT que valen NULL para las filas excluidas (los B-tree no indexan NULL).
-- El nombre de la columna generada entra en la consulta para que el optimizador la use.

CREATE INDEX idx_usuarios_rol_activo ON usuarios (rol, activo);

CREATE INDEX idx_documentos_estado ON documentos (estado);
CREATE INDEX idx_documentos_creado_por ON documentos (creado_por);
CREATE INDEX idx_documentos_creado_en ON documentos (creado_en DESC);

CREATE INDEX idx_versiones_documento_tipo ON versiones_documento (tipo_version);
CREATE INDEX idx_versiones_documento_creado_en ON versiones_documento (creado_en DESC);

CREATE INDEX idx_anotaciones_version ON anotaciones_entidad (version_id);
CREATE INDEX idx_anotaciones_categoria ON anotaciones_entidad (categoria_id);
CREATE INDEX idx_anotaciones_accion ON anotaciones_entidad (accion_aplicada);

ALTER TABLE anotaciones_entidad
    ADD COLUMN idx_pendientes_key VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin
        AS (IF(accion_aplicada = 'pendiente_revision', accion_aplicada, NULL)) PERSISTENT,
    ADD COLUMN idx_revisado_key CHAR(36) CHARACTER SET ascii COLLATE ascii_bin
        AS (IF(revisado_por IS NOT NULL, revisado_por, NULL)) PERSISTENT,
    ADD INDEX idx_anotaciones_pendientes (version_id, categoria_id, idx_pendientes_key),
    ADD INDEX idx_anotaciones_revisado_por (idx_revisado_key);

CREATE INDEX idx_revisiones_version ON revisiones (version_id);
CREATE INDEX idx_revisiones_revisor_estado ON revisiones (revisor_id, estado);
CREATE INDEX idx_revisiones_creado_en ON revisiones (creado_en DESC);

CREATE INDEX idx_auditoria_entidad ON auditoria (entidad_tipo, entidad_id);
CREATE INDEX idx_auditoria_usuario_fecha ON auditoria (usuario_id, creado_en DESC);
CREATE INDEX idx_auditoria_evento_fecha ON auditoria (evento, creado_en DESC);

ALTER TABLE reglas_anonimizacion
    ADD COLUMN activa_idx TINYINT(1)
        AS (IF(activa, 1, NULL)) PERSISTENT,
    ADD INDEX idx_reglas_activa (activa_idx);
