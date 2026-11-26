-- partitioning.sql
-- Particionado mensual de auditoria (pg_partman) + retención automática
-- Requiere: CREATE EXTENSION pg_partman; (superuser)
-- Ejecutar UNA VEZ en producción (no en migraciones Flyway normales)
--
-- V8 crea auditoria sin PARTITION BY. PostgreSQL no permite convertirla con
-- ALTER TABLE ... PARTITION BY, así que aquí se recrea. No se edita V8: la BD
-- V1-V15 está cerrada (0011, 0015). La PK de la tabla particionada pasa a
-- (id, creado_en) porque toda PK debe incluir la clave de partición (E-17,
-- decisión 0017). El id sigue siendo BIGSERIAL: la secuencia es global.

-- ============================================================
-- 1. Recrear auditoria como tabla particionada (E-03 y E-17)
-- ============================================================
DO $$
DECLARE
    seq_name text;
BEGIN
    IF to_regclass('public.auditoria') IS NULL THEN
        RAISE EXCEPTION 'No existe public.auditoria: ejecuta primero las migraciones Flyway';
    END IF;

    seq_name := pg_get_serial_sequence('public.auditoria', 'id');

    IF EXISTS (
        SELECT 1
        FROM pg_class
        WHERE oid = 'public.auditoria'::regclass
          AND relkind = 'p'
    ) THEN
        RAISE NOTICE 'public.auditoria ya está particionada; se omite la recreación';
        RETURN;
    END IF;

    -- La secuencia sobrevive al DROP si deja de estar ligada a la columna vieja.
    IF seq_name IS NOT NULL THEN
        EXECUTE format('ALTER SEQUENCE %s OWNED BY NONE', seq_name);
    END IF;

    -- Sin INCLUDING CONSTRAINTS: la PK antigua (solo id) no es válida al particionar.
    CREATE TABLE public.auditoria_partitioned (
        LIKE public.auditoria
            INCLUDING DEFAULTS INCLUDING IDENTITY INCLUDING COMMENTS INCLUDING STORAGE
    ) PARTITION BY RANGE (creado_en);

    ALTER TABLE public.auditoria_partitioned
        ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id, creado_en);

    ALTER TABLE public.auditoria_partitioned
        ADD CONSTRAINT auditoria_usuario_id_fkey
        FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE SET NULL;

    INSERT INTO public.auditoria_partitioned (
        id, evento, entidad_tipo, entidad_id, usuario_id,
        ip_origen, user_agent, detalle, hash_anterior, creado_en
    )
    SELECT id, evento, entidad_tipo, entidad_id, usuario_id,
           ip_origen, user_agent, detalle, hash_anterior, creado_en
      FROM public.auditoria;

    COMMENT ON TABLE public.auditoria_partitioned IS
        'Registro inmutable de todas las acciones (legal compliance)';

    DROP TABLE public.auditoria;
    ALTER TABLE public.auditoria_partitioned RENAME TO auditoria;

    IF seq_name IS NOT NULL THEN
        EXECUTE format('ALTER SEQUENCE %s OWNED BY public.auditoria.id', seq_name);
        EXECUTE format(
            'SELECT setval(%L, COALESCE((SELECT MAX(id) FROM public.auditoria), 1), (SELECT count(*) > 0 FROM public.auditoria))',
            seq_name
        );
    END IF;

    -- V10 creó estos índices sobre la tabla antigua; el DROP los eliminó.
    CREATE INDEX idx_auditoria_entidad ON public.auditoria (entidad_tipo, entidad_id);
    CREATE INDEX idx_auditoria_usuario_fecha ON public.auditoria (usuario_id, creado_en DESC);
    CREATE INDEX idx_auditoria_evento_fecha ON public.auditoria (evento, creado_en DESC);

    -- triggers.sql ya creó la función; el DROP se llevó por delante el trigger.
    IF to_regprocedure('public.trg_audit_hash_chain()') IS NOT NULL THEN
        CREATE TRIGGER trg_audit_hash_chain
            BEFORE INSERT ON public.auditoria
            FOR EACH ROW EXECUTE FUNCTION trg_audit_hash_chain();
    END IF;
END $$;

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
-- recreados arriba tras la partición; pg_partman los propaga a las particiones.
-- CREATE INDEX idx_auditoria_entidad ON public.auditoria(entidad_tipo, entidad_id);
-- CREATE INDEX idx_auditoria_usuario_fecha ON public.auditoria(usuario_id, creado_en DESC);
-- CREATE INDEX idx_auditoria_evento_fecha ON public.auditoria(evento, creado_en DESC);

-- Forzar creación en particiones existentes (E-16: el padre es 'public.auditoria'):
SELECT partman.run_maintenance(p_parent_table := 'public.auditoria');

-- ============================================================
-- 4. Job cron para mantenimiento (ejecutar cada hora via pg_cron o cron externo)
-- ============================================================
-- Opción A: pg_cron (extensión en BD)
-- SELECT cron.schedule('partman-auditoria-hourly', '0 * * * *', 'SELECT partman.run_maintenance(''public.auditoria'')');

-- Opción B: systemd timer / cron en servidor app
-- 0 * * * * postgres psql -c "SELECT partman.run_maintenance('public.auditoria');"

-- ============================================================
-- 5. Verificación y monitoreo
-- ============================================================
-- Ver particiones creadas:
-- SELECT * FROM partman.show_partitions('public.auditoria', true);

-- Ver configuración:
-- SELECT * FROM partman.part_config WHERE parent_table = 'public.auditoria';

-- Comprobar retención:
-- SELECT * FROM partman.check_retention('public.auditoria');

-- ============================================================
-- 6. Backup de particiones antes de DROP (opcional, si política lo exige)
-- ============================================================
-- pg_partman permite hook: p_retention_schema = 'partman_archive'
-- Las particiones expiradas se mueven a schema partman_archive en vez de DROP.
-- Para activar:
-- UPDATE partman.part_config SET retention_schema = 'partman_archive' WHERE parent_table = 'public.auditoria';
-- CREATE SCHEMA partman_archive;
-- GRANT USAGE ON SCHEMA partman_archive TO app_user;
