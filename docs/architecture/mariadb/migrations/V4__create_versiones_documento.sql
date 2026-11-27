-- MariaDB 11.4+ · equivalente de migrations/V4__create_versiones_documento.sql

CREATE TABLE versiones_documento (
    id                  CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    documento_id        CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    numero_version      INT NOT NULL,
    tipo_version        VARCHAR(30) NOT NULL,
    contenido_texto     TEXT,
    contenido_html      TEXT,
    ruta_pdf            VARCHAR(1000),
    motor_ocr           VARCHAR(50),
    modelo_ia           VARCHAR(100),
    confianza_promedio  DECIMAL(4,3),
    metadatos_proceso   JSON NOT NULL DEFAULT '{}',
    creado_por          CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    creado_en           DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_versiones_documento PRIMARY KEY (id),
    CONSTRAINT uq_version_documento UNIQUE (documento_id, numero_version),
    CONSTRAINT chk_versiones_numero CHECK (numero_version > 0),
    CONSTRAINT chk_versiones_tipo CHECK (tipo_version IN (
        'original', 'ocr_texto', 'anonimizado_ia', 'revisado_humano', 'final_aprobado'
    )),
    CONSTRAINT chk_versiones_confianza CHECK (confianza_promedio BETWEEN 0 AND 1),
    CONSTRAINT fk_versiones_documento_documento FOREIGN KEY (documento_id)
        REFERENCES documentos (id) ON DELETE CASCADE,
    CONSTRAINT fk_versiones_creado_por FOREIGN KEY (creado_por)
        REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Historial de versiones: original → OCR → anonimizado → revisado → final';
