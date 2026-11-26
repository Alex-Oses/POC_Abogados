-- MariaDB 11.4+ · equivalente de ../triggers.sql
-- Ejecutar DESPUÉS de las migraciones V1–V15 y de views.sql.
-- Diferencias principales frente a PostgreSQL:
--   · no hay TG_TABLE_NAME/TG_OP: cada tabla/evento tiene su propio trigger;
--   · no hay RAISE EXCEPTION: se usa SIGNAL SQLSTATE '45000';
--   · un trigger no puede UPDATE su propia tabla: el pase a es_actual de las
--     versiones anteriores se hace en sp_insert_version_documento (llamado por la app);
--   · sha256(bytea) -> SHA2(texto, 64) sobre la serialización JSON de MariaDB.
--     El hash NO es byte-idéntico al de PostgreSQL (E-23 queda abierto).

DELIMITER //

-- ============================================================
-- 1. updated_at (un trigger por tabla: no hay función genérica de trigger)
-- ============================================================
DROP TRIGGER IF EXISTS trg_usuarios_updated_at//
CREATE TRIGGER trg_usuarios_updated_at BEFORE UPDATE ON usuarios FOR EACH ROW
BEGIN
    SET NEW.actualizado_en = CURRENT_TIMESTAMP(6);
END//

DROP TRIGGER IF EXISTS trg_documentos_updated_at//
CREATE TRIGGER trg_documentos_updated_at BEFORE UPDATE ON documentos FOR EACH ROW
BEGIN
    SET NEW.actualizado_en = CURRENT_TIMESTAMP(6);
END//

DROP TRIGGER IF EXISTS trg_reglas_anonimizacion_updated_at//
CREATE TRIGGER trg_reglas_anonimizacion_updated_at BEFORE UPDATE ON reglas_anonimizacion FOR EACH ROW
BEGIN
    SET NEW.actualizado_en = CURRENT_TIMESTAMP(6);
END//

DROP TRIGGER IF EXISTS trg_configuracion_sistema_updated_at//
CREATE TRIGGER trg_configuracion_sistema_updated_at BEFORE UPDATE ON configuracion_sistema FOR EACH ROW
BEGIN
    SET NEW.actualizado_en = CURRENT_TIMESTAMP(6);
END//

DROP TRIGGER IF EXISTS trg_revisiones_updated_at//
CREATE TRIGGER trg_revisiones_updated_at BEFORE UPDATE ON revisiones FOR EACH ROW
BEGIN
    SET NEW.actualizado_en = CURRENT_TIMESTAMP(6);
END//

-- ============================================================
-- 2. Hash encadenado en auditoria
-- ============================================================
DROP FUNCTION IF EXISTS fn_audit_compute_hash//
CREATE FUNCTION fn_audit_compute_hash(p_row JSON, p_prev CHAR(64))
RETURNS CHAR(64) CHARACTER SET ascii
DETERMINISTIC
NO SQL
BEGIN
    -- JSON_MERGE_PATCH = equivalente de row_data || jsonb_build_object('prev_hash', prev_hash).
    RETURN SHA2(CONCAT(JSON_MERGE_PATCH(p_row, JSON_OBJECT('prev_hash', p_prev))), 64);
END//

DROP TRIGGER IF EXISTS trg_audit_hash_chain//
CREATE TRIGGER trg_audit_hash_chain BEFORE INSERT ON auditoria FOR EACH ROW
BEGIN
    DECLARE v_prev CHAR(64);
    DECLARE v_row JSON;

    -- Mismo orden que PostgreSQL: (creado_en DESC, id DESC), decisión 0017.
    SELECT hash_anterior INTO v_prev
      FROM auditoria
     ORDER BY creado_en DESC, id DESC
     LIMIT 1;

    SET v_row = JSON_OBJECT(
        'evento', NEW.evento,
        'entidad_tipo', NEW.entidad_tipo,
        'entidad_id', NEW.entidad_id,
        'usuario_id', NEW.usuario_id,
        'ip_origen', NEW.ip_origen,
        'user_agent', NEW.user_agent,
        'detalle', NEW.detalle,
        'creado_en', NEW.creado_en
    );

    SET NEW.hash_anterior = fn_audit_compute_hash(v_row, COALESCE(v_prev, REPEAT('0', 64)));
