-- partitioning.sql
-- Particionado mensual de auditoria (pg_partman) + retención automática
-- Requiere: CREATE EXTENSION pg_partman; (superuser)
-- Ejecutar UNA VEZ en producción (no en migraciones Flyway normales)

-- ============================================================
-- 1. Preparar tabla auditoria como particionada (si no lo está)
-- ============================================================
-- NOTA: Si auditoria ya existe con datos, hay que migrar:
--   CREATE TABLE auditoria_partitioned (LIKE auditoria INCLUDING ALL) PARTITION BY RANGE (creado_en);
--   INSERT INTO auditoria_partitioned SELECT * FROM auditoria;
--   DROP TABLE auditoria; ALTER TABLE auditoria_partitioned RENAME TO auditoria;
--   Luego crear índices en la tabla particionada (se propagan a particiones).

-- Asumimos tabla vacía o ya particionada:
ALTER TABLE auditoria
    PARTITION BY RANGE (creado_en);

-- ============================================================
-- 2. Configurar pg_partman
-- ============================================================
-- parent_table: tabla particionada
-- control: columna de particionado (timestamp)
-- partition_interval: '1 month'
-- partition_type: 'range'
-- retention: '120 months' (10 años = 120 meses)
-- retention_keep_table: false (DROP particiones viejas)
-- infinite_time_partitions: true (crear futuras automáticamente)

SELECT partman.create_parent(
    p_parent_table         := 'public.auditoria',
    p_control              := 'creado_en',
    p_type                 := 'range',
    p_interval             := '1 month',
    p_premake              := 12,           -- crear 12 meses por adelantado
    p_default_table        := true,         -- tabla default para datos fuera de rango
    p_automatic_maintenance := 'on',        -- mantenimiento automático
    p_retention            := '120 months', -- retención 10 años
    p_retention_keep_table := false,        -- DROP particiones expiradas
    p_inherit_indexes      := true          -- índices se heredan
);

-- ============================================================
-- 3. Índices locales (se crean en cada partición automáticamente)
-- ============================================================
-- Ya definidos en V10__create_indexes.sql, pero pg_partman los propaga:
-- CREATE INDEX idx_auditoria_entidad ON auditoria(entidad_tipo, entidad_id);
-- CREATE INDEX idx_auditoria_usuario_fecha ON auditoria(usuario_id, creado_en DESC);
-- CREATE INDEX idx_auditoria_evento_fecha ON auditoria(evento, creado_en DESC);

-- Forzar creación en particiones existentes:
SELECT partman.run_maintenance(p_parent_table := 'public.auditia');

-- ============================================================
-- 4. Job cron para mantenimiento (ejecutar cada hora via pg_cron o cron externo)
-- ============================================================
-- Opción A: pg_cron (extensión en BD)
-- SELECT cron.schedule('partman-auditia-hourly', '0 * * * *', 'SELECT partman.run_maintenance(''public.auditia'')');

-- Opción B: systemd timer / cron en servidor app
-- 0 * * * * postgres psql -c "SELECT partman.run_maintenance('public.auditia');"

-- ============================================================
-- 5. Verificación y monitoreo
-- ============================================================
-- Ver particiones creadas:
-- SELECT * FROM partman.show_partitions('public.auditia', true);

-- Ver configuración:
-- SELECT * FROM partman.part_config WHERE parent_table = 'public.auditia';

-- Comprobar retención:
-- SELECT * FROM partman.check_retention('public.auditia');

-- ============================================================
-- 6. Backup de particiones antes de DROP (opcional, si política lo exige)
-- ============================================================
-- pg_partman permite hook: p_retention_schema = 'partman_archive'
-- Las particiones expiradas se mueven a schema partman_archive en vez de DROP.
-- Para activar:
-- UPDATE partman.part_config SET retention_schema = 'partman_archive' WHERE parent_table = 'public.auditia';
-- CREATE SCHEMA partman_archive;
-- GRANT USAGE ON SCHEMA partman_archive TO app_user;