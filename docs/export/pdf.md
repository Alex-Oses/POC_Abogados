# PDF final — reconstrucción desde la estructura

**Estado:** aceptado (23/11/2026), pendiente de implementar.
**Contrato:** `docs/api/endpoints.md` (`POST /documents/{id}/export` y `POST /transform/build`).
**Reglas:** `docs/reglas/aprobacion.md` (A-16 a A-19).
**Decisión:** [0007](../../vault/Decisiones/0007-generacion-pdf-final.md).
**Responsable:** @Rubén.

## 1. Alcance

Generar el PDF definitivo de una versión aprobada a partir de tres cosas que ya existen: el texto de revisión, los bloques de layout y las decisiones humanas sobre cada entidad. La generación no vuelve a ejecutar OCR ni Presidio y no decide qué entidad se mantiene o sustituye.

PaddleOCR-VL 1.6, la versión que usamos, **devuelve solo texto, sin coordenadas**. La geometría no sale del OCR: se obtiene al principio del proceso, de la capa de texto del PDF original si existe o de un detector de layout aparte; si no hay ninguna de las dos, se usan bloques sintéticos por página. El export consume lo que ya esté guardado y nunca vuelve a analizar el documento.

La implementación vive en el backend Python, junto a FastAPI y los servicios de dominio. ReportLab recibe datos ya validados por el servicio de exportación y escribe únicamente el PDF reconstruido.

Fuera de alcance: exportación a Word, PDF/A, firma electrónica y el modo imagen (ver decisión 0007).

## 2. Decisión

Se **reconstruye** la página: lienzo nuevo, texto nuevo, sin ningún píxel del escaneo original.

El motivo no es estético. El PDF es lo único que sale del despacho, y si el original no está dentro no hay forma de recuperarlo: ni capa de texto oculta, ni metadatos, ni zona sin censurar. Un recorte mal colocado en el modo imagen es una fuga; aquí no hay recortes.

La contrapartida, aceptada: sellos, firmas manuscritas y textura del escaneo no se reproducen. Se conserva la maquetación, no el aspecto.

## 3. Entrada y salida

| Entrada | Uso |
|---|---|
| `versiones_documento` (`final_aprobado`, o `anonimizado_ia` para vista previa) | Texto de origen; **nunca** sustituciones ya materializadas |
| `bloques_layout` | Bloques de la **versión revisada** (la que referencian las anotaciones); `final_aprobado` no los duplica. Geometría, orden de lectura, etiqueta y texto por bloque; base de los offsets |
| `anotaciones_entidad` | Qué se sustituye y qué se mantiene; `decision_revisor`, `bloque_id` |
| `configuracion_sistema` | `pdf_export_incluir_marcas_agua`, `pdf_export_metadatos_limpios` |

| Salida | Dónde |
|---|---|
| PDF | `versiones_documento.ruta_pdf` |
| SHA-256 | `versiones_documento.metadatos_proceso->>'hash_export'` |
| Estado | `documentos.estado = 'exportado'` |

**Semántica del texto.** `contenido_texto` y `contenido_html` de cualquier versión guardan el texto **de origen**, tal como lo leyó el OCR o el layout. Las sustituciones no se escriben en la versión: viven en `anotaciones_entidad` y se aplican al construir una salida (PDF o texto plano). Así los offsets siguen siendo válidos y no hay doble sustitución. `final_aprobado` es la instantánea aprobada del texto de origen y del conjunto de decisiones, no un texto ya censurado.

El modelo de datos no cambia: `ruta_pdf` y `metadatos_proceso` ya existen; el hash va dentro de `metadatos_proceso->>'hash_export'` y la fecha de exportación es `documentos.exportado_en` (`V15`).

## 4. La estructura

Un JSON por versión, no por página. Es un derivado: se puede borrar y regenerar de forma determinista desde `bloques_layout` y el texto.

```json
{
  "version_id": "uuid",
  "motor": "paddle-ocr-vl-1.6",
  "origen_geometria": "layout",
  "estilo": {
    "fuente_cuerpo": "NotoSerif",
    "fuente_titulo": "NotoSans",
    "escala_pt": [8, 9, 10, 11, 12, 14, 18, 24],
    "margen_izq_pt": 70.9,
    "margen_der_pt": 70.9
  },
  "paginas": [
    {
      "numero": 1,
      "ancho_pt": 595.3,
      "alto_pt": 841.9,
      "bloques": [
        {
          "bloque_id": "uuid",
          "rol": "titulo",
          "bbox_pt": [70.9, 711.9, 524.4, 751.9],
          "estilo": { "tamano_pt": 18, "negrita": true, "alineacion": "centro" },
          "lineas": ["ESCRITURA DE COMPRAVENTA"]
        }
      ],
      "tablas": [
        { "bloque_id": "uuid", "bbox_pt": [70.9, 500.0, 524.4, 600.0],
          "filas": 3, "columnas": 2, "bordes": true }
      ],
      "graficos": [
        { "bloque_id": "uuid", "bbox_pt": [420.0, 80.0, 520.0, 170.0], "sustituto": "SELLO" }
      ]
    }
  ]
}
```