END//

-- Inserción de eventos de auditoría (sustituye a inet_client_addr/current_setting).
DROP PROCEDURE IF EXISTS sp_audit_insert//
CREATE PROCEDURE sp_audit_insert(
    p_evento VARCHAR(100), p_ent_tipo VARCHAR(50), p_entidad_id CHAR(36),
    p_usuario_id CHAR(36), p_detalle JSON
)
BEGIN
    INSERT INTO auditoria (evento, entidad_tipo, entidad_id, usuario_id, detalle, ip_origen, user_agent)
    VALUES (p_evento, p_ent_tipo, p_entidad_id, p_usuario_id, p_detalle,
            SUBSTRING_INDEX(USER(), '@', -1), COALESCE(@application_name, DATABASE()));
END//

DROP TRIGGER IF EXISTS trg_audit_documentos_ai//
CREATE TRIGGER trg_audit_documentos_ai AFTER INSERT ON documentos FOR EACH ROW
BEGIN
    CALL sp_audit_insert('DOCUMENTO_SUBIDO', 'documento', NEW.id, NEW.creado_por,
        JSON_OBJECT('nombre', NEW.nombre_original, 'hash', NEW.hash_sha256));
END//

DROP TRIGGER IF EXISTS trg_audit_documentos_au//
CREATE TRIGGER trg_audit_documentos_au AFTER UPDATE ON documentos FOR EACH ROW
BEGIN
    IF OLD.estado <> NEW.estado THEN
        CALL sp_audit_insert('DOCUMENTO_ESTADO_CAMBIO', 'documento', NEW.id, NEW.creado_por,
            JSON_OBJECT('estado_anterior', OLD.estado, 'estado_nuevo', NEW.estado));
    END IF;
END//

DROP TRIGGER IF EXISTS trg_audit_versiones_ai//
CREATE TRIGGER trg_audit_versiones_ai AFTER INSERT ON versiones_documento FOR EACH ROW
BEGIN
    CALL sp_audit_insert('VERSION_CREADA', 'version', NEW.id, NEW.creado_por,
        JSON_OBJECT('tipo', NEW.tipo_version, 'motor_ocr', NEW.motor_ocr, 'modelo_ia', NEW.modelo_ia));
END//

DROP TRIGGER IF EXISTS trg_audit_anotaciones_ai//
CREATE TRIGGER trg_audit_anotaciones_ai AFTER INSERT ON anotaciones_entidad FOR EACH ROW
BEGIN
    CALL sp_audit_insert('ENTIDAD_DETECTADA', 'anotacion', NEW.id, NEW.revisado_por,
        JSON_OBJECT(
            'categoria', (SELECT codigo FROM categorias_sensibles WHERE id = NEW.categoria_id),
            'accion', NEW.accion_aplicada,
            'confianza', NEW.confianza_deteccion
        ));
END//

DROP TRIGGER IF EXISTS trg_audit_anotaciones_au//
CREATE TRIGGER trg_audit_anotaciones_au AFTER UPDATE ON anotaciones_entidad FOR EACH ROW
BEGIN
    IF OLD.accion_aplicada <> NEW.accion_aplicada THEN
        CALL sp_audit_insert('ENTIDAD_MODIFICADA_MANUAL', 'anotacion', NEW.id, NEW.revisado_por,
            JSON_OBJECT('accion_anterior', OLD.accion_aplicada,
                        'accion_nueva', NEW.accion_aplicada,
                        'revisor', NEW.revisado_por));
    END IF;
END//

DROP TRIGGER IF EXISTS trg_audit_revisiones_ai//
CREATE TRIGGER trg_audit_revisiones_ai AFTER INSERT ON revisiones FOR EACH ROW
BEGIN
    CALL sp_audit_insert('REVISION_INICIADA', 'revision', NEW.id, NEW.asignado_a,
        JSON_OBJECT('version_id', NEW.version_id, 'intento', NEW.numero_intento));
END//

