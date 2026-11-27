-- MariaDB 11.4+ · equivalente de migrations/V15__flujo_revision_y_export.sql
-- No hay V13 ni V16. Los índices parciales de PostgreSQL se implementan con columnas
-- generadas PERSISTENT (NULL = fila excluida); las FK se sueltan por nombre, no por
-- CONSTRAINT genérico, porque MariaDB distingue DROP CHECK / DROP INDEX / DROP FOREIGN KEY.

-- ---------------------------------------------------------------------------
-- 1. documentos: estados nuevos y doble firma (A-15, A-19, A-21)
-- ---------------------------------------------------------------------------
ALTER TABLE documentos DROP CHECK documentos_estado_check;

ALTER TABLE documentos ADD CONSTRAINT documentos_estado_check CHECK (estado IN (
    'pendiente', 'ocr_procesando', 'ocr_completado', 'anonimizando',
    'en_revision', 'aprobado', 'rechazado', 'pendiente_visto_bueno',
    'exportado', 'eliminado'
));

ALTER TABLE documentos
    ADD COLUMN requiere_visto_bueno BOOLEAN NOT NULL DEFAULT false
        COMMENT 'A-15: se calcula al cerrar la revisión y se persiste; no se recalcula después',
    ADD COLUMN visto_bueno_por CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    ADD COLUMN visto_bueno_en DATETIME(6),
    ADD COLUMN cerrado_en DATETIME(6),
    ADD COLUMN eliminado_en DATETIME(6),
    ADD COLUMN exportado_en DATETIME(6),
    ADD COLUMN clave_cifrado VARCHAR(100);

ALTER TABLE documentos
    ADD CONSTRAINT fk_documentos_visto_bueno_por FOREIGN KEY (visto_bueno_por)
        REFERENCES usuarios (id) ON DELETE SET NULL;

-- El único pasa a ser por creador y excluye lo borrado lógicamente.
ALTER TABLE documentos DROP INDEX uq_documentos_hash;

ALTER TABLE documentos
    ADD COLUMN hash_activo_key CHAR(64) CHARACTER SET ascii COLLATE ascii_bin
        AS (IF(estado <> 'eliminado', hash_sha256, NULL)) PERSISTENT,
    ADD UNIQUE INDEX uq_documentos_hash_creador (creado_por, hash_activo_key);

-- ---------------------------------------------------------------------------
-- 2. revisiones: cola sin dueño (A-05) y cierre optimista (A-23)
-- ---------------------------------------------------------------------------
-- Se suelta la FK antes de cambiar la nulabilidad de la columna renombrada.
ALTER TABLE revisiones DROP FOREIGN KEY fk_revisiones_revisor;
ALTER TABLE revisiones RENAME COLUMN revisor_id TO asignado_a;
ALTER TABLE revisiones
    MODIFY COLUMN asignado_a CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NULL;
ALTER TABLE revisiones
    ADD CONSTRAINT fk_revisiones_asignado FOREIGN KEY (asignado_a)
        REFERENCES usuarios (id) ON DELETE RESTRICT;

ALTER TABLE revisiones DROP CHECK revisiones_estado_check;
ALTER TABLE revisiones
    MODIFY COLUMN estado VARCHAR(30) NOT NULL DEFAULT 'en_cola';
ALTER TABLE revisiones ADD CONSTRAINT revisiones_estado_check CHECK (estado IN (
    'en_cola', 'en_proceso', 'aprobado', 'rechazado_con_cambios', 'devuelto'
));

ALTER TABLE revisiones
    ADD COLUMN documento_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    ADD COLUMN asignado_en DATETIME(6),
    ADD COLUMN fecha_limite DATETIME(6),
    ADD COLUMN aviso_24h_enviado_en DATETIME(6),
    ADD COLUMN actualizado_en DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6);

-- Relleno para un clon con datos: la revisión hereda el documento de su versión.
UPDATE revisiones r
    JOIN versiones_documento v ON v.id = r.version_id
   SET r.documento_id = v.documento_id
 WHERE r.documento_id IS NULL;

ALTER TABLE revisiones
    MODIFY COLUMN documento_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL;

ALTER TABLE revisiones
    ADD CONSTRAINT uq_revisiones_version_intento UNIQUE (version_id, numero_intento);
ALTER TABLE versiones_documento
    ADD CONSTRAINT uq_versiones_documento_id UNIQUE (id, documento_id);

ALTER TABLE revisiones DROP FOREIGN KEY fk_revisiones_version;
ALTER TABLE revisiones
    ADD CONSTRAINT fk_revisiones_version_documento
    FOREIGN KEY (version_id, documento_id)
    REFERENCES versiones_documento (id, documento_id)
    ON DELETE CASCADE;

