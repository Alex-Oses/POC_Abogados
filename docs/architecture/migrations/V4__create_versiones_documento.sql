-- Historial de versiones: original → OCR → anonimizado → revisado → final

CREATE TABLE versiones_documento (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    documento_id        UUID NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    numero_version      INT NOT NULL CHECK (numero_version > 0),
    tipo_version        VARCHAR(30) NOT NULL CHECK (tipo_version IN (
        'original', 'ocr_texto', 'anonimizado_ia', 'revisado_humano', 'final_aprobado'
    )),
    contenido_texto     TEXT,
    contenido_html      TEXT,
    ruta_pdf            VARCHAR(1000),
    motor_ocr           VARCHAR(50),
    modelo_ia           VARCHAR(100),
    confianza_promedio  DECIMAL(4,3) CHECK (confianza_promedio BETWEEN 0 AND 1),
    metadatos_proceso   JSONB NOT NULL DEFAULT '{}',
    creado_por          UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uq_version_documento UNIQUE (documento_id, numero_version)
);

COMMENT ON TABLE versiones_documento IS 'Cadena de custodia textual del documento';
COMMENT ON COLUMN versiones_documento.tipo_version IS '1=original(subido), 2=OCR, 3=IA anonimiza, 4=humano revisa, 5=final';
COMMENT ON COLUMN versiones_documento.contenido_html IS 'Texto con spans/markup de entidades detectadas para UI diff';
COMMENT ON COLUMN versiones_documento.metadatos_proceso IS 'Tiempos, parámetros modelo, warnings, tokens consumidos';