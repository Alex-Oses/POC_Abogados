# 0004 · ¿Anonimizar antes o después de la revisión humana?

- **Estado**: Aceptada (2026-11-17, @Rubén)
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

**Opción 1**, aceptada por @Rubén el 2026-11-17: se guarda el original cifrado durante la revisión y la anonimización se aplica al construir las versiones de revisión y al exportar.

Motivos, con lo ya medido:

- La revisión del OCR que pide la propuesta necesita el texto y la imagen originales: sin ellos no se puede marcar una palabra ilegible ni corregir una lectura. Y la calidad del OCR no es un detalle: con un 4 % de errores, uno de cada diez datos personales se escapa de la anonimización ([`docs/presidio.md`](../../docs/presidio.md) § 6.4).
- La propia maqueta ya está construida así: la pantalla de revisión muestra el escaneo y el texto, y la de anonimización compara el original con lo tapado. La opción 2 obligaría a rehacer las dos.
- La opción 1 no debilita la promesa: el original se guarda cifrado, solo lo ve quien tiene permiso, y **lo que sale del Colegio es el PDF reconstruido** con el texto anonimizado ([[0007-generacion-pdf-final]]), que no contiene píxeles del original.
- Consecuencia: la [[API]] cambia. Donde hoy anonimiza al subir, guarda el original cifrado y la versión limpia; la anonimización se aplica al construir las versiones de revisión y al exportar.
