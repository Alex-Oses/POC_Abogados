-- Reglas configurables por tipo de materia (Civil, Penal, Menores, RGPD, etc.)

CREATE TABLE reglas_anonimizacion (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo              VARCHAR(50) NOT NULL UNIQUE,
    nombre              VARCHAR(200) NOT NULL,
    descripcion         TEXT,
    configuracion       JSONB NOT NULL,
    version             INT NOT NULL DEFAULT 1 CHECK (version > 0),
    activa              BOOLEAN NOT NULL DEFAULT true,
    creado_por          UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE reglas_anonimizacion IS 'Perfiles de anonimización por ámbito jurídico';
COMMENT ON COLUMN reglas_anonimizacion.configuracion IS 'Ej: {"entidades_obligatorias":["DNI_NIE","NOMBRE_PERSONA"],"accion_por_defecto":"tachar","umbral_confianza":0.85,"excepciones":{"NOMBRE_PERSONA":["juez","fiscal"]}}';