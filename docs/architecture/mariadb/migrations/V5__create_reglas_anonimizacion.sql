-- MariaDB 11.4+ · equivalente de migrations/V5__create_reglas_anonimizacion.sql

CREATE TABLE reglas_anonimizacion (
    id                CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    codigo            VARCHAR(50) NOT NULL,
    nombre            VARCHAR(200) NOT NULL,
    descripcion       TEXT,
    configuracion     JSON NOT NULL
                      COMMENT 'Ej: {"entidades_obligatorias":["DNI_NIE","NOMBRE_PERSONA"],"accion_por_defecto":"tachar","umbral_confianza":0.85,"excepciones":{"NOMBRE_PERSONA":["juez","fiscal"]}}',
    version           INT NOT NULL DEFAULT 1,
    activa            BOOLEAN NOT NULL DEFAULT true,
    creado_por        CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    creado_en         DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    actualizado_en    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_reglas_anonimizacion PRIMARY KEY (id),
    CONSTRAINT uq_reglas_codigo UNIQUE (codigo),
    CONSTRAINT chk_reglas_version CHECK (version > 0),
    CONSTRAINT fk_reglas_creado_por FOREIGN KEY (creado_por)
        REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Perfiles de anonimización por ámbito jurídico';
