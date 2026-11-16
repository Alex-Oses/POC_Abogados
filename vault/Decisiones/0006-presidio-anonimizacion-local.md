# 0006 · Presidio para detectar datos personales en local

- **Estado**: Propuesta
- **Fecha**: 2026-11-16
- **Autor**: @ia-claude-alex (para @Alex)

## Contexto

Hay que anonimizar sin que los documentos salgan del servidor. Ver [[Anonimizacion con Presidio]].

## Decisión

Usar Presidio (analyzer + anonymizer) con spaCy en castellano y catalán, con patrones propios para lo que no trae (referencia catastral, matrícula, dirección completa). La detección es una propuesta: la persona revisora decide en la pantalla de anonimización.

## Consecuencias

- Dependencia Python en el backend (@Rubén) o como servicio aparte (@Kevin).
- Para el POC, la exportación genera un PDF nuevo desde el texto anonimizado; tapar la imagen original queda como deuda.
