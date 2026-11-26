-- MariaDB 11.4+ · equivalente de migrations/V8__create_auditoria.sql
-- BIGSERIAL -> BIGINT AUTO_INCREMENT; INET -> VARCHAR(45); JSONB -> JSON.
-- La PK sigue siendo solo (id), igual que en PostgreSQL; partitioning.sql la recrea
-- como (id, creado_en) y retira la FK porque InnoDB no admite FK en tablas particionadas.

CREATE TABLE auditoria (
    id            BIGINT NOT NULL AUTO_INCREMENT,
    evento        VARCHAR(100) NOT NULL
                  COMMENT 'DOCUMENTO_SUBIDO, OCR_COMPLETADO, ANONIMIZACION_IA, ENTIDAD_MODIFICADA, REVISION_APROBADA, PDF_EXPORTADO, USUARIO_CREADO, REGLA_CAMBIADA',
    entidad_tipo  VARCHAR(50),
    entidad_id    CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    usuario_id    CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    ip_origen     VARCHAR(45) CHARACTER SET ascii COLLATE ascii_bin,
    user_agent    TEXT,
    detalle       JSON NOT NULL
                  COMMENT 'JSON con antes/después, parámetros, contexto completo',
    hash_anterior CHAR(64) CHARACTER SET ascii COLLATE ascii_bin
                  COMMENT 'SHA-256(row_anterior) para cadena de custodia inmutable',
    creado_en     DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_auditoria PRIMARY KEY (id),
    CONSTRAINT fk_auditoria_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Registro inmutable de todas las acciones (legal compliance)';
