-- triggers.sql
-- Triggers automáticos: updated_at, hash_anterior encadenado, validaciones
-- Ejecutar DESPUÉS de crear todas las tablas (V9) y ANTES de seeds (V11)

-- ============================================================
-- Extensión requerida para hash
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 1. Función genérica updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.actualizado_en = now();
    RETURN NEW;
END;
$$;

-- Aplicar a tablas con actualizado_en
CREATE TRIGGER trg_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER trg_documentos_updated_at
    BEFORE UPDATE ON documentos
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER trg_reglas_anonimizacion_updated_at
    BEFORE UPDATE ON reglas_anonimizacion
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER trg_configuracion_sistema_updated_at
    BEFORE UPDATE ON configuracion_sistema
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- `revisiones.actualizado_en` es el If-Match del cierre (A-23): lo mantiene este trigger.
CREATE TRIGGER trg_revisiones_updated_at
    BEFORE UPDATE ON revisiones
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================
-- 2. Hash encadenado en auditoria (inmutabilidad)
-- ============================================================
CREATE OR REPLACE FUNCTION audit_compute_hash(row_data jsonb, prev_hash char(64))
RETURNS CHAR(64) LANGUAGE sql IMMUTABLE AS $$
    SELECT encode(
        sha256(
            (row_data || jsonb_build_object('prev_hash', prev_hash))::text
        ),
        'hex'
    )::CHAR(64);
$$;

CREATE OR REPLACE FUNCTION trg_audit_hash_chain()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    last_hash CHAR(64);
    row_json  JSONB;
BEGIN
    -- Obtener hash de la fila anterior (la más reciente)
    SELECT hash_anterior INTO last_hash
    FROM auditoria
    ORDER BY id DESC
    LIMIT 1;

    -- Construir JSON de la fila nueva (sin hash_anterior)
    row_json = jsonb_build_object(
        'evento', NEW.evento,
        'entidad_tipo', NEW.entidad_tipo,
        'entidad_id', NEW.entidad_id,
        'usuario_id', NEW.usuario_id,
        'ip_origen', NEW.ip_origen,
        'user_agent', NEW.user_agent,
        'detalle', NEW.detalle,
        'creado_en', NEW.creado_en
    );

    NEW.hash_anterior = audit_compute_hash(row_json, COALESCE(last_hash, repeat('0',64)::CHAR(64)));
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_audit_hash_chain
    BEFORE INSERT ON auditoria
    FOR EACH ROW EXECUTE FUNCTION trg_audit_hash_chain();

-- ============================================================
-- 3. numero_version auto-incremental por documento
-- ============================================================
CREATE OR REPLACE FUNCTION trg_version_auto_number()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.numero_version IS NULL OR NEW.numero_version = 0 THEN
        SELECT COALESCE(MAX(numero_version), 0) + 1
        INTO NEW.numero_version
        FROM versiones_documento
        WHERE documento_id = NEW.documento_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_version_auto_number
    BEFORE INSERT ON versiones_documento
    FOR EACH ROW EXECUTE FUNCTION trg_version_auto_number();

-- ============================================================
-- 4. Validación: no borrar categoría si tiene anotaciones
-- ============================================================
CREATE OR REPLACE FUNCTION trg_categoria_prevent_delete()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM anotaciones_entidad WHERE categoria_id = OLD.id) THEN
        RAISE EXCEPTION 'No se puede borrar categoría %: tiene % anotaciones asociadas',
            OLD.codigo, (SELECT COUNT(*) FROM anotaciones_entidad WHERE categoria_id = OLD.id);
    END IF;
    RETURN OLD;
END;
$$;

CREATE TRIGGER trg_categoria_prevent_delete
    BEFORE DELETE ON categorias_sensibles
    FOR EACH ROW EXECUTE FUNCTION trg_categoria_prevent_delete();

-- ============================================================
-- 5. Validación: revisor debe tener el rol en usuarios_roles
-- ============================================================
CREATE OR REPLACE FUNCTION trg_revision_validar_revisor()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Nulo es válido: la revisión nace en cola sin dueño (A-05).
    IF NEW.asignado_a IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM usuarios_roles
           WHERE usuario_id = NEW.asignado_a
             AND rol = 'revisor'
       ) THEN
        RAISE EXCEPTION 'Usuario % no tiene rol revisor', NEW.asignado_a;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_revision_validar_revisor
    BEFORE INSERT OR UPDATE ON revisiones
    FOR EACH ROW EXECUTE FUNCTION trg_revision_validar_revisor();

