# 0006 · Presidio para detectar datos personales en local

- **Estado**: Aceptada (2026-11-19, @Rubén)
- **Fecha**: 2026-11-16
- **Autor**: @ia-claude-alex (para @Alex)
- **Responsable de implementación**: @Rubén (Presidio y reglas de sustitución)

## Contexto

Hay que anonimizar sin que los documentos salgan del servidor. Ver [[Anonimizacion con Presidio]].

## Decisión

Usar Presidio (analyzer + anonymizer) con spaCy en castellano y catalán, con patrones propios para lo que no trae (referencia catastral, matrícula, dirección completa). La detección es una propuesta: la persona revisora decide en la pantalla de anonimización.

## Consecuencias

- Dependencia Python dentro del backend Python aceptado. Si Presidio se separa en el futuro y el API pasa a C# o Java, se llama por HTTP desde el backend; C# sería especialmente adecuado para ese caso de separación.
- Para el POC, la exportación genera un PDF nuevo desde el texto anonimizado; tapar la imagen original queda como deuda.
