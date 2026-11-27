# 2026-11-27 · @ia-claude-alex

## Hecho

- #55 cerrado y rama `feat/backend-documentos` borrada: #56 de @Rubén lo sustituye y ya está en `main`.
- `main` al día (#52, #56, #57). Pruebas sin BD en verde: 22 passed, 12 skipped (las de BD piden `DATABASE_TEST_URL`; en el portátil no hay Postgres).
- Respondida a @Marina la pregunta del contraste: el umbral es 80 sobre 0-255, no 80 %; se mantiene `min(c,100)` para la demo.

## Paso al servidor

- El DGX Spark no llega: se usa la VM de Azure donde ya se probó.
- `docker-compose.yml` levanta todo con el perfil `servidor` (BD, Ollama + descarga del modelo, app, Caddy HTTPS); `docker compose up -d db` sigue sirviendo para desarrollo.
- `scripts/servidor_docker.sh`: instala Docker, genera `.env` con claves aleatorias y arranca. Sección nueva al principio de `docs/GUIA_SERVIDOR.md`.
- Sin probar: el portátil no tiene Docker. Solo `docker compose config` y la clave Fernet generada.

## Pendiente

- Votar 0017 y 0018 es de @Rubén y @Kevin.
- Respondidas a @Rubén: protección (opción 2), I2 (ya resuelto en #41) y reglas aprobadas. Falta: envío del PDF por correo.
