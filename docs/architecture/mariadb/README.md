# Arquitectura de Base de Datos — portabilidad a MariaDB

> **Estado:** segunda opción **documentada**, no el despliegue principal. [[0002-postgresql]] sigue **Aceptada**: PostgreSQL 14+ con Flyway es el objetivo y el backend Python (`psycopg` 3, SQL directo) **no cambia**. Esta carpeta es un esquema equivalente y ejecutable para MariaDB, recogido en la decisión [[0018-mariadb-segunda-opcion]] (Propuesta). Para desplegarlo como motor único haría falta una decisión nueva y reescribir el driver del backend.

Fuente del modelo: [`vault/Proyecto/Modelo de datos.md`](../../vault/Proyecto/Modelo%20de%20datos.md) (**v0.3**, 14 tablas y 19 relaciones), la misma que la versión PostgreSQL. Esquema principal: [../README.md](../README.md). No se escriben `V13` ni `V16`, igual que en PostgreSQL.

## Objetivo y versión

- **MariaDB 11.4 LTS o superior** (InnoDB, `utf8mb4`). Funciones usadas: CTE/ventana (10.2+), `CHECK` (10.2.1+), columnas generadas (10.2+), `JSON_MERGE_PATCH` (10.3+), `RENAME COLUMN` (10.5+), índices `DESC` reales (10.8+), `CREATE OR REPLACE VIEW`.
- Sin extensiones de servidor: no hay `pgcrypto`, `uuid-ossp` ni `pg_partman`.
- 14 migraciones `V1`–`V15` (sin `V13`), más `views.sql`, `triggers.sql` y `partitioning.sql`.

## Árbol

```
docs/architecture/mariadb/
├── README.md                 ← esta matriz
├── migrations/
│   ├── V1__create_usuarios.sql
│   ├── V2__create_categorias_sensibles.sql
│   ├── V3__create_documentos.sql
│   ├── V4__create_versiones_documento.sql
│   ├── V5__create_reglas_anonimizacion.sql
│   ├── V6__create_anotaciones_entidad.sql
│   ├── V7__create_revisiones.sql
│   ├── V8__create_auditoria.sql
│   ├── V9__create_configuracion_sistema.sql
│   ├── V10__create_indexes.sql
│   ├── V11__seed_categorias_sensibles.sql
│   ├── V12__seed_configuracion_inicial.sql
│   ├── V14__create_bloques_layout.sql
│   └── V15__flujo_revision_y_export.sql
├── views.sql
├── triggers.sql
└── partitioning.sql
```

## Orden de ejecución

```bash
# 1. Migraciones base (Flyway apuntando a esta carpeta)
flyway -url=jdbc:mariadb://host:3306/icat_anon \
       -locations=filesystem:docs/architecture/mariadb/migrations \
       migrate

# 2. Vistas y triggers (cliente mariadb; los procedures usan DELIMITER)
mariadb -u usuario -p icat_anon < docs/architecture/mariadb/views.sql
mariadb -u usuario -p icat_anon < docs/architecture/mariadb/triggers.sql

# 3. Particionado de auditoria (una sola vez; idempotente)
mariadb -u usuario -p icat_anon < docs/architecture/mariadb/partitioning.sql
```

Si no hay Flyway, aplicar los 14 `V*.sql` en orden numérico con el cliente `mariadb`. Los scripts usan `DELIMITER //`, así que **no se pueden ejecutar desde un driver que envíe una sentencia a la vez** sin antes dividir por delimitador.

## Matriz de tipos

