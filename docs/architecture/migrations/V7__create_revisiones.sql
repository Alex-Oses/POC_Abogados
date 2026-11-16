-- Workflow: una persona aprueba; cualquier edición exige otra revisión

CREATE TABLE revisiones (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id              UUID NOT NULL REFERENCES versiones_documento(id) ON DELETE CASCADE,
    revisor_id              UUID NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    estado                  VARCHAR(30) NOT NULL DEFAULT 'en_proceso'
                            CHECK (estado IN (
                                'en_proceso', 'aprobado', 'rechazado_con_cambios', 'devuelto'
                            )),
    numero_intento          INT NOT NULL DEFAULT 1 CHECK (numero_intento > 0),
    tiempo_revision_seg     INT CHECK (tiempo_revision_seg >= 0),
    comentario_general      TEXT,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_en           TIMESTAMPTZ
);

COMMENT ON TABLE revisiones IS 'Ciclos de revisión humana sobre versión anonimizada';
COMMENT ON COLUMN revisiones.numero_intento IS '1=primera revisión, 2=tras edición del transcriptor, 3=...';
COMMENT ON COLUMN revisiones.estado IS 'rechazado_con_cambios=vuelve a transcriptor; devuelto=revisor no puede decidir';