-- A-04: una sola revisión abierta por DOCUMENTO (índice parcial -> columna generada).
ALTER TABLE revisiones
    ADD COLUMN abierta_key VARCHAR(10) CHARACTER SET ascii COLLATE ascii_bin
        AS (IF(estado IN ('en_cola', 'en_proceso'), 'ABIERTA', NULL)) PERSISTENT,
    ADD COLUMN plazo_key DATETIME(6)
        AS (IF(estado IN ('en_cola', 'en_proceso'), fecha_limite, NULL)) PERSISTENT,
    ADD UNIQUE INDEX uq_revisiones_abierta_por_documento (documento_id, abierta_key),
    ADD INDEX idx_revisiones_plazo (plazo_key);

ALTER TABLE revisiones
    RENAME INDEX idx_revisiones_revisor_estado TO idx_revisiones_asignado_estado;

-- ---------------------------------------------------------------------------
-- 3. anotaciones: una sola base de offsets (B3)
-- ---------------------------------------------------------------------------
ALTER TABLE anotaciones_entidad
    ADD COLUMN bloque_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin;

ALTER TABLE bloques_layout
    ADD CONSTRAINT uq_bloques_layout_id_version UNIQUE (id, version_id);

ALTER TABLE anotaciones_entidad
    ADD CONSTRAINT fk_anotaciones_bloque_version
    FOREIGN KEY (bloque_id, version_id)
    REFERENCES bloques_layout (id, version_id)
    ON DELETE CASCADE;

ALTER TABLE anotaciones_entidad DROP CHECK anotaciones_entidad_accion_aplicada_check;
ALTER TABLE anotaciones_entidad ADD CONSTRAINT anotaciones_entidad_accion_aplicada_check
    CHECK (accion_aplicada IN (
        'censurar', 'etiqueta', 'iniciales', 'pseudonimizado',
        'eliminado', 'mantenido', 'tachado', 'pendiente_revision'
    ));

ALTER TABLE anotaciones_entidad
    ADD COLUMN bloque_idx CHAR(36) CHARACTER SET ascii COLLATE ascii_bin
        AS (IF(bloque_id IS NOT NULL, bloque_id, NULL)) PERSISTENT,
    ADD INDEX idx_anotaciones_bloque (bloque_idx);

-- ---------------------------------------------------------------------------
-- 4. categorias_sensibles.prioridad (contrato §7)
-- ---------------------------------------------------------------------------
ALTER TABLE categorias_sensibles
    ADD COLUMN prioridad INT NOT NULL DEFAULT 100
        COMMENT 'Menor = se aplica antes cuando dos categorías solapan. 100 = sin preferencia';

-- ---------------------------------------------------------------------------
-- 5. Seeds corregidos (H6, H8) y claves de A-20
-- ---------------------------------------------------------------------------
UPDATE categorias_sensibles SET rgpd_especial = false WHERE codigo = 'NUSS';

UPDATE configuracion_sistema
   SET valor = '["paddleocr-vl"]'
 WHERE clave = 'motores_ocr_disponibles';

UPDATE configuracion_sistema
   SET valor = 'false'
 WHERE clave = 'preservar_formato_pdf';

UPDATE configuracion_sistema
   SET valor = '"censurar"',
       descripcion = 'Acción por defecto: censurar|etiqueta|iniciales|pseudonimizado|eliminado'
 WHERE clave = 'accion_por_defecto';

DELETE FROM configuracion_sistema WHERE clave = 'tiempo_max_revision_minutos';

UPDATE configuracion_sistema SET valor = '15' WHERE clave = 'version_esquema_bd';

INSERT IGNORE INTO configuracion_sistema (clave, valor, descripcion) VALUES
    ('revision_plazo_horas', '48',
     'A-20: horas laborables para cerrar una revisión'),
    ('revision_aviso_horas', '24',
     'A-20: horas laborables antes del aviso al revisor y, si sigue en cola, al supervisor'),
    ('calendario_laboral',
     '{"lunes_a_viernes": "09:00-18:00", "festivos": []}',
     'A-20: horario laboral y festivos ISO (YYYY-MM-DD). Vacío = no se descuenta ningún festivo');

-- ---------------------------------------------------------------------------
-- 6. Identidad y sesiones (0012, 0015; B1)
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_metricas_revisor;
DROP TRIGGER IF EXISTS trg_revision_validar_revisor;
ALTER TABLE usuarios DROP CHECK chk_usuarios_rol;
ALTER TABLE usuarios DROP INDEX idx_usuarios_rol_activo;
ALTER TABLE usuarios DROP COLUMN rol;

