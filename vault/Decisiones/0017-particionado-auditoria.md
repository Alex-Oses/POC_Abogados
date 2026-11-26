# 0017 · Particionado de `auditoria`: PK compuesta y recreación operativa

- **Estado**: Propuesta (2026-11-26, @ia-opencode-maga369)
- **Fecha**: 2026-11-26
- **Autor**: @ia-opencode-maga369
- **Se decide con**: @Marina (base de datos), @Rubén (backend), @Kevin (despliegue)
- **Votos**: pendientes. Según [[AGENTS]], solo una persona pasa esta nota a **Aceptada**.

## Contexto

`V8__create_auditoria.sql:4` crea `id BIGSERIAL PRIMARY KEY` en una tabla normal. `partitioning.sql` quiere particionarla por `creado_en`, pero PostgreSQL no admite `ALTER TABLE … PARTITION BY`: hay que recrearla (E-03). Además, en una tabla particionada toda `PRIMARY KEY` debe incluir la columna de particionado, así que la PK actual no se puede copiar con `LIKE … INCLUDING ALL` (E-17).

La BD `V1`–`V15` está cerrada: [[0011-ajustes-al-modelo-de-marina]] y [[0015-identidad-en-v15]] prohíben editar `V8` y abrir `V16`. El arreglo tiene que vivir en el script operativo, no en Flyway. La cadena de `hash_anterior` lee «la fila anterior» ordenando por `id` en `triggers.sql` y en `backend/app/db/queries/audit.sql`; ese orden debe acompañar al cambio de partición.

## Decisión

1. **No editar `V8` ni crear `V16`.** `partitioning.sql` recrea `auditoria` como tabla particionada por `creado_en` si todavía no lo está; si ya está particionada, no hace nada.
2. **La PK de la tabla particionada es `(id, creado_en)`**. `id` sigue siendo `BIGSERIAL`: la secuencia es global y se conserva al recrear la tabla.
3. **La cadena de hashes ordena por `(creado_en DESC, id DESC)`** en `triggers.sql` y en `audit.sql`, para que ambos sitios coincidan con la clave de partición.
4. La recreación conserva la FK a `usuarios`, los índices de `V10`, los comentarios, la secuencia y el trigger `trg_audit_hash_chain`, y copia las filas existentes antes de sustituir la tabla.
5. Las llamadas a `pg_partman` usan siempre `'public.auditoria'` (E-16).

## Consecuencias

- `partitioning.sql` pasa a ser idempotente y ejecutable en el paso 3 del README; antes fallaba siempre (E-03, E-16, E-17).
- Cambia la noción de «fila anterior» de la cadena de auditoría: pasa a ser la de mayor `creado_en` y, en caso de empate, mayor `id`. Con `creado_en = now()` y una secuencia global, el resultado coincide con el orden anterior en condiciones normales; con timestamps manipulados o reintroducidos, puede diferir.
- No se tocan las migraciones versionadas, así que Flyway no cambia de checksum. Sí hay que re-ejecutar `triggers.sql` (y la recreación ya reengancha el trigger de auditoría).
- **E-23 sigue abierto**: el trigger y el backend calculan el hash con formas distintas de la fila. Este cambio unifica el orden, no el contenido del hash.
- Sin PostgreSQL 16 en este equipo, todo está revisado solo por lectura. Falta ejecutar `flyway clean` + `migrate`, `views.sql`, `triggers.sql` y `partitioning.sql` desde cero, y correr las pruebas de integración del backend.

## Fuentes

[[Registro de errores]] E-01, E-03, E-16, E-17 y E-23; `docs/architecture/migrations/V8__create_auditoria.sql`, `docs/architecture/partitioning.sql`, `docs/architecture/triggers.sql` y `backend/app/db/queries/audit.sql`.
