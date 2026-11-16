# Tablero

Formato: `- [ ] tarea · @dueño · enlace`. Mueve la línea entre secciones en tu PR.

## Pendiente

**Entrega viernes 20/11** (ver [[Equipo]]):
- [ ] Especificación funcional con criterios «cómo comprobarlo»
- [ ] Enfoque técnico: arquitectura y por qué cada opción
- [ ] Pasar la [[Maqueta]] a Figma (html.to.design) y enlazar el prototipo · @Alex
- [ ] Decidir el caso a presentar (justicia gratuita, anonimización o ambos)

Resto:
- [ ] Confirmar la opción 1 de [[0004-anonimizacion-antes-o-despues-de-revision]] (la recomendación está escrita en la decisión) · @Rubén
- [ ] Decidir si el OCR es síncrono o por página asíncrona y ajustar la [[API]]
- [ ] Endpoint que reciba un PDF y devuelva texto por página con su color de semáforo · [[Rendimiento OCR]]
- [ ] Semáforo de calidad: contraste antes del OCR (< 80 → volver a escanear) y heurísticas de texto después
- [ ] Validación de DNI/NIE (letra de control) e IBAN
- [ ] Corrección catalana: «l·l» y apóstrofo tipográfico
- [ ] Alinear el modelo de datos con la API (sesión de 24 h vs. tabla `documentos`) · [[Base de datos]]
- [ ] Dibujar `er-diagram.md` en Mermaid (el README de BBDD lo cita pero no existe)
- [ ] Implementar el PDF final: estructura + reconstrucción con reportlab · [[0006-generacion-pdf-final]]
- [ ] Preparar la reunión con el ICAT (preguntas en [[Propuesta ICAT]])
- [ ] Prueba de humo del stack en Arm64 y medición del OCR en el servidor · [[Servidor definitivo]] · @Kevin @Alex

## En curso

## Hecho

- [x] Maqueta navegable del flujo completo · [[Maqueta]] · @ia-claude-alex
- [x] Ajuste de Presidio: modelos `sm/md/lg`, palabras a ignorar, patrones de dirección, matrícula, catastral y nombres en mayúsculas · [`docs/presidio.md`](../docs/presidio.md) · @ia-claude-alex
- [x] Presidio medido: 13 configuraciones, corpus de validación y PDF · [[Anonimizacion con Presidio]] · @ia-claude-alex
- [x] Documentación de la [[Maqueta]] con capturas, en `.md` y `.pdf` · @ia-claude-alex
- [x] Propuesta funcional y de diseño · [[Propuesta ICAT]]
- [x] Pruebas de rendimiento de PaddleOCR-VL 1.6 · [[Rendimiento OCR]]
- [x] Benchmark de OCR en línea de comandos y comparativa de equipos (portátil, este portátil sin GPU y VM del servidor) · [[Rendimiento OCR]] · @ia-opencode-alex
- [x] Borrador de endpoints v1 · [[API]]
- [x] Contrato de endpoints v1 completo (40 rutas) y reglas de usuarios y aprobación · [[0005-reglas-usuarios-y-aprobacion]]
- [x] Primer borrador del modelo de datos · [[Base de datos]]
- [x] Diseño del PDF final (reconstrucción desde la estructura) · [[0006-generacion-pdf-final]]
- [x] Servidor definitivo decidido: NVIDIA DGX Spark (GB10, 128 GB unificados, Arm64) · [[Servidor definitivo]] · @Alex

## Preguntas abiertas

<!-- - @destinatario: pregunta · @autor -->
- @Rubén: `GET /documents/{id}/versions/{n}/blocks` en `docs/api/endpoints.md` devuelve un `bbox` por bloque, pero PaddleOCR-VL por Ollama (prompt `OCR:`) devuelve **solo texto, sin coordenadas**. Ahora mismo nada puede rellenar ese `bbox`. La decisión [[0006-generacion-pdf-final]] ya admite los dos modos en `origen_geometria` (ver [`docs/export/pdf.md`](../docs/export/pdf.md)), así que no bloquea el export: la pregunta es si el OCR definitivo dará las cajas o el contrato debe dejar de pedirlas. · @ia-claude-alex
