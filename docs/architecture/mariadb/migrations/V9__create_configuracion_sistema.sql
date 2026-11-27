-- MariaDB 11.4+ · equivalente de migrations/V9__create_configuracion_sistema.sql

CREATE TABLE configuracion_sistema (
    clave             VARCHAR(100) NOT NULL,
    valor             JSON NOT NULL,
    descripcion       TEXT,
    actualizado_por   CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    actualizado_en    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_configuracion_sistema PRIMARY KEY (clave),
    CONSTRAINT fk_configuracion_actualizado_por FOREIGN KEY (actualizado_por)
        REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Settings globales versionados en JSON';
