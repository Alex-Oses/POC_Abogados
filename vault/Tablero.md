# Tablero

Formato: `- [ ] tarea · @dueño · enlace`. Mueve la línea entre secciones en tu PR.

## Bloqueos

- Ninguno abierto. El de licencia (PyMuPDF) quedó cerrado el 27/11: ver **Hecho**.

## Pendiente

- [ ] 27/11: instalar y probar en el servidor de **Azure** (el DGX Spark se descarta) con `docker-compose.servidor.yml` (sin scripts: BD, Ollama, app y Caddy HTTPS en el puerto 8443) · `docs/GUIA_SERVIDOR.md` · @Alex-Oses

- [ ] Envío por correo del PDF exportado (anonimizado o transcrito) a quien lo deba recibir. Pendiente de hablar el 27/11: ver [[2026-11-26-ia-claude-alex]] · @Alex-Oses

- [ ] Decidir qué defectos SQL abiertos del [[Registro de errores]] se corrigen antes del 30/11: E-18 y E-19 (vistas), E-20, E-26, E-28 y E-30. El backend no usa las vistas, así que hoy solo afectan a informes · @Marina

**Entrega lunes 30/11** (ver [[Equipo]]):
- [ ] Especificación funcional con criterios «cómo comprobarlo»
- [ ] Presentar el stack completo funcionando (frontend React + backend FastAPI + PostgreSQL + OCR PaddleOCR-VL + Presidio) con los PDF de ejemplo; la maqueta ya no se pasa a Figma · @Alex
- [ ] Decidir el caso a presentar (justicia gratuita, anonimización o ambos)
- [x] BBDD: `V1`–`V15` y `views.sql` validados desde cero en PostgreSQL 16.4 y aplicados por el compose de la demo; en el servidor los aplica el instalador · @Marina
- [ ] Backend (API)
- [ ] Frontend
- [ ] OCR funcionando en Ollama
- [ ] Presidio anonimiza
- [ ] Probar despliegue en el servidor de prueba
- [ ] Conectar Frontend a servidor de prueba
- [ ] Mirar de integrar yagmail
- [ ] Investigar y trabajor sobre la demanda del sharepoint / checkpoint

Resto:
- [x] Stack del backend decidido: **Python 3.12 + FastAPI** · único stack para API, Presidio y PDF · C#/Java quedan como alternativas · [[0014-stack-backend-c-sharp-java-python]] · @Rubén
- [x] Identidad implementada (24/11): `V15`, `v_metricas_revisor`, trigger de revisor y diccionario alineados con [[0012-identidad-y-roles]], manteniendo intacto el modelo lógico-relacional · [[0015-identidad-en-v15]] · @Rubén
- [x] Modelo de roles aceptado (24/11, @Rubén): tres roles, sin supervisor, varios por usuario y **en tabla `usuarios_roles`**; @Kevin y @Alex pueden dejar constancia por Teams · [[0012-identidad-y-roles]] · @Rubén
- [ ] Cerrar el registro OIDC del ICAT (SSO **en pausa** desde el 26/11, con intención de retomarlo): `GET /auth/sso/login` y `GET /auth/sso/callback` ya están redactados como propuesta; solo falta que el ICAT entregue el registro · @Rubén @Kevin
- [x] Integrar Presidio en el backend (26/11): `app/services/presidio.py` con las 6 categorías iniciales (Nombre, DNI/NIE, Email, Teléfono, Dirección, IBAN), fallback regex sin spaCy, `ocr.py` separado de la lógica de Presidio · `backend/` · @ia-antigravity-ruben
- [ ] Validar el esquema MariaDB desde cero (`flyway clean` + `migrate`, `views.sql`, `triggers.sql`, `partitioning.sql` y una inserción con dos versiones para comprobar `es_actual`): hoy no hay motor y está revisado solo por lectura · @Kevin · [[0018-mariadb-segunda-opcion]]
- [x] Ajustar Presidio (27/11, @Rubén): se queda **`es_core_news_md`**, no `lg` — es el que se midió en [[Anonimizacion con Presidio]] y el que cabe en el servidor; las palabras a ignorar, los patrones de dirección y la matrícula ya están en `backend/app/services/presidio.py`. `lg` solo si en la demo fallan nombres reales

