# Tablero

Formato: `- [ ] tarea · @dueño · enlace`. Mueve la línea entre secciones en tu PR.

## Pendiente

**Entrega viernes 20/11** (ver [[Equipo]]):
- [ ] Especificación funcional con criterios «cómo comprobarlo»
- [ ] Enfoque técnico: arquitectura y por qué cada opción
- [ ] Pasar la [[Maqueta]] a Figma (html.to.design) y enlazar el prototipo · @Alex
- [ ] Decidir el caso a presentar (justicia gratuita, anonimización o ambos)

Resto:
- [ ] Decidir el stack del backend: Python + FastAPI o C# · [[0008-stack-backend]] · @Rubén @Kevin
- [ ] Cerrar los 8 bloqueantes de [[Coherencia]]: identidad, modelo, export y visto bueno · @Rubén @Marina
- [ ] Decidir identidad: SSO Office 365, cuentas locales o ambas · [[Coherencia]] · @Rubén @Kevin
- [ ] Bajar al modelo `sesiones_usuario`, `tokens_usuario`, `bloques_layout` y la tabla de páginas · [[Coherencia]] · @Marina
- [ ] Unificar el hash del PDF y quitar `expira_en` de 24 h del expediente · [[Coherencia]] · @Rubén
- [ ] Renombrar `visto-bueno`, `{numero}` y `{usuario_id}` antes de Figma · [[Coherencia]] · @Rubén
- [ ] Ajustar Presidio: modelo `lg`, palabras a ignorar, patrones de dirección y matrícula · [[Anonimizacion con Presidio]] · @Alex

- [ ] Resolver la contradicción anonimización automática vs. revisión humana · [[0004-anonimizacion-antes-o-despues-de-revision]]
- [ ] Confirmar la opción 1 de [[0004-anonimizacion-antes-o-despues-de-revision]] (la recomendación está escrita en la decisión) · @Rubén
- [ ] Decidir si el OCR es síncrono o por página asíncrona y ajustar la [[API]]
- [ ] Endpoint que reciba un PDF y devuelva texto por página con su color de semáforo · [[Rendimiento OCR]]
- [ ] Semáforo de calidad: contraste antes del OCR (< 80 → volver a escanear) y heurísticas de texto después
- [ ] Validación de DNI/NIE (letra de control) e IBAN
- [ ] Corrección catalana: «l·l» y apóstrofo tipográfico
- [ ] Alinear el modelo de datos con la API (sesión de 24 h vs. tabla `documentos`) · [[Base de datos]]
- [ ] Dibujar `er-diagram.md` en Mermaid (el README de BBDD lo cita pero no existe)
- [ ] Implementar el PDF final: estructura + reconstrucción con reportlab · [[0007-generacion-pdf-final]]
- [ ] Preparar la reunión con el ICAT (preguntas en [[Propuesta ICAT]])

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
- [x] Diseño del PDF final (reconstrucción desde la estructura) · [[0007-generacion-pdf-final]]
- [x] Revisión de coherencia del proyecto y recorte de A-15 a categorías especiales · [[Coherencia]]

## Preguntas abiertas

<!-- - @destinatario: pregunta · @autor -->
- @Alex: ¿bajamos la protección de `main`? Hoy exige 1 aprobación en todo, y con dos personas con escritura cada PR mío espera a que lo mires: es el mayor freno del día a día. Propuesta en tres pasos, de menos a más: **(1)** `CODEOWNERS` con revisión obligatoria solo de `backend/`, `docs/api/`, `docs/reglas/` y `docs/architecture/migrations/`, y los PR que solo tocan `vault/`, `maqueta/` o `docs/export/` se auto-mergean con CI verde; **(2)** si GitHub no les encaja así, bajar a 0 aprobaciones y exigir solo `Require status checks` + `Require conversation resolution`; **(3)** mantener el bloqueo de push directo a `main` en cualquier caso. Lo que no propongo es quitar la protección: solo el paso por revisión en lo que no es código. · @ia-opencode-ruben
- @Rubén: `GET /documents/{id}/versions/{n}/blocks` en `docs/api/endpoints.md` devuelve un `bbox` por bloque, pero PaddleOCR-VL por Ollama (prompt `OCR:`) devuelve **solo texto, sin coordenadas**. Ahora mismo nada puede rellenar ese `bbox`. Opciones en [[Anonimizacion con Presidio]] § «Riesgo detectado»: exportar un PDF nuevo desde el texto (sin `bbox`) o un segundo OCR solo para las cajas. ¿Cuál encaja con el contrato? · @ia-claude-alex
- @Rubén: `GET /documents/{id}/versions/{n}/blocks` en `docs/api/endpoints.md` devuelve un `bbox` por bloque, pero PaddleOCR-VL por Ollama (prompt `OCR:`) devuelve **solo texto, sin coordenadas**. Ahora mismo nada puede rellenar ese `bbox`. La decisión [[0006-generacion-pdf-final]] ya admite los dos modos en `origen_geometria` (ver [`docs/export/pdf.md`](../docs/export/pdf.md)), así que no bloquea el export: la pregunta es si el OCR definitivo dará las cajas o el contrato debe dejar de pedirlas. · @ia-claude-alex
- @Alex: ¿el servidor definitivo tendrá GPU? La VM actual no la tiene y el OCR se queda en ~260 páginas/hora (100 páginas ≈ 20 min). · @ia-opencode-alex
