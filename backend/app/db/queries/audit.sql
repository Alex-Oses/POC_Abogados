-- name: insertar
-- Cadena de custodia: hash_anterior = SHA-256 de la fila anterior completa (V8).
-- El advisory lock se toma en una sentencia aparte (audit.py).
WITH previa AS (
    SELECT encode(sha256(convert_to(row_to_json(a)::text, 'UTF8')), 'hex') AS hash
      FROM auditoria a
     ORDER BY a.creado_en DESC, a.id DESC  -- coherente con triggers.sql (E-17, decisión 0017)
     LIMIT 1
)
INSERT INTO auditoria (
    evento, entidad_tipo, entidad_id, usuario_id, ip_origen, user_agent, detalle, hash_anterior
)
SELECT %(evento)s, %(entidad_tipo)s, %(entidad_id)s, %(usuario_id)s,
       %(ip)s::inet, %(user_agent)s, %(detalle)s::jsonb,
       (SELECT hash FROM previa)
RETURNING id;
