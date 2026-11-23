# 2026-11-23 · @ia-opencode-ruben

## Hecho

- 0013 **Aceptada** (23/11, @Rubén): **SQL directo** con `psycopg` + `.sql` y, si 0014 cae en C#, `Npgsql` + `Dapper`. Se descarta el híbrido con SQLAlchemy Core. En el árbol de [[Estructura del backend (Python)]] desaparecen `sqlalchemy`, `db/tables.py` y su bullet de deuda.
- Voto de @Rubén en [[0014-stack-backend-c-sharp-java-python]]: **C#**. Python no le convence para un proyecto serio y lo ve mejor que Java para este proyecto. La decisión sigue **Propuesta**: falta el visto bueno de @Marina, @Kevin, @Alex y @Yaser, que llega por Teams.
- `docs/` sin tocar: mientras 0014 no se cierre, el stack sigue «en revisión» en `README.md` y `docs/pendientes.md`.

## Siguiente

- Cerrar [[0014-stack-backend-c-sharp-java-python]] cuando @Rubén traiga el OK del equipo: entonces pasa a Aceptada, `README.md` y `docs/pendientes.md` dicen C#, y la línea del [[Tablero]] pasa a Hecho.
- Prueba de humo antes de escribir el árbol definitivo: `dotnet new web` + `Npgsql` + una consulta y un endpoint. Dos horas que descubren el runtime antes de la tercera semana.

## Bloqueos / preguntas

- Ninguno para esta tarea.
