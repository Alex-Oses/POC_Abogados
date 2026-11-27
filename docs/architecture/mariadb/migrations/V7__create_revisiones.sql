-- MariaDB 11.4+ · equivalente de migrations/V7__create_revisiones.sql
-- Las FK se nombran explícitamente: V15 las suelta por nombre.

CREATE TABLE revisiones (
    id                  CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    version_id          CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    revisor_id          CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    estado              VARCHAR(30) NOT NULL DEFAULT 'en_proceso',
    numero_intento      INT NOT NULL DEFAULT 1,
    tiempo_revision_seg INT,
    comentario_general  TEXT,
    creado_en           DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    finalizado_en       DATETIME(6),

    CONSTRAINT pk_revisiones PRIMARY KEY (id),
    CONSTRAINT revisiones_estado_check CHECK (estado IN (
        'en_proceso', 'aprobado', 'rechazado_con_cambios', 'devuelto'
    )),
    CONSTRAINT chk_revisiones_intento CHECK (numero_intento > 0),
    CONSTRAINT chk_revisiones_tiempo CHECK (tiempo_revision_seg >= 0),
    CONSTRAINT fk_revisiones_version FOREIGN KEY (version_id)
        REFERENCES versiones_documento (id) ON DELETE CASCADE,
    CONSTRAINT fk_revisiones_revisor FOREIGN KEY (revisor_id)
        REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Ciclos de revisión humana sobre versión anonimizada';
