-- MariaDB 11.4+ · equivalente de migrations/V6__create_anotaciones_entidad.sql
-- Los campos bbox_* legacy se conservan igual que en PostgreSQL (E-51, decisión de @Marina pendiente).

CREATE TABLE anotaciones_entidad (
    id                    CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    version_id            CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    categoria_id          CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    inicio_offset         INT NOT NULL,
    fin_offset            INT NOT NULL,
    texto_original        TEXT NOT NULL,
    pagina_numero         INT,
    bbox_x                DECIMAL(8,2),
    bbox_y                DECIMAL(8,2),
    bbox_ancho            DECIMAL(8,2),
    bbox_alto             DECIMAL(8,2),
    accion_aplicada       VARCHAR(30) NOT NULL
                          COMMENT 'tachado=████, pseudonimizado=[NOMBRE_1], eliminado="", mantenido=original, pendiente_revision=cola revisor',
    texto_sustitucion     VARCHAR(500)
                          COMMENT 'Texto que reemplaza al original en versión anonimizada',
    confianza_deteccion   DECIMAL(4,3) NOT NULL,
    motor_deteccion       VARCHAR(50) NOT NULL,
    revisado_por          CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    revisado_en           DATETIME(6),
    decision_revisor      VARCHAR(30)
                          COMMENT 'Trazabilidad: revisor confirma/cambia/rechaza detección IA',
    observaciones_revisor TEXT,
    creado_en             DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_anotaciones_entidad PRIMARY KEY (id),
    CONSTRAINT chk_anotaciones_inicio CHECK (inicio_offset >= 0),
    CONSTRAINT chk_anotaciones_fin CHECK (fin_offset > inicio_offset),
    CONSTRAINT chk_anotaciones_pagina CHECK (pagina_numero > 0),
    CONSTRAINT chk_anotaciones_confianza CHECK (confianza_deteccion BETWEEN 0 AND 1),
    CONSTRAINT anotaciones_entidad_accion_aplicada_check CHECK (accion_aplicada IN (
        'tachado', 'pseudonimizado', 'eliminado', 'mantenido', 'pendiente_revision'
    )),
    CONSTRAINT chk_anotaciones_decision CHECK (decision_revisor IN (
        'confirmado', 'modificado', 'falso_positivo', 'falso_negativo'
    )),
    CONSTRAINT fk_anotaciones_version FOREIGN KEY (version_id)
        REFERENCES versiones_documento (id) ON DELETE CASCADE,
    CONSTRAINT fk_anotaciones_categoria FOREIGN KEY (categoria_id)
        REFERENCES categorias_sensibles (id) ON DELETE RESTRICT,
    CONSTRAINT fk_anotaciones_revisado_por FOREIGN KEY (revisado_por)
        REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Línea a línea: qué se detectó, qué se hizo, quién lo validó';
