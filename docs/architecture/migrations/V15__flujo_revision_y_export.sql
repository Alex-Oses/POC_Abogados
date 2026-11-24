-- V15 · Flujo de revisión y export
-- Base: el modelo de @Marina (vault/Proyecto/Modelo de datos.md), que manda.
-- Cierra B4 y B7 de vault/Proyecto/Coherencia.md y baja A-04, A-05, A-15, A-19, A-20 y A-23.
-- 0005 está aceptada. B8 se resolvió sin migración: el hash vive en
-- versiones_documento.metadatos_proceso->>'hash_export'.
-- No borra datos: `revisiones.revisor_id` se renombra a `asignado_a`, no se tira.

-- ---------------------------------------------------------------------------
-- 1. documentos: estados nuevos y columnas de la doble firma (A-15, A-19, A-21)
-- ---------------------------------------------------------------------------
ALTER TABLE documentos DROP CONSTRAINT documentos_estado_check;

ALTER TABLE documentos ADD CONSTRAINT documentos_estado_check CHECK (estado IN (
    'pendiente', 'ocr_procesando', 'ocr_completado', 'anonimizando',
    'en_revision', 'aprobado', 'rechazado', 'pendiente_visto_bueno',
    'exportado', 'eliminado'
));

ALTER TABLE documentos
    ADD COLUMN requiere_visto_bueno BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN visto_bueno_por     UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    ADD COLUMN visto_bueno_en      TIMESTAMPTZ,
    ADD COLUMN cerrado_en          TIMESTAMPTZ,
    ADD COLUMN eliminado_en        TIMESTAMPTZ,
    ADD COLUMN exportado_en        TIMESTAMPTZ,
    ADD COLUMN clave_cifrado       VARCHAR(100);

COMMENT ON COLUMN documentos.requiere_visto_bueno IS 'A-15: se calcula al cerrar la revisión y se persiste; no se recalcula después';
COMMENT ON COLUMN documentos.visto_bueno_por IS 'A-15: revisor que firmó POST /documents/{id}/sign-off';
COMMENT ON COLUMN documentos.cerrado_en IS 'A-19: cierre del expediente; lo escribe el export (contrato §10)';
COMMENT ON COLUMN documentos.eliminado_en IS 'Borrado lógico de DELETE /documents/{id}; no borra versiones ni auditoría';
COMMENT ON COLUMN documentos.exportado_en IS 'A-18: fecha del PDF definitivo; el hash idempotente vive en la versión';
COMMENT ON COLUMN documentos.clave_cifrado IS '0004: identificador de la clave con la que se cifró el original; nunca el material de la clave';

-- `hash_sha256` deja de ser único global: dos personas pueden subir el mismo PDF.
-- El único pasa a ser por creador y excluye lo borrado lógicamente (modelo de @Marina + I-7 de 0010).
ALTER TABLE documentos DROP CONSTRAINT uq_documentos_hash;

CREATE UNIQUE INDEX uq_documentos_hash_creador
    ON documentos (creado_por, hash_sha256)
    WHERE estado <> 'eliminado';

-- ---------------------------------------------------------------------------
-- 2. revisiones: cola sin dueño (A-05), plazo (A-20) y cierre optimista (A-23)
--    `revisor_id` pasa a llamarse `asignado_a`: es la única columna de
--    responsabilidad. Quién cerró queda en `auditoria` y en `versiones_documento`.
-- ---------------------------------------------------------------------------
ALTER TABLE revisiones RENAME COLUMN revisor_id TO asignado_a;
ALTER TABLE revisiones ALTER COLUMN asignado_a DROP NOT NULL;

ALTER TABLE revisiones DROP CONSTRAINT revisiones_estado_check;

ALTER TABLE revisiones ALTER COLUMN estado SET DEFAULT 'en_cola';
ALTER TABLE revisiones ADD CONSTRAINT revisiones_estado_check CHECK (estado IN (
    'en_cola', 'en_proceso', 'aprobado', 'rechazado_con_cambios', 'devuelto'
));

ALTER TABLE revisiones
    ADD COLUMN documento_id          UUID,
    ADD COLUMN asignado_en           TIMESTAMPTZ,
    ADD COLUMN fecha_limite          TIMESTAMPTZ,
    ADD COLUMN aviso_24h_enviado_en  TIMESTAMPTZ,
    ADD COLUMN actualizado_en        TIMESTAMPTZ NOT NULL DEFAULT now();

-- Relleno para un clon con datos: la revisión hereda el documento de su versión.
UPDATE revisiones r
   SET documento_id = v.documento_id
  FROM versiones_documento v
 WHERE v.id = r.version_id
   AND r.documento_id IS NULL;

ALTER TABLE revisiones ALTER COLUMN documento_id SET NOT NULL;

ALTER TABLE revisiones
    ADD CONSTRAINT uq_revisiones_version_intento UNIQUE (version_id, numero_intento);

