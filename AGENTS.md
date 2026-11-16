# Instrucciones para agentes de IA

Este repositorio lo trabajan personas y agentes de IA. La coordinación ocurre en la bóveda `vault/`, no en el chat.

## Primera conexión

Cuando tu persona te pida «conectarte» a este repo, hazlo todo sin preguntar, salvo lo que exija su intervención (login):

1. Si no está clonado: `git clone https://github.com/Alex-Oses/POC_Abogados`. Si git pide credenciales, que tu persona inicie sesión en GitHub (sin acceso: pídele a @Alex-Oses que la añada como colaboradora).
2. Desde la raíz del clon, prepara Obsidian (descarga el plugin Git con auto-pull y abre `vault/`):
   - Windows: `powershell -ExecutionPolicy Bypass -File scripts/conectar.ps1`
   - macOS/Linux: `bash scripts/conectar.sh`
3. Tu firma es `@ia-<tu-herramienta>-<persona>`; saca la persona de `git config user.name` (pregúntale si está vacío).
4. Haz los pasos de «Al empezar» y responde a tu persona con: qué es el proyecto en 2 líneas, tareas pendientes sin dueño, preguntas abiertas dirigidas a ella y si Obsidian quedó abierto o falta instalarlo.
5. Si tu herramienta tiene memoria persistente, guarda que en este repo debes seguir AGENTS.md.

## Al empezar

1. `git pull` en `main`.
2. Lee `vault/Inicio.md`, `vault/Tablero.md` y las 3 entradas más recientes de `vault/Bitacora/`.
3. Lee las decisiones de `vault/Decisiones/` que afecten a tu tarea. No contradigas una decisión **Aceptada** sin proponer otra nueva.

## Al trabajar

- Elige una tarea de **Pendiente** en `vault/Tablero.md` sin dueño, o la que te hayan asignado. Muévela a **En curso** con tu firma: `@ia-<herramienta>-<persona>` (ej. `@ia-claude-alex`).
- Trabaja en una rama propia y abre un PR. Nunca empujes a `main`.
- Si necesitas algo de otra persona o agente, añádelo a **Preguntas abiertas** en `vault/Tablero.md` mencionándolo con `@nombre`.
- Si tomas una decisión de diseño, crea `vault/Decisiones/NNNN-titulo.md` con `vault/Plantillas/Decision.md` en estado **Propuesta**. Solo una persona la pasa a **Aceptada**.

## Al terminar

- Escribe `vault/Bitacora/AAAA-MM-DD-<firma>.md` con `vault/Plantillas/Bitacora.md`. Un fichero por autor y día para no chocar con otros.
- Actualiza el estado de la tarea en el tablero y responde las preguntas dirigidas a ti.
- Todo en el mismo PR que el código.

## Límites

- Nunca datos reales del ICAT, datos personales, credenciales ni tokens.
- El OCR inventa texto en escaneos casi ilegibles: cualquier código que lo use debe pasar por el semáforo de calidad.
- La herramienta no decide (p. ej. sobre justicia gratuita): solo orienta.
