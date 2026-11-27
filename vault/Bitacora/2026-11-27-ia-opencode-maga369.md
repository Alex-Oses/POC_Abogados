# 2026-11-27 · @ia-opencode-maga369

## Hecho

- Integrado `main` (#54) en `base-de-datos-v03`: conflicto resuelto en [[Tablero]] conservando el objetivo de entrega del **lunes 30/11** y retirando la tarea antigua de «34 defectos abiertos», ya cubierta por la cuarta pasada del [[Registro de errores]].
- Respondidas en [[Tablero]] las preguntas dirigidas a @Marina:
  - **Contraste**: no se amplía el `CHECK`; se queda `0-100`. Para el piloto se mantiene `min(c,100)` y el bruto en `contraste_bruto`, documentado como contraste recortado. Si @ia-claude-alex confirma que el umbral es 80 %, se normaliza en backend (`round(c * 100 / 255)`) y se ajusta el semáforo con pruebas con escaneos reales, antes de la demo.
  - **Columnas de revisión y justicia gratuita**: JSON para el piloto; no se añaden columnas ni tabla. Se promoverán solo si aparecen consultas o filtros que lo exijan.
  - **E-51/E-53**: los `bbox_*` legacy se conservan como respaldo sin lectores; el backend usa `bloque_id`. No se añaden columnas de la v0.3 ahora.
- Actualizado [[Registro de errores]]: E-51 pasa de **bloqueado** a **decidido** (se conservan los `bbox_*`; el backend no los lee).
- Puestas en [[Tablero]] las dos propuestas para que las respondan @Rubén y @Kevin: [[0017-particionado-auditoria]] y [[0018-mariadb-segunda-opcion]]. Ambas siguen en **Propuesta** hasta que una persona las acepte.

## Siguiente

- Que @Rubén y @Kevin respondan a las dos propuestas en el [[Tablero]].
- Si se confirma el umbral del 80 %, cambiar la normalización de contraste en backend, ajustar el semáforo y añadir la prueba correspondiente.
- Revisar y mergear el PR #52, que ya incluye la validación PostgreSQL 16 y estas respuestas.

## Bloqueos / preguntas

- `0017` y `0018` siguen en **Propuesta**: solo una persona puede pasarlas a Aceptada.
- E-53 sigue abierto en los puntos 1, 2, 3 y 7; hoy solo se ha decidido no añadir columnas nuevas.
- `pg_partman` y la validación real de MariaDB siguen pendientes de entorno y decisión.
