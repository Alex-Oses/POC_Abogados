# Tablero

Formato: `- [ ] tarea · @dueño · enlace`. Mueve la línea entre secciones en tu PR.

## Pendiente

**Entrega viernes 27/11** (ver [[Equipo]]):
- [ ] Especificación funcional con criterios «cómo comprobarlo»
- [ ] Pasar la [[Maqueta]] a Figma (html.to.design) y enlazar el prototipo · @Alex
- [ ] Decidir el caso a presentar (justicia gratuita, anonimización o ambos)

Resto:
- [ ] Decidir el stack del backend: Python + FastAPI o C# · [[0008-stack-backend]] · @Rubén @Kevin
- [ ] Cerrar los bloqueantes que quedan de [[Coherencia]]: identidad (B1, B2) · @Rubén @Marina
- [ ] Decidir identidad: SSO del ICAT sin gestión de cuentas y admin local solo de desarrollo · [[0009-identidad]] · @Rubén @Kevin @Marina @Alex
- [ ] Aceptar el modelo de roles: tres roles, sin supervisor, varios por usuario y **en columna `usuarios.roles`, sin tabla de roles** · [[0012-identidad-y-roles]] · @Marina @Kevin @Alex
- [ ] Aceptar 0009 y completar el callback SSO del contrato con el registro OIDC del ICAT (ya hay dos rutas propuestas) · @Rubén @Kevin
- [ ] Ajustar Presidio: modelo `lg`, palabras a ignorar, patrones de dirección y matrícula · [[Anonimizacion con Presidio]] · @Alex

- [ ] Decidir si el OCR es síncrono o por página asíncrona y ajustar la [[API]]
- [ ] Endpoint que reciba un PDF y devuelva texto por página con su color de semáforo · [[Rendimiento OCR]]
- [ ] Semáforo de calidad: contraste antes del OCR (< 80 → volver a escanear) y heurísticas de texto después
- [ ] Validación de DNI/NIE (letra de control) e IBAN
- [ ] Corrección catalana: «l·l» y apóstrofo tipográfico
- [ ] Implementar el PDF final: estructura + reconstrucción con reportlab · [[0007-generacion-pdf-final]]
- [ ] Preparar la reunión con el ICAT (preguntas en [[Propuesta ICAT]])
- [ ] Prueba de humo del stack en Arm64 y medición del OCR en el servidor · [[Servidor definitivo]] · @Kevin @Alex

## En curso

## Hecho

- [x] B8 cerrado (19/11, @Rubén): el hash del PDF es **de la versión**, en `versiones_documento.metadatos_proceso->>'hash_export'`; `documentos` solo guarda `exportado_en`. Sin `V16` · [[Coherencia]]
- [x] Contrato cerrado sin tocar la BD: `GET /documents/{id}/pages` y `GET /documents/{id}/original` (B5), offsets de anotaciones sobre `contenido_texto` (B3), `/reopen` acepta `aprobado` con motivo (A-19) y A-17/A-24 decididas · `docs/api/endpoints.md`, `docs/reglas/` · @ia-opencode-ruben
- [x] `/assign` y `/sign-off` se quedan en el contrato, en pausa (decisión de @Rubén, 19/11)
- [x] Doble transcripción (A-24) decidida: dos lecturas, diff en `metadatos_proceso` y avisos en `paginas_documento.avisos` · @Rubén
- [x] Revisión de coherencia de API, backend, usuarios y aprobación contra las reglas y el modelo: `actualizado_en`, estado `eliminado`, `paginas_documento`, A-09/A-11 y `sesiones_usuario.expira_en` · `docs/api/endpoints.md`, `docs/reglas/`, [[Enfoque tecnico]], [[0012-identidad-y-roles]] · @ia-opencode-ruben
- [x] Decidida la sesión (18/11, @Rubén): **opción B**, sesión propia en `sesiones_usuario`. U-16 a U-20 siguen vigentes · [[0012-identidad-y-roles]] · @Rubén
- [x] Bajar al modelo de @Marina en migraciones: `V14` y `V15` escritas y [[0011-ajustes-al-modelo-de-marina]] **aceptada** (17/11, @Marina) · PR #28 pendiente de merge · `V13` y `V16` no se escriben: la BD es definitiva · [[0010-modelo-de-datos]] · @ia-opencode-maga369
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
- @Marina: [[0012-identidad-y-roles]] cambia tu modelo aceptado, pero **la BD es definitiva y `V13` no se escribe**. `usuarios` se queda con `rol` y `activo`, sin `sso_subject`, sin `password_hash` y sin `sesiones_usuario`. ¿El alta y la sesión se implementan sobre esas dos columnas, o el login queda fuera del piloto? · @ia-opencode-ruben