**Coordenadas.** `bloques_layout` usa píxeles con origen arriba-izquierda; el PDF, puntos con origen abajo-izquierda. La conversión es:

```text
x_pt     = x_px * (ancho_pt / pagina_ancho)
y_pt     = (pagina_alto - (y_px + alto_px)) * (alto_pt / pagina_alto)
ancho_pt = bbox_ancho * (ancho_pt / pagina_ancho)
alto_pt  = bbox_alto * (alto_pt / pagina_alto)
```

`y_pt` es la esquina inferior izquierda de la caja en el PDF. Sin restar `alto_px` todo sale desplazado hacia arriba.

**Dónde se guarda.** `documentos/{id}/v{n}/estructura.json` en el almacenamiento, con el puntero `estructura_path` en `metadatos_proceso`. La base de datos no se toca y el puntero se actualiza con `jsonb_set`, nunca reemplazando el objeto entero (así no se pisa `hash_export`).

**Cuándo se construye.** De forma perezosa, en la primera petición de vista previa o de export de esa versión. Es regenerable: si falta o no parsea, se reconstruye desde `bloques_layout`; si ya está exportada y la reconstrucción no coincide con el hash, se responde `EXPORT_INTEGRITY` y no se toca nada. Tras exportar, estructura y PDF quedan congelados con la versión.

### De dónde sale la geometría

PaddleOCR-VL 1.6 no da cajas. Al principio del proceso, antes de la revisión, se intenta en este orden:

1. **La capa de texto del PDF subido.** `pypdf` (BSD) extrae texto y cajas disponibles sin OCR. Si una versión no expone cajas suficientes, se pasa al punto 2.
2. **Un detector de layout aparte.** Sobre un escaneo sin capa, PP-Structure de PaddleOCR o `docling` (MIT) devuelven `label` y `coordinate` por bloque. Cuesta una pasada más por página, pero se hace una sola vez.
3. **Bloques sintéticos por página.** Si no hay geometría, se crea **un bloque por página** con `etiqueta = 'text'`, el `bbox` de la página completa y el texto del OCR en `contenido`. Es lo que permite que existan offsets y que el render funcione en modo `secuencial`.

Ningún paso de esta lista se ejecuta durante el export: cuando se exporta, los bloques ya existen.

| Modo | Cuándo | Qué se pinta |
|---|---|---|
| `layout` | Hay `bbox` por bloque | Cada bloque en su caja |
| `secuencial` | Solo hay texto, con bloque sintético por página | Flujo de una columna en A4: bloques en orden de lectura, título/subtítulo/párrafo por `label` si viene, márgenes y escala normalizados |

En modo secuencial el PDF es un documento nuevo bien maquetado, no una réplica de la retícula: se conserva el orden y la jerarquía, no las posiciones.

### Normalización: la consistencia

La estructura no se copia tal cual del detector, se normaliza una vez por documento:

| Regla | Cómo |
|---|---|
| Rol | Por `label`: `doc_title` → título, `paragraph_title` → subtítulo, `text` → párrafo, `table` → tabla, `image`/`seal` → gráfico, `footer`/`page_number` → pie |
| Tamaño | `alto_caja / n_lineas * 0.75`, llevado al valor más cercano de `escala_pt` |
| Márgenes | Mediana de `x1` y de `ancho - x2` de los bloques de texto del documento entero |
| Alineación | Centrado si el centro del bloque coincide con el de la caja de texto en menos del 2 % del ancho y tiene una o dos líneas; si no, izquierda |
| Orden | `(pagina_numero, orden_lectura)`; nunca por posición en pantalla |
| Vacíos | Se descartan los bloques sin texto salvo `image`/`seal`, que pasan a `graficos` |
| Página | Tamaño de `pagina_ancho/alto`; si falta, A4 |

Esto es lo que evita el efecto «recortes pegados»: aunque la anonimización cambie la longitud del texto, la retícula y los tamaños son los mismos en todas las páginas.

## 5. Texto que se pinta

