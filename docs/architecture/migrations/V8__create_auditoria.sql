-- Log inmutable encadenado (hash_anterior) para trazabilidad legal

CREATE TABLE auditoria (
    id                      BIGSERIAL PRIMARY KEY,
    evento                  VARCHAR(100) NOT NULL,
    entidad_tipo            VARCHAR(50),
    entidad_id              UUID,
    usuario_id              UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    ip_origen               INET,
    user_agent              TEXT,
    detalle                 JSONB NOT NULL,
    hash_anterior           CHAR(64),
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Particionado por mes (requiere PostgreSQL 11+)
-- Se crean particiones automáticamente via pg_partman o script mensual
-- CREATE TABLE auditoria_2026_01 PARTITION OF auditoria FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

COMMENT ON TABLE auditoria IS 'Registro inmutable de todas las acciones (legal compliance)';
COMMENT ON COLUMN auditoria.evento IS 'DOCUMENTO_SUBIDO, OCR_COMPLETADO, ANONIMIZACION_IA, ENTIDAD_MODIFICADA, REVISION_APROBADA, PDF_EXPORTADO, USUARIO_CREADO, REGLA_CAMBIADA';
COMMENT ON COLUMN auditoria.hash_anterior IS 'SHA-256(row_anterior) para cadena de custodia inmutable';
COMMENT ON COLUMN auditoria.detalle IS 'JSON con antes/después, parámetros, contexto completo';