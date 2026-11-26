# 2026-11-26 · @ia-opencode-maga369

## Hecho

- Cerrados los cuatro defectos SQL del tablero: E-01 (`sha256` sobre `bytea` con `convert_to`), E-03 y E-17 (recreación de `auditoria` como tabla particionada con PK `(id, creado_en)`, sin tocar `V8` ni abrir `V16`) y E-16 (`auditia` → `auditoria` en las llamadas a `pg_partman`).
- `partitioning.sql` recrea la tabla solo si no está particionada, conserva secuencia, FK, índices, comentarios y el trigger de hash; `triggers.sql` y `backend/app/db/queries/audit.sql` ordenan la cadena por `(creado_en, id)`.
- Corregida la cabecera de `triggers.sql`, que todavía mandaba ejecutarlo antes de los seeds (E-29). El README manda hacerlo después de `V1`–`V15` y de `views.sql`.
- Escrita la decisión [[0017-particionado-auditoria]] en estado **Propuesta**: cambia la PK de la tabla particionada y el orden de la cadena de auditoría. No contradice 0011 ni 0015 porque no edita migraciones versionadas.
- Actualizados el [[Registro de errores]], el [[Tablero]] y el README de arquitectura en el mismo PR.
- Escrita la arquitectura MariaDB como **segunda opción documentada** en `docs/architecture/mariadb/`: 14 migraciones `V1`–`V15` (sin `V13` ni `V16`), `views.sql`, `triggers.sql`, `partitioning.sql` y un README con matriz de tipos/funciones y límites. PostgreSQL sigue siendo el motor principal y el backend `psycopg` no cambia.
- Escrita la decisión [[0018-mariadb-segunda-opcion]] en estado **Propuesta**: matiza [[0002-postgresql]] sin derogarla. El README de arquitectura enlaza la carpeta y deja claro que MariaDB no es un despliegue alternativo mientras no haya decisión nueva.
- Construida la base desde cero en PostgreSQL 16.4 portátil, **sin Docker**, escuchando solo en `127.0.0.1:55432`. Aplicadas `V1`–`V15`, `views.sql`, `triggers.sql` y la recreación de `auditoria` con `ON_ERROR_STOP=1`: 17 tablas base (14 del modelo + 3 particiones), 5 vistas, 24 FK, 25 triggers, 24 categorías seed, `version_esquema_bd = 15`, PK `(id, creado_en)` y tabla particionada.
- La ejecución destapó tres defectos P0 que la revisión por lectura no vio, corregidos en los scripts operativos: **E-54** (`auditoria_pkey` ya existía: la PK now se crea tras `DROP`/`RENAME`), **E-55** (`OLD.estado` en `versiones_documento`: comparaciones con `to_jsonb(OLD/NEW)`) y **E-56** (`CASE` sin `ELSE` con `tipo_version='original'`: `ELSE v_estado := NULL`). E-56 también se arregló en `mariadb/triggers.sql`.
- Creadas particiones manuales solo para validar; `pg_partman` no está en los binarios oficiales, así que las secciones 2+ de `partitioning.sql` quedan sin ejecutar.
- Ejecutados los tests del backend contra la base: dos fallos destaparon **E-57** (U-17 revocaba la sesión más nueva; `ORDER BY creado_en DESC` en `auth.sql`) y **E-58** (`/health` dependía del orden de los tests; estado aislado en `test_sin_bd.py`). Resultado final: **15/15 con `DATABASE_TEST_URL`** y 11 passed + 4 skipped sin ella.
- Validación funcional con datos ficticios: cadena de hash con dos valores distintos, versiones `1,2` con una sola `es_actual`, documento en `ocr_completado` y tres vistas consultables. Registrada en [[Registro de errores]] (cuarta pasada).

## Siguiente

- Que @Marina, @Rubén o @Kevin pasen [[0017-particionado-auditoria]] y [[0018-mariadb-segunda-opcion]] a **Aceptadas** (o las rechacen) antes de desplegar. Ya no falta la validación PostgreSQL de `0017`: está hecha.
- Instalar `pg_partman` en el entorno de despliegue y ejecutar las secciones 2+ de `partitioning.sql` (creación de particiones, mantenimiento y retención) con el job de `pg_cron`.
- Validar el esquema MariaDB desde cero cuando haya motor (`flyway clean` + `migrate`, los tres scripts y dos versiones para comprobar `es_actual`).
- Decidir E-23 (concurrencia de la cadena), E-51 (`bbox_*` legacy, @Marina) y E-53 (columnas de la v0.3).

## Bloqueos / preguntas

- `pg_partman` no viene con PostgreSQL 16.4: las particiones de la prueba se crearon a mano y el mantenimiento automático sigue sin probarse.
- No hay motor MariaDB operativo: ese esquema sigue revisado solo por lectura, aunque E-56 ya está corregido allí.
- E-23 sigue abierto: el trigger y el backend siguen calculando el hash de la fila de forma distinta; en MariaDB la serialización difiere además de motor a motor, así que no se pueden mezclar cadenas.
- E-51 sigue bloqueado a la espera de la decisión de @Marina sobre los `bbox_*` legacy; no se ha tocado ni en PostgreSQL ni en MariaDB.
- E-53 se hereda en el port: faltan columnas de la v0.3 que [[0012-identidad-y-roles]] rechaza y que exigen decisión nueva.
- El servidor PostgreSQL se apaga al terminar la sesión para no dejar el puerto abierto en un ordenador de empresa; el directorio de datos se conserva en la carpeta temporal.
