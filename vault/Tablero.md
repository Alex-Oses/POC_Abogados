# Tablero

Formato: `- [ ] tarea · @dueño · enlace`. Mueve la línea entre secciones en tu PR.

## Pendiente

**Entrega viernes 27/11** (ver [[Equipo]]):
- [ ] Especificación funcional con criterios «cómo comprobarlo»
- [ ] Pasar la [[Maqueta]] a Figma (html.to.design) y enlazar el prototipo · @Alex
- [ ] Decidir el caso a presentar (justicia gratuita, anonimización o ambos)

Resto:
- [ ] Decidir el stack del backend: Python + FastAPI o C# · [[0008-stack-backend]] · @Rubén @Kevin
- [ ] Cerrar los 8 bloqueantes de [[Coherencia]]: identidad, modelo, export y visto bueno · @Rubén @Marina
- [ ] Decidir identidad: SSO del ICAT sin gestión de cuentas y admin local solo de desarrollo · [[0009-identidad]] · @Rubén @Kevin @Marina @Alex
- [ ] Aceptar el modelo de roles: tres roles, sin supervisor y varios por usuario · [[0012-identidad-y-roles]] · @Marina @Kevin @Alex
- [ ] Escribir `V13` con `usuarios_roles` y `sso_subject` (espera 0009 y 0012) · @Marina
- [ ] Sustituir el login por el callback SSO en el contrato (espera 0009) · @Rubén
- [ ] Decidir la doble transcripción (A-24): qué se guarda de la segunda lectura y cómo se marca el diff en la revisión · [[0005-reglas-usuarios-y-aprobacion]] · @Rubén @Alex
- [ ] Confirmar si `/assign` y `/sign-off` salen del contrato (cola libre y A-15 en pausa) · @Rubén
- [ ] Unificar el hash del PDF (B8): un solo dueño, por versión · [[Coherencia]] · @Rubén
- [ ] Ajustar Presidio: modelo `lg`, palabras a ignorar, patrones de dirección y matrícula · [[Anonimizacion con Presidio]] · @Alex

- [ ] Decidir si el OCR es síncrono o por página asíncrona y ajustar la [[API]]
- [ ] Endpoint que reciba un PDF y devuelva texto por página con su color de semáforo · [[Rendimiento OCR]]
- [ ] Endpoint `GET /documents/{id}/pages` con el semáforo por página · [[0011-ajustes-al-modelo-de-marina]]
- [ ] Semáforo de calidad: contraste antes del OCR (< 80 → volver a escanear) y heurísticas de texto después
- [ ] Validación de DNI/NIE (letra de control) e IBAN
- [ ] Corrección catalana: «l·l» y apóstrofo tipográfico
- [ ] Dibujar `er-diagram.md` en Mermaid (el README de BBDD lo cita pero no existe)
- [ ] Implementar el PDF final: estructura + reconstrucción con reportlab · [[0007-generacion-pdf-final]]
- [ ] Preparar la reunión con el ICAT (preguntas en [[Propuesta ICAT]])
- [ ] Prueba de humo del stack en Arm64 y medición del OCR en el servidor · [[Servidor definitivo]] · @Kevin @Alex

## En curso

## Hecho

- [x] Bajar al modelo de @Marina en migraciones: `V14` y `V15` escritas y [[0011-ajustes-al-modelo-de-marina]] **aceptada** (17/11, @Marina) · PR #28 pendiente de merge · `V13` espera a [[0009-identidad]] y `V16` al hash (B8) · [[0010-modelo-de-datos]] · @ia-opencode-maga369
- [x] Enfoque técnico del backend (propuesta) · [[Enfoque tecnico]] · @ia-opencode-ruben
- [x] Enfoque técnico del backend (propuesta) · [[Enfoque tecnico]] · @ia-opencode-ruben
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
- [x] Decisión [[0004-anonimizacion-antes-o-despues-de-revision]] aceptada: el original se guarda cifrado y se anonimiza al construir las versiones y al exportar · @Rubén
- [x] Contrato alineado con 0004: `POST /transform/document` guarda el original cifrado y no anonimiza; `anonymize` construye la versión de revisión · @Rubén
- [x] Rutas renombradas (I9): `sign-off`, `{numero_version}` y `DELETE /admin/users/{id}/sessions` · @Rubén
- [x] Entrega al cliente movida del 20/11 al **27/11**
- [x] `expira_en` fuera del expediente (B6): A-21 lo limita a los temporales del OCR y el contrato deja de devolver `404` por caducidad · @Rubén
- [x] Geometría del PDF: se elige por documento (capa de texto → modelo de layout → secuencial); escrito en `docs/export/pdf.md` · @Rubén
- [x] Servidor definitivo decidido: NVIDIA DGX Spark (GB10, 128 GB unificados, Arm64) · [[Servidor definitivo]] · @Alex

## Preguntas abiertas

<!-- - @destinatario: pregunta · @autor -->
- @Alex: ¿bajamos la protección de `main`? Hoy exige 1 aprobación en todo, y con dos personas con escritura cada PR mío espera a que lo mires: es el mayor freno del día a día. Propuesta en tres pasos, de menos a más: **(1)** `CODEOWNERS` con revisión obligatoria solo de `backend/`, `docs/api/`, `docs/reglas/` y `docs/architecture/migrations/`, y los PR que solo tocan `vault/`, `maqueta/` o `docs/export/` se auto-mergean con CI verde; **(2)** si GitHub no les encaja así, bajar a 0 aprobaciones y exigir solo `Require status checks` + `Require conversation resolution`; **(3)** mantener el bloqueo de push directo a `main` en cualquier caso. Lo que no propongo es quitar la protección: solo el paso por revisión en lo que no es código. · @ia-opencode-ruben
- @Rubén: con `V14` y `V15` escritas quedan dos cosas fuera de la BD: **B8** (¿el hash del PDF es de la versión o del documento?) y el endpoint **`GET /documents/{id}/pages`**, sin el cual `paginas_documento` no tiene lector. Mi recomendación para B8 está en [[0011-ajustes-al-modelo-de-marina]]. · @ia-opencode-maga369
- @Marina: [[0012-identidad-y-roles]] cambia tu modelo aceptado en tres puntos: `usuarios_roles` (N:M) en lugar de `usuarios.rol`, `usuarios.sso_subject` y `tokens_usuario` sin uso en producción. Cabe entero en `V13`, que aún no existe, así que no hay datos que migrar; pero el diagrama y `data-dictionary.md` los decides tú. ¿Lo aceptas o lo corriges? · @ia-opencode-ruben
