-- MariaDB 11.4+ · equivalente de ../partitioning.sql
-- Particionado mensual de auditoria + retención. No hay pg_partman: se usa
-- RANGE COLUMNS(creado_en) y dos procedimientos de mantenimiento.
-- Ejecutar UNA VEZ (idempotente) tras migraciones, vistas y triggers.
--
-- Límite de InnoDB: una tabla particionada por el usuario NO puede tener FK.
-- Por eso se retira fk_auditoria_usuario y se emula ON DELETE SET NULL con
-- trg_usuarios_auditoria_set_null. La PK pasa a (id, creado_en) por la misma
-- regla que en PostgreSQL (decisión 0017). El AUTO_INCREMENT id sigue siendo global.

DELIMITER //

-- Añade el mes siguiente dividiendo la partición pmax (conserva los datos que hubiera).
DROP PROCEDURE IF EXISTS sp_auditoria_add_partition//
CREATE PROCEDURE sp_auditoria_add_partition(p_mes DATE)
BEGIN
    DECLARE v_nombre VARCHAR(20);
    DECLARE v_limite VARCHAR(10);
    DECLARE v_existe INT;

    SET v_nombre = CONCAT('p', DATE_FORMAT(p_mes, '%Y_%m'));
    SET v_limite = DATE_FORMAT(DATE_ADD(STR_TO_DATE(DATE_FORMAT(p_mes, '%Y-%m-01'), '%Y-%m-%d'), INTERVAL 1 MONTH), '%Y-%m-%d');

    SELECT COUNT(*) INTO v_existe
      FROM information_schema.PARTITIONS
     WHERE TABLE_SCHEMA = DATABASE()
       AND TABLE_NAME = 'auditoria'
       AND PARTITION_NAME = v_nombre;

    IF v_existe = 0 THEN
        SET @sql = CONCAT(
            'ALTER TABLE auditoria REORGANIZE PARTITION pmax INTO (',
            'PARTITION ', v_nombre, ' VALUES LESS THAN (''', v_limite, '''), ',
            'PARTITION pmax VALUES LESS THAN (MAXVALUE))'
        );
        PREPARE st FROM @sql;
        EXECUTE st;
        DEALLOCATE PREPARE st;
    END IF;
END//

-- Retención: 120 meses = 10 años. Nunca borra pmax.
DROP PROCEDURE IF EXISTS sp_auditoria_drop_partition//
CREATE PROCEDURE sp_auditoria_drop_partition(p_nombre VARCHAR(20))
BEGIN
    DECLARE v_existe INT;

    SELECT COUNT(*) INTO v_existe
      FROM information_schema.PARTITIONS
     WHERE TABLE_SCHEMA = DATABASE()
       AND TABLE_NAME = 'auditoria'
       AND PARTITION_NAME = p_nombre;

    IF v_existe > 0 AND p_nombre <> 'pmax' THEN
        SET @sql = CONCAT('ALTER TABLE auditoria DROP PARTITION `', p_nombre, '`');
        PREPARE st FROM @sql;
        EXECUTE st;
        DEALLOCATE PREPARE st;
    END IF;
END//

-- Sustituto de ON DELETE SET NULL sobre la tabla particionada.
DROP TRIGGER IF EXISTS trg_usuarios_auditoria_set_null//
CREATE TRIGGER trg_usuarios_auditoria_set_null AFTER DELETE ON usuarios FOR EACH ROW
BEGIN
    UPDATE auditoria SET usuario_id = NULL WHERE usuario_id = OLD.id;
END//

-- Recreación idempotente de auditoria como tabla particionada.
DROP PROCEDURE IF EXISTS sp_auditoria_particionar//
CREATE PROCEDURE sp_auditoria_particionar()
BEGIN
    DECLARE v_particiones INT;
    DECLARE v_fk INT;

    SELECT COUNT(*) INTO v_particiones
      FROM information_schema.PARTITIONS
     WHERE TABLE_SCHEMA = DATABASE()
       AND TABLE_NAME = 'auditoria'
       AND PARTITION_NAME IS NOT NULL;

    IF v_particiones > 0 THEN
        -- Ya está particionada: no se toca nada.
        SELECT 'auditoria ya estaba particionada' AS resultado;
    ELSE
        SELECT COUNT(*) INTO v_fk
          FROM information_schema.TABLE_CONSTRAINTS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'auditoria'
           AND CONSTRAINT_TYPE = 'FOREIGN KEY'
           AND CONSTRAINT_NAME = 'fk_auditoria_usuario';

        IF v_fk > 0 THEN
            SET @sql = 'ALTER TABLE auditoria DROP FOREIGN KEY fk_auditoria_usuario';
            PREPARE st FROM @sql;
            EXECUTE st;
            DEALLOCATE PREPARE st;
        END IF;

        SET @sql = 'ALTER TABLE auditoria DROP PRIMARY KEY, ADD PRIMARY KEY (id, creado_en)';
        PREPARE st FROM @sql;
        EXECUTE st;
        DEALLOCATE PREPARE st;

        SET @sql = CONCAT(
            'ALTER TABLE auditoria PARTITION BY RANGE COLUMNS(creado_en) (',
            'PARTITION p2026_01 VALUES LESS THAN (''2026-02-01''),',
            'PARTITION p2026_02 VALUES LESS THAN (''2026-03-01''),',
            'PARTITION p2026_03 VALUES LESS THAN (''2026-04-01''),',
            'PARTITION p2026_04 VALUES LESS THAN (''2026-05-01''),',
            'PARTITION p2026_05 VALUES LESS THAN (''2026-06-01''),',
            'PARTITION p2026_06 VALUES LESS THAN (''2026-07-01''),',
            'PARTITION p2026_07 VALUES LESS THAN (''2026-08-01''),',
            'PARTITION p2026_08 VALUES LESS THAN (''2026-09-01''),',
            'PARTITION p2026_09 VALUES LESS THAN (''2026-10-01''),',
            'PARTITION p2026_10 VALUES LESS THAN (''2026-11-01''),',
            'PARTITION p2026_11 VALUES LESS THAN (''2026-12-01''),',
            'PARTITION p2026_12 VALUES LESS THAN (''2027-01-01''),',
            'PARTITION pmax VALUES LESS THAN (MAXVALUE))'
        );
        PREPARE st FROM @sql;
        EXECUTE st;
        DEALLOCATE PREPARE st;

        SELECT 'auditoria particionada por mes' AS resultado;
    END IF;
END//

DELIMITER ;

CALL sp_auditoria_particionar();

-- ============================================================
-- Mantenimiento (programar con Cron o EVENT; no hay equivalente a pg_partman)
-- ============================================================
-- CALL sp_auditoria_add_partition('2027-01-01');       -- crear el mes siguiente
-- CALL sp_auditoria_drop_partition('p2026_01');        -- aplicar retención de 120 meses

-- Ejemplo de EVENT (requiere event_scheduler=ON):
-- CREATE EVENT ev_auditoria_mensual
--   ON SCHEDULE EVERY 1 MONTH STARTS (CURRENT_DATE + INTERVAL 1 MONTH)
--   DO CALL sp_auditoria_add_partition(DATE_FORMAT(CURRENT_DATE + INTERVAL 2 MONTH, '%Y-%m-01'));

-- Verificación:
-- SELECT PARTITION_NAME, PARTITION_DESCRIPTION
--   FROM information_schema.PARTITIONS
--  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'auditoria'
--  ORDER BY PARTITION_ORDINAL_POSITION;
