# 2026-11-27 · @ia-claude-alex

## Hecho

- #55 cerrado y rama `feat/backend-documentos` borrada: #56 de @Rubén lo sustituye y ya está en `main`.
- `main` al día (#52, #56, #57). Pruebas sin BD en verde: 22 passed, 12 skipped (las de BD piden `DATABASE_TEST_URL`; en el portátil no hay Postgres).
- Respondida a @Marina la pregunta del contraste: el umbral es 80 sobre 0-255, no 80 %; se mantiene `min(c,100)` para la demo.

## Paso al servidor

- El DGX Spark no llega: se usa la VM de Azure donde ya se probó.
- En el servidor no se pueden ejecutar scripts ni abrir 80/443: `docker-compose.servidor.yml` lo hace todo (secretos y certificado propio generados en un contenedor, BD, Ollama + modelo, app, Caddy en 8443 o `PUERTO`). `docker-compose.yml` de desarrollo no cambia. Sección nueva al principio de `docs/GUIA_SERVIDOR.md`.
- Sin probar: el portátil no tiene Docker. Solo `docker compose config` y la clave Fernet generada.

## Pendiente

- Votar 0017 y 0018 es de @Rubén y @Kevin.
- Respondidas a @Rubén: protección (opción 2), I2 (ya resuelto en #41) y reglas aprobadas. Falta: envío del PDF por correo.
- Sin espacio en la VM para la imagen de Ollama (CUDA): el compose usa el Ollama ya instalado en la VM (`network_mode: host`, BD en 127.0.0.1:5433, app en 127.0.0.1:8001).
- La VM usa Docker rootless y es compartida (8001 y 5433 ocupados): sin `network_mode: host`; solo Caddy publica `PUERTO`, Ollama por `10.0.0.4:11434`.
- Servidor probado: funciona por el reenvío de puertos de VS Code (`https://localhost:8443`); el 8443 público lo bloquea el NSG. OCR en CPU, lento.
- Desmarcar muchas entidades daba 503 `pool_agotado`: `decide` en `static/app.js` lanza los PATCH de 4 en 4. Pregunta a @Rubén en el Tablero.
