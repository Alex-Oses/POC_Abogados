-- name: config_listar
SELECT clave, valor, descripcion, actualizado_en
  FROM configuracion_sistema
 ORDER BY clave;

-- name: config_upsert
-- Contrato §8: crea o actualiza la clave y audita el cambio.
INSERT INTO configuracion_sistema (clave, valor, descripcion, actualizado_por)
VALUES (%(clave)s, %(valor)s::jsonb, %(descripcion)s, %(usuario_id)s)
ON CONFLICT (clave) DO UPDATE
   SET valor = EXCLUDED.valor,
       descripcion = COALESCE(EXCLUDED.descripcion, configuracion_sistema.descripcion),
       actualizado_por = EXCLUDED.actualizado_por,
       actualizado_en = now()
RETURNING clave, valor, descripcion, actualizado_en;
