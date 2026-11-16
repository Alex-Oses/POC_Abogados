-- Personal que transcribe/revisa documentos iCAT

CREATE TABLE usuarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    nombre_completo VARCHAR(200) NOT NULL,
    rol             VARCHAR(50) NOT NULL CHECK (rol IN ('transcriptor', 'revisor', 'admin', 'supervisor')),
    activo          BOOLEAN NOT NULL DEFAULT true,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE usuarios IS 'Personal del sistema: transcriptores, revisores, admins';
COMMENT ON COLUMN usuarios.rol IS 'transcriptor=corrige OCR, revisor=valida anonimización, admin=gestiona usuarios/reglas, supervisor=métricas';