- [x] Decidir si el OCR es síncrono o por página asíncrona y ajustar la [[API]] → [[0020-cola-ocr-en-segundo-plano]] (**Aceptada** 27/11, @Rubén)
- [x] Endpoint de OCR (27/11): `POST /transform/document` devuelve `202` y las páginas salen por `GET /documents/{id}/progress` (NDJSON) con su semáforo de contraste · [[Rendimiento OCR]]
- [ ] Semáforo de calidad: contraste antes del OCR (< 80 → volver a escanear) y heurísticas de texto después
- [ ] Validación de DNI/NIE (letra de control) e IBAN
- [ ] Corrección catalana: «l·l» y apóstrofo tipográfico
- [x] PDF final con ReportLab implementado (26/11): `backend/app/services/export.py` con estructura, sustituciones por bloque, hash en `metadatos_proceso->>'hash_export'` e idempotencia; cubierto por `tests/test_export.py` · [[0007-generacion-pdf-final]] · @Rubén
- [ ] Preparar la reunión con el ICAT (preguntas en [[Propuesta ICAT]])
- [ ] Prueba de humo del stack en Arm64 y medición del OCR en el servidor · [[Servidor definitivo]] · @Kevin @Alex

## En curso

- Nada en curso. El [[Tablero]] solo lista aquí lo que alguien está tocando ahora mismo.

## Hecho

- [x] Arranque en Docker documentado (27/11): [docs/ARRANQUE_DOCKER.md](../docs/ARRANQUE_DOCKER.md) explica el compose de desarrollo (`poc_abogados`) y el del servidor (`icat`), la tabla de puertos de la VM compartida, como probar el del servidor sin pisar los contenedores de otro (`-p icat-ruben`), el acceso por tunel SSH y el diagnostico del OCR · @ia-opencode-ruben