DROP TRIGGER IF EXISTS trg_audit_revisiones_au//
CREATE TRIGGER trg_audit_revisiones_au AFTER UPDATE ON revisiones FOR EACH ROW
BEGIN
    IF OLD.estado <> NEW.estado THEN
        CALL sp_audit_insert(
            CASE NEW.estado
                WHEN 'aprobado' THEN 'REVISION_APROBADA'
                WHEN 'rechazado_con_cambios' THEN 'REVISION_RECHAZADA'
                ELSE 'REVISION_ESTADO_CAMBIO'
            END,
            'revision', NEW.id, NEW.asignado_a,
            JSON_OBJECT('estado_anterior', OLD.estado, 'estado_nuevo', NEW.estado));
    END IF;
END//

DROP TRIGGER IF EXISTS trg_audit_reglas_ai//
CREATE TRIGGER trg_audit_reglas_ai AFTER INSERT ON reglas_anonimizacion FOR EACH ROW
BEGIN
    CALL sp_audit_insert('REGLA_CREADA', 'regla', NEW.id, NEW.creado_por,
        JSON_OBJECT('codigo', NEW.codigo, 'version', NEW.version));
END//

DROP TRIGGER IF EXISTS trg_audit_reglas_au//
CREATE TRIGGER trg_audit_reglas_au AFTER UPDATE ON reglas_anonimizacion FOR EACH ROW
BEGIN
    CALL sp_audit_insert('REGLA_MODIFICADA', 'regla', NEW.id, NEW.creado_por,
        JSON_OBJECT('codigo', NEW.codigo,
                    'version_anterior', OLD.version,
                    'version_nueva', NEW.version));
END//

-- ============================================================
-- 3. numero_version auto-incremental por documento
-- ============================================================
DROP TRIGGER IF EXISTS trg_version_auto_number//
CREATE TRIGGER trg_version_auto_number BEFORE INSERT ON versiones_documento FOR EACH ROW
BEGIN
    DECLARE v_num INT;

    IF NEW.numero_version IS NULL OR NEW.numero_version = 0 THEN
        SELECT COALESCE(MAX(numero_version), 0) + 1 INTO v_num
          FROM versiones_documento
         WHERE documento_id = NEW.documento_id;
        SET NEW.numero_version = v_num;
    END IF;

    SET NEW.es_actual = true;
END//

-- MariaDB no permite que un trigger actualice su propia tabla. La app debe insertar
-- las versiones con este procedimiento para que la anterior deje de ser la vigente.
DROP PROCEDURE IF EXISTS sp_insert_version_documento//
CREATE PROCEDURE sp_insert_version_documento(
    p_id CHAR(36), p_documento_id CHAR(36), p_numero_version INT, p_tipo_version VARCHAR(30),
    p_contenido_texto TEXT, p_contenido_html TEXT, p_ruta_pdf VARCHAR(1000),
    p_motor_ocr VARCHAR(50), p_modelo_ia VARCHAR(100), p_confianza DECIMAL(4,3),
    p_metadatos JSON, p_creado_por CHAR(36)
)
BEGIN
    UPDATE versiones_documento
       SET es_actual = false
     WHERE documento_id = p_documento_id
       AND es_actual;

    INSERT INTO versiones_documento (
        id, documento_id, numero_version, tipo_version, contenido_texto, contenido_html,
        ruta_pdf, motor_ocr, modelo_ia, confianza_layout_promedio, metadatos_proceso,
        creado_por, es_actual
    ) VALUES (
        COALESCE(p_id, UUID()), p_documento_id, p_numero_version, p_tipo_version,
        p_contenido_texto, p_contenido_html, p_ruta_pdf, p_motor_ocr, p_modelo_ia,
        p_confianza, COALESCE(p_metadatos, JSON_OBJECT()), p_creado_por, true
    );
END//

-- ============================================================
-- 4. Validación: no borrar categoría si tiene anotaciones
-- ============================================================
DROP TRIGGER IF EXISTS trg_categoria_prevent_delete//
CREATE TRIGGER trg_categoria_prevent_delete BEFORE DELETE ON categorias_sensibles FOR EACH ROW
BEGIN
    DECLARE v_count INT;

    SELECT COUNT(*) INTO v_count
      FROM anotaciones_entidad
     WHERE categoria_id = OLD.id;

    IF v_count > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'No se puede borrar una categoria con anotaciones asociadas';
    END IF;
