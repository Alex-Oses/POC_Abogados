-- MariaDB 11.4+ · equivalente de migrations/V3__create_documentos.sql
-- JSONB -> JSON (LONGTEXT + JSON_VALID en MariaDB); CHAR(64) ascii_bin para hashes.

CREATE TABLE documentos (
    id                  CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    nombre_original     VARCHAR(500) NOT NULL,
    hash_sha256         CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    mime_type           VARCHAR(100) NOT NULL,
    tamano_bytes        BIGINT NOT NULL,
    ruta_almacenamiento VARCHAR(1000) NOT NULL,
    estado              VARCHAR(50) NOT NULL DEFAULT 'pendiente',
    metadatos_extras    JSON NOT NULL DEFAULT '{}',
    creado_por          CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    creado_en           DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    actualizado_en      DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_documentos PRIMARY KEY (id),
    CONSTRAINT uq_documentos_hash UNIQUE (hash_sha256),
    CONSTRAINT chk_documentos_tamano CHECK (tamano_bytes > 0),
    CONSTRAINT documentos_estado_check CHECK (estado IN (
        'pendiente', 'ocr_procesando', 'ocr_completado',
        'anonimizando', 'en_revision', 'aprobado', 'rechazado', 'exportado'
    )),
    CONSTRAINT fk_documentos_creado_por FOREIGN KEY (creado_por)
        REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Documentos de entrada: PDF/imagen escaneada';
