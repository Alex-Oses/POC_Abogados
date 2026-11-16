-- Índices de rendimiento (ejecutar tras crear tablas + seeds)

-- usuarios
CREATE INDEX idx_usuarios_rol_activo ON usuarios(rol, activo);

-- documentos
CREATE INDEX idx_documentos_estado ON documentos(estado);
CREATE INDEX idx_documentos_creado_por ON documentos(creado_por);
CREATE INDEX idx_documentos_creado_en ON documentos(creado_en DESC);

-- versiones_documento
CREATE INDEX idx_versiones_documento_tipo ON versiones_documento(tipo_version);
CREATE INDEX idx_versiones_documento_creado_en ON versiones_documento(creado_en DESC);

-- anotaciones_entidad (tabla más grande → índices críticos)
CREATE INDEX idx_anotaciones_version ON anotaciones_entidad(version_id);
CREATE INDEX idx_anotaciones_categoria ON anotaciones_entidad(categoria_id);
CREATE INDEX idx_anotaciones_accion ON anotaciones_entidad(accion_aplicada);
CREATE INDEX idx_anotaciones_pendientes ON anotaciones_entidad(version_id, categoria_id) 
    WHERE accion_aplicada = 'pendiente_revision';
CREATE INDEX idx_anotaciones_revisado_por ON anotaciones_entidad(revisado_por) 
    WHERE revisado_por IS NOT NULL;

-- revisiones
CREATE INDEX idx_revisiones_version ON revisiones(version_id);
CREATE INDEX idx_revisiones_revisor_estado ON revisiones(revisor_id, estado);
CREATE INDEX idx_revisiones_creado_en ON revisiones(creado_en DESC);

-- auditoria (particionada → índices locales en cada partición)
CREATE INDEX idx_auditoria_entidad ON auditoria(entidad_tipo, entidad_id);
CREATE INDEX idx_auditoria_usuario_fecha ON auditoria(usuario_id, creado_en DESC);
CREATE INDEX idx_auditoria_evento_fecha ON auditoria(evento, creado_en DESC);

-- reglas_anonimizacion
CREATE INDEX idx_reglas_activa ON reglas_anonimizacion(activa) WHERE activa = true;