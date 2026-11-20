# 0013 · Consultas: SQL directo o híbrido con SQLAlchemy Core

- **Estado**: Propuesta
- **Fecha**: 2026-11-20
- **Autor**: @ia-opencode-ruben
- **Se decide con**: @Rubén (backend)
- **Votos**: pendiente. La decide @Rubén.

## Contexto

[[0008-stack-backend]] fijó Python 3.12 + FastAPI y **SQL explícito**, con el ORM descartado a propósito. Queda por decidir *cómo se escribe ese SQL*: a mano con `psycopg` 3, o con **SQLAlchemy Core**. Core no es el ORM: no hay clases mapeadas ni sesiones con identidad, así que esta decisión no revierte 0008.

El modelo de @Marina no es genérico: `JSONB`, vistas (`v_documento_actual`, `v_metricas_revisor`), índices parciales, `DISTINCT ON`, particiones y tomas de cola con `UPDATE ... WHERE estado = 'en_cola'`. Flyway es el dueño del esquema y en backend hay una persona.

| Criterio | SQL directo (`psycopg` 3 + `.sql`) | SQLAlchemy Core |
|---|---|---|
| Inyección SQL | Segura con marcadores `%s`; insegura en cuanto alguien escribe un `f"..."`. Depende de la disciplina | Segura por construcción: los valores van siempre parametrizados |
| Verbosidad (consulta simple) | 3 líneas: `execute`, `fetchall`, mapear | 6-8 líneas entre `select()`, `where()`, `execute()` |
| Verbosidad (consulta compleja) | El SQL se lee tal cual; el texto es el que entiende el DBA | Se compone por piezas, pero hay que traducirlo mentalmente a SQL |
| `JSONB` (`metadatos_proceso->>'hash_export'`) | Natural: `->`, `->>`, `@>`, `jsonb_path_query` | Válido, pero los operadores propios de PG se escriben con `text()` u `op()` |
| Vistas | `SELECT * FROM v_...` y listo | Hay que declararlas como `Table` a mano o usar `text()` |
| Índices parciales, `DISTINCT ON`, `LATERAL`, particiones | Copiar y pegar del esquema | Se puede, pero acabas en `text()` más de lo que querrías |
| Mapeo fila → Pydantic | Manual (`dict(row)`), explícito | `mappings()` da el mismo dict. Empate |
| Filtros dinámicos (`?estado=&page=&limit=`) | Concatenas condiciones con cuidado; aquí es donde se cuela el bug | `if estado: q = q.where(...)`, limpio |
| Errores | Los de psycopg, con el nombre real de la columna y el SQLSTATE | Los envuelve; a veces hay que desenvolver para ver el SQLSTATE |
| Validación en runtime | Ninguna (Core tampoco valida contra la BD). Empate | Ninguna |
| Autocompletado de columnas | Ninguno | Con `Table` declaradas, sí |
| Refactor de una columna | Buscar y reemplazar en `.sql` | Cambiar la definición de la tabla; los usos se rompen solos |
| Dependencia extra | Ninguna (`psycopg` ya está) | `sqlalchemy` (~10 MB, MIT) |
| Migraciones | Flyway | Flyway igual: no se usa Alembic |
| Rendimiento | El mínimo overhead | Overhead pequeño e irrelevante: el cuello es la GPU |
| Curva para quien no es experto en Python | El SQL ya lo sabe; falta aprender psycopg (poco) | Hay que aprender SQL **y** la API de Core |
| Mantenimiento por una persona | El SQL vive en `.sql` con nombre y se lee en un tirón | La consulta está repartida entre Python y la cabeza de quien la escribió |

## Decisión

**Híbrido.** SQLAlchemy Core para el 80 % (listados con filtros, CRUD, permisos) y `text()` o ficheros `.sql` con nombre para el 20 % que es PostgreSQL puro: vistas, informes de `v_metricas_revisor`, `JSONB` del hash, `DISTINCT ON` y tomas de cola.

Core cubre justo donde el SQL a mano se rompe (filtros opcionales, listas `IN`, paginación) y bajar a SQL cuando la consulta se complica es una válvula de escape que siempre funciona.

Si se rechaza, todo va con `psycopg` + `.sql` y el riesgo se concentra en la composición dinámica de filtros.

## Consecuencias

- Nueva dependencia `sqlalchemy`, ya prevista en el árbol de [[Estructura del backend]].
- `db/tables.py` declara a mano las tablas y vistas que se consultan con Core. **Si Flyway cambia una columna, hay que tocarlo**: ese coste es la razón de no meterlo todo por Core.
- Flyway sigue siendo el dueño del esquema; no entra Alembic.
- Los `.sql` con nombre se quedan para informes, vistas y colas.
- Queda escrito que «SQLAlchemy» aquí no significa ORM, para que nadie lea que 0008 se ha revertido.
