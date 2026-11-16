-- Parámetros globales del sistema

CREATE TABLE configuracion_sistema (
    clave                   VARCHAR(100) PRIMARY KEY,
    valor                   JSONB NOT NULL,
    descripcion             TEXT,
    actualizado_por         UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE configuracion_sistema IS 'Settings globales versionados en JSONB';