El texto de partida es `bloques_layout.contenido` de la **versión revisada** (la de las anotaciones, `revisiones.version_id`). `final_aprobado` es la marca de aprobación y la dueña de `ruta_pdf` y del hash, pero no duplica bloques ni texto sustituido. Cada anotación se traduce a un reemplazo **dentro de su bloque**:

| `decision_revisor` | Qué se pinta |
|---|---|
| `confirmado` | `texto_sustitucion` de la anotación |
| `modificado` | `texto_sustitucion` editado por el revisor |
| `falso_positivo` | `texto_original` (no era un dato) |
| `falso_negativo` | `texto_sustitucion` obligatorio: el dato que el detector no vio también se sustituye |
| `null` | **Error**: no se exporta con anotaciones pendientes (A-09) |

Una anotación sin `bloque_id`, o con decisión `confirmado`, `modificado` o `falso_negativo` y sin `texto_sustitucion`, devuelve `422`: no se puede garantizar que el texto de origen desaparezca.

**Comprobación del rango.** `inicio_offset` y `fin_offset` son índices de carácter dentro de `bloques_layout.contenido` del bloque enlazado. Antes de sustituir se normaliza a Unicode NFC el fragmento y `texto_original`; si no coinciden exactamente, el export falla con `409 OFFSET_MISMATCH`. No se adivina ni se recoloca: la estructura y el texto se han desincronizado y hay que reprocesar.

Los reemplazos se aplican de mayor a menor `inicio_offset` para que los índices no se desplacen. El texto resultante de cada bloque es el que se pinta; ninguna salida contiene el `texto_original` de una anotación confirmada, modificada o falso negativo.

## 6. Algoritmo

1. Cargar la revisión aprobada, la versión revisada (la de las anotaciones), sus bloques y sus anotaciones en una sola consulta por documento; la fila `final_aprobado` aporta el estado y recibe `ruta_pdf` y `hash_export`. Bloquear la fila del documento (`SELECT … FOR UPDATE`).
2. Verificar que no queda ninguna anotación sin decisión, sin bloque o con `texto_original` que no cuadre.
3. Localizar la estructura guardada o construirla en modo `layout` o `secuencial`.
4. Abrir `reportlab` con `rl_config.invariant = 1` y A4/página original.
5. Para cada página: fondo blanco, bloques en orden de lectura (`layout`: en su caja; `secuencial`: en flujo de una columna), tablas como retícula, gráficos como recuadro con la etiqueta `[SELLO]` o `[IMAGEN]`.
6. Pie de página con «ANONIMIZADO — CONFIDENCIAL» si la config lo pide.
7. Metadatos limpios: sin autor original, sin fechas del escaneo, sin GPS; título neutro.
8. Calcular SHA-256, escribir el PDF en un temporal del mismo directorio, sincronizarlo y renombrarlo de forma atómica. Después actualizar `ruta_pdf`, `metadatos_proceso` (`hash_export` y `estructura_path`) y `documentos.estado` en la misma transacción. Si la transacción falla, se retira el temporal.
9. Segunda llamada: si la versión está `exportado` y existen fichero y hash, se recalcula el hash del fichero y se devuelve sin regenerar. Si no cuadra o falta, `500 EXPORT_INTEGRITY`: **nunca** se sobrescribe el PDF de una versión exportada (A-18). La recuperación es restaurar la copia de seguridad, no generar otro PDF.

**Tablas.** El contenido del bloque `table` se sustituye primero y luego se parsea como tabla markdown de tuberías (`| a | b |`). Si no parsea, se intenta HTML `<table>`; si tampoco, el bloque degrada a párrafo y se registra un aviso en `metadatos_proceso`. Las celdas siempre llevan las sustituciones ya aplicadas.

**Determinismo.** `rl_config.invariant = 1` fija fecha e identificador, pero el hash solo es estable dentro del mismo entorno: mismas versiones de ReportLab, `pypdf` y de las fuentes Noto. Las dependencias se fijan en el despliegue; un cambio de versión puede cambiar el hash y se trata como cambio de entorno, no como regeneración silenciosa de un expediente.

## 7. Dependencias

```
fastapi, uvicorn, psycopg, reportlab, pypdf
```

Todas con licencia permisiva (MIT/BSD). `pypdf` aporta geometría de capa de texto con licencia BSD; no se usa PyMuPDF (AGPL). Las fuentes Noto Serif y Noto Sans (OFL) se incrustan como subconjunto; ReportLab lo hace solo.

## 8. Rendimiento

