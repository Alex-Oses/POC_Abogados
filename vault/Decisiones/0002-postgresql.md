# 0002 · PostgreSQL con migraciones Flyway

- **Estado**: Aceptada (2026-11-19, @Rubén)
- **Fecha**: 2026-11-16
- **Autor**: equipo POC

## Contexto

Existe un primer borrador del modelo en PostgreSQL ([[Base de datos]]), pero el documento de la [[API]] dice que la base de datos aún no está decidida.

## Decisión

Adoptar PostgreSQL 14+ con migraciones Flyway en `docs/architecture/migrations`.

## Consecuencias

Hay que confirmarlo con el equipo y revisar el encaje sesión (API) ↔ documento (BBDD).
