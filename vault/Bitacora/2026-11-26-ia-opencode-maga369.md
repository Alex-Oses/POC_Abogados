# 2026-11-26 · @ia-opencode-maga369

## Hecho

- Cerrados los cuatro defectos SQL del tablero: E-01 (`sha256` sobre `bytea` con `convert_to`), E-03 y E-17 (recreación de `auditoria` como tabla particionada con PK `(id, creado_en)`, sin tocar `V8` ni abrir `V16`) y E-16 (`auditia` → `auditoria` en las llamadas a `pg_partman`).
- `partitioning.sql` recrea la tabla solo si no está particionada, conserva secuencia, FK, índices, comentarios y el trigger de hash; `triggers.sql` y `backend/app/db/queries/audit.sql` ordenan la cadena por `(creado_en, id)`.
- Corregida la cabecera de `triggers.sql`, que todavía mandaba ejecutarlo antes de los seeds (E-29). El README manda hacerlo después de `V1`–`V15` y de `views.sql`.
- Escrita la decisión [[0017-particionado-auditoria]] en estado **Propuesta**: cambia la PK de la tabla particionada y el orden de la cadena de auditoría. No contradice 0011 ni 0015 porque no edita migraciones versionadas.
- Actualizados el [[Registro de errores]], el [[Tablero]] y el README de arquitectura en el mismo PR.
- Escrita la arquitectura MariaDB como **segunda opción documentada** en `docs/architecture/mariadb/`: 14 migraciones `V1`–`V15` (sin `V13` ni `V16`), `views.sql`, `triggers.sql`, `partitioning.sql` y un README con matriz de tipos/funciones y límites. PostgreSQL sigue siendo el motor principal y el backend `psycopg` no cambia.
- Escrita la decisión [[0018-mariadb-segunda-opcion]] en estado **Propuesta**: matiza [[0002-postgresql]] sin derogarla. El README de arquitectura enlaza la carpeta y deja claro que MariaDB no es un despliegue alternativo mientras no haya decisión nueva.

## Siguiente

- Que @Marina, @Rubén o @Kevin pasen [[0017-particionado-auditoria]] y [[0018-mariadb-segunda-opcion]] a **Aceptadas** (o las rechacen) antes de desplegar.
- Ejecutar `flyway clean` + `migrate`, `views.sql`, `triggers.sql` y `partitioning.sql` en PostgreSQL 16 y correr las pruebas de integración del backend (hoy se saltan).
- Validar el esquema MariaDB desde cero (`flyway clean` + `migrate`, los tres scripts y una inserción con dos versiones para comprobar `es_actual`) y, con el motor confirmado por el equipo, pasar a construir la base de datos.

## Bloqueos / preguntas

- No hay motor PostgreSQL ni MariaDB operativo en este equipo: todo el SQL está revisado solo por lectura, ningún script se ha ejecutado.
- E-23 sigue abierto: el trigger y el backend siguen calculando el hash de la fila de forma distinta; en MariaDB la serialización difiere además de motor a motor, así que no se pueden mezclar cadenas.
- E-51 sigue bloqueado a la espera de la decisión de @Marina sobre los `bbox_*` legacy; no se ha tocado ni en PostgreSQL ni en MariaDB.
- E-53 se hereda en el port: faltan columnas de la v0.3 que [[0012-identidad-y-roles]] rechaza y que exigen decisión nueva.
