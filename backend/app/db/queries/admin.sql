-- name: listar_configuracion
SELECT clave, valor, descripcion, actualizado_en
FROM configuracion_sistema
ORDER BY clave ASC;

-- name: upsert_configuracion
INSERT INTO configuracion_sistema (clave, valor, descripcion, actualizado_en)
VALUES (%(clave)s, %(valor)s, %(descripcion)s, now())
ON CONFLICT (clave) DO UPDATE
SET valor = EXCLUDED.valor,
    descripcion = COALESCE(EXCLUDED.descripcion, configuracion_sistema.descripcion),
    actualizado_en = now()
RETURNING clave, valor, descripcion, actualizado_en;
