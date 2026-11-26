-- name: listar_reglas
SELECT id, nombre, descripcion, patron, activa
FROM reglas_anonimizacion
ORDER BY nombre ASC
LIMIT %(limit)s OFFSET %(offset)s;

-- name: contar_reglas
SELECT count(*) AS total
FROM reglas_anonimizacion;

-- name: crear_regla
INSERT INTO reglas_anonimizacion (nombre, descripcion, patron, activa)
VALUES (%(nombre)s, %(descripcion)s, %(patron)s, %(activa)s)
RETURNING id, nombre, descripcion, patron, activa;

-- name: actualizar_regla
UPDATE reglas_anonimizacion
SET nombre = COALESCE(%(nombre)s, nombre),
    descripcion = COALESCE(%(descripcion)s, descripcion),
    patron = COALESCE(%(patron)s, patron),
    activa = COALESCE(%(activa)s, activa)
WHERE id = %(id)s
RETURNING id, nombre, descripcion, patron, activa;

-- name: listar_categorias
SELECT id, codigo, nombre, descripcion, activa
FROM categorias_sensibles
ORDER BY codigo ASC
LIMIT %(limit)s OFFSET %(offset)s;

-- name: contar_categorias
SELECT count(*) AS total
FROM categorias_sensibles;

-- name: crear_categoria
INSERT INTO categorias_sensibles (codigo, nombre, descripcion, activa)
VALUES (%(codigo)s, %(nombre)s, %(descripcion)s, %(activa)s)
RETURNING id, codigo, nombre, descripcion, activa;

-- name: actualizar_categoria
UPDATE categorias_sensibles
SET nombre = COALESCE(%(nombre)s, nombre),
    descripcion = COALESCE(%(descripcion)s, descripcion),
    activa = COALESCE(%(activa)s, activa)
WHERE id = %(id)s
RETURNING id, codigo, nombre, descripcion, activa;
