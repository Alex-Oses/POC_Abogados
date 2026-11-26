-- name: usuario_por_email
-- `usuarios` tiene índice único sobre lower(email).
SELECT id, email, nombre, apellidos, estado, password_hash
FROM usuarios
WHERE lower(email) = lower(%(email)s);

-- name: sesion_por_token
SELECT s.id AS sesion_id, s.usuario_id, u.id, s.creado_en, s.expira_en, s.ultimo_uso_en,
       u.email, u.nombre, u.apellidos, u.estado,
       ARRAY(SELECT ur.rol FROM usuarios_roles ur WHERE ur.usuario_id = u.id ORDER BY ur.rol) AS roles
FROM sesiones_usuario s
JOIN usuarios u ON u.id = s.usuario_id
WHERE s.token_hash = %(token_hash)s
  AND s.revocado_en IS NULL;

-- name: crear_sesion
INSERT INTO sesiones_usuario (usuario_id, token_hash, expira_en, ip_origen, user_agent)
VALUES (%(usuario_id)s, %(token_hash)s, %(expira_en)s, %(ip)s::inet, %(user_agent)s)
RETURNING id;

-- name: desalojar_sesiones
-- U-17: al crear la cuarta se revoca la más antigua. `conservar` = max - 1.
UPDATE sesiones_usuario
   SET revocado_en = now()
 WHERE id IN (
       SELECT id FROM sesiones_usuario
        WHERE usuario_id = %(usuario_id)s
          AND revocado_en IS NULL
          AND expira_en > now()
        -- E-57: DESC conserva las `conservar` sesiones más recientes; con ASC
        -- se revocaba la más nueva en lugar de la más antigua (U-17).
        ORDER BY creado_en DESC
       OFFSET %(conservar)s
 );

-- name: tocar_sesion
UPDATE sesiones_usuario
   SET ultimo_uso_en = now(), expira_en = %(expira_en)s
 WHERE id = %(id)s;

-- name: revocar_sesion
UPDATE sesiones_usuario SET revocado_en = now()
 WHERE id = %(id)s AND revocado_en IS NULL;

-- name: revocar_sesiones_usuario
UPDATE sesiones_usuario SET revocado_en = now()
 WHERE usuario_id = %(usuario_id)s AND revocado_en IS NULL;

-- name: actualizar_password
UPDATE usuarios
   SET password_hash = %(password_hash)s, actualizado_en = now()
 WHERE id = %(id)s;

-- name: password_hash_por_id
SELECT password_hash FROM usuarios WHERE id = %(id)s;
