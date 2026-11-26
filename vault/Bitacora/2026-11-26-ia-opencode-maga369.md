# 2026-11-26 · @ia-opencode-maga369

## Hecho

- Cerrados los cuatro defectos SQL del tablero: E-01 (`sha256` sobre `bytea` con `convert_to`), E-03 y E-17 (recreación de `auditoria` como tabla particionada con PK `(id, creado_en)`, sin tocar `V8` ni abrir `V16`) y E-16 (`auditia` → `auditoria` en las llamadas a `pg_partman`).
- `partitioning.sql` recrea la tabla solo si no está particionada, conserva secuencia, FK, índices, comentarios y el trigger de hash; `triggers.sql` y `backend/app/db/queries/audit.sql` ordenan la cadena por `(creado_en, id)`.
- Corregida la cabecera de `triggers.sql`, que todavía mandaba ejecutarlo antes de los seeds (E-29). El README manda hacerlo después de `V1`–`V15` y de `views.sql`.
- Escrita la decisión [[0017-particionado-auditoria]] en estado **Propuesta**: cambia la PK de la tabla particionada y el orden de la cadena de auditoría. No contradice 0011 ni 0015 porque no edita migraciones versionadas.
- Actualizados el [[Registro de errores]], el [[Tablero]] y el README de arquitectura en el mismo PR.

## Siguiente

- Que @Marina, @Rubén o @Kevin pasen [[0017-particionado-auditoria]] a **Aceptada** (o la rechacen) antes de desplegar el particionado.
- Ejecutar `flyway clean` + `migrate`, `views.sql`, `triggers.sql` y `partitioning.sql` en PostgreSQL 16 y correr las pruebas de integración del backend (hoy se saltan).

## Bloqueos / preguntas

- No hay motor PostgreSQL ni Docker operativo en este equipo: el SQL está revisado solo por lectura.
- E-23 sigue abierto: el trigger y el backend siguen calculando el hash de la fila de forma distinta. Este cambio solo unifica el orden de la cadena.
- E-51 sigue bloqueado a la espera de la decisión de @Marina sobre los `bbox_*` legacy; no se ha tocado.