- [x] 27/11: **PR #56 mergeado** — backend de documentos que sustituye a #55: ocho fallos de reglas corregidos, `anonymize.py`/`export.py` separados y `backend/Dockerfile`. Quedan las pruebas de BD, que necesitan un entorno con PostgreSQL · @ia-opencode-ruben
- [x] **Bloqueo de licencia cerrado (27/11)**: PyMuPDF (AGPL-3.0) retirado del backend. `services/ocr.py` rasteriza y lee la capa de texto con `pypdfium2` (Apache-2.0 OR BSD-3-Clause); `scripts/generar_pruebas.py` compone con ReportLab y rasteriza con pypdfium2; las tres pruebas ya no lo importan. `pyproject.toml` declara `pypdfium2` y [[0007-generacion-pdf-final]]/[[0008-stack-backend]] vuelven a cumplirse · @ia-opencode-ruben
- [x] Rutas del contrato que faltaban (27/11): `POST/PATCH /rules`, `POST/PATCH /categories`, `GET /config` y `PUT /config/{clave}` (solo admin), `PATCH /reviews/{id}/assign` y `POST /documents/{id}/sign-off`. El SSO sigue en pausa por decisión, no por código · @ia-opencode-ruben
- [x] E-22 corregido (27/11): `nueva_version` bloquea la fila del documento (`SELECT … FOR UPDATE`) antes de calcular `MAX(numero_version) + 1`; dos cierres simultáneos ya no chocan con el único · @ia-opencode-ruben
- [x] Base construida y validada en PostgreSQL 16.4 sin Docker (26/11): `V1`–`V15`, vistas, triggers y recreación de `auditoria` ejecutados desde cero; 15/15 tests con base · @ia-opencode-maga369 · [[Registro de errores]] (cuarta pasada)
- [x] Cerrados E-54, E-55 y E-56 (scripts SQL) y E-57 y E-58 (backend) y documentada la arquitectura MariaDB en el mismo PR · @ia-opencode-maga369 · `docs/architecture/`, `docs/architecture/mariadb/`, `backend/app/db/queries/auth.sql`, `backend/tests/test_sin_bd.py` · [[0017-particionado-auditoria]] y [[0018-mariadb-segunda-opcion]] en **Propuesta** (pendientes de aprobación; PR #52 abierto)

- [x] Backend Python creado (26/11): fundación FastAPI, identidad local de desarrollo, administración de usuarios y auditoría encadenada; `ruff` limpio y 7 pruebas en verde, 4 de BD saltadas por falta de PostgreSQL · `backend/` · [[Estructura del backend (Python)]] · @ia-opencode-ruben
- [x] Admin de desarrollo con **los tres roles** (26/11): la cuenta sembrada por entorno (U-21) permite recorrer el flujo completo sin SSO; el SSO queda en pausa · `backend/app/services/users.py` · @ia-opencode-ruben
- [x] Panel de investigación de reconstrucción de PDF (26/11): lector de estructura, render de vista previa por imágenes, OCR desde Markdown y utilidades de fuentes · `investigacion/reconstruccion_pdf/` · @ia-opencode-ruben
- [x] Frontend React con todas las pantallas de la [[Maqueta]] conectado al OCR real, semáforo de contraste, export PDF y arranque con un clic (26/11, @ia-claude-alex)
- [x] App demo de OCR (25/11, @ia-opencode-alex): `ocr_web_app.py` + `templates/index.html` convierten el PDF a imágenes con PyMuPDF y lo transcriben página a página con PaddleOCR-VL 1.6 vía Ollama; `/ocr` emite eventos NDJSON (`start`, `page`, `done`, `error`) y el navegador los lee en streaming, así que el progreso por página es real · verificado de extremo a extremo con un PDF de 2 páginas
- [x] PDF final decidido: reconstrucción desde estructura con ReportLab, modo layout/secuencial, hash en la versión e idempotencia; responsabilidad de @Rubén · [[0007-generacion-pdf-final]] · 23/11/2026
- [x] Consultas decididas (23/11, @Rubén): **SQL directo** con el driver y un mapeador fino (`psycopg` + `.sql`, o `Npgsql` + `Dapper` si 0014 cae en C#); sin SQLAlchemy y sin declarar el esquema · [[0013-consultas-sql-o-sqlalchemy-core]] · @Rubén
- [x] Identidad decidida (24/11, @Rubén): el SQL de [[0012-identidad-y-roles]] está al final de `V15` editada, sin `V13` ni `V16`; B1 resuelto en [[Coherencia]] · [[0015-identidad-en-v15]] · @Rubén
- [x] Identidad decidida (20/11, @Rubén): SSO del ICAT sin gestión de cuentas y admin local solo de desarrollo · [[0009-identidad]] · @Rubén
- [x] Roles confirmados (20/11, @Rubén): tabla `usuarios_roles (N:M)` de @Marina, sin pegas al `JOIN`/`EXISTS` de `v_metricas_revisor` ni al trigger de revisor · [[0012-identidad-y-roles]] · @Rubén

- [x] B8 cerrado (19/11, @Rubén): el hash del PDF es **de la versión**, en `versiones_documento.metadatos_proceso->>'hash_export'`; `documentos` solo guarda `exportado_en`. Sin `V16` · [[Coherencia]]
- [x] Contrato cerrado sin tocar la BD: `GET /documents/{id}/pages` y `GET /documents/{id}/original` (B5), `/reopen` acepta `aprobado` con motivo (A-19) y A-17/A-24 decididas · `docs/api/endpoints.md`, `docs/reglas/` · @ia-opencode-ruben
- [x] Offsets de anotación por bloque (25/11): `bloque_id` con FK compuesta, contrato, vistas y `pdf.md` alineados con el modelo ER · [[0015-identidad-en-v15]] · @ia-opencode-ruben
- [x] `/assign` y `/sign-off` se quedan en el contrato, en pausa (decisión de @Rubén, 19/11)
- [x] Doble transcripción (A-24) decidida: dos lecturas, diff en `metadatos_proceso` y avisos en `paginas_documento.avisos` · @Rubén
- [x] Revisión de coherencia de API, backend, usuarios y aprobación contra las reglas y el modelo: `actualizado_en`, estado `eliminado`, `paginas_documento`, A-09/A-11 y `sesiones_usuario.expira_en` · `docs/api/endpoints.md`, `docs/reglas/`, [[Enfoque tecnico]], [[0012-identidad-y-roles]] · @ia-opencode-ruben
- [x] [[Registro de errores]] con 30 hallazgos (evidencia, impacto y estado) y los falsos positivos descartados; incluye la auditoría de la base de datos: 14 migraciones, vistas y triggers · @ia-opencode-maga369
- [x] Tercera pasada del [[Registro de errores]]: 20 hallazgos nuevos contra el contrato, el export, el RGPD y la maqueta (E-31 a E-50) · @ia-opencode-ruben
- [x] Once de esos hallazgos aplicados sin tocar migraciones (E-31, E-32, E-35, E-37, E-40, E-41, E-45, E-46, E-48, E-49 y E-50); quedan 34 abiertos · @ia-opencode-ruben
- [x] Diagrama ER en Mermaid, uno solo, en [[Modelo de datos]]; el README de arquitectura deja de citar `er-diagram.md` · @ia-opencode-maga369
- [x] Un solo diagrama ER (18/11): retirados el «Diagrama propuesto» de [[0010-modelo-de-datos]] y `docs/architecture/diagrama-bbdd-borrador.png`; el vigente es [[Modelo de datos]], con 0011, `V14`/`V15` y los roles en `usuarios_roles` · @ia-opencode-maga369
- [x] [`docs/reglas/reglas-de-negocio.md`](../docs/reglas/reglas-de-negocio.md) con las 36 reglas vigentes, las 9 retiradas y la tabla «Cambios pedidos», para editar a mano · @ia-opencode-maga369
- [x] Decididos los roles (18/11, @Marina): **tabla `usuarios_roles (usuario_id, rol)`**, no columna · [[0012-identidad-y-roles]] · @Marina
- [x] Decidida la sesión (18/11, @Rubén): **opción B**, sesión propia en `sesiones_usuario`. U-16 a U-20 siguen vigentes · [[0012-identidad-y-roles]] · @Rubén
- [x] Bajar al modelo de @Marina en migraciones: `V14` y `V15` escritas y [[0011-ajustes-al-modelo-de-marina]] **aceptada** (17/11, @Marina) · PR #28 y #29 mergeados · `V13` y `V16` no se escriben: la BD es definitiva · [[0010-modelo-de-datos]] · @ia-opencode-maga369
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
- [x] [[Coherencia]] actualizada a 20/11: B2, I1, I2, I3, I9 y H1-H8 cerrados; solo queda B1 (identidad) y los defectos que piden decisión · @ia-opencode-ruben
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
- @Rubén: en el servidor, al desmarcar muchas entidades el frontend lanzaba un `PATCH /annotations/{id}` por entidad a la vez y salían 503 `pool_agotado` (pool de 10, `timeout=5`). Los ~5 s no eran la auditoría: los 40 hilos del threadpool se quedaban esperando conexión y las peticiones que ya la tenían no podían cerrar su transacción (el teardown de la dependencia `connection` también necesita hilo) hasta que saltaba el `timeout=5` del pool. Arreglado limitando el frontend a 4 PATCH a la vez (`static/app.js`, `decide`). Sigue siendo posible con muchas peticiones simultáneas de cualquier origen: ¿añadimos un PATCH en lote o subimos el pool? No he tocado el backend. · @ia-claude-alex
- @Alex: **petición de @Rubén — no rehacer el backend sin consultar las reglas aprobadas.** Revisar y mejorar el código, adelante; cambiar de paso lo que el equipo ya aprobó, no. En #55 el defecto de `/anonymize` y `/reopen` pasó de `censurar` a `borrar` sin decisión (y `docs/architecture/rgpd-considerations.md` dice lo contrario), y el borrado durante el OCR resucitaba documentos; detectarlo y arreglarlo ha costado una sesión de revisión y otra de cambios (`fix/backend-cola-reglas`, commit `a085e83`). Antes de tocar `backend/app`, el SQL o el contrato: lee `docs/reglas/aprobacion.md`, `docs/reglas/reglas-de-negocio.md` y `docs/api/endpoints.md`; si algo no encaja, propón una decisión nueva o pregúntame aquí antes de cambiarlo. · @Rubén (vía @ia-opencode-ruben) · **Visto (27/11, @Alex):** de acuerdo.
- @Alex: **#55 queda sustituido por #56** (misma funcionalidad + reglas corregidas + `main` ya integrado; #55 llevaba días en conflicto). Revísalo ahí y cierra #55 cuando las pruebas de BD estén en verde; el detalle, en [[2026-11-27-ia-opencode-ruben]]. · @ia-opencode-ruben · **Hecho (27/11, @Alex):** #55 cerrado y rama borrada; pruebas sin BD en verde en `main` (22 passed).
- @Alex: ¿bajamos la protección de `main`? Hoy exige 1 aprobación en todo, y con dos personas con escritura cada PR mío espera a que lo mires: es el mayor freno del día a día. Propuesta en tres pasos, de menos a más: **(1)** `CODEOWNERS` con revisión obligatoria solo de `backend/`, `docs/api/`, `docs/reglas/` y `docs/architecture/migrations/`, y los PR que solo tocan `vault/`, `maqueta/` o `docs/export/` se auto-mergean con CI verde; **(2)** si GitHub no les encaja así, bajar a 0 aprobaciones y exigir solo `Require status checks` + `Require conversation resolution`; **(3)** mantener el bloqueo de push directo a `main` en cualquier caso. Lo que no propongo es quitar la protección: solo el paso por revisión en lo que no es código. · @ia-opencode-ruben · **Respondido (27/11, @Alex):** opción 2: 0 aprobaciones, solo CI `vault` en verde y conversaciones resueltas; push directo a `main` sigue bloqueado. Lo cambia @Alex en el ruleset `main protegida`.
- ~~@Marina: [[0012-identidad-y-roles]] cambia tu modelo aceptado, pero **la BD es definitiva y `V13` no se escribe**. `usuarios` se queda con `rol` y `activo`, sin `usuarios_roles`, sin `sso_subject`, sin `password_hash` y sin `sesiones_usuario`. ¿El alta y la sesión se implementan sobre esas dos columnas, o el login queda fuera del piloto?~~ **Resuelto (23/11)**: se implementa completo al final de `V15` editada ([[0015-identidad-en-v15]]).
- @Alex: la maqueta promete «zones de la imatge esborrades (no només tapades)», pero el PDF final se reconstruye sin ningún píxel del escaneo (0007): no hay imagen que borrar y tampoco se conservan sellos ni firmas manuscritas. ¿Cambiamos el texto por «el PDF no contiene ninguna imagen del original» o preferís mantener la promesa tal cual en la demo? (I2) · @ia-opencode-ruben · **Respondido (27/11, @Alex):** cambiar el texto. Ya está desde #41: `g2` dice «Sense l'escaneig original: ni imatge ni capa de text».
- @Marina: el port a MariaDB mantiene tus `bbox_*` legacy tal cual (E-51) y tampoco incorpora las columnas de la v0.3 que faltan (E-53). ¿Conservamos la geometría como respaldo o la quitamos con plan de datos, y decides tú qué columnas entran en una migración nueva? · @ia-opencode-maga369 · **Respondido (27/11, @Marina):** conservamos los `bbox_*` como respaldo legacy y sin lectores; el backend usa `bloque_id`. No añadimos columnas de la v0.3 ahora: quedan como deuda documentada y solo entran si se abre una migración nueva con una consulta que lo justifique.
- ~~@Rubén: he dejado PostgreSQL como motor principal y el backend con `psycopg` intacto; [[0018-mariadb-segunda-opcion]] solo documenta MariaDB. ¿Confirmas que no quieres que adaptemos las consultas `.sql` mientras tanto?~~ · @ia-opencode-maga369 · **Respondido (27/11)**: correcto, PostgreSQL sigue siendo el motor y no se tocan las consultas `.sql`. De #52 el backend solo necesitaba la cadena de hash ordenada por `(creado_en, id)` —ya está en `audit.sql`— y el aislamiento de `test_sin_bd` (E-58); `V1`–`V15` no cambian, así que no hay más adaptación. Sigue abierta E-23 (trigger y backend calculando el mismo hash). · @ia-opencode-ruben

- @Rubén @Kevin: propuesta [[0017-particionado-auditoria]]: dejar `auditoria` como tabla particionada por `creado_en`, con PK `(id, creado_en)` y cadena `(creado_en DESC, id DESC)`, recreada desde `partitioning.sql` sin editar `V8` ni abrir `V16`. Ya está validada en PostgreSQL 16.4. ¿La aceptáis o la rechazáis? · @Marina · **Voto (27/11, @Rubén): OK.** Falta @Kevin para cerrarla.
- @Rubén @Kevin: propuesta [[0018-mariadb-segunda-opcion]]: mantener PostgreSQL 14+ como motor principal y MariaDB 11.4 como segunda opción documentada, sin cambiar el backend `psycopg` ni el despliegue. ¿La aceptáis o la rechazáis? · @Marina · **Voto (27/11, @Rubén): OK.** Falta @Kevin para cerrarla.
- @Kevin: si MariaDB llega a desplegarse en el DGX Spark (Arm64), hay que programar `sp_auditoria_add_partition()` cada mes y `sp_auditoria_drop_partition()` para los 120 meses de retención. ¿Lo asumes tú y confirmas soporte de MariaDB 11.4 en Arm64? · @ia-opencode-maga369
- @Kevin: en PostgreSQL, `pg_partman` no viene en los binarios oficiales; he validado la recreación y las particiones a mano, pero no el mantenimiento ni la retención automática. ¿Instalamos la extensión en el despliegue y ejecutamos las secciones 2+ de `partitioning.sql`, o sustituimos el job por un `pg_cron` propio? · @ia-opencode-maga369
- ~~@Rubén: `docs/architecture/triggers.sql` no se aplica en PostgreSQL 16: `function sha256(text) does not exist` (hace falta `sha256(convert_to(..., 'UTF8'))`). Además `trg_documento_estado_auto` tiene un `CASE` sin `ELSE` que falla con `tipo_version='original'` y al crear una revisión `en_cola`, y `trg_audit_hash_chain` pisaría el hash que ya calcula el backend. Hoy el backend hace ese trabajo sin triggers. ¿Los corriges o los retiramos?~~ · @ia-claude-alex · **Resuelto en este PR salvo E-23**: E-01 y E-56 corregidos y ejecutados en PG16; el trigger sigue calculando la cadena y la diferencia con el backend sigue abierta (E-23) · @ia-opencode-maga369
- @Rubén @Marina: `paginas_documento.contraste` tiene `CHECK 0-100`, pero el semáforo mide 0-255 con umbral 80. Ahora se guarda `min(c,100)` y el valor real en `metadatos_proceso.paginas.N.contraste_bruto`. ¿Ampliamos el CHECK a 0-255 o normalizamos a 0-100? · @ia-claude-alex · **Respondido (27/11, @Marina):** no ampliamos el `CHECK`; el esquema se queda en `0-100`. Para el piloto mantenemos `min(c,100)` y el bruto en `contraste_bruto`, documentado como **contraste recortado, no porcentaje**. Si @ia-claude-alex confirma que el umbral debe ser 80 %, se normaliza en backend (`round(c * 100 / 255)`) y se ajusta el semáforo en una decisión aparte, con pruebas con escaneos reales; no lo cambiaría antes de la demo. · **Respondido (27/11, @Alex):** el umbral **no** es 80 %: es 80 sobre la escala 0-255 (`contraste_minimo = 80` en `backend/app/core/config.py`, ≈31 %). Con el tope `min(c,100)` el semáforo sigue igual: se queda así para la demo.
- @Rubén @Marina: faltan columnas para (a) página validada/editada en revisión, (b) modo de anonimización elegido (censurar, etiqueta, seudónimo…) y (c) resultado de la comprobación de justicia gratuita. Hoy van en `versiones_documento.metadatos_proceso` (`paginas_validadas`, `modo`) y `documentos.metadatos_extras.justicia_gratuita`. ¿Os vale en JSON o preferís columnas/tabla? · @ia-claude-alex · **Respondido (27/11, @Marina):** para el piloto, JSON. No añadimos columnas ni tabla: `paginas_validadas` y `modo` siguen en `versiones_documento.metadatos_proceso`, y justicia gratuita en `documentos.metadatos_extras.justicia_gratuita`. Mantener claves estables y validación en backend; solo se promueven a columnas si aparecen consultas o filtros que lo exijan, y entonces será una migración nueva.
- ~~@Rubén: no hay ninguna regla en `reglas_anonimizacion` sembrada; `regla_id` es opcional y por defecto se usan todas las categorías activas. ¿Sembramos una regla por defecto en `V12`?~~ · @ia-claude-alex · **Respondido (27/11, @Rubén):** no. `regla_id` opcional con «todas las categorías activas» es el comportamiento correcto y el que ya implementa el backend; sembrar una regla en `V12` obligaría a una migración nueva (la BD está cerrada: no hay `V16`) y congelaría categorías que deben seguir al catálogo. Si hace falta una regla concreta, se crea por API (`POST /rules`).
- ~~@Rubén: el contrato dice «422 si el OCR no produce texto», pero un documento totalmente ilegible se guarda igual para que salga en la bandeja y se pueda reescanear. ¿Cambiamos el contrato?~~ · @ia-claude-alex · **Respondido (27/11, @Rubén):** se cambia el contrato, no el comportamiento. El documento se guarda en `pendiente` con `ocr.error = OCR_SIN_TEXTO` y se reescanea; `422` queda para lo que de verdad no es procesable. Actualizado `docs/api/endpoints.md`.
- ~~@Rubén: corregido un fallo en `backend/app/db/queries/auth.sql`: `desalojar_sesiones` ordenaba `creado_en ASC` y cerraba las sesiones más nuevas en vez de la más antigua (ahora `DESC`; el test fallaba antes). Revísalo en el PR.~~ · @ia-claude-alex · **Confirmado en este PR** como E-57, con 15/15 tests con base · @ia-opencode-maga369 · **Confirmado (27/11, @Rubén):** `DESC` es lo que pide U-17 (cerrar la más antigua); se queda.
- ~~@Rubén: al unir `main` en #53 se retiró la capa de #48 que no casa con V1..V15 (`review.sql` usa `revisiones.documento_id`, `motivo`, `actualizado_en` y `anotaciones.inicio/fin/estado`, que no existen; `rules.sql` usa `patron` y `crear_categoria` omite `nivel_riesgo`): `api/v1/{admin,anonymize,export,review,rules}.py`, sus servicios y SQL, `schemas/` y los stubs de `integrations/` y `jobs/`. Tu `services/presidio.py` queda como único sitio del analizador (con `es_core_news_md` y los reconocedores medidos). Faltan por reescribir sobre el esquema real: `PATCH /reviews/{id}/assign`, `POST /documents/{id}/sign-off`, `POST/PATCH /rules`, `POST/PATCH /categories`, `GET/PUT /config`. ¿Te encargas o lo repartimos?~~ · @ia-claude-alex · **Respondido (27/11, @Rubén):** ya está hecho y mergeado en #56 — `PATCH /reviews/{id}/assign`, `POST /documents/{id}/sign-off`, `POST/PATCH /rules`, `POST/PATCH /categories` y `GET/PUT /config`, reescritos sobre `V1`–`V15`, con `ruff` limpio y 22 pruebas en verde (12 de BD saltadas). No hay nada que repartir.
