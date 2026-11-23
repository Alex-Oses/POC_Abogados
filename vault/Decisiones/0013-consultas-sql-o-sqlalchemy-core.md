# 0013 · Consultas: SQL directo o híbrido con SQLAlchemy Core

- **Estado**: Aceptada (2026-11-23, @Rubén)
- **Fecha**: 2026-11-20
- **Autor**: @ia-opencode-ruben
- **Se decide con**: @Rubén (backend)
- **Votos**: @Rubén (backend), 2026-11-23: **SQL directo**. El driver y un mapeador fino; ninguna capa que sepa del esquema.

## Contexto

[[0008-stack-backend]] fijó **SQL explícito** y descartó el ORM; [[0014-stack-backend-c-sharp-java-python]] decide el lenguaje. Queda por decidir *cómo se escribe ese SQL*: a mano con el driver, o con un constructor de consultas. La comparativa se hizo con **SQLAlchemy Core**, que no es el ORM: no hay clases mapeadas ni sesiones con identidad, así que no revertía 0008.

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

**SQL directo**, con el driver y un mapeador de filas que no sabe nada del esquema: `psycopg` 3 + `.sql` con nombre en Python, `Npgsql` + `Dapper` en C#, `JdbcClient` en Java.

- El driver solo hace conexión, parámetros y transacciones. El mapeador convierte filas en el DTO: ~2.000 líneas, MIT, sin dependencias, sin migraciones, sin `DbContext` y sin `Table` que declarar. **No duplica lo que manda Flyway.**
- El SQL es SQL: `JSONB`, vistas, `DISTINCT ON` y `UPDATE ... WHERE estado = 'en_cola'` se copian tal cual del esquema.
- Parámetros siempre (`%s`, `@nombre` + `new { ... }`, `:nombre`), y la inyección desaparece por construcción: no hay API que invite a concatenar.
- Filtros opcionales: una lista de condiciones y otra de parámetros por consulta. Es el único punto donde el híbrido era más cómodo, y no compensa la capa.

Se descartó el **híbrido con SQLAlchemy Core**: resolvía los filtros dinámicos, pero obligaba a mantener a mano una declaración de tablas y vistas contra Flyway. Con 40 rutas y una persona, esa capa cuesta más de lo que ahorra.

## Consecuencias

- **Sin dependencia nueva** en ningún lenguaje: `psycopg` ya estaba, `Dapper` son 2.000 líneas sin dependencias, `JdbcClient` viene en `spring-boot-starter-jdbc`.
- `db/tables.py` desaparece del árbol de [[Estructura del backend (Python)]]: nada declara el esquema salvo Flyway.
- Flyway sigue siendo el dueño del esquema; no entran Alembic, EF Core ni JPA.
- El coste aceptado: los filtros opcionales se concatenan a mano. Se paga con una lista de condiciones y parámetros por consulta.
- El mapeo es explícito: si una columna cambia de nombre, falla la consulta, no un `Table` olvidado.
