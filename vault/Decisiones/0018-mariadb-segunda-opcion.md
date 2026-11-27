# 0018 · MariaDB como segunda opción documentada

- **Estado**: Propuesta (2026-11-26, @ia-opencode-maga369)
- **Fecha**: 2026-11-26
- **Autor**: @ia-opencode-maga369
- **Se decide con**: @Marina (base de datos), @Rubén (backend), @Kevin (despliegue)
- **Votos**: pendientes. Según [[AGENTS]], solo una persona pasa esta nota a **Aceptada**.
- **Relación**: matiza [[0002-postgresql]], que sigue **Aceptada**; no la sustituye ni la deroga.

## Contexto

[[0002-postgresql]] fijó PostgreSQL 14+ con migraciones Flyway como base del POC, y [[0014-stack-backend-c-sharp-java-python]] y [[0013-consultas-sql-o-sqlalchemy-core]] fijaron un backend Python con SQL directo y `psycopg` 3. La arquitectura PostgreSQL está escrita en `docs/architecture/` y alineada con `Modelo-ER-POC-ICAT-v0.3` (14 tablas, 19 relaciones).

El equipo pidió también una arquitectura equivalente para MariaDB para tener una segunda opción sobre la mesa, sin decidir aún el motor de despliegue. No hay instancia de MariaDB operativa en este equipo, así que el esquema está revisado solo por lectura.

## Decisión

1. **PostgreSQL 14+ sigue siendo el motor principal y el objetivo de despliegue.** No se cambia Flyway, no se edita ninguna migración versionada y no se toca el backend Python (`psycopg` 3, consultas `.sql`, vistas y triggers actuales).
2. **MariaDB 11.4 LTS+ queda como alternativa documentada**, con un esquema ejecutable en `docs/architecture/mariadb/`: 14 migraciones `V1`–`V15` (sin `V13` ni `V16`), `views.sql`, `triggers.sql`, `partitioning.sql` y un README con matriz de tipos/funciones y límites.
3. El esquema MariaDB conserva el modelo v0.3, los nombres de tabla y restricción y el orden de ejecución; solo traduce construcciones no portables:
   - `UUID`/`JSONB`/`INET`/`TIMESTAMPTZ` → `CHAR(36) ascii_bin`/`JSON`/`VARCHAR(45)`/`DATETIME(6)` en UTC;
   - índices parciales y de expresión → columnas generadas `PERSISTENT` con `NULL` para las filas excluidas;
   - `LATERAL`, `DISTINCT ON`, `FILTER` y `PERCENTILE_CONT` → tablas derivadas con `ROW_NUMBER()` y `SUM(CASE WHEN ...)`;
   - `pg_partman` → particiones `RANGE COLUMNS` y procedimientos `sp_auditoria_add_partition()` / `sp_auditoria_drop_partition()`.
4. **Límites asumidos y documentados**: un trigger MariaDB no puede actualizar su propia tabla, así que `es_actual` lo gestiona `sp_insert_version_documento()` (la app debe usarlo en lugar de un `INSERT` directo); InnoDB no admite FK en tablas particionadas, así que `auditoria` emula `ON DELETE SET NULL` con un trigger; la cadena de hash no es byte-idéntica entre motores por distinta serialización JSON/tiempo/IP.
5. **Pasar a MariaDB como motor único exigiría una decisión nueva**: habría que reescribir el driver y las consultas del backend, revisar la cadena de custodia y validar el esquema desde cero. Esta nota no autoriza ese cambio.

## Consecuencias

- El despliegue y las pruebas siguen apuntando a PostgreSQL: esta decisión no añade trabajo al backend ni cambia el pipeline de Flyway.
- La carpeta `docs/architecture/mariadb/` es referencia y punto de partida, no un segundo despliegue que mantener en paralelo sin decisión nueva.
- E-23 sigue abierto en PostgreSQL y se hereda en MariaDB con una diferencia añadida: **no se puede mezclar una cadena de auditoría empezada en un motor con la de otro**.
- E-51 (`bbox_*` legacy) y E-53 (columnas de la v0.3 ausentes) se heredan sin resolver: hacen falta @Marina y una decisión nueva respectivamente.
- PostgreSQL 16.4 sí se ha ejecutado desde cero el 26/11 (`V1`–`V15`, vistas, triggers, recreación de `auditoria`, particiones manuales y 15/15 tests). MariaDB sigue sin motor y revisado solo por lectura: falta su `flyway clean` + `migrate`, los tres scripts y una prueba con dos versiones para comprobar `es_actual`. E-56 ya está corregido en el port tras la ejecución PostgreSQL.

## Fuentes

[[0002-postgresql]], [[0013-consultas-sql-o-sqlalchemy-core]], [[0014-stack-backend-c-sharp-java-python]], [[0015-identidad-en-v15]], [[0017-particionado-auditoria]] y [[Registro de errores]] E-23, E-51 y E-53. Esquemas: `docs/architecture/README.md` y `docs/architecture/mariadb/README.md`.