| PostgreSQL | MariaDB | Nota |
|---|---|---|
| `UUID` + `gen_random_uuid()` | `CHAR(36) CHARACTER SET ascii COLLATE ascii_bin` + `UUID()` | Mismo formato textual. `ascii_bin` evita comparaciones case-insensitive y reduce el índice. |
| `JSONB` | `JSON` | En MariaDB es alias de `LONGTEXT` con `JSON_VALID`; **no** es binario y no tiene GIN. Se indexan rutas concretas con columnas generadas. |
| `TIMESTAMPTZ` | `DATETIME(6)` | `TIMESTAMP` de MariaDB tiene rango 1970–2038 y convierte zona horaria; se guarda **UTC** y la app decide la zona de salida. |
| `INET` | `VARCHAR(45) CHARACTER SET ascii COLLATE ascii_bin` | Cubre IPv4 e IPv6; se pierden los operadores `<<=`, `>>=` y la validación de tipo. |
| `BIGSERIAL` | `BIGINT NOT NULL AUTO_INCREMENT` | La secuencia es global también después de particionar. |
| `BOOLEAN` | `BOOLEAN` (`TINYINT(1)`) | Equivalente. |
| `DECIMAL(p,s)` | `DECIMAL(p,s)` | Igual. |
| `CHAR(64)` (hash) | `CHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | Evita que la collation ignore diferencias entre hashes. |
| `TEXT` con `UNIQUE` | `VARCHAR(n)` | MariaDB exige prefijo para indexar `TEXT`. `sso_subject` → `VARCHAR(255)`, `token_hash` → `CHAR(64)`. |
| `COMMENT ON TABLE/COLUMN` | `COMMENT '...'` en `CREATE TABLE` / columna | Equivalente; las vistas no admiten comment, se documenta aquí. |

## Matriz de funciones y sintaxis

| PostgreSQL | MariaDB |
|---|---|
| `now()` | `CURRENT_TIMESTAMP(6)` |
| `sha256(bytea)` + `encode(..., 'hex')` | `SHA2(texto, 64)` |
| `convert_to(x,'UTF8')` | `CONCAT(x, '')` (cast implícito a texto) |
| `row_data \|\| jsonb_build_object(...)` | `JSON_MERGE_PATCH(row_data, JSON_OBJECT(...))` |
| `jsonb_build_object(...)` | `JSON_OBJECT(...)` |
| `::jsonb` | Literal de cadena validado por la columna `JSON` |
| `lower(email)` en índice | Columna generada `email_lower` + índice |
| `inet_client_addr()` | `SUBSTRING_INDEX(USER(), '@', -1)` |
| `current_setting('application_name', true)` | Variable de sesión `@application_name` (o `DATABASE()`) |
| `EXTRACT(EPOCH FROM (b - a))/3600` | `TIMESTAMPDIFF(SECOND, a, b)/3600` |
| `concat_ws(' ', a, b)` | `CONCAT_WS(' ', a, b)` |
| `COUNT(*) FILTER (WHERE c)` | `SUM(CASE WHEN c THEN 1 ELSE 0 END)` |
| `DISTINCT ON` / `JOIN LATERAL` | `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)` en tabla derivada |
| `PERCENTILE_CONT(0.5) WITHIN GROUP` | Mediana con `ROW_NUMBER()` + `COUNT(*) OVER ()` |
| `ON CONFLICT (clave) DO NOTHING` | `INSERT IGNORE` |
| `UPDATE ... FROM` | `UPDATE t JOIN ... SET ...` |
| `ALTER TABLE ... RENAME COLUMN` | Igual (10.5+) |
| `ALTER TABLE ... RENAME INDEX` | Igual |
| `DROP CONSTRAINT` | `DROP CHECK` / `DROP INDEX` / `DROP FOREIGN KEY` según el tipo |
| `RAISE EXCEPTION` | `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '...'` |
| `EXECUTE FUNCTION f()` | Cuerpo del trigger o `CALL sp_...()` |
| `CREATE OR REPLACE FUNCTION` | `DROP FUNCTION IF EXISTS` + `CREATE FUNCTION` |
| `TG_TABLE_NAME`, `TG_OP` | Un trigger por tabla/evento (MariaDB < 12.0 solo admite un evento por trigger) |
| `pg_partman` | `sp_auditoria_add_partition()` / `sp_auditoria_drop_partition()` + Cron/EVENT |

## Límites de portabilidad (leer antes de desplegar)

1. **Índices parciales y de expresión.** MariaDB no los tiene. Los nueve `CREATE INDEX ... WHERE` y los tres `CREATE UNIQUE INDEX ... WHERE` de PostgreSQL se implementan con columnas generadas `PERSISTENT` que valen `NULL` para las filas excluidas. Las columnas generadas **son visibles** en `SELECT *` y ocupan espacio; las consultas que quieran usar el índice deben filtrar por el nombre de la columna generada.
2. **`es_actual` no lo mantiene un trigger.** En PostgreSQL `trg_version_auto_number` actualiza otras filas de `versiones_documento` desde un trigger de esa misma tabla. MariaDB prohíbe eso (error 1442). El trigger MariaDB asigna `numero_version` y marca la fila nueva como actual; **la bajada de las anteriores la hace `sp_insert_version_documento()`**, que la app debe llamar en lugar de un `INSERT` directo. Si se inserta directamente, el índice único `uq_versiones_documento_actual` rechaza la segunda versión vigente.
3. **FK y particiones son incompatibles en InnoDB.** `auditoria` pierde `fk_auditoria_usuario` al particionarse. `trg_usuarios_auditoria_set_null` emula `ON DELETE SET NULL`. `ON UPDATE` no se necesita porque `usuarios.id` no se modifica.
4. **La cadena de hash no es portable.** `JSONB::text` de PostgreSQL y la serialización `JSON` de MariaDB producen cadenas distintas (orden de claves, formato de `TIMESTAMP`, `INET`), así que los hashes difieren entre motores incluso con los mismos datos. E-23 sigue abierto para la versión PostgreSQL; en MariaDB se documenta como diferencia adicional. **No se puede mezclar una cadena empezada en un motor con la otra.**
5. **Mantenimiento de particiones.** No hay `pg_partman`: hay que programar `sp_auditoria_add_partition()` mensualmente y `sp_auditoria_drop_partition()` para la retención de 120 meses. `pmax` nunca se borra.
6. **Regex de seeds.** En `V11` las barras se duplican (`\\d`) porque MariaDB interpreta `\d` como escape no reconocido y lo convierte en `d`.
7. **E-53/E-51 se heredan.** Las columnas que la v0.3 pide y el SQL no trae (`intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso`, `password_cambiado_en`, `otorgado_en`, `otorgado_por`) están ausentes también aquí: [[0012-identidad-y-roles]] las rechaza y hace falta decisión nueva. Los `bbox_*` legacy siguen esperando a @Marina (E-51).

## Comprobación mínima

```sql
SELECT COUNT(*) FROM information_schema.tables
 WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE';  -- 14

SELECT COUNT(*) FROM information_schema.key_column_usage
 WHERE table_schema = DATABASE() AND constraint_name LIKE 'fk_%'; -- relaciones

SELECT TABLE_NAME, PARTITION_NAME FROM information_schema.PARTITIONS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'auditoria';

SELECT COUNT(*) FROM v_documento_actual;
SELECT COUNT(*) FROM v_entidades_pendientes_revision;
SELECT COUNT(*) FROM v_metricas_revisor;
SELECT COUNT(*) FROM v_dashboard_estados;
SELECT COUNT(*) FROM v_entidad_detalle_diff;
```

Sin MariaDB operativo en este equipo, estos scripts están revisados solo por lectura: **no ejecutados**. La validación pendiente es `flyway clean` + `migrate` desde cero, los cinco scripts y una prueba de inserción con dos versiones para comprobar `es_actual`.