-- ============================================================
-- 6. Auto-actualizar estado documento según versiones/revisiones
-- ============================================================
CREATE OR REPLACE FUNCTION trg_documento_estado_auto()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_tipo        VARCHAR(30);
    v_rev_estado  VARCHAR(30);
    v_documento   UUID;
    v_estado      VARCHAR(50);
BEGIN
    -- El estado se calcula en una variable: `versiones_documento` no tiene columna
    -- `estado`, y la versión anterior de este trigger escribía en NEW.estado.
    IF TG_TABLE_NAME = 'versiones_documento' THEN
        v_documento := NEW.documento_id;
        v_tipo := NEW.tipo_version;
        CASE v_tipo
            WHEN 'ocr_texto'       THEN v_estado := 'ocr_completado';
            WHEN 'anonimizado_ia'  THEN v_estado := 'en_revision';
            WHEN 'revisado_humano' THEN v_estado := 'en_revision';
            WHEN 'final_aprobado'  THEN
                -- A-15: con categoría del art. 9, la aprobación del revisor no basta.
                IF (SELECT requiere_visto_bueno FROM documentos WHERE id = v_documento) THEN
                    v_estado := 'pendiente_visto_bueno';
                ELSE
                    v_estado := 'aprobado';
                END IF;
        END CASE;

    ELSIF TG_TABLE_NAME = 'revisiones' THEN
        v_documento := NEW.documento_id;
        v_rev_estado := NEW.estado;
        CASE v_rev_estado
            WHEN 'aprobado' THEN
                IF (SELECT requiere_visto_bueno FROM documentos WHERE id = v_documento) THEN
                    v_estado := 'pendiente_visto_bueno';
                ELSE
                    v_estado := 'aprobado';
                END IF;
            WHEN 'rechazado_con_cambios' THEN
                v_estado := 'rechazado';
        END CASE;
    END IF;

    IF v_estado IS NOT NULL THEN
        UPDATE documentos SET estado = v_estado, actualizado_en = now()
        WHERE id = v_documento;
    END IF;

    RETURN NULL; -- AFTER trigger
END;
$$;

CREATE TRIGGER trg_documento_estado_auto_version
    AFTER INSERT ON versiones_documento
    FOR EACH ROW EXECUTE FUNCTION trg_documento_estado_auto();

CREATE TRIGGER trg_documento_estado_auto_revision
    AFTER INSERT OR UPDATE ON revisiones
    FOR EACH ROW EXECUTE FUNCTION trg_documento_estado_auto();

-- ============================================================
-- 7. Log automático en auditoria para eventos clave
-- ============================================================
CREATE OR REPLACE FUNCTION trg_audit_log_event()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    ev VARCHAR(100);
    ent_tipo VARCHAR(50);
    ent_id UUID;
    det JSONB;
    usr UUID;
