# PDF final — reconstrucción desde la estructura

**Estado:** propuesta (16/11/2026), pendiente de implementar.
**Contrato:** `docs/api/endpoints.md` (`POST /documents/{id}/export` y `POST /transform/build`).
**Reglas:** `docs/reglas/aprobacion.md` (A-16 a A-19).
**Decisión:** [0007](../../vault/Decisiones/0007-generacion-pdf-final.md).

## 1. Alcance

Generar el PDF definitivo de una versión aprobada a partir de dos cosas que ya existen: el texto anonimizado y la estructura de la maquetación. No hace OCR, no anonimiza y no decide nada: solo compone.

Fuera de alcance: exportación a Word, PDF/A, firma electrónica y el modo imagen (ver decisión 0006).

## 2. Decisión

Se **reconstruye** la página: lienzo nuevo, texto nuevo, sin ningún píxel del escaneo original.

El motivo no es estético. El PDF es lo único que sale del despacho, y si el original no está dentro no hay forma de recuperarlo: ni capa de texto oculta, ni metadatos, ni zona sin censurar. Un recorte mal colocado en el modo imagen es una fuga; aquí no hay recortes.

La contrapartida, aceptada: sellos, firmas manuscritas y textura del escaneo no se reproducen. Se conserva la maquetación, no el aspecto.

## 3. Entrada y salida

| Entrada | Uso |
|---|---|
| `versiones_documento` (`final_aprobado`, o `anonimizado_ia` para vista previa) | `contenido_texto` y `contenido_html` |
| `bloques_layout` | Geometría, orden de lectura, etiqueta y texto por bloque |
| `anotaciones_entidad` | Qué se sustituye y qué se mantiene; `decision_revisor` |
| `configuracion_sistema` | `pdf_export_incluir_marcas_agua`, `pdf_export_metadatos_limpios` |

| Salida | Dónde |
|---|---|
| PDF | `versiones_documento.ruta_pdf` |
| SHA-256 | `versiones_documento.metadatos_proceso->>'hash_export'` |
| Estado | `documentos.estado = 'exportado'` |

El modelo de datos no cambia: `ruta_pdf` y `metadatos_proceso` ya existen y el hash va dentro de `metadatos_proceso->>'hash_export'`; la fecha de exportación es `documentos.exportado_en` (`V15`).

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

**Coordenadas.** `bloques_layout` usa píxeles con origen arriba-izquierda; el PDF, puntos con origen abajo-izquierda. La conversión es `x_pt = x_px * (ancho_pt / pagina_ancho)` y `y_pt = alto_pt - y2_px * (alto_pt / pagina_alto)`. Sin ese paso todo sale girado o en la esquina.

**Dónde se guarda.** `documentos/{id}/v{n}/estructura.json` en el almacenamiento, con el puntero en `metadatos_proceso`. La base de datos no se toca.

**Cuánto vive.** Lo mismo que la versión. Un TTL corto rompe el export diferido; si se quiere TTL, 30 días y el export la regenera cuando falte.

### Si el OCR no devuelve cajas

La geometría fina depende de la salida de layout de PaddleOCR-VL (`label`, `coordinate`, `orden_lectura`). Hoy, con el prompt `OCR:` por Ollama, el modelo devuelve **solo texto, sin posiciones**; está anotado en `vault/Investigacion/Anonimizacion con Presidio.md` y abierto en el tablero. El export no puede esperar a resolverlo, así que la estructura admite dos modos en `origen_geometria`:

| Modo | Cuándo | Qué se pinta |
|---|---|---|
| `layout` | Hay `bbox` por bloque | Cada bloque en su caja, como se describe arriba |
| `secuencial` | Solo hay texto | Flujo de una columna en A4: bloques en orden de lectura, título/subtítulo/párrafo por `label` si viene, márgenes y escala normalizados |

En modo secuencial el PDF es un documento nuevo bien maquetado, no una réplica de la retícula: se conserva el orden y la jerarquía, no las posiciones. Es lo que ya recomienda la investigación de Presidio (opción 1) y no cambia nada del resto del diseño: cuando el layout llegue, el mismo JSON se rellena con `bbox` y el render no se toca.

#### De dónde pueden salir las cajas

El texto lo da el OCR; la geometría no tiene por qué venir del mismo sitio. Por orden de coste:

1. **El propio PDF subido, si tiene capa de texto.** `PyMuPDF` (`page.get_text("dict")`) devuelve bloques, líneas y palabras con su caja, su tamaño de fuente y su origen, sin OCR y en milisegundos. Cubre el caso normal de un despacho: PDF generados por Word o por un escáner con OCR. La caja es la del original, que es justo lo que se quiere para reconstruir.
2. **Un modelo de layout, si es un escaneo sin capa.** El pipeline completo de PaddleOCR/PP-Structure (no el GGUF de Ollama) devuelve `label` y `coordinate` por bloque; `docling` (MIT) es la alternativa si el primero no encaja en el servidor. Cuesta una pasada más por página.
3. **Nada.** Modo `secuencial`, que ya está diseñado.

La recomendación es no elegir una: **el modo se decide por documento**. Al construir la estructura se intenta, en este orden, (1) la capa de texto del PDF subido, (2) las cajas del modelo de layout, (3) el flujo secuencial; y lo que quede se guarda en `origen_geometria` para que el render sea reproducible. Un lote real del Colegio traerá las tres cosas mezcladas, y así cada documento se reconstruye todo lo fiel que su original permita. Mientras no haya documentos reales medidos, el orden anterior es también la respuesta por defecto.

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

