---
description: Registra tu decisión o voto sobre una entrada de vault/Decisiones
---
Argumentos recibidos: `$ARGUMENTS`. El primer token es el número (`0002`) y el resto es tu decisión o voto. Si no hay resto, es un OK a la propuesta. La persona eres tú: `git config user.name`.

Registra la decisión con este procedimiento. No leas la bóveda entera ni resumas el proyecto: un `grep` del número basta.

1. **Localiza el fichero**: `vault/Decisiones/NNNN-*.md`, con un glob. Si no existe, créalo desde `vault/Plantillas/Decision.md` con el slug que salga del texto, estado `Propuesta`, autor `@ia-opencode-<persona>` y el texto en § Decisión; termina ahí.
2. **Acepta o vota** en la cabecera del fichero, sin tocar el resto:
   - OK o texto que cierra la propuesta → `- **Estado**: Aceptada (AAAA-MM-DD, @Persona)`.
   - Voto sin cerrarla (la decisión tiene `**Votos**` y faltan otros) → añade tu voto a `**Votos**` con el formato `@Persona (rol), AAAA-MM-DD: **texto**. Faltan @…`, quitándote de la lista de «Faltan». La decisión sigue `Propuesta`.
   - Rechazo → `Rechazada (AAAA-MM-DD, @Persona)`.
3. **Tablero** (`vault/Tablero.md`), solo si se acepta: pasa a **Hecho** la línea de **Pendiente** que enlace a ese número, con el resultado en una frase; si no hay línea, no añadas nada. Un voto no toca el tablero.
4. **Coherencia** (`vault/Proyecto/Coherencia.md`), solo si la decisión cierra un bloqueante: marca esa fila como `**Resuelto (AAAA-MM-DD)**`. Si no sabes cuál, no lo toques.
5. **Contrato o reglas**, solo si la decisión cambia algo de `docs/`: aplica el cambio mínimo y regenera el `.docx` afectado con `python local/md2docx.py <md> local/<nombre>.docx <Título> <Subtítulo> <Ref>`. Si no cambia nada, no regeneres ninguno.
6. **Bitácora**: una línea en `vault/Bitacora/AAAA-MM-DD-ia-opencode-<persona>.md` (créala desde `vault/Plantillas/Bitacora.md` si no existe). No reescribas la entrada entera.
7. **Commit y push** a la rama actual, con el PR abierto si lo hay. Nunca a `main`.

Límites: solo una persona pasa una decisión a Aceptada, y esa persona eres tú; no toques `docs/architecture/` ni las migraciones; revierte `vault/.obsidian/community-plugins.json` antes de commitear; no reformatees markdown ni añadas secciones que nadie pidió.

Responde con 3–5 líneas: qué has registrado, qué ficheros has tocado y qué sigue pendiente para cerrarla.
