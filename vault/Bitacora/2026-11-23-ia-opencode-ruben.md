# 2026-11-23 · @ia-opencode-ruben

## Hecho

- 0013 **Aceptada** (23/11, @Rubén): **SQL directo** con `psycopg` + `.sql` y, si 0014 cae en C#, `Npgsql` + `Dapper`. Se descarta el híbrido con SQLAlchemy Core. En el árbol de [[Estructura del backend (Python)]] desaparecen `sqlalchemy`, `db/tables.py` y su bullet de deuda.
- 0015 **Aceptada** (23/11, @Rubén): la identidad de [[0012-identidad-y-roles]] va al final de `V15` editada, no a una migración nueva. Cierra **B1** de [[Coherencia]]; la BD sigue siendo `V1`-`V15` y hay que recrear la base de desarrollo (`flyway clean` + `migrate`).
- Voto de @Rubén en [[0014-stack-backend-c-sharp-java-python]]: **C#**. Python no le convence para un proyecto serio y lo ve mejor que Java para este proyecto. La decisión sigue **Propuesta**: falta el visto bueno de @Marina, @Kevin, @Alex y @Yaser, que llega por Teams.
- `docs/` alineado en lo justo: `docs/pendientes.md` §3-§4 y `docs/reglas/usuarios.md` §7 apuntan a `V15` editada; el stack sigue «en revisión» porque 0014 no se ha cerrado.

## Siguiente

- Cerrar [[0014-stack-backend-c-sharp-java-python]] cuando @Rubén traiga el OK del equipo: entonces pasa a Aceptada, `README.md` y `docs/pendientes.md` dicen C#, y la línea del [[Tablero]] pasa a Hecho.
- Prueba de humo antes de escribir el árbol definitivo: `dotnet new web` + `Npgsql` + una consulta y un endpoint. Dos horas que descubren el runtime antes de la tercera semana.
- Implementar [[0015-identidad-en-v15]]: editar `V15`, `views.sql`, `triggers.sql` y `data-dictionary.md`, y recrear la base de desarrollo. No se toca `docs/architecture/` en esta nota.

## Bloqueos / preguntas

- Ninguno para esta tarea.