-- La FK compuesta garantiza que `documento_id` es el de verdad el de la versión:
-- sin esto, el índice de A-04 podría vigilar un documento que no toca.
ALTER TABLE versiones_documento
    ADD CONSTRAINT uq_versiones_documento_id UNIQUE (id, documento_id);

ALTER TABLE revisiones DROP CONSTRAINT revisiones_version_id_fkey;

ALTER TABLE revisiones
    ADD CONSTRAINT fk_revisiones_version_documento
    FOREIGN KEY (version_id, documento_id)
    REFERENCES versiones_documento (id, documento_id)
    ON DELETE CASCADE;

-- A-04: una sola revisión abierta (en_cola o en_proceso) por DOCUMENTO.
-- El único de V7 era (version_id, numero_intento) y no lo implementaba.
CREATE UNIQUE INDEX uq_revisiones_abierta_por_documento
    ON revisiones (documento_id)
    WHERE estado IN ('en_cola', 'en_proceso');

-- A-20: barrido de plazos y avisos de 24 h sobre lo que sigue abierto.
CREATE INDEX idx_revisiones_plazo
    ON revisiones (fecha_limite)
    WHERE estado IN ('en_cola', 'en_proceso');

-- El índice de V10 cambia de nombre con la columna (su definición ya apunta a asignado_a).
ALTER INDEX idx_revisiones_revisor_estado RENAME TO idx_revisiones_asignado_estado;

-- ---------------------------------------------------------------------------
-- 3. anotaciones: una sola base de offsets (B3) y las acciones de I1
--    Los offsets son índices dentro de bloques_layout.contenido (contrato §5).
-- ---------------------------------------------------------------------------
ALTER TABLE anotaciones_entidad
    ADD COLUMN bloque_id UUID REFERENCES bloques_layout(id) ON DELETE CASCADE;

COMMENT ON COLUMN anotaciones_entidad.bloque_id IS 'Bloque sobre cuyo `contenido` cuentan inicio_offset y fin_offset (contrato §5)';
COMMENT ON COLUMN anotaciones_entidad.inicio_offset IS 'Índice de carácter dentro de bloques_layout.contenido, no del texto completo';
COMMENT ON COLUMN anotaciones_entidad.accion_aplicada IS 'censurar|censurar con etiqueta|iniciales|pseudonimizado|eliminado|mantenido|tachado(uso interno)|pendiente_revision';

ALTER TABLE anotaciones_entidad DROP CONSTRAINT anotaciones_entidad_accion_aplicada_check;

ALTER TABLE anotaciones_entidad ADD CONSTRAINT anotaciones_entidad_accion_aplicada_check
    CHECK (accion_aplicada IN (
        'censurar', 'etiqueta', 'iniciales', 'pseudonimizado',
        'eliminado', 'mantenido', 'tachado', 'pendiente_revision'
    ));

CREATE INDEX idx_anotaciones_bloque
    ON anotaciones_entidad (bloque_id)
    WHERE bloque_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 4. categorias_sensibles.prioridad: el contrato §7 ya la devuelve y no existía.
--    Orden de aplicación cuando dos categorías solapan en el mismo texto.
-- ---------------------------------------------------------------------------
ALTER TABLE categorias_sensibles
    ADD COLUMN prioridad INT NOT NULL DEFAULT 100;

COMMENT ON COLUMN categorias_sensibles.prioridad IS 'Menor = se aplica antes cuando dos categorías solapan. 100 = sin preferencia';

-- ---------------------------------------------------------------------------
-- 5. Seeds corregidos (H6, H8) y claves que A-20 lee y nadie había sembrado
-- ---------------------------------------------------------------------------
-- H8: NUSS es un identificador, no un dato del art. 9 RGPD; no debe disparar doble firma.
UPDATE categorias_sensibles
   SET rgpd_especial = false
 WHERE codigo = 'NUSS';

-- H6: motores OCR en cloud (contradice 0001), formato preservado (contradice 0007),
-- timeout de 60 min (el plazo de A-20 es de 48 h laborables) y versión del esquema.
UPDATE configuracion_sistema
   SET valor = '["paddleocr-vl"]'::jsonb
 WHERE clave = 'motores_ocr_disponibles';

UPDATE configuracion_sistema
   SET valor = 'false'::jsonb
 WHERE clave = 'preservar_formato_pdf';

UPDATE configuracion_sistema
   SET valor = '"censurar"'::jsonb,
       descripcion = 'Acción por defecto: censurar|etiqueta|iniciales|pseudonimizado|eliminado'
 WHERE clave = 'accion_por_defecto';

DELETE FROM configuracion_sistema
 WHERE clave = 'tiempo_max_revision_minutos';

UPDATE configuracion_sistema
   SET valor = '15'::jsonb
 WHERE clave = 'version_esquema_bd';

