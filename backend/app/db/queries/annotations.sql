-- name: categorias_listar
SELECT id, codigo, nombre, regex_patron, prioridad, nivel_riesgo, rgpd_especial, activa
  FROM categorias_sensibles
 WHERE (%(activa)s::boolean IS NULL OR activa = %(activa)s)
 ORDER BY prioridad, codigo;

-- name: categorias_de_regla
SELECT c.id, c.codigo, c.nombre, c.prioridad, rc.configuracion
  FROM regla_categorias rc JOIN categorias_sensibles c ON c.id = rc.categoria_id
 WHERE rc.regla_id = %(regla_id)s AND c.activa;

-- name: reglas_listar
SELECT r.id, r.codigo, r.version, r.nombre, r.activa,
       COALESCE((SELECT json_agg(json_build_object('categoria_id', c.id, 'codigo', c.codigo,
                                                   'configuracion', rc.configuracion))
                   FROM regla_categorias rc JOIN categorias_sensibles c ON c.id = rc.categoria_id
                  WHERE rc.regla_id = r.id), '[]') AS categorias
  FROM reglas_anonimizacion r
 WHERE (%(activa)s::boolean IS NULL OR r.activa = %(activa)s)
 ORDER BY r.codigo, r.version;

-- name: regla_por_id
SELECT id, codigo, activa FROM reglas_anonimizacion WHERE id = %(id)s;

-- name: regla_por_id_completa
SELECT id, codigo, version, nombre, activa FROM reglas_anonimizacion WHERE id = %(id)s;

-- name: regla_por_codigo
SELECT id, codigo, version, activa FROM reglas_anonimizacion
 WHERE codigo = %(codigo)s ORDER BY version DESC LIMIT 1;

-- name: regla_activa_codigo
SELECT id FROM reglas_anonimizacion
 WHERE codigo = %(codigo)s AND activa AND id <> %(id)s;

-- name: regla_insertar
-- Contrato §7: si el código ya existe sin regla activa, se crea la siguiente versión.
INSERT INTO reglas_anonimizacion (codigo, nombre, descripcion, configuracion, version, creado_por)
SELECT %(codigo)s, %(nombre)s, %(descripcion)s, %(configuracion)s::jsonb,
       COALESCE(MAX(version), 0) + 1, %(creado_por)s
  FROM reglas_anonimizacion WHERE codigo = %(codigo)s
RETURNING id, codigo, version, nombre, activa;

-- name: regla_actualizar
UPDATE reglas_anonimizacion
   SET nombre = COALESCE(%(nombre)s, nombre),
       descripcion = COALESCE(%(descripcion)s, descripcion),
       configuracion = COALESCE(%(configuracion)s::jsonb, configuracion),
       activa = COALESCE(%(activa)s, activa),
       actualizado_en = now()
 WHERE id = %(id)s
RETURNING id, codigo, version, nombre, activa;

-- name: regla_categorias_borrar
DELETE FROM regla_categorias WHERE regla_id = %(regla_id)s;

-- name: regla_categoria_insertar
INSERT INTO regla_categorias (regla_id, categoria_id, configuracion)
VALUES (%(regla_id)s, %(categoria_id)s, %(configuracion)s::jsonb);

-- name: categoria_por_codigo
SELECT id FROM categorias_sensibles WHERE codigo = %(codigo)s;

-- name: categoria_por_id
SELECT id FROM categorias_sensibles WHERE id = %(id)s;

-- name: categoria_insertar
INSERT INTO categorias_sensibles (codigo, nombre, descripcion, regex_patron, prioridad,
                                   nivel_riesgo, rgpd_especial)
VALUES (%(codigo)s, %(nombre)s, %(descripcion)s, %(regex_patron)s, %(prioridad)s,
        %(nivel_riesgo)s, %(rgpd_especial)s)
RETURNING id, codigo, nombre, descripcion, regex_patron, prioridad, nivel_riesgo,
          rgpd_especial, activa;

