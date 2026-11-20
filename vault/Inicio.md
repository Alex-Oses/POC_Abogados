# POC Abogados · ICAT

Bóveda compartida del equipo. Vive dentro del repo: cada `git pull` la actualiza para todos, y se cambia por PR como el código.

## Mapa

- [[Equipo]]: quién lleva qué, herramientas y la entrega del viernes 27/11
- [[Tablero]]: tareas, quién las lleva y preguntas abiertas
- [[Registro de errores]]: defectos encontrados en el repo, con evidencia y estado
- Proyecto
  - [[Maqueta]]: prototipo navegable del flujo completo
  - [[Propuesta ICAT]]: qué se construye y para quién
  - [[Rendimiento OCR]]: resultados de PaddleOCR-VL 1.6
  - [[API]]: contrato HTTP v1
  - [[Base de datos]]: modelo PostgreSQL
  - [[Modelo de datos]]: modelo de @Marina y en qué se diferencia de 0010
  - [[Coherencia]]: contradicciones abiertas entre contrato, modelo y maqueta
  - [[Enfoque tecnico]]: enfoque del backend y su frontera con el ETL (entrega 27/11, propuesta)
  - [[Estructura del backend (Python)]] · [[Estructura del backend (CSharp)]] · [[Estructura del backend (Java)]]: carpetas e imports previstos, una por lenguaje
- `docs/api/` y `docs/reglas/`: contrato completo y reglas de negocio (detalle)
- `docs/export/`: generación del PDF final desde la estructura guardada
- `vault/Investigacion/`: investigaciones con su coste (deuda técnica), p. ej. [[Anonimizacion con Presidio]]; los scripts de los bancos de pruebas están en `investigacion/`
- `Decisiones/`: decisiones de diseño (ADR)
- `Bitacora/`: una nota por autor y día
- `Plantillas/`: plantillas de decisión y bitácora

## Normas

- Personas e IAs siguen [AGENTS.md](../AGENTS.md).
- Firma: `@nombre` para personas, `@ia-<herramienta>-<persona>` para agentes.
- Sin datos reales ni personales.