| Operación | Coste |
|---|---|
| Construir la estructura desde `bloques_layout` | 2-5 ms/página |
| Normalizar estilos | ~1 ms/documento |
| Render de texto y tablas | 3-8 ms/página |
| **PDF de 100 páginas** | **< 1,5 s** |
| Memoria pico | < 100 MB (página a página, sin cargar el documento entero) |
| Estructura en disco | 3-8 KB/página |

El detector de layout es un coste de ingesta, no de export. Para comparar: el OCR de esas 100 páginas tarda unos 2 minutos en la GPU; el export es entre el 1 % y el 2 % de ese coste y no usa GPU.

## 9. Pruebas

Obligatorias, en `backend/tests/test_pdf_export.py`:

1. **No fuga**: extraer el texto del PDF y comprobar que no aparece ningún `texto_original` de anotaciones confirmadas, modificadas ni falso negativo.
2. **Sí sustituido**: el texto extraído contiene `[NOMBRE_1]`, `[DNI_1]` y similares.
3. **Determinista**: dos ejecuciones producen el mismo SHA-256.
4. **Pendiente bloquea**: una anotación sin `decision_revisor` devuelve error, no PDF.
5. **Sin bloque bloquea**: una anotación sin `bloque_id` devuelve `422`.
6. **Falso negativo**: se sustituye y el texto original no aparece.
7. **Offsets por bloque**: dos bloques con el mismo texto no se confunden; el reemplazo cae en el bloque correcto.
8. **Unicode y espacios**: acentos descompuestos y comillas tipográficas no rompen el export; una diferencia real devuelve `409 OFFSET_MISMATCH`.
9. **Tabla**: una tabla de 3×2 conserva sus valores anonimizados y su número de filas.
10. **Concurrencia**: dos exportaciones simultáneas producen un solo fichero y un solo hash; la perdedora devuelve el mismo binario.
11. **Integridad**: con `exportado`, fichero ausente o hash manipulado devuelve `500` y no reescribe el PDF.
12. **Secuencial**: un documento sin cajas genera un bloque sintético por página y un PDF válido.
13. **Presupuesto**: 20 páginas sintéticas por debajo de 1 s en el portátil de referencia.

## 10. Riesgos y límites

| Riesgo | Mitigación |
|---|---|
| Sellos y firmas desaparecen | Sustituto explícito `[SELLO]`/`[FIRMA]`; el revisor lo ve antes de aprobar |
| Tablas mal reconocidas | Si el markdown y el HTML no parsean, el bloque degrada a párrafo y la prueba 9 lo detecta |
| Fidelidad visual distinta al escaneo | Aceptada en la decisión 0007; el modo imagen queda como posibilidad futura |
| Sin geometría, no hay réplica de la retícula | Bloque sintético por página y modo `secuencial`; cuando llegue el layout, el mismo JSON gana `bbox` sin tocar el render |
| Estructura desincronizada | Fallar antes de escribir el PDF (`409 OFFSET_MISMATCH`), nunca generar uno a medias |
| Párrafos largos que no caben en su caja | Reducir un escalón la fuente; si aún no cabe, recortar con `…` y registrar aviso en `metadatos_proceso` |
| Pérdida del PDF ya exportado | No se regenera: se restaura de copia. El expediente exportado es terminal |
| PDF sin cifrar en reposo y sin PDF/A ni firma | Fuera de alcance; si el juzgado lo exige, será una decisión nueva |
| Dependencias que cambian el hash | Versiones fijadas; el hash se valida contra el fichero, no contra un valor de confianza |

## 11. Plan de entrega

| Fase | Qué | Aceptación |
|---|---|---|
| 1 | Generar y guardar la estructura normalizada desde `bloques_layout` | JSON válido para un documento real de 3 páginas; regenerable con el mismo resultado |
| 2 | Render de texto y páginas (sin tablas) | PDF abre en el visor, texto seleccionable y acentos catalanes correctos |
| 3 | Tablas, gráficos sustitutos y pie | Pruebas 9 y 13 en verde |
| 4 | Export: hash, `ruta_pdf`, estado, bloqueo e idempotencia | Pruebas 1-4, 10 y 11 en verde |
| 5 | Integración con `POST /documents/{id}/export` y `POST /transform/build` | `409` en estado incorrecto, `200` con binario y `X-Document-Hash` |
| 6 | Modo secuencial | Prueba 12 en verde con un escaneo sin capa |

## 12. Fuera de alcance

Word, PDF/A-2b, firma electrónica y el modo imagen + repintado por bloques. Este último está descrito como posibilidad futura en `vault/Decisiones/0007-generacion-pdf-final.md`.
