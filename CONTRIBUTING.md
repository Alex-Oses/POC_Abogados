# Cómo contribuir

## Flujo

1. Actualiza `main`: `git pull`.
2. Crea una rama: `tipo/descripcion-corta`, por ejemplo `feat/endpoint-ocr`, `fix/semaforo-contraste`, `docs/api-v1`.
3. Si la tarea está en [vault/Tablero.md](vault/Tablero.md), muévela a **En curso** con tu nombre en el mismo PR.
4. Haz commits pequeños con mensaje en imperativo (`Añade validación de DNI`).
5. Escribe tu entrada en `vault/Bitacora/AAAA-MM-DD-autor.md` (qué hiciste, qué queda, qué bloquea).
6. Abre el PR contra `main` rellenando la plantilla. Pide revisión a un compañero.
7. Al aprobarse, **Squash and merge** y borra la rama.

## Reglas

- `main` está protegida: sin push directo, al menos 1 aprobación y la comprobación `vault` en verde.
- Un PR = un cambio con sentido propio. Si crece mucho, pártelo.
- Decisiones de diseño o de arquitectura: nota nueva en `vault/Decisiones/` usando la plantilla.
- Nunca datos reales del ICAT, datos personales ni secretos en el repo.

## Protección de `main` (ya configurada)

Ruleset «main protegida» en **Settings → Rules → Rulesets**. Los administradores solo pueden saltarse la aprobación dentro de un PR, nunca con push directo:

- Require a pull request before merging → Required approvals: **1**
- Dismiss stale pull request approvals when new commits are pushed
- Require status checks to pass → añadir **vault**
- Block force pushes
- **Settings → General → Pull Requests**: activar solo *Allow squash merging* y *Automatically delete head branches*.

Añade a los compañeros en **Settings → Collaborators** con permiso *Write*.

## Obsidian

`scripts/conectar.ps1` (Windows) o `scripts/conectar.sh` (macOS/Linux) instala el plugin **Git** (Vinzent03) en `vault/` con pull al abrir y cada 10 min, sin push, y abre la bóveda en Obsidian. Tu IA lo ejecuta sola al conectarse (ver AGENTS.md). Haz tus cambios en una rama y súbelos por PR como el resto del código.
