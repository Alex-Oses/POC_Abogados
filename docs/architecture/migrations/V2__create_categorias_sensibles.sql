-- Catálogo de tipos de datos sensibles (RGPD Art. 9 + LOPD)

CREATE TABLE categorias_sensibles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo              VARCHAR(50) NOT NULL UNIQUE,
    nombre              VARCHAR(150) NOT NULL,
    descripcion         TEXT,
    regex_patron        VARCHAR(500),
    nivel_riesgo        VARCHAR(20) NOT NULL CHECK (nivel_riesgo IN ('alto', 'medio', 'bajo')),
    rgpd_especial       BOOLEAN NOT NULL DEFAULT false,
    activa              BOOLEAN NOT NULL DEFAULT true
);

COMMENT ON TABLE categorias_sensibles IS 'Catálogo maestro de entidades sensibles detectables';
COMMENT ON COLUMN categorias_sensibles.rgpd_especial IS 'TRUE = Categoría especial Art. 9 RGPD (salud, origen racial, genéticos, etc.)';
COMMENT ON COLUMN categorias_sensibles.regex_patron IS 'Regex opcional para validación rápida post-detección';