# Arquitectura de Base de Datos - Anonimización iCAT

> Esquema relacional para sistema de anonimización de documentos judiciales con revisión humana (RGPD/LOPD compliant).

---

## 📁 Estructura

docs/architecture/ ├── README.md # Este archivo ├── data-dictionary.md # Diccionario de datos completo ├── rgpd-considerations.md # Análisis legal RGPD/LOPD + checklist ├── migrations/ # Migraciones Flyway (V1..V15) │ ├── V1__create_usuarios.sql │ ├── V2__create_categorias_sensibles.sql │ ├── V3__create_documentos.sql │ ├── V4__create_versiones_documento.sql │ ├── V5__create_reglas_anonimizacion.sql │ ├── V6__create_anotaciones_entidad.sql │ ├── V7__create_revisiones.sql │ ├── V8__create_auditoria.sql │ ├── V9__create_configuracion_sistema.sql │ ├── V10__create_indexes.sql │ ├── V11__seed_categorias_sensibles.sql │ ├── V12__seed_configuracion_inicial.sql │ ├── V14__create_bloques_layout.sql # modelo de @Marina: bloques y páginas (B3, B5) │ ├── V15__flujo_revision_y_export.sql # cola, visto bueno, identidad y plazos (B1, B4, A-04, A-15, A-20) │   └── (V13 identidad: no se escribe, la BD es definitiva) ├── views.sql # Vistas API-ready (5 vistas) ├── triggers.sql # Triggers automáticos (16 triggers) └── partitioning.sql # Particionado pg_partman (auditoría)


---

## 🚀 Despliegue Rápido

### Requisitos
- PostgreSQL **14+**
- Extensiones (ejecutar como superuser):
  ```sql
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  CREATE EXTENSION IF NOT EXISTS pgcrypto;
  CREATE EXTENSION IF NOT EXISTS pg_partman;  -- solo para partitioning.sql
  ```

### Orden de ejecución

```bash
# 1. Migraciones base (Flyway recomendado)
flyway -url=jdbc:postgresql://host:5432/icat_anon \
       -locations=filesystem:docs/architecture/migrations \
       migrate

# 2. Vistas y triggers (psql directo)
psql -d icat_anon -f docs/architecture/views.sql
psql -d icat_anon -f docs/architecture/triggers.sql

# 3. Particionado auditoría (una sola vez en prod, requiere pg_partman)
psql -d icat_anon -f docs/architecture/partitioning.sql
```