-- name: categoria_actualizar
UPDATE categorias_sensibles
   SET nombre = COALESCE(%(nombre)s, nombre),
       descripcion = COALESCE(%(descripcion)s, descripcion),
       regex_patron = COALESCE(%(regex_patron)s, regex_patron),
       prioridad = COALESCE(%(prioridad)s, prioridad),
       nivel_riesgo = COALESCE(%(nivel_riesgo)s, nivel_riesgo),
       rgpd_especial = COALESCE(%(rgpd_especial)s, rgpd_especial),
       activa = COALESCE(%(activa)s, activa),
       actualizado_en = now()
 WHERE id = %(id)s
RETURNING id, codigo, nombre, descripcion, regex_patron, prioridad, nivel_riesgo,
          rgpd_especial, activa;

-- name: anotacion_insertar
INSERT INTO anotaciones_entidad (version_id, bloque_id, categoria_id, inicio_offset, fin_offset,
                                 texto_original, pagina_numero, accion_aplicada,
                                 texto_sustitucion, confianza_deteccion, motor_deteccion,
                                 regla_id, decision_revisor, revisado_por, revisado_en)
VALUES (%(version_id)s, %(bloque_id)s, %(categoria_id)s, %(inicio)s, %(fin)s, %(texto)s,
        %(pagina)s, %(accion)s, %(sustitucion)s, %(confianza)s, %(motor)s, %(regla_id)s,
        %(decision)s, %(revisado_por)s, CASE WHEN %(revisado_por)s::uuid IS NULL THEN NULL ELSE now() END)
RETURNING id;

-- name: anotaciones_listar
SELECT a.id, a.version_id, a.bloque_id, a.categoria_id, c.codigo AS categoria, a.inicio_offset,
       a.fin_offset, a.texto_original, b.pagina_numero, a.accion_aplicada, a.texto_sustitucion,
       a.confianza_deteccion, a.motor_deteccion, a.decision_revisor, a.observaciones_revisor
  FROM anotaciones_entidad a
  JOIN versiones_documento v ON v.id = a.version_id
  JOIN categorias_sensibles c ON c.id = a.categoria_id
  LEFT JOIN bloques_layout b ON b.id = a.bloque_id
 WHERE v.documento_id = %(documento_id)s
   AND a.version_id = COALESCE(%(version_id)s::uuid,
        (SELECT id FROM versiones_documento WHERE documento_id = %(documento_id)s AND es_actual))
   AND (%(categoria_id)s::uuid IS NULL OR a.categoria_id = %(categoria_id)s)
   AND (NOT %(pendientes)s OR a.decision_revisor IS NULL)
 ORDER BY b.pagina_numero, a.inicio_offset;

-- name: anotacion_por_id
SELECT a.id, a.version_id, a.accion_aplicada, a.decision_revisor, v.documento_id
  FROM anotaciones_entidad a JOIN versiones_documento v ON v.id = a.version_id
 WHERE a.id = %(id)s;

-- name: anotacion_actualizar
UPDATE anotaciones_entidad
   SET accion_aplicada = %(accion)s, texto_sustitucion = %(sustitucion)s,
       decision_revisor = %(decision)s, observaciones_revisor = %(observaciones)s,
       revisado_por = %(revisado_por)s, revisado_en = now()
 WHERE id = %(id)s;

-- name: revision_en_proceso_version
-- A-11: con la revisión cerrada, las anotaciones son de solo lectura.
SELECT id FROM revisiones WHERE version_id = %(version_id)s AND estado = 'en_proceso';

-- name: anotaciones_para_aplicar
SELECT bloque_id, inicio_offset, fin_offset, texto_original, texto_sustitucion,
       accion_aplicada, decision_revisor
  FROM anotaciones_entidad WHERE version_id = %(version_id)s;

-- name: anotaciones_pendientes
SELECT id FROM anotaciones_entidad
 WHERE version_id = %(version_id)s AND (decision_revisor IS NULL OR bloque_id IS NULL);
