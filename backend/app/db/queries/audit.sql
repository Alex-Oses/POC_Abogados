-- name: insertar
-- Cadena de custodia: hash_anterior = SHA-256 de la fila anterior completa (V8).
-- El advisory lock se toma en una sentencia aparte (audit.py).
WITH previa AS (
    SELECT encode(sha256(convert_to(row_to_json(a)::text, 'UTF8')), 'hex') AS hash
      FROM auditoria a
     ORDER BY a.id DESC
     LIMIT 1
)
INSERT INTO auditoria (
    evento, entidad_tipo, entidad_id, usuario_id, ip_origen, user_agent, detalle, hash_anterior
)
SELECT %(evento)s, %(entidad_tipo)s, %(entidad_id)s, %(usuario_id)s,
       %(ip)s::inet, %(user_agent)s, %(detalle)s::jsonb,
       (SELECT hash FROM previa)
RETURNING id;

-- name: auditoria_listar
SELECT id, evento, entidad_tipo, entidad_id, usuario_id, host(ip_origen) AS ip_origen,
       creado_en, detalle, COUNT(*) OVER () AS total
  FROM auditoria
 WHERE (%(entidad_tipo)s::text IS NULL OR entidad_tipo = %(entidad_tipo)s)
   AND (%(entidad_id)s::uuid IS NULL OR entidad_id = %(entidad_id)s)
   AND (%(usuario_id)s::uuid IS NULL OR usuario_id = %(usuario_id)s)
   AND (%(desde)s::timestamptz IS NULL OR creado_en >= %(desde)s)
   AND (%(hasta)s::timestamptz IS NULL OR creado_en < %(hasta)s)
 ORDER BY id DESC
 LIMIT %(limit)s OFFSET %(offset)s;
