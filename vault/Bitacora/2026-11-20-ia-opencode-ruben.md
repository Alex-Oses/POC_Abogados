# 2026-11-20 · @ia-opencode-ruben

## Hecho

- `README.md` alineado con lo mergeado el 19/11 (PR #34) y con la maqueta del 20/11 (PR #35): contrato en «propuesta, 40 rutas», fila nueva de reglas de negocio y exportación descrita como PDF reconstruido sin píxeles del escaneo.
- El árbol de carpetas deja de prometer un «diagrama» dentro de `docs/architecture/`: el ER vigente es [[Modelo de datos]].
- Tercera pasada del [[Registro de errores]]: 20 hallazgos nuevos (E-31 a E-50) contra el contrato, el export, el RGPD y la maqueta; el [[Tablero]] pasa a 34 defectos abiertos. Sin tocar `docs/architecture/` ni migraciones.
- Arreglados once de ellos (E-31, E-32, E-35, E-37, E-40, E-41, E-45, E-46, E-48, E-49 y E-50): contrato, `pdf.md`, README de arquitectura, maqueta, `usuarios.md`, `pendientes.md`, [[Modelo de datos]] y U-12. Quedan fuera E-33 (decisión de diseño), E-34, E-36, E-38, E-39 y E-44 (decisión y/o BD), E-42, E-43 y E-47 (viven en migraciones).
- 0009 aceptada por @Rubén: SSO del ICAT sin gestión de cuentas y admin local solo de desarrollo; la opción de cuentas locales queda como alternativa si el ICAT no puede dar SSO en plazo. B2 resuelto en [[Coherencia]]; `docs/pendientes.md` y el contrato dejan de esperarla.
- 0012: @Rubén confirma la tabla `usuarios_roles` de @Marina y no ve problema en el `JOIN`/`EXISTS` de la vista ni en el trigger; sigue **Propuesta** a falta de @Kevin y @Alex.

- [[0008-stack-backend]] se aceptó el 20/11 con Python 3.12 + FastAPI y se **reabrió el mismo día**: al sacar el ETL del backend (§2 del [[Enfoque tecnico]]) desaparece el argumento de «un solo lenguaje». 0008 queda **Sustituida por [[0014-stack-backend-c-sharp-java-python]]**, en **Propuesta** y a falta de @Rubén, que compara C#, Java y Python con sus seis criterios (pocas librerías, legibilidad, responsabilidades, Docker, tipado y velocidad).
- El equipo son cinco personas, @Yaser incluido (ETL): queda escrito en [[Equipo]] para que no dependa de lo que cada uno recuerde.
- [[Coherencia]] actualizada el 20/11: de once contradicciones queda una (B1); I1, H6 y H8 se cerraron con `V15`, e I2, I3 y H5 con el contrato y 0004.
- Nueva [[0013-consultas-sql-o-sqlalchemy-core]] en **Propuesta**, encargada a @Rubén: SQL directo con `psycopg` o híbrido con SQLAlchemy Core para el 80 % y `text()`/`.sql` para vistas, informes y colas.
- [[Estructura del backend]]: borrador con el árbol de carpetas y los imports previstos, para editar entre @Rubén y yo. Handlers síncronos, `services/` y `middleware/` separados, sin `modules/OCR` (eso es ETL).

## Siguiente

- Revisar los 34 defectos que siguen abiertos en el [[Registro de errores]] y decidir cuáles entran antes del 27/11.
- @Rubén decide [[0014-stack-backend-c-sharp-java-python]] (C#, Java o Python) y [[0013-consultas-sql-o-sqlalchemy-core]].

## Bloqueos / preguntas

- Ninguno para esta tarea.
