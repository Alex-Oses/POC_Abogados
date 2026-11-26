-- name: listar_usuarios
-- Contrato §2: listado paginado con filtros opcionales.
SELECT u.id, u.email, u.nombre, u.apellidos, u.estado,
       ARRAY(SELECT ur.rol FROM usuarios_roles ur WHERE ur.usuario_id = u.id ORDER BY ur.rol) AS roles,
       COUNT(*) OVER() AS total
FROM usuarios u
WHERE (%(estado)s::varchar IS NULL OR u.estado = %(estado)s)
  AND (%(rol)s::varchar IS NULL OR EXISTS (
        SELECT 1 FROM usuarios_roles ur
         WHERE ur.usuario_id = u.id AND ur.rol = %(rol)s))
ORDER BY u.creado_en DESC
LIMIT %(limit)s OFFSET %(offset)s;

-- name: usuario_por_id
SELECT u.id, u.email, u.nombre, u.apellidos, u.estado, u.motivo_baja, u.eliminado_en,
       ARRAY(SELECT ur.rol FROM usuarios_roles ur WHERE ur.usuario_id = u.id ORDER BY ur.rol) AS roles
FROM usuarios u
WHERE u.id = %(id)s;

-- name: actualizar_usuario
UPDATE usuarios
   SET estado = %(estado)s,
       motivo_baja = %(motivo_baja)s,
       eliminado_en = %(eliminado_en)s,
       actualizado_en = now()
 WHERE id = %(id)s;

-- name: borrar_roles
DELETE FROM usuarios_roles WHERE usuario_id = %(id)s;

-- name: agregar_rol
INSERT INTO usuarios_roles (usuario_id, rol) VALUES (%(id)s, %(rol)s)
ON CONFLICT DO NOTHING;

-- name: sembrar_admin
-- U-06/U-21: no pisa roles; deja la cuenta activa y con la credencial del entorno.
INSERT INTO usuarios (email, nombre, apellidos, password_hash, estado)
VALUES (%(email)s, %(nombre)s, '', %(password_hash)s, 'activo')
ON CONFLICT (lower(email)) DO UPDATE
   SET password_hash = EXCLUDED.password_hash,
       estado = 'activo',
       motivo_baja = NULL,
       eliminado_en = NULL,
       actualizado_en = now()
RETURNING id;
