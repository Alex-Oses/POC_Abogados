#!/bin/sh
# Aplica V1..V15 en orden de versión (no alfabético) y las vistas.
# Solo para desarrollo: en producción manda Flyway (docs/architecture/README.md).
set -e
for f in $(ls /migrations/migrations/V*.sql | sort -V); do
  echo "aplicando $f"
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
done
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /migrations/views.sql
# Base de pruebas con el mismo esquema.
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE icat_test TEMPLATE $POSTGRES_DB"