CREATE TABLE usuarios_roles (
    usuario_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    rol        VARCHAR(50) NOT NULL,
    CONSTRAINT pk_usuarios_roles PRIMARY KEY (usuario_id, rol),
    CONSTRAINT usuarios_roles_rol_check CHECK (rol IN ('transcriptor', 'revisor', 'admin')),
    CONSTRAINT fk_usuarios_roles_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE usuarios DROP COLUMN activo;
ALTER TABLE usuarios
    ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    ADD COLUMN motivo_baja TEXT,
    ADD COLUMN eliminado_en DATETIME(6),
    ADD COLUMN sso_subject VARCHAR(255),
    ADD COLUMN password_hash TEXT,
    ADD CONSTRAINT usuarios_estado_check CHECK (estado IN ('activo', 'bloqueado', 'baja')),
    ADD CONSTRAINT uq_usuarios_sso_subject UNIQUE (sso_subject);

ALTER TABLE usuarios DROP INDEX uq_usuarios_email;
ALTER TABLE usuarios
    ADD COLUMN email_lower VARCHAR(255) AS (LOWER(email)) PERSISTENT;
CREATE UNIQUE INDEX uq_usuarios_email_lower ON usuarios (email_lower);

CREATE INDEX idx_usuarios_estado ON usuarios (estado);
CREATE INDEX idx_usuarios_roles_rol ON usuarios_roles (rol);

CREATE TABLE sesiones_usuario (
    id            CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    usuario_id    CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    token_hash    CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'SHA-256 del token opaco',
    creado_en     DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    expira_en     DATETIME(6) NOT NULL,
    ultimo_uso_en DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    revocado_en   DATETIME(6),
    ip_origen     VARCHAR(45) CHARACTER SET ascii COLLATE ascii_bin,
    user_agent    TEXT,

    CONSTRAINT pk_sesiones_usuario PRIMARY KEY (id),
    CONSTRAINT uq_sesiones_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_sesiones_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_sesiones_usuario_usuario
    ON sesiones_usuario (usuario_id, creado_en DESC);

-- ---------------------------------------------------------------------------
-- 7. Campos y relaciones del modelo entidad-relación vigente
-- ---------------------------------------------------------------------------
ALTER TABLE usuarios RENAME COLUMN nombre_completo TO nombre;
ALTER TABLE usuarios ADD COLUMN apellidos VARCHAR(200) NOT NULL DEFAULT '';

ALTER TABLE versiones_documento
    RENAME COLUMN confianza_promedio TO confianza_layout_promedio;
ALTER TABLE versiones_documento
    ADD COLUMN pipeline_version VARCHAR(100),
    ADD COLUMN regla_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    ADD COLUMN es_actual BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE versiones_documento
    ADD CONSTRAINT fk_versiones_regla FOREIGN KEY (regla_id)
        REFERENCES reglas_anonimizacion (id) ON DELETE SET NULL;

UPDATE versiones_documento v
    JOIN (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY documento_id ORDER BY numero_version DESC) AS posicion
          FROM versiones_documento
    ) u ON u.id = v.id AND u.posicion = 1
   SET v.es_actual = true;

ALTER TABLE versiones_documento
    ADD COLUMN es_actual_key TINYINT(1) AS (IF(es_actual, 1, NULL)) PERSISTENT;
CREATE UNIQUE INDEX uq_versiones_documento_actual
    ON versiones_documento (documento_id, es_actual_key);

ALTER TABLE anotaciones_entidad
    ADD COLUMN regla_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    ADD CONSTRAINT fk_anotaciones_regla FOREIGN KEY (regla_id)
        REFERENCES reglas_anonimizacion (id) ON DELETE SET NULL;

ALTER TABLE categorias_sensibles
    ADD COLUMN creado_en DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    ADD COLUMN actualizado_en DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6);

ALTER TABLE reglas_anonimizacion DROP INDEX uq_reglas_codigo;
CREATE UNIQUE INDEX uq_reglas_codigo_version
    ON reglas_anonimizacion (codigo, version);
CREATE UNIQUE INDEX uq_reglas_codigo_activa
    ON reglas_anonimizacion (codigo, activa_idx);

CREATE TABLE regla_categorias (
    regla_id      CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    categoria_id  CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    configuracion JSON NOT NULL DEFAULT '{}',

    CONSTRAINT pk_regla_categorias PRIMARY KEY (regla_id, categoria_id),
    CONSTRAINT fk_regla_categorias_regla FOREIGN KEY (regla_id)
        REFERENCES reglas_anonimizacion (id) ON DELETE CASCADE,
    CONSTRAINT fk_regla_categorias_categoria FOREIGN KEY (categoria_id)
        REFERENCES categorias_sensibles (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
