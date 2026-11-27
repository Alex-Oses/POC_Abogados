-- MariaDB 11.4+ · equivalente de migrations/V14__create_bloques_layout.sql
-- Sin V13 ni V16, igual que en PostgreSQL; el índice parcial se sustituye por columna generada.

CREATE TABLE paginas_documento (
    id            CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    documento_id  CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    numero        INT NOT NULL,
    contraste     INT,
    estado        VARCHAR(20) NOT NULL DEFAULT 'ok',
    avisos        JSON NOT NULL DEFAULT '[]',
    leida_ocr     BOOLEAN NOT NULL DEFAULT false,
    creado_en     DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_paginas_documento PRIMARY KEY (id),
    CONSTRAINT uq_paginas_documento_numero UNIQUE (documento_id, numero),
    CONSTRAINT chk_paginas_numero CHECK (numero > 0),
    CONSTRAINT chk_paginas_contraste CHECK (contraste BETWEEN 0 AND 100),
    CONSTRAINT paginas_documento_estado_check CHECK (estado IN ('ok', 'revisar', 'ilegible')),
    CONSTRAINT fk_paginas_documento FOREIGN KEY (documento_id)
        REFERENCES documentos (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Una fila por página física: contraste medido y semáforo de calidad';

ALTER TABLE paginas_documento
    ADD COLUMN estado_idx VARCHAR(20)
        AS (IF(estado <> 'ok', estado, NULL)) PERSISTENT,
    ADD INDEX idx_paginas_documento_estado (documento_id, estado_idx);

ALTER TABLE documentos
    ADD COLUMN num_paginas INT
        COMMENT 'Páginas del fichero; lo devuelven POST /transform/document, GET /documents y GET /documents/{id}',
    ADD CONSTRAINT chk_documentos_num_paginas CHECK (num_paginas > 0);

CREATE TABLE bloques_layout (
    id                CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    version_id        CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    pagina_numero     INT NOT NULL,
    orden_lectura     INT NOT NULL,
    etiqueta          VARCHAR(40) NOT NULL,
    confianza         DECIMAL(4,3),
    forma             VARCHAR(10) NOT NULL DEFAULT 'rect',
    bbox_x            DECIMAL(10,2) NOT NULL,
    bbox_y            DECIMAL(10,2) NOT NULL,
    bbox_ancho        DECIMAL(10,2) NOT NULL,
    bbox_alto         DECIMAL(10,2) NOT NULL,
    pagina_ancho      DECIMAL(10,2) NOT NULL,
    pagina_alto       DECIMAL(10,2) NOT NULL,
    puntos            JSON,
    contenido         TEXT NOT NULL DEFAULT '',
    calidad_semaforo  VARCHAR(10),
    creado_en         DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_bloques_layout PRIMARY KEY (id),
    CONSTRAINT uq_bloques_layout_orden UNIQUE (version_id, pagina_numero, orden_lectura),
    CONSTRAINT chk_bloques_pagina CHECK (pagina_numero > 0),
    CONSTRAINT chk_bloques_orden CHECK (orden_lectura >= 0),
    CONSTRAINT chk_bloques_confianza CHECK (confianza BETWEEN 0 AND 1),
    CONSTRAINT bloques_layout_forma_check CHECK (forma IN ('rect', 'quad', 'poly')),
    CONSTRAINT chk_bloques_bbox_x CHECK (bbox_x >= 0),
    CONSTRAINT chk_bloques_bbox_y CHECK (bbox_y >= 0),
    CONSTRAINT chk_bloques_bbox_ancho CHECK (bbox_ancho > 0),
    CONSTRAINT chk_bloques_bbox_alto CHECK (bbox_alto > 0),
    CONSTRAINT chk_bloques_pagina_ancho CHECK (pagina_ancho > 0),
    CONSTRAINT chk_bloques_pagina_alto CHECK (pagina_alto > 0),
    CONSTRAINT chk_bloques_puntos CHECK (forma = 'rect' OR puntos IS NOT NULL),
    CONSTRAINT bloques_layout_semaforo_check CHECK (calidad_semaforo IN ('verde', 'amarillo', 'rojo')),
    CONSTRAINT fk_bloques_version FOREIGN KEY (version_id)
        REFERENCES versiones_documento (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Bloques del layout por versión: offsets de anotaciones, visor y reconstrucción del PDF';
