# 0006 — Generación del PDF final

- **Estado**: Propuesta
- **Fecha**: 2026-11-16
- **Autor**: @ia-opencode-ruben

## Contexto

El expediente se cierra con `POST /documents/{id}/export` (regla A-16 de [docs/reglas/aprobacion.md](../../docs/reglas/aprobacion.md)). Falta decidir **qué se guarda del original y cómo se reconstruye el PDF final**, con tres restricciones del proyecto:

- El 95 % del corpus son escaneos procesados con PaddleOCR-VL 1.6 sobre Ollama, que devuelve **cajas por bloque** con `label`, `coordinate` y `orden_lectura`. No hay coordenadas por palabra ni estilos.
- El PDF es lo único que sale del despacho: no puede contener texto recuperable del original.
- El export tiene que consumir poco tiempo y recursos; no puede volver a pasar por OCR.

Detalle técnico completo: [docs/export/pdf.md](../../docs/export/pdf.md).

## Decisión

**Opción 1 — reconstruir desde la estructura.** Se guarda un JSON de estructura por versión (`documentos/{id}/v{n}/estructura.json`, puntero en `versiones_documento.metadatos_proceso`) y el PDF se compone desde ahí con el texto ya anonimizado:

- Lienzo nuevo en `reportlab`, una página por página del original, con sus medidas.
- Cada bloque en su `bbox` convertida de píxeles a puntos, en orden de lectura. Si el OCR solo devuelve texto, sin cajas, el mismo render usa un flujo de una columna con el orden y la jerarquía (`origen_geometria = secuencial`, sección 4 de [docs/export/pdf.md](../../docs/export/pdf.md)).
- Estilos normalizados una vez por documento (escala tipográfica fija, márgenes por mediana, alineación por centrado del bloque, rol por `label`).
- Tablas dibujadas como retícula con las celdas anonimizadas; sellos e imágenes sustituidos por `[SELLO]`/`[IMAGEN]`.
- Sin píxeles, sin capa de texto oculta, sin metadatos del escaneo.
- Determinista (`rl_config.invariant = 1`): mismo texto, mismo SHA-256, y el export es idempotente.

La estructura es **derivada y regenerable**: se puede borrar y reconstruir desde `bloques_layout` con el mismo resultado. Vive lo mismo que la versión, no 24 h.

## Opción 2 — no elegida: imagen del escaneo + repintado por bloque

Se incrusta el raster original y se tapan las entidades con cajas opacas, dibujando el texto sustituido encima. Queda registrada como **posibilidad futura**, no descartada:

- Fidelidad visual casi idéntica al escaneo (incluye sellos, firmas y textura).
- Coste mayor: recortar y recomprimir el raster son 20-40 ms/página frente a 5-10 ms de la reconstrucción.
- Riesgo de privacidad: los píxeles del original siguen dentro del PDF. Como no hay coordenadas por palabra, una entidad dentro de un párrafo obliga a tapar el bloque entero, y un fallo de detección o una caja desplazada deja el dato visible. No cumple «eliminar de verdad el texto original (capa, imagen y metadatos)» del README.

**Cuándo reconsiderarla:** solo en páginas con `etiqueta = table|seal|image` donde la reconstrucción se quede corta, y siempre con revisión humana de la caja antes de exportar. Si se adopta, será una decisión nueva que sustituya a esta.

## Consecuencias

- **Coste:** estructura 2-5 ms/página, render 3-8 ms/página; 100 páginas en menos de 1,5 s y sin GPU, frente a ~2 min de OCR.
- **Fidelidad:** se conserva la maquetación, no el aspecto. Sellos, firmas manuscritas y ruido del escaneo no se reproducen.
- **Modelo de datos:** no se toca. `versiones_documento.ruta_pdf` y `metadatos_proceso` ya existen; `hash_export` se guarda en `metadatos_proceso->>'hash_export'`.
- **Geometría:** depende de que el OCR devuelva cajas. PaddleOCR-VL por Ollama con el prompt `OCR:` devuelve solo texto hoy; el export funciona en modo secuencial y gana la retícula original cuando el layout esté disponible.
- **Dependencias:** `fastapi`, `uvicorn`, `psycopg`, `reportlab`. Nada de PyMuPDF (AGPL).
- **Pruebas obligatorias:** no fuga del texto original, presencia del texto sustituido, determinismo del hash, bloqueo con anotaciones pendientes.
- Depende de [[0004-anonimizacion-antes-o-despues-de-revision]]: el flujo asume que se conserva el original y se anonimiza antes de la revisión.
- Fuera de alcance: Word, PDF/A y firma electrónica.
