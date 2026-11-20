---
description: Registra tu decisión o voto sobre una entrada de vault/Decisiones
---
Argumentos: `$ARGUMENTS`. El primer token es el número de decisión; el resto, tu decisión o voto (sin resto = OK). La persona eres tú: `git config user.name`.

1. **Localiza** `vault/Decisiones/NNNN-*.md`. Si no existe, créalo desde `vault/Plantillas/Decision.md` (estado `Propuesta`, autor `@ia-opencode-<persona>`, texto en § Decisión) y termina.
2. **Cabecera**, sin tocar el resto:
   - Cierra la propuesta → `- **Estado**: Aceptada (AAAA-MM-DD, @Persona)`.
   - Voto con otros pendientes → añade `@Persona (rol), AAAA-MM-DD: **texto**. Faltan @…` a `**Votos**`; sigue `Propuesta`.
   - Rechazo → `Rechazada (AAAA-MM-DD, @Persona)`.
3. **Si se acepta**: pasa a **Hecho** la línea del **Tablero** que enlace a ese número; si cierra un bloqueante, márcalo `**Resuelto (AAAA-MM-DD)**` en `Coherencia.md`.
4. **Si cambia algo de `docs/`**, aplica el cambio mínimo.
5. **Bitácora**: una línea en `vault/Bitacora/AAAA-MM-DD-ia-opencode-<persona>.md`.
6. **Commit y push** a la rama actual (nunca a `main`), con el PR abierto si lo hay.

Límites: solo una persona pasa una decisión a Aceptada, y eres tú; no toques `docs/architecture/` ni las migraciones; revierte `vault/.obsidian/community-plugins.json` antes de commitear; no reformatees markdown.

Responde en 3–5 líneas: qué registraste, qué ficheros tocaste y qué falta para cerrarla.
