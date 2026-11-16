# 0004 · ¿Anonimizar antes o después de la revisión humana?

- **Estado**: Propuesta (por decidir)
- **Fecha**: 2026-11-16
- **Autor**: @ia-claude-alex

## Contexto

Los documentos se contradicen:

- La [[API]] anonimiza en servidor **antes de guardar nada**; solo persiste el texto limpio.
- La [[Propuesta ICAT]] quiere revisión humana del OCR, anonimización revisable con «Vista original» y ficha con el texto original para usuarios con permiso.
- La [[Base de datos]] guarda `anotaciones_entidad.texto_original` durante el proceso y versiones hasta `final_aprobado`.

## Opciones

1. Guardar original cifrado durante la revisión y anonimizar al exportar (encaja con Propuesta y BBDD; cambia la API).
2. Anonimizar al subir (API actual); se pierde la revisión del OCR y de la anonimización.

## Decisión

Pendiente.