Cada anotación se traduce a un reemplazo dentro del bloque:

| `decision_revisor` | Qué se pinta |
|---|---|
| `confirmado` | `texto_sustitucion` de la anotación |
| `modificado` | `texto_sustitucion` editado por el revisor |
| `falso_positivo` | `texto_original` (no era un dato) |
| `falso_negativo` | El texto del bloque tal cual, con la entidad añadida a mano |
| `null` | **Error**: no se exporta con anotaciones pendientes (A-09) |

Los reemplazos se aplican de mayor a menor `inicio_offset` para que los índices no se desplacen. Si `texto_original` no coincide exactamente con el rango del bloque, el export falla con `409`: la estructura y el texto se han desincronizado y hay que reprocesar, no adivinar.

## 6. Algoritmo

1. Cargar la versión, sus bloques y las anotaciones en una sola consulta por documento.
2. Verificar que no queda ninguna anotación sin decisión.
3. Construir la estructura normalizada (sección 4) en modo `layout` o `secuencial` según haya `bbox`.
4. Abrir `reportlab` con `rl_config.invariant = 1` y A4/página original.
5. Para cada página: fondo blanco, bloques en orden de lectura (`layout`: en su caja; `secuencial`: en flujo de una columna), tablas como retícula, gráficos como recuadro con la etiqueta `[SELLO]` o `[IMAGEN]`.
6. Pie de página con «ANONIMIZADO — CONFIDENCIAL» si la config lo pide.
7. Metadatos limpios: sin autor original, sin fechas del escaneo, sin GPS; título neutro.
8. Calcular SHA-256, escribir el PDF, actualizar `ruta_pdf`, `metadatos_proceso` y `documentos.estado`.
9. Segunda llamada: si `ruta_pdf` existe y el hash cuadra, se devuelve el fichero guardado sin regenerar.

## 7. Dependencias

```
fastapi, uvicorn, psycopg, reportlab
```

Cuatro, todas con licencia permisiva (MIT/BSD). Nada de PyMuPDF (AGPL): obligaría a abrir el código del producto. Las fuentes Noto Serif y Noto Sans (OFL) se incrustan como subconjunto; reportlab lo hace solo.

## 8. Rendimiento

| Operación | Coste |
|---|---|
| Construir la estructura desde `bloques_layout` | 2-5 ms/página |
| Normalizar estilos | ~1 ms/documento |
| Render de texto y tablas | 3-8 ms/página |
| **PDF de 100 páginas** | **< 1,5 s** |
| Memoria pico | < 100 MB (página a página, sin cargar el documento entero) |
| Estructura en disco | 3-8 KB/página |

Para comparar: el OCR de esas 100 páginas tarda unos 2 minutos en la GPU. El export es entre el 1 % y el 2 % de ese coste y no usa GPU.

## 9. Pruebas

Obligatorias, en `backend/tests/test_pdf_export.py`:

1. **No fuga**: extraer el texto del PDF y comprobar que no aparece ningún `texto_original` de anotaciones confirmadas.
2. **Sí sustituido**: el texto extraído contiene `[NOMBRE_1]`, `[DNI_1]` y similares.
3. **Determinista**: dos ejecuciones producen el mismo SHA-256.
4. **Pendiente bloquea**: una anotación sin `decision_revisor` devuelve error, no PDF.
5. **Tabla**: una tabla de 3x2 conserva sus valores anonimizados y su número de filas.
6. **Presupuesto**: 20 páginas sintéticas por debajo de 1 s en el portátil de referencia.

## 10. Riesgos y límites

| Riesgo | Mitigación |
|---|---|
| Sellos y firmas desaparecen | Sustituto explícito `[SELLO]`/`[FIRMA]`; el revisor lo ve antes de aprobar |
| Tablas mal reconocidas | Si el HTML no parsea, el bloque degrada a párrafo y la prueba 5 lo detecta |
| Fidelidad visual distinta al escaneo | Aceptada en la decisión 0006; el modo imagen queda como posibilidad futura |
| Sin `bbox` del OCR, la retícula original no se puede replicar | Modo `secuencial`: flujo de una columna con orden y jerarquía; cuando llegue el layout, el mismo JSON gana `bbox` sin tocar el render |
| Estructura desincronizada | Fallar antes de escribir el PDF; nunca generar uno a medias |
| Párrafos largos que no caben en su caja | Reducir un escalón la fuente; si aún no cabe, recortar con `…` y registrar aviso en `metadatos_proceso` |

## 11. Plan de entrega

| Fase | Qué | Aceptación |
|---|---|---|
| 1 | Generar y guardar la estructura normalizada desde `bloques_layout` | JSON válido para un documento real de 3 páginas; regenerable con el mismo resultado |
| 2 | Render de texto y páginas (sin tablas) | PDF abre en el visor, texto seleccionable y acentos catalanes correctos |
| 3 | Tablas, gráficos sustitutos y pie | Pruebas 5 y 6 en verde |
| 4 | Export: hash, `ruta_pdf`, estado e idempotencia | Pruebas 1-4 en verde |
| 5 | Integración con `POST /documents/{id}/export` y `POST /transform/build` | `409` en estado incorrecto, `200` con binario y `X-Document-Hash` |

## 12. Fuera de alcance

Word, PDF/A-2b, firma electrónica y el modo imagen + repintado por bloques. Este último está descrito como posibilidad futura en `vault/Decisiones/0007-generacion-pdf-final.md`.
