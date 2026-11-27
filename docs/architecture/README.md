# Arquitectura de Base de Datos — Anonimización iCAT

> Modelo objetivo: **`Modelo-ER-POC-ICAT-v0.3`** (24/11/2026), 14 tablas y 19 relaciones. La edición actual de `V15` ya crea las 14 tablas; quedan algunas columnas del modelo que el SQL no trae (ver E-53 en el [diccionario](data-dictionary.md)).
>
> **Motor principal: PostgreSQL 14+** ([[0002-postgresql]], Aceptada). Existe además un [esquema equivalente para MariaDB](mariadb/README.md) como **segunda opción documentada**, no como despliegue alternativo: [[0018-mariadb-segunda-opcion]] (Propuesta). El backend Python no cambia.

---

## Modelo y esquema

| | Modelo v0.3 | SQL en `migrations/` |
|---|---|---|
| Tablas | 14 | 14 (las tres de identidad/reglas nacen al final de `V15`, [[0015-identidad-en-v15]]) |
| Relaciones con nombre | 19 | las de las 14 tablas, con FK compuesta para `anotaciones_entidad.bloque_id` |
| FK internas | 23 + 1 referencia externa a la tabla de claves | las de V1–V15 |
| Vistas | — | 5 |
| Triggers | — | 16 |

La fuente del modelo es [`vault/Proyecto/Modelo de datos.md`](../../vault/Proyecto/Modelo%20de%20datos.md) y, en detalle, el [diccionario de datos](data-dictionary.md). Consideraciones RGPD: [rgpd-considerations.md](rgpd-considerations.md).

| Tabla del modelo | ¿En `migrations/`? |
|---|---|
| `usuarios` | Sí (`V1` + `V15`); sin los cuatro campos de bloqueo/intentos de la v0.3 |
| `usuarios_roles` | Sí (`V15`); sin `otorgado_en` ni `otorgado_por` |
| `sesiones_usuario` | Sí (`V15`); con `ultimo_uso_en`, ausente en la v0.3 |
| `documentos` | Sí (`V3` + `V15`); el hash del PDF vive en la versión (B8) |
| `paginas_documento` | Sí (`V14`) |
| `versiones_documento` | Sí (`V4` + `V15`), con `es_actual`, `pipeline_version`, `confianza_layout_promedio` y `regla_id` |
| `bloques_layout` | Sí (`V14`) |
| `revisiones` | Sí (`V7` + `V15`) |
| `anotaciones_entidad` | Sí (`V6` + `V15`), con `regla_id` y offsets por bloque (E-21, E-25) |
| `categorias_sensibles` | Sí (`V2` + `V15`), con timestamps |
| `reglas_anonimizacion` | Sí (`V5` + `V15`), con `UNIQUE (codigo, version)` |
| `regla_categorias` | Sí (`V15`) |
| `auditoria` | Sí (`V8`) |
| `configuracion_sistema` | Sí (`V9`) |

**Validado en PostgreSQL 16.4 (26/11)**: base `icat_anon_dev` creada desde cero sin Docker con `V1`–`V15`, `views.sql`, `triggers.sql` y la recreación de `auditoria` (17 tablas base, 5 vistas, 24 FK, 25 triggers, 24 categorías seed, `version_esquema_bd = 15`). Los 15 tests del backend pasan con base. Queda sin ejecutar el mantenimiento de `pg_partman`, que no viene en los binarios oficiales; las particiones de la prueba se crearon a mano. Ver [[Registro de errores]], cuarta pasada.

---

## 📁 Estructura

```text
docs/architecture/
├── README.md                       # Este archivo
├── data-dictionary.md              # Diccionario del modelo v0.3 (14 tablas)
├── rgpd-considerations.md          # Análisis legal RGPD/LOPD + checklist
├── migrations/                     # Migraciones Flyway (V1..V15, sin V13)
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
│   ├── V14__create_bloques_layout.sql     # bloques y páginas (B3, B5)
│   └── V15__flujo_revision_y_export.sql   # cola, visto bueno, identidad y reglas (B1, B4, A-04, A-15, A-20)
├── views.sql                       # Vistas API-ready (5 vistas)
├── triggers.sql                    # Triggers automáticos (16 triggers)
├── partitioning.sql                # Particionado pg_partman (auditoría)
└── mariadb/                        # Segunda opción documentada · [[0018-mariadb-segunda-opcion]]
    ├── README.md                   # Matriz de tipos/funciones y límites
    ├── migrations/                 # V1–V15 adaptadas (sin V13 ni V16)
    ├── views.sql
    ├── triggers.sql
    └── partitioning.sql
```

---

## 🚀 Despliegue rápido

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

# 3. Particionado auditoría (una sola vez en prod, requiere pg_partman).
#    Recrea auditoria si aún no está particionada; la PK pasa a (id, creado_en)
#    según la decisión 0017 (Propuesta). No edita las migraciones Flyway.
psql -d icat_anon -f docs/architecture/partitioning.sql
```

---

## Segunda opción: MariaDB

[`docs/architecture/mariadb/`](mariadb/README.md) contiene el mismo modelo (14 tablas, 19 relaciones) adaptado a MariaDB 11.4 LTS: migraciones `V1`–`V15`, vistas, triggers, particionado y una matriz de tipos/funciones. **PostgreSQL sigue siendo el motor principal** ([[0002-postgresql]]): MariaDB está en [[0018-mariadb-segunda-opcion]] como propuesta, no como despliegue, y el backend `psycopg` no cambia. El README de MariaDB documenta los límites que condicionan la portabilidad (índices parciales, `es_actual`, FK con particiones y cadena de hash).
