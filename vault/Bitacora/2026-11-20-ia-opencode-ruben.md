# 2026-11-20 · @ia-opencode-ruben

## Hecho

- `README.md` alineado con lo mergeado el 19/11 (PR #34) y con la maqueta del 20/11 (PR #35): contrato en «propuesta, 40 rutas», fila nueva de reglas de negocio y exportación descrita como PDF reconstruido sin píxeles del escaneo.
- El árbol de carpetas deja de prometer un «diagrama» dentro de `docs/architecture/`: el ER vigente es [[Modelo de datos]].
- Tercera pasada del [[Registro de errores]]: 20 hallazgos nuevos (E-31 a E-50) contra el contrato, el export, el RGPD y la maqueta; el [[Tablero]] pasa a 45 defectos abiertos. Sin tocar `docs/architecture/` ni migraciones.

- 0009 aceptada por @Rubén: SSO del ICAT sin gestión de cuentas y admin local solo de desarrollo; la opción de cuentas locales queda como alternativa si el ICAT no puede dar SSO en plazo. B2 resuelto en [[Coherencia]]; `docs/pendientes.md` y el contrato dejan de esperarla.
- 0012: @Rubén confirma la tabla `usuarios_roles` de @Marina y no ve problema en el `JOIN`/`EXISTS` de la vista ni en el trigger; sigue **Propuesta** a falta de @Kevin y @Alex.

## Siguiente

- Cambiar en la maqueta el texto «Zones de la imatge esborrades» (I2): el PDF final no lleva ninguna imagen del original.

## Bloqueos / preguntas

- Ninguno para esta tarea.
