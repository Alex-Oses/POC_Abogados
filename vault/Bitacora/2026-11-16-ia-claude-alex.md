# 2026-11-16 · @ia-claude-alex

## Hecho

- README, CONTRIBUTING, AGENTS.md, plantilla de PR y comprobación `vault` en CI.
- Bóveda inicial: resúmenes de la propuesta, el rendimiento OCR, la API y la BBDD; tablero y decisiones 0001-0004.
- Borrador de BBDD copiado a `docs/architecture`.
- Conexión automática: al pedir a una IA «conéctate al repo», clona, ejecuta `scripts/conectar.*` (Obsidian + plugin Git con auto-pull) y resume el tablero (AGENTS.md § Primera conexión).
- Equipo, herramientas y la entrega del viernes en [[Equipo]].
- Prueba de Presidio en local: cobertura 10/10, 6 falsos positivos → [[Anonimizacion con Presidio]], decisión [[0006-presidio-anonimizacion-local]].
- [[Maqueta]] navegable del flujo completo (CA/ES), con el recorrido probado de principio a fin.
- Presidio medido con 13 configuraciones y corpus de validación aparte: 94,4 % de datos tapados en castellano (100 % en el de ajuste) · [`docs/presidio.md`](../../docs/presidio.md).
- Documentación con capturas de la maqueta · [`docs/maqueta.md`](../../docs/maqueta.md). Ambas en `.md` y `.pdf`.

## Siguiente

- @Alex: pasar la maqueta a Figma con html.to.design.
- Decidir el caso a presentar el viernes.
- Decidir [[0004-anonimizacion-antes-o-despues-de-revision]] (ahora con el dato de que el OCR no da coordenadas).

## Bloqueos / preguntas

- @Rubén: el `bbox` de `/blocks` no lo puede dar el OCR actual (ver [[Tablero]] § Preguntas abiertas).

- @Alex: el equipo usa Trello para tareas; ¿quitamos [[Tablero]] o lo dejamos solo para las IAs?