BEGIN
    -- Determinar evento según tabla y operación
    IF TG_TABLE_NAME = 'documentos' AND TG_OP = 'INSERT' THEN
        ev := 'DOCUMENTO_SUBIDO'; ent_tipo := 'documento'; ent_id := NEW.id;
        det := jsonb_build_object('nombre', NEW.nombre_original, 'hash', NEW.hash_sha256);
        usr := NEW.creado_por;

    ELSIF TG_TABLE_NAME = 'documentos' AND TG_OP = 'UPDATE' AND OLD.estado <> NEW.estado THEN
        ev := 'DOCUMENTO_ESTADO_CAMBIO'; ent_tipo := 'documento'; ent_id := NEW.id;
        det := jsonb_build_object('estado_anterior', OLD.estado, 'estado_nuevo', NEW.estado);
        usr := NEW.creado_por;

    ELSIF TG_TABLE_NAME = 'versiones_documento' AND TG_OP = 'INSERT' THEN
        ev := 'VERSION_CREADA'; ent_tipo := 'version'; ent_id := NEW.id;
        det := jsonb_build_object('tipo', NEW.tipo_version, 'motor_ocr', NEW.motor_ocr, 'modelo_ia', NEW.modelo_ia);
        usr := NEW.creado_por;

    ELSIF TG_TABLE_NAME = 'anotaciones_entidad' AND TG_OP = 'INSERT' THEN
        ev := 'ENTIDAD_DETECTADA'; ent_tipo := 'anotacion'; ent_id := NEW.id;
        det := jsonb_build_object('categoria', (SELECT codigo FROM categorias_sensibles WHERE id = NEW.categoria_id),
                                   'accion', NEW.accion_aplicada, 'confianza', NEW.confianza_deteccion);
        usr := NEW.revisado_por;

    ELSIF TG_TABLE_NAME = 'anotaciones_entidad' AND TG_OP = 'UPDATE' AND OLD.accion_aplicada <> NEW.accion_aplicada THEN
        ev := 'ENTIDAD_MODIFICADA_MANUAL'; ent_tipo := 'anotacion'; ent_id := NEW.id;
        det := jsonb_build_object('accion_anterior', OLD.accion_aplicada, 'accion_nueva', NEW.accion_aplicada,
                                   'revisor', NEW.revisado_por);
        usr := NEW.revisado_por;

    ELSIF TG_TABLE_NAME = 'revisiones' AND TG_OP = 'INSERT' THEN
        ev := 'REVISION_INICIADA'; ent_tipo := 'revision'; ent_id := NEW.id;
        det := jsonb_build_object('version_id', NEW.version_id, 'intento', NEW.numero_intento);
        usr := NEW.asignado_a;

    ELSIF TG_TABLE_NAME = 'revisiones' AND TG_OP = 'UPDATE' AND OLD.estado <> NEW.estado THEN
        ev := CASE NEW.estado
            WHEN 'aprobado' THEN 'REVISION_APROBADA'
            WHEN 'rechazado_con_cambios' THEN 'REVISION_RECHAZADA'
            ELSE 'REVISION_ESTADO_CAMBIO' END;
        ent_tipo := 'revision'; ent_id := NEW.id;
        det := jsonb_build_object('estado_anterior', OLD.estado, 'estado_nuevo', NEW.estado);
        usr := NEW.asignado_a;

    ELSIF TG_TABLE_NAME = 'reglas_anonimizacion' AND TG_OP = 'INSERT' THEN
        ev := 'REGLA_CREADA'; ent_tipo := 'regla'; ent_id := NEW.id;
        det := jsonb_build_object('codigo', NEW.codigo, 'version', NEW.version);
        usr := NEW.creado_por;

    ELSIF TG_TABLE_NAME = 'reglas_anonimizacion' AND TG_OP = 'UPDATE' THEN
        ev := 'REGLA_MODIFICADA'; ent_tipo := 'regla'; ent_id := NEW.id;
        det := jsonb_build_object('codigo', NEW.codigo, 'version_anterior', OLD.version, 'version_nueva', NEW.version);
        usr := NEW.creado_por;

    ELSE
        RETURN NEW; -- No loggear
    END IF;

    INSERT INTO auditoria (evento, entidad_tipo, entidad_id, usuario_id, detalle, ip_origen, user_agent)
    VALUES (ev, ent_tipo, ent_id, usr, det, inet_client_addr(), current_setting('application_name', true));

    RETURN NEW;
END;
$$;

-- Aplicar a tablas principales
CREATE TRIGGER trg_audit_documentos
    AFTER INSERT OR UPDATE ON documentos
    FOR EACH ROW EXECUTE FUNCTION trg_audit_log_event();

CREATE TRIGGER trg_audit_versiones
    AFTER INSERT ON versiones_documento
    FOR EACH ROW EXECUTE FUNCTION trg_audit_log_event();

CREATE TRIGGER trg_audit_anotaciones
    AFTER INSERT OR UPDATE ON anotaciones_entidad
    FOR EACH ROW EXECUTE FUNCTION trg_audit_log_event();

CREATE TRIGGER trg_audit_revisiones
    AFTER INSERT OR UPDATE ON revisiones
    FOR EACH ROW EXECUTE FUNCTION trg_audit_log_event();

CREATE TRIGGER trg_audit_reglas
    AFTER INSERT OR UPDATE ON reglas_anonimizacion
    FOR EACH ROW EXECUTE FUNCTION trg_audit_log_event();

COMMENT ON FUNCTION trg_audit_log_event IS 'Autolog en auditoria para trazabilidad legal sin tocar código app';
