-- V14 · Estructura del OCR: bloques de layout y semáforo por página
-- Base: el modelo de @Marina (vault/Proyecto/Modelo de datos.md), que manda.
-- Cierra B3 (bloques_layout no existía) y B5 (semáforo por página) de vault/Proyecto/Coherencia.md.
-- No modifica V1-V12 ni borra nada: solo añade tabla, columna e índices.
-- Se puede aplicar hoy: no depende de 0005, 0007 ni 0009.

-- ---------------------------------------------------------------------------
-- 1. Páginas del documento: semáforo de calidad antes y después del OCR (B5)
--    El contraste decide si la página se transcribe (umbral 80); `avisos` es
--    lo que ve el revisor y `leida_ocr` si el motor llegó a leerla.
-- ---------------------------------------------------------------------------
CREATE TABLE paginas_documento (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    documento_id    UUID NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    numero          INT NOT NULL CHECK (numero > 0),
    contraste       INT CHECK (contraste BETWEEN 0 AND 100),
    estado          VARCHAR(20) NOT NULL DEFAULT 'ok'
                    CHECK (estado IN ('ok', 'revisar', 'ilegible')),
    avisos          JSONB NOT NULL DEFAULT '[]',
    leida_ocr       BOOLEAN NOT NULL DEFAULT false,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_paginas_documento_numero UNIQUE (documento_id, numero)
);

COMMENT ON TABLE paginas_documento IS 'Una fila por página física: contraste medido y semáforo de calidad';
COMMENT ON COLUMN paginas_documento.contraste IS 'Contraste medido 0-100; por debajo de 80 no se transcribe (< 80 → volver a escanear)';
COMMENT ON COLUMN paginas_documento.estado IS 'ok=se lee, revisar=dudosa, ilegible=no se transcribe (el OCR inventaría texto)';
COMMENT ON COLUMN paginas_documento.avisos IS 'JSON con los avisos de la página: [{tipo, mensaje, bbox}]';

-- Solo las páginas que no están bien: es la lista que alimenta «por volver a escanear».
CREATE INDEX idx_paginas_documento_estado
    ON paginas_documento (documento_id, estado)
    WHERE estado <> 'ok';

-- ---------------------------------------------------------------------------
-- 2. `documentos.num_paginas` (B5): hoy lo devuelven tres respuestas del contrato
--    y no existe como columna. Nulo hasta que termina el OCR, que es quien lo sabe.
-- ---------------------------------------------------------------------------
ALTER TABLE documentos
    ADD COLUMN num_paginas INT CHECK (num_paginas > 0);

COMMENT ON COLUMN documentos.num_paginas IS 'Páginas del fichero; lo devuelven POST /transform/document, GET /documents y GET /documents/{id}';

-- ---------------------------------------------------------------------------
-- 3. Bloques de layout (B3): la base de los offsets y la entrada del PDF final.
--    Geometría en píxeles de la página renderizada, con el tamaño de esa página
--    en el propio bloque: así se escala al visor y sobrevive a un re-render.
--    `bbox` se guarda siempre; `puntos` añade el polígono cuando la forma no es recta.
-- ---------------------------------------------------------------------------
CREATE TABLE bloques_layout (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id        UUID NOT NULL REFERENCES versiones_documento(id) ON DELETE CASCADE,
    pagina_numero     INT NOT NULL CHECK (pagina_numero > 0),
    orden_lectura     INT NOT NULL CHECK (orden_lectura >= 0),
    etiqueta          VARCHAR(40) NOT NULL,
    confianza         DECIMAL(4,3) CHECK (confianza BETWEEN 0 AND 1),
    forma             VARCHAR(10) NOT NULL DEFAULT 'rect'
                      CHECK (forma IN ('rect', 'quad', 'poly')),
    bbox_x            DECIMAL(10,2) NOT NULL CHECK (bbox_x >= 0),
    bbox_y            DECIMAL(10,2) NOT NULL CHECK (bbox_y >= 0),
    bbox_ancho        DECIMAL(10,2) NOT NULL CHECK (bbox_ancho > 0),
    bbox_alto         DECIMAL(10,2) NOT NULL CHECK (bbox_alto > 0),
    pagina_ancho      DECIMAL(10,2) NOT NULL CHECK (pagina_ancho > 0),
    pagina_alto       DECIMAL(10,2) NOT NULL CHECK (pagina_alto > 0),
    puntos            JSONB,
    contenido         TEXT NOT NULL DEFAULT '',
    calidad_semaforo  VARCHAR(10) CHECK (calidad_semaforo IN ('verde', 'amarillo', 'rojo')),
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_bloques_layout_orden UNIQUE (version_id, pagina_numero, orden_lectura),
    CONSTRAINT ck_bloques_layout_puntos CHECK (forma = 'rect' OR puntos IS NOT NULL)
);

COMMENT ON TABLE bloques_layout IS 'Bloques del layout por versión: offsets de anotaciones, visor y reconstrucción del PDF';
COMMENT ON COLUMN bloques_layout.etiqueta IS 'text|table|doc_title|paragraph_title|image|seal|header|footer… (label del detector)';
COMMENT ON COLUMN bloques_layout.confianza IS 'Score del detector 0..1';
COMMENT ON COLUMN bloques_layout.forma IS 'rect, quad o poly; el contrato usa `puntos` cuando no es rect';
COMMENT ON COLUMN bloques_layout.bbox_x IS 'Píxeles de la página renderizada, no normalizado (contrato §4)';
COMMENT ON COLUMN bloques_layout.pagina_ancho IS 'Ancho de la página con el que se midió el bbox: permite escalar sin perder precisión';
COMMENT ON COLUMN bloques_layout.puntos IS 'Vértices [[x,y],…] en píxeles de la misma página; solo para quad y poly';
COMMENT ON COLUMN bloques_layout.contenido IS 'Markdown reconocido del bloque: es el texto sobre el que cuentan los offsets de las anotaciones';
COMMENT ON COLUMN bloques_layout.calidad_semaforo IS 'Semáforo del OCR por bloque (POC OCR §8): verde, amarillo o rojo';
