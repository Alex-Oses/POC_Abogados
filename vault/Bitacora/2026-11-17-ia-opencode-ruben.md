# 2026-11-17 · @ia-opencode-ruben

## Hecho

- Documentos de `docs/reglas/` al `.docx` corporativo: `endpoints.docx` y `usuarios.docx` corregidos (tablas con ancho proporcional, portada con la imagen al 67 % de brillo, última página conservada) y `aprobaciones.docx` generado desde `docs/reglas/aprobacion.md`. Los `.docx` viven en `local/`, no se versionan.
- Decisión [[0004-anonimizacion-antes-o-despues-de-revision]] aceptada por @Rubén: el original se guarda cifrado y la anonimización se aplica al construir las versiones de revisión y al exportar.
- Contrato alineado con 0004 en `docs/api/endpoints.md`: `/transform/document` guarda el original cifrado y no anonimiza; `anonymize` es el paso que construye la versión de revisión; el export pinta la versión aprobada.
- Rutas renombradas (I9 de [[Coherencia]]): `/visto-bueno` → `/sign-off`, `{numero}` → `{numero_version}` y `DELETE /admin/sessions/{usuario_id}` → `DELETE /admin/users/{id}/sessions`, en el contrato y en las dos reglas.
- Geometría del PDF: se decide **por documento** (capa de texto del PDF original → modelo de layout → secuencial). Escrito en `docs/export/pdf.md` § «Si el OCR no devuelve cajas»; los documentos del Colegio aún no están medidos.
- `expira_en` fuera del expediente (B6): la regla A-21 solo lo deja como TTL de los temporales del OCR y el contrato deja de devolver `404` por caducidad en texto, PDF y export.
- Propuesta [[0009-identidad]]: SSO del ICAT + un admin local de emergencia. Voto de @Rubén a favor; falta @Kevin, @Marina y @Alex.
- Voto de @Rubén en [[0008-stack-backend]]: Python + FastAPI. Faltan @Marina, @Kevin y @Alex.
- Entrega al cliente movida del viernes 20/11 al **viernes 27/11** en [[Equipo]], [[Inicio]] y [[Tablero]].
- [[Tablero]]: pasan a Hecho la confirmación de 0004, el renombrado, la alineación del contrato, la caducidad y la geometría del PDF; se retira la pregunta del `bbox`, ya respondida, y los restos del merge del 16/11.
- Comando `/decisiones` (`.opencode/commands/decisiones.md`) con `scripts/decisiones.py`: lee `vault/Decisiones/` y `vault/Tablero.md` y devuelve en una tabla qué propuestas, preguntas y tareas esperan a una persona. Sin explorar la bóveda, para gastar poco.
- Comando `/decidir` (`.opencode/commands/decidir.md`): registra un OK o un voto sobre una decisión (`/decidir 0002 mi OK`) con un procedimiento fijo — cabecera de la decisión, tablero, coherencia, bitácora y commit en la rama actual. Sin script y sin recorrer la bóveda.

## Siguiente

- Cerrar [[0008-stack-backend]] y [[0009-identidad]] con @Marina, @Kevin y @Alex.
- Unificar el hash del PDF (B8) antes de implementar el export.

## Bloqueos / preguntas

- Ver [[Tablero]] § Preguntas abiertas: los bloqueantes de [[Coherencia]] (modelo y visto bueno) siguen esperando respuesta de @Rubén.
