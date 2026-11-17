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
- Informe [`docs/pendientes.md`](../../docs/pendientes.md): los tres frentes que no se pueden implementar (identidad, geometría del PDF y modelo de datos), con la tabla de las 14 tablas afectadas y las migraciones `V13`-`V15`. Incluye §6 «Cómo mantenerlo», con los cuatro disparadores de actualización, porque una lista vieja es peor que ninguna.
- Propuesta [[0010-modelo-de-datos]] para @Marina: qué cambia en cada tabla y por qué, tres migraciones no destructivas y un diagrama `mermaid` del modelo objetivo. Cuatro preguntas abiertas (precisión del `bbox`, tabla de seudónimos, `citext` y clave del original cifrado).
- [[Modelo de datos]]: el diagrama que ha dibujado @Marina el 17/11, copiado tal cual, y la comparación con 0010. Marina cierra `requiere_visto_bueno`, `eliminado`, `es_actual`, la trazabilidad de versiones, el `bbox` con tamaño de página y la cadena de hash de la auditoría; quedan abiertos `expira_en` (vuelve B6), el dueño del hash (B8 al revés que 0007), las 5 acciones de anonimización (I1), `revisor_id` frente a `asignado_a` (B4) y el índice de A-04; y falta la tabla de páginas (B5), la marca del cifrado (0004), `sso_subject` (0009) y los seudónimos (I2).
- [[Coherencia]] § «Cómo se cierra» paso 3 y [[Tablero]] apuntan ya a 0010; se retira la tarea de «sesión de 24 h», que B6 dejó obsoleta.

## Siguiente

- Cerrar [[0008-stack-backend]] y [[0009-identidad]] con @Marina, @Kevin y @Alex.
- Cerrar [[0010-modelo-de-datos]] con @Marina: `V14` (bloques, páginas) no depende de nadie y desbloquea OCR, PDF y semáforo.
- Unificar el hash del PDF (B8) antes de implementar el export.

## Bloqueos / preguntas

- Ver [[Tablero]] § Preguntas abiertas: los bloqueantes de [[Coherencia]] (modelo y visto bueno) siguen esperando respuesta de @Rubén.
