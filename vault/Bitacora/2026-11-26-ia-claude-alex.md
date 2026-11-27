# 2026-11-26 · @ia-claude-alex

## Hecho
- Frontend React (UMD + htm, sin build) con todas las pantallas de la [[Maqueta]]: login, landing, safata, procesando, revisión, justicia gratuita, anonimización, exportado, archivo e informes; CA/ES y guía de la demo.
- Conectado al OCR real: subida con modo único o doble, streaming por página, imagen junto al texto editable, diferencias en rojo con el recuadro sobre la imagen, avisos de DNI/NIE e IBAN mal formados y validación por página.
- Backend: semáforo de contraste (< 80 no se transcribe), `POST /page/<id>/<n>/ocr` (volver a transcribir o reescanear), `POST /export` (PDF solo desde el texto), `OCR_MOCK=1` y ruta relativa.
- `scripts/arrancar_demo.bat`: arranca Ollama, el modelo, la app y el navegador con un clic (`mock` para probar sin modelo).
- Probado de extremo a extremo con Playwright y `OCR_MOCK=1`.

## Siguiente
- Probar con PaddleOCR-VL real y escaneos reales: validar el umbral de contraste (percentil 0,05 %).
- El export corta el texto que no cabe en una página.

## Bloqueos / preguntas
- Justicia gratuita y anonimización siguen con datos ficticios de la maqueta.

## Hecho (tarde)
- Backend FastAPI real en `backend/` (sobre #48): documentos, OCR en streaming, páginas, revisión, justicia gratuita, anonimización con Presidio, export con hash, archivo con búsqueda, informes y auditoría, todo en PostgreSQL sin tocar V1..V15. `ruff` limpio y `pytest` 12/12 con BD.
- Frontend conectado a `/api/v1` sin datos ficticios; probado con Playwright con OCR simulado y con PaddleOCR-VL real.
- Despliegue decidido: todo en un servidor de Azure (pendiente de los datos de la VM). Preguntas de esquema para @Rubén y @Marina en el tablero.

## Siguiente
- Cola de OCR para dejar PDF transcribiéndose de noche y script de despliegue en Azure.

## Hecho (noche)
- Cola de OCR en segundo plano con guardado por página ([[0020-cola-ocr-en-segundo-plano]], Propuesta) y frontend adaptado (bandeja como portada, progreso por documento).
- `scripts/instalar_servidor.sh`: instala en Ubuntu 24.04 la BD (modelo de Marina V1..V15 + vistas), Ollama, la app como servicio systemd y Caddy con HTTPS por IP. Deja `arrancar.sh`, `parar.sh`, `actualizar.sh` y `logs.sh`.
- `docker-compose.yml`: Postgres solo en `127.0.0.1` (Docker se salta ufw) y `restart: unless-stopped`.

## Bloqueos / preguntas
- `triggers.sql` y `partitioning.sql` de #52 no se aplican en el servidor: el backend ya mantiene versiones y auditoría, y falta `pg_partman`. @Marina: confirmar si debe ir así.
- Script sin probar en un servidor real.
- «Subido por» en bandeja y archivo (usuario logueado o carpeta de SharePoint), en `metadatos_extras` sin tocar el esquema.
- `POST /documents/{id}/export/transcrito` → `<nombre>_trans.pdf`; el anonimizado ya salía como `_anon.pdf`.
- Entrada por SharePoint ([[0019-entrada-por-sharepoint]], Propuesta). Probada con un Graph falso; falta un tenant real.
- `DATABASE_URL` con `127.0.0.1`: con Postgres solo en IPv4, `localhost` (::1) colgaba la conexión en Windows. 25/25 tests.
- Bandeja: modo de transcripción (doble/única) por documento, doble por defecto, filtros (estado, subido por, modo) y descarga ZIP (`POST /documents/export/zip`, `_trans` o `_anon`).
- Justicia gratuita: tarjetas de expedientes y vista previa de páginas con el tipo detectado.
- Animaciones CSS (sin JS, se apagan con reduce-motion).
- Resumen completo: [[2026-11-26 Cambios de la sesión]].

## Pendiente para el 27/11: envío por correo tras exportar
- Idea: al exportar, enviar el PDF por correo (smtplib, sin dependencias) con el buzón de Microsoft 365.
- A decidir con @Alex-Oses:
  1. El PDF transcrito lleva datos personales: ¿solo a dominios internos (lista blanca en el servidor)? Propuesta: anonimizado a cualquiera, transcrito solo interno.
  2. Destinatario: a) casilla al exportar con el correo de quien subió el documento, b) fijo por tipo en `.env`, c) ambos.
  3. Buzón remitente y datos SMTP.
- Auditoría funcional de la web (agente Evidence Collector) y arreglos: subida duplicada ya no dice «acabada», justicia gratuita en catalán (tipos, aviso, nombre e ingresos con «Nom:»/«Ingressos:»), confirmación al enviar con documentación incompleta, eventos de auditoría legibles, estado visible en móvil, «seudónimos» solo con ese modo, guía fija abajo a la derecha y documentos huérfanos de antes de la cola marcados como fallidos. Sin cambiar: el resaltado del menú (las pantallas de flujo cuelgan de Safata y Exportat de Arxiu).
- Pruebas (agente + API): cola de 7 ficheros con cancelar y recarga, edición con formato que persiste y llega a la anonimización, validar, Ctrl+→, avisos, JPG/PNG y rechazo 415. Arreglos: cancelado ya no sale como error, rechazados en aviso fijo, errores del backend traducidos.
- Servidor: BD externa (`DATABASE_URL`) con `scripts/comprobar_bd.py`, `DOMINIO` con Let's Encrypt, producción sin `/docs`, fuentes locales (sin Google), logs en `logs/` y `diagnostico.sh` con claves tapadas. Instalación probada en un Ubuntu 24.04 limpio (contenedor): OK, y con BD mala falla con línea, comando y log.
- `scripts/generar_pruebas.py`: 17 documentos ficticios en `pruebas/` (no se suben).
- Revisión: cabecera con el recuento de páginas y miniatura actual siempre visible (con 20+ páginas la columna se cortaba sin aviso).
- `docs/GUIA_SERVIDOR.md` (guía paso a paso), `scripts/crear_usuario.py` (altas mientras no haya SSO) y `scripts/copia_seguridad.sh`. Comandos de la guía probados en un Ubuntu 24.04 limpio contra `icat_test`.
