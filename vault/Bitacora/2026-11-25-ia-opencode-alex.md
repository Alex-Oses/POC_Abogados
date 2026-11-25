# 2026-11-25 · @ia-opencode-alex

## Hecho

- **Diseño de la maqueta aplicado**: cabecera ICAT, Roboto y los tokens de color de `maqueta/index.html`; una sola zona de arrastre y tiles por página (pendiente → girando con un spinner en la página en curso → verde con su tiempo) en lugar de la barra de progreso, y los resultados como tarjetas con el texto completo. Se mantiene una sola página (decisión de @Alex) en vez del flujo de tres vistas de la maqueta.
- **App demo de OCR**: `ocr_web_app.py` (Flask) convierte el PDF a imágenes con PyMuPDF y lo manda página a página a PaddleOCR-VL 1.6 por Ollama; `templates/index.html` sube el PDF y muestra la transcripción por página.
- **Progreso real**: `/ocr` responde con NDJSON en streaming (`start`, `page`, `done`, `error`) y el navegador lo lee con `response.body.getReader()`. Antes la barra consultaba un endpoint de mentira que siempre decía «procesando».
- Corregidos un `forEach` sin cerrar que rompía el script entero y el volcado del texto OCR con `innerHTML`, que se comía los `<` y `&`.
- Verificado de extremo a extremo con un PDF de 2 páginas: `start` → dos eventos `page` con el texto exacto → `done` (119 s). También los errores: fichero no PDF (400) y sin fichero (400).

## Siguiente

- Decidir si la demo se prueba también en el servidor Arm64 o solo en local.
- Pasar el texto por el semáforo de calidad antes de usarlo con escaneos ilegibles: el modelo inventa texto cuando no lee bien.

## Bloqueos / preguntas

- Ninguno.
