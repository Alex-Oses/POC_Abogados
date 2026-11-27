# 2026-11-27 · @ia-opencode-maga369

## Hecho

- Integrado `main` (#54) en `base-de-datos-v03`: conflicto resuelto en [[Tablero]] conservando el objetivo de entrega del **lunes 30/11** y retirando la tarea antigua de «34 defectos abiertos», ya cubierta por la cuarta pasada del [[Registro de errores]].
- Respondidas en [[Tablero]] las preguntas dirigidas a @Marina:
  - **Contraste**: no se amplía el `CHECK`; se queda `0-100`. Para el piloto se mantiene `min(c,100)` y el bruto en `contraste_bruto`, documentado como contraste recortado. Si @ia-claude-alex confirma que el umbral es 80 %, se normaliza en backend (`round(c * 100 / 255)`) y se ajusta el semáforo con pruebas con escaneos reales, antes de la demo.
  - **Columnas de revisión y justicia gratuita**: JSON para el piloto; no se añaden columnas ni tabla. Se promoverán solo si aparecen consultas o filtros que lo exijan.
  - **E-51/E-53**: los `bbox_*` legacy se conservan como respaldo sin lectores; el backend usa `bloque_id`. No se añaden columnas de la v0.3 ahora.
- Actualizado [[Registro de errores]]: E-51 pasa de **bloqueado** a **decidido** (se conservan los `bbox_*`; el backend no los lee).
- Puestas en [[Tablero]] las dos propuestas para que las respondan @Rubén y @Kevin: [[0017-particionado-auditoria]] y [[0018-mariadb-segunda-opcion]]. Ambas siguen en **Propuesta** hasta que una persona las acepte. (PR #57 mergeado el mismo 27/11, `c839ded`.)

### Revisión de `main` tras #56–#59 (tarde)

- **Propuestas**: [[0017-particionado-auditoria]] y [[0018-mariadb-segunda-opcion]] siguen en **Propuesta** con el **OK de @Rubén** (27/11); solo falta @Kevin. No hay ninguna propuesta nueva dirigida a @Marina.
- **Pregunta pendiente para @Marina** (estaba en [[2026-11-26 Cambios de la sesión]], no en el Tablero): confirmar que en el servidor no se aplican `triggers.sql` ni `partitioning.sql`. **Confirmado**: el despliegue solo aplica `V1`–`V15` y `views.sql` (`backend/db/init.sh` y el compose); aplicar los triggers duplicaría la cadena de hashes (E-23). `partitioning.sql` queda como script manual para cuando se decida particionar.
- [[Tablero]]: «BBDD» de la entrega del 30/11 marcada como hecha (esquema validado en PostgreSQL 16.4 y aplicado por el compose). Añadida la tarea de decidir qué defectos SQL abiertos se corrigen antes del 30/11 (E-18, E-19, E-20, E-26, E-28 y E-30); las vistas no las usa el backend, así que hoy solo afectan a informes.
- [[Registro de errores]]: **E-22** pasa a **corregido** (lo cerró @ia-opencode-ruben con `SELECT … FOR UPDATE` en `nueva_version`); **E-14** pasa a **descartado** (`V15:199` elimina `usuarios.rol`, así que el `CHECK` de `V1` desaparece; solo quedan dos comentarios).
- [[Equipo]] e [[Inicio]]: la entrega pasa al **lunes 30/11** y la maqueta deja de presentarse como Figma, como ya decía el Tablero desde #54. Corregida la misma fecha en [[Enfoque tecnico]] y en las tres [[Estructura del backend (Python)|estructuras del backend]].
- [[Tablero]]: el **PR #56** pasa de **En curso** a **Hecho** (está mergeado; solo quedan las pruebas de BD, que necesitan PostgreSQL).

## Siguiente

- Que @Kevin vote las dos propuestas en el [[Tablero]]; @Rubén ya dio el OK.
- Decidir los defectos SQL abiertos antes del 30/11 y, si toca, corregir E-18/E-19 (vistas) y E-20.
- Si se confirma el umbral del 80 %, cambiar la normalización de contraste en backend, ajustar el semáforo y añadir la prueba correspondiente.

## Bloqueos / preguntas

- `0017` y `0018` siguen en **Propuesta**: solo una persona puede pasarlas a Aceptada.
- E-53 sigue abierto en los puntos 1, 2, 3 y 7; hoy solo se ha decidido no añadir columnas nuevas.
- `pg_partman` y la validación real de MariaDB siguen pendientes de entorno y decisión.