-- A-20 las nombra y no existían: sin ellas el plazo se calcula con una constante
-- escondida en el código, que es justo lo que la regla evita.
INSERT INTO configuracion_sistema (clave, valor, descripcion) VALUES
    ('revision_plazo_horas', '48',
     'A-20: horas laborables para cerrar una revisión'),
    ('revision_aviso_horas', '24',
     'A-20: horas laborables antes del aviso al revisor y, si sigue en cola, al supervisor'),
    ('calendario_laboral',
     '{"lunes_a_viernes": "09:00-18:00", "festivos": []}',
     'A-20: horario laboral y festivos ISO (YYYY-MM-DD). Vacío = no se descuenta ningún festivo')
ON CONFLICT (clave) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. Identidad y sesiones (0012, 0015; B1)
--     La BD mantiene V1..V15: la identidad se añade al final de V15.
--     Se sueltan las dependencias de rol/activo antes de retirar columnas.
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_metricas_revisor;
DROP TRIGGER IF EXISTS trg_revision_validar_revisor ON revisiones;
DROP FUNCTION IF EXISTS trg_revision_validar_revisor();

ALTER TABLE usuarios DROP COLUMN rol;

CREATE TABLE usuarios_roles (
    usuario_id UUID NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    rol        VARCHAR(50) NOT NULL CHECK (rol IN ('transcriptor', 'revisor', 'admin')),
    PRIMARY KEY (usuario_id, rol)
);

ALTER TABLE usuarios DROP COLUMN activo;
ALTER TABLE usuarios
    ADD COLUMN estado       VARCHAR(20) NOT NULL DEFAULT 'activo'
        CHECK (estado IN ('activo', 'bloqueado', 'baja')),
    ADD COLUMN motivo_baja  TEXT,
    ADD COLUMN eliminado_en TIMESTAMPTZ,
    ADD COLUMN sso_subject  TEXT UNIQUE,
    ADD COLUMN password_hash TEXT;

DROP INDEX IF EXISTS idx_usuarios_rol_activo;
CREATE INDEX idx_usuarios_estado ON usuarios (estado);
CREATE INDEX idx_usuarios_roles_rol ON usuarios_roles (rol);

CREATE TABLE sesiones_usuario (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  UUID NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_en   TIMESTAMPTZ NOT NULL,
    ultimo_uso_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    revocado_en TIMESTAMPTZ,
    ip_origen   INET,
    user_agent  TEXT
);

CREATE INDEX idx_sesiones_usuario_usuario
    ON sesiones_usuario (usuario_id, creado_en DESC);

-- ---------------------------------------------------------------------------
-- 7. Campos y relaciones que forman parte del modelo entidad-relación vigente
-- ---------------------------------------------------------------------------
ALTER TABLE usuarios RENAME COLUMN nombre_completo TO nombre;
ALTER TABLE usuarios ADD COLUMN apellidos VARCHAR(200) NOT NULL DEFAULT '';
ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_email_key;
CREATE UNIQUE INDEX uq_usuarios_email_lower ON usuarios (lower(email));

ALTER TABLE versiones_documento
    RENAME COLUMN confianza_promedio TO confianza_layout_promedio;
ALTER TABLE versiones_documento
    ADD COLUMN pipeline_version VARCHAR(100),
    ADD COLUMN regla_id UUID REFERENCES reglas_anonimizacion(id) ON DELETE SET NULL,
    ADD COLUMN es_actual BOOLEAN NOT NULL DEFAULT false;
WITH ultimas AS (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY documento_id ORDER BY numero_version DESC) AS posicion
    FROM versiones_documento
)
UPDATE versiones_documento v
   SET es_actual = true
  FROM ultimas u
 WHERE v.id = u.id
   AND u.posicion = 1;
CREATE UNIQUE INDEX uq_versiones_documento_actual
    ON versiones_documento (documento_id)
    WHERE es_actual;

ALTER TABLE anotaciones_entidad
    ADD COLUMN regla_id UUID REFERENCES reglas_anonimizacion(id) ON DELETE SET NULL;

ALTER TABLE categorias_sensibles
    ADD COLUMN creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE reglas_anonimizacion
    DROP CONSTRAINT IF EXISTS reglas_anonimizacion_codigo_key;
CREATE UNIQUE INDEX uq_reglas_codigo_version
    ON reglas_anonimizacion (codigo, version);
CREATE UNIQUE INDEX uq_reglas_codigo_activa
    ON reglas_anonimizacion (codigo)
    WHERE activa;

CREATE TABLE regla_categorias (
    regla_id     UUID NOT NULL REFERENCES reglas_anonimizacion(id) ON DELETE CASCADE,
    categoria_id UUID NOT NULL REFERENCES categorias_sensibles(id) ON DELETE CASCADE,
    configuracion JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (regla_id, categoria_id)
);
