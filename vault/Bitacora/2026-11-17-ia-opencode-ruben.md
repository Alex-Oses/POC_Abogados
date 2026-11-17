# 2026-11-17 · @ia-opencode-ruben

## Hecho

- Documentos de `docs/reglas/` al `.docx` corporativo: `endpoints.docx` y `usuarios.docx` corregidos (tablas con ancho proporcional, portada con la imagen al 67 % de brillo, última página conservada) y `aprobaciones.docx` generado desde `docs/reglas/aprobacion.md`. Los `.docx` viven en `local/`, no se versionan.
- Decisión [[0004-anonimizacion-antes-o-despues-de-revision]] aceptada por @Rubén: el original se guarda cifrado y la anonimización se aplica al construir las versiones de revisión y al exportar.
- Contrato alineado con 0004 en `docs/api/endpoints.md`: `/transform/document` guarda el original cifrado y no anonimiza; `anonymize` es el paso que construye la versión de revisión; el export pinta la versión aprobada.
- Rutas renombradas (I9 de [[Coherencia]]): `/visto-bueno` → `/sign-off`, `{numero}` → `{numero_version}` y `DELETE /admin/sessions/{usuario_id}` → `DELETE /admin/users/{id}/sessions`, en el contrato y en las dos reglas.
- `docs/export/pdf.md` § «Si el OCR no devuelve cajas»: las tres fuentes posibles de geometría (capa de texto del PDF con PyMuPDF, modelo de layout, modo secuencial), por orden de coste.
- Voto de @Rubén en [[0008-stack-backend]]: Python + FastAPI. Faltan @Marina, @Kevin y @Alex.
- Entrega al cliente movida del viernes 20/11 al **viernes 27/11** en [[Equipo]], [[Inicio]] y [[Tablero]].
- [[Tablero]]: la confirmación de 0004, el renombrado y la alineación del contrato pasan a Hecho; se quitan los restos del merge del 16/11 (una línea duplicada del PDF final y una pregunta del `bbox` repetida).

## Siguiente

- Cerrar [[0008-stack-backend]] con @Marina, @Kevin y @Alex.
- Decidir la geometría del PDF: probar si los PDF reales del Colegio traen capa de texto antes de añadir un modelo de layout.

## Bloqueos / preguntas

- Ver [[Tablero]] § Preguntas abiertas: el `bbox` por bloque, la identidad (SSO o local) y los bloqueantes de [[Coherencia]] siguen esperando respuesta de @Rubén.
