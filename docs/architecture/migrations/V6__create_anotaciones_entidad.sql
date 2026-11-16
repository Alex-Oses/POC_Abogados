-- Cada entidad detectada en el texto (trazabilidad total antes/después)

CREATE TABLE anotaciones_entidad (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id              UUID NOT NULL REFERENCES versiones_documento(id) ON DELETE CASCADE,
    categoria_id            UUID NOT NULL REFERENCES categorias_sensibles(id) ON DELETE RESTRICT,
    -- Posición en texto plano
    inicio_offset           INT NOT NULL CHECK (inicio_offset >= 0),
    fin_offset              INT NOT NULL CHECK (fin_offset > inicio_offset),
    texto_original          TEXT NOT NULL,
    -- Posición en PDF (para render visual "antes/después")
    pagina_numero           INT CHECK (pagina_numero > 0),
    bbox_x                  DECIMAL(8,2),
    bbox_y                  DECIMAL(8,2),
    bbox_ancho              DECIMAL(8,2),
    bbox_alto               DECIMAL(8,2),
    -- Decisión de anonimización
    accion_aplicada         VARCHAR(30) NOT NULL CHECK (accion_aplicada IN (
        'tachado', 'pseudonimizado', 'eliminado', 'mantenido', 'pendiente_revision'
    )),
    texto_sustitucion       VARCHAR(500),
    confianza_deteccion     DECIMAL(4,3) NOT NULL CHECK (confianza_deteccion BETWEEN 0 AND 1),
    motor_deteccion         VARCHAR(50) NOT NULL,
    -- Revisión humana
    revisado_por            UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    revisado_en             TIMESTAMPTZ,
    decision_revisor        VARCHAR(30) CHECK (decision_revisor IN (
        'confirmado', 'modificado', 'falso_positivo', 'falso_negativo'
    )),
    observaciones_revisor   TEXT,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE anotaciones_entidad IS 'Línea a línea: qué se detectó, qué se hizo, quién lo validó';
COMMENT ON COLUMN anotaciones_entidad.accion_aplicada IS 'tachado=████, pseudonimizado=[NOMBRE_1], eliminado="", mantenido=original, pendiente_revision=cola revisor';
COMMENT ON COLUMN anotaciones_entidad.texto_sustitucion IS 'Texto que reemplaza al original en versión anonimizada';
COMMENT ON COLUMN anotaciones_entidad.decision_revisor IS 'Trazabilidad: revisor confirma/cambia/rechaza detección IA';