# 2026-11-26 · Cambios de la sesión (@ia-claude-alex)

Rama `feat/backend-documentos`. Sin cambios de esquema de BD: no hay migraciones nuevas y lo nuevo va en `metadatos_extras` (JSONB existente) o en consultas `SELECT`.

## Añadido

- **Cola de OCR en segundo plano** con guardado por página ([[0017-cola-ocr-en-segundo-plano]], Propuesta): `services/cola.py`, `GET /documents/{id}/progress`, `GET /documents/{id}/stream`, `POST /documents/{id}/cancel`. Reanuda tras reinicio.
- **Entrada por SharePoint** ([[0019-entrada-por-sharepoint]], Propuesta): `services/sharepoint.py`. PDF en `Entrada/<Persona>/` se suben solos, «subido por» = carpeta, y se mueven a `Procesados` o `Rechazados`. Variables `SHAREPOINT_*`.
- **«Subido por»** en bandeja, archivo y detalle (`subido_por`): usuario logueado o carpeta de SharePoint.
- **PDF transcrito antes de anonimizar**: `POST /documents/{id}/export/transcrito` → `<nombre>_trans.pdf`. El anonimizado pasa a `<nombre>_anon.pdf`.
- **ZIP**: `POST /documents/export/zip` (`tipo` `anon` o `trans`, hasta 100 ids; los no listos se saltan y se cuentan en `X-Omitidos`).
- **Bandeja**: modo de transcripción por documento, filtros (estado, subido por, modo), selección con casillas y botones ZIP. También en el archivo.
- **Justicia gratuita**: tarjetas con los expedientes revisables y vista previa de páginas con el tipo detectado; botón para abrir la página en revisión.
- **Animaciones CSS** en pantallas, tablas, botones, modales, avisos y cola. Solo transform/opacity; se apagan con `prefers-reduced-motion`.
- **Despliegue**: `scripts/instalar_servidor.sh` (Ubuntu 24.04: Docker + Postgres con el modelo de Marina V1..V15 + vistas, Ollama, app como servicio systemd, Caddy con HTTPS por IP). Deja `arrancar.sh`, `parar.sh`, `actualizar.sh` y `logs.sh`.
- **Tests**: `test_cola_ocr_bd.py`, `test_richtext.py`, `test_sharepoint.py`; el flujo completo cubre «subido por», `_trans`, `_anon` y ZIP. 25/25 con BD.

## Añadido (tarde-noche)

- **Guía del servidor**: `docs/GUIA_SERVIDOR.md`, con lista de comprobación para la prueba.
- **Instalador**: BD externa (`DATABASE_URL`, la de Marina) comprobada con `scripts/comprobar_bd.py`; `DOMINIO` con Let's Encrypt; producción sin `/docs`; logs en `logs/` y `diagnostico.sh` con claves tapadas. Probado en un Ubuntu 24.04 limpio.
- **Scripts**: `crear_usuario.py` (altas mientras no haya SSO), `copia_seguridad.sh` y `generar_pruebas.py`.
- **Documentos de prueba**: 17 ficticios en `pruebas/` (único sitio donde se admiten PDF en el repo).
- **Fuentes locales**: sin Google Fonts; la web no llama a terceros.
- **Arreglos de la auditoría**: subida duplicada, justicia gratuita en catalán, eventos legibles, cancelados sin error, rechazados en aviso fijo y miniaturas de revisión.

## Cambiado

- **Doble transcripción** seleccionada por defecto.
- **Frontend**: la bandeja es la portada (fuera la landing); abrir documentos mientras se transcriben; barra de formato tipo Word; recuadro rojo sin esperar; «esborrar» por defecto; censurar en gris oscuro.
- **`docker-compose.yml`**: Postgres solo en `127.0.0.1` (Docker se salta ufw) y `restart: unless-stopped`.
- **`DATABASE_URL`** con `127.0.0.1` en lugar de `localhost`: con Postgres solo en IPv4, `localhost` (::1) colgaba la conexión en Windows.
- **`Content-Disposition`** con `filename*=UTF-8''…`: nombres con tildes no rompen la descarga.
- **`db/pool.py`**: recrea el pool si estaba cerrado (varios arranques en pruebas).

## Eliminado

- La landing como pantalla de inicio (la ruta `#landing` redirige a `#safata`).
- El sufijo `_anonimizado.pdf` (ahora `_anon.pdf`).

## Pendiente

- Envío por correo tras exportar: decidir el 27/11 (ver [[2026-11-26-ia-claude-alex]]).
- Probar SharePoint con un tenant real y el script en el servidor de Azure (abrir 80/443 en el NSG).
- @Marina: confirmar que en el servidor no se aplican `triggers.sql` ni `partitioning.sql` (#52).
- Probar en el servidor real (27/11) con la lista de la guía.
