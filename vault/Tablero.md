# Tablero

Formato: `- [ ] tarea · @dueño · enlace`. Mueve la línea entre secciones en tu PR.

## Pendiente

**Entrega viernes 20/11** (ver [[Equipo]]):
- [ ] Especificación funcional con criterios «cómo comprobarlo»
- [ ] Enfoque técnico: arquitectura y por qué cada opción
- [ ] Pasar la [[Maqueta]] a Figma (html.to.design) y enlazar el prototipo · @Alex
- [ ] Decidir el caso a presentar (justicia gratuita, anonimización o ambos)

Resto:
- [ ] Ajustar Presidio: modelo `lg`, palabras a ignorar, patrones de dirección y matrícula · [[Anonimizacion con Presidio]] · @Alex

- [ ] Resolver la contradicción anonimización automática vs. revisión humana · [[0004-anonimizacion-antes-o-despues-de-revision]]
- [ ] Decidir si el OCR es síncrono o por página asíncrona y ajustar la [[API]]
- [ ] Endpoint que reciba un PDF y devuelva texto por página con su color de semáforo · [[Rendimiento OCR]]
- [ ] Semáforo de calidad: contraste antes del OCR (< 80 → volver a escanear) y heurísticas de texto después
- [ ] Validación de DNI/NIE (letra de control) e IBAN
- [ ] Corrección catalana: «l·l» y apóstrofo tipográfico
- [ ] Alinear el modelo de datos con la API (sesión de 24 h vs. tabla `documentos`) · [[Base de datos]]
- [ ] Dibujar `er-diagram.md` en Mermaid (el README de BBDD lo cita pero no existe)
- [ ] Preparar la reunión con el ICAT (preguntas en [[Propuesta ICAT]])

## En curso

## Hecho

- [x] Maqueta navegable del flujo completo · [[Maqueta]] · @ia-claude-alex
- [x] Primera prueba de Presidio en local · [[Anonimizacion con Presidio]] · @ia-claude-alex
- [x] Propuesta funcional y de diseño · [[Propuesta ICAT]]
- [x] Pruebas de rendimiento de PaddleOCR-VL 1.6 · [[Rendimiento OCR]]
- [x] Borrador de endpoints v1 · [[API]]
- [x] Primer borrador del modelo de datos · [[Base de datos]]

## Preguntas abiertas

<!-- - @destinatario: pregunta · @autor -->
