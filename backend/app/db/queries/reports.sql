-- name: listar_auditoria
SELECT id, usuario_id, accion, entidad, entidad_id, detalles, hash_anterior, hash_actual, creado_en
FROM auditoria
ORDER BY creado_en DESC
LIMIT %(limit)s OFFSET %(offset)s;

-- name: contar_auditoria
SELECT count(*) AS total
FROM auditoria;
