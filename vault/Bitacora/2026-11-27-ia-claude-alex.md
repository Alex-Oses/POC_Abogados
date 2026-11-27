# 2026-11-27 · @ia-claude-alex

## Hecho

- #55 cerrado y rama `feat/backend-documentos` borrada: #56 de @Rubén lo sustituye y ya está en `main`.
- `main` al día (#52, #56, #57). Pruebas sin BD en verde: 22 passed, 12 skipped (las de BD piden `DATABASE_TEST_URL`; en el portátil no hay Postgres).
- Respondida a @Marina la pregunta del contraste: el umbral es 80 sobre 0-255, no 80 %; se mantiene `min(c,100)` para la demo.

## Paso al servidor

Desde `main`, siguiendo `docs/GUIA_SERVIDOR.md` (lista de comprobación al final). En el servidor, pasar también las pruebas de BD con `DATABASE_TEST_URL`.

## Pendiente

- Votar 0017 y 0018 es de @Rubén y @Kevin.
- Sin contestar aún (@Alex): protección de `main`, texto de la maqueta sobre imágenes borradas (I2), envío del PDF por correo.
