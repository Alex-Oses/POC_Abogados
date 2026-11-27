-- MariaDB 11.4+ · equivalente de migrations/V2__create_categorias_sensibles.sql

CREATE TABLE categorias_sensibles (
    id            CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    codigo        VARCHAR(50) NOT NULL,
    nombre        VARCHAR(150) NOT NULL,
    descripcion   TEXT,
    regex_patron  VARCHAR(500)
                  COMMENT 'Regex opcional para validación rápida post-detección',
    nivel_riesgo  VARCHAR(20) NOT NULL,
    rgpd_especial BOOLEAN NOT NULL DEFAULT false
                  COMMENT 'TRUE = Categoría especial Art. 9 RGPD (salud, origen racial, genéticos, etc.)',
    activa        BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT pk_categorias_sensibles PRIMARY KEY (id),
    CONSTRAINT uq_categorias_codigo UNIQUE (codigo),
    CONSTRAINT chk_categorias_nivel_riesgo CHECK (nivel_riesgo IN ('alto', 'medio', 'bajo'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Catálogo maestro de entidades sensibles detectables';
