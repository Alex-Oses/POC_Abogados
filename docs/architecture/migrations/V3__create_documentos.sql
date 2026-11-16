-- Documentos de entrada: PDF/imagen escaneada

CREATE TABLE documentos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre_original     VARCHAR(500) NOT NULL,
    hash_sha256         CHAR(64) NOT NULL,
    mime_type           VARCHAR(100) NOT NULL,
    tamano_bytes        BIGINT NOT NULL CHECK (tamano_bytes > 0),
    ruta_almacenamiento VARCHAR(1000) NOT NULL,
    estado              VARCHAR(50) NOT NULL DEFAULT 'pendiente'
                        CHECK (estado IN (
                            'pendiente', 'ocr_procesando', 'ocr_completado',
                            'anonimizando', 'en_revision', 'aprobado', 'rechazado', 'exportado'
                        )),
    metadatos_extras    JSONB NOT NULL DEFAULT '{}',
    creado_por          UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uq_documentos_hash UNIQUE (hash_sha256)
);

COMMENT ON TABLE documentos IS 'Documentos fuente subidos al sistema';
COMMENT ON COLUMN documentos.hash_sha256 IS 'SHA-256 del binario original para deduplicación';
COMMENT ON COLUMN documentos.metadatos_extras IS 'JSON flexible: folio, juzgado, fecha_doc, tipo_procedimiento, etc.';
COMMENT ON COLUMN documentos.ruta_almacenamiento IS 'Ruta en S3/MinIO/FS: bucket/prefix/uuid.pdf';