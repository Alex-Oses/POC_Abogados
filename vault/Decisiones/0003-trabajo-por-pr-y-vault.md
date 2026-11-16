# 0003 · Trabajo por PR y bóveda Obsidian en el repo

- **Estado**: Aceptada
- **Fecha**: 2026-11-16
- **Autor**: @Alex-Oses

## Contexto

Varias personas y agentes de IA trabajan en paralelo y necesitan un sitio común para organizarse.

## Decisión

- `main` protegida; todo entra por PR con 1 aprobación.
- La bóveda Obsidian vive en `vault/` dentro del repo: se actualiza con cada `git pull`, sin servicios de sincronización externos.
- Cada PR toca `vault/` (comprobación `vault` en CI); se puede omitir con `[sin-vault]` en el título.
- Bitácora en un fichero por autor y día para evitar conflictos de merge.

## Consecuencias

Las IAs se coordinan leyendo y escribiendo el tablero, las decisiones y la bitácora (ver AGENTS.md).