END//

-- ============================================================
-- 5. Validación: el revisor debe tener el rol en usuarios_roles
-- ============================================================
DROP PROCEDURE IF EXISTS sp_revision_validar_revisor//
CREATE PROCEDURE sp_revision_validar_revisor(p_asignado CHAR(36))
BEGIN
    -- NULL es válido: la revisión nace en cola sin dueño (A-05).
    IF p_asignado IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM usuarios_roles
         WHERE usuario_id = p_asignado AND rol = 'revisor'
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El usuario no tiene rol revisor';
    END IF;
END//

DROP TRIGGER IF EXISTS trg_revision_validar_revisor_bi//
CREATE TRIGGER trg_revision_validar_revisor_bi BEFORE INSERT ON revisiones FOR EACH ROW
BEGIN
    CALL sp_revision_validar_revisor(NEW.asignado_a);
END//

DROP TRIGGER IF EXISTS trg_revision_validar_revisor_bu//
CREATE TRIGGER trg_revision_validar_revisor_bu BEFORE UPDATE ON revisiones FOR EACH ROW
BEGIN
    CALL sp_revision_validar_revisor(NEW.asignado_a);
END//

-- ============================================================
-- 6. Auto-actualizar estado del documento según versión/revisión
-- ============================================================
DROP PROCEDURE IF EXISTS sp_documento_estado_auto//
CREATE PROCEDURE sp_documento_estado_auto(
    p_documento CHAR(36), p_tipo VARCHAR(30), p_rev_estado VARCHAR(30)
)
BEGIN
    DECLARE v_req BOOLEAN;
    DECLARE v_estado VARCHAR(50) DEFAULT NULL;

    IF p_tipo IS NOT NULL THEN
        CASE p_tipo
            WHEN 'ocr_texto' THEN SET v_estado = 'ocr_completado';
            WHEN 'anonimizado_ia' THEN SET v_estado = 'en_revision';
            WHEN 'revisado_humano' THEN SET v_estado = 'en_revision';
            WHEN 'final_aprobado' THEN
                SELECT requiere_visto_bueno INTO v_req FROM documentos WHERE id = p_documento;
                IF v_req THEN
                    SET v_estado = 'pendiente_visto_bueno';
                ELSE
                    SET v_estado = 'aprobado';
                END IF;
        END CASE;
    ELSEIF p_rev_estado IS NOT NULL THEN
        CASE p_rev_estado
            WHEN 'aprobado' THEN
                SELECT requiere_visto_bueno INTO v_req FROM documentos WHERE id = p_documento;
                IF v_req THEN
                    SET v_estado = 'pendiente_visto_bueno';
                ELSE
                    SET v_estado = 'aprobado';
                END IF;
            WHEN 'rechazado_con_cambios' THEN SET v_estado = 'rechazado';
        END CASE;
    END IF;

    IF v_estado IS NOT NULL THEN
        UPDATE documentos
           SET estado = v_estado, actualizado_en = CURRENT_TIMESTAMP(6)
         WHERE id = p_documento;
    END IF;
END//

DROP TRIGGER IF EXISTS trg_documento_estado_version_ai//
CREATE TRIGGER trg_documento_estado_version_ai AFTER INSERT ON versiones_documento FOR EACH ROW
BEGIN
    CALL sp_documento_estado_auto(NEW.documento_id, NEW.tipo_version, NULL);
END//

DROP TRIGGER IF EXISTS trg_documento_estado_revision_ai//
CREATE TRIGGER trg_documento_estado_revision_ai AFTER INSERT ON revisiones FOR EACH ROW
BEGIN
    CALL sp_documento_estado_auto(NEW.documento_id, NULL, NEW.estado);
END//

DROP TRIGGER IF EXISTS trg_documento_estado_revision_au//
CREATE TRIGGER trg_documento_estado_revision_au AFTER UPDATE ON revisiones FOR EACH ROW
BEGIN
    CALL sp_documento_estado_auto(NEW.documento_id, NULL, NEW.estado);
END//

DELIMITER ;
