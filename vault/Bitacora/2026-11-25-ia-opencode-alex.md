# 2026-11-25 · @ia-opencode-alex

## Hecho

- **Diseño de la maqueta aplicado**: cabecera ICAT, Roboto y los tokens de color de `maqueta/index.html`; una sola zona de arrastre y tiles por página (pendiente → girando con un spinner en la página en curso → verde con su tiempo) en lugar de la barra de progreso, y los resultados como tarjetas con el texto completo. Se mantiene una sola página (decisión de @Alex) en vez del flujo de tres vistas de la maqueta.
- **App demo de OCR**: `ocr_web_app.py` (Flask) convierte el PDF a imágenes con PyMuPDF y lo manda página a página a PaddleOCR-VL 1.6 por Ollama; `templates/index.html` sube el PDF y muestra la transcripción por página.
- **Progreso real**: `/ocr` responde con NDJSON en streaming (`start`, `page`, `done`, `error`) y el navegador lo lee con `response.body.getReader()`. Antes la barra consultaba un endpoint de mentira que siempre decía «procesando».
- Corregidos un `forEach` sin cerrar que rompía el script entero y el volcado del texto OCR con `innerHTML`, que se comía los `<` y `&`.
- Verificado de extremo a extremo con un PDF de 2 páginas: `start` → dos eventos `page` con el texto exacto → `done` (119 s). También los errores: fichero no PDF (400) y sin fichero (400).

- **Página y transcripción en paralelo**: cada subida recibe un `upload_id` y sus páginas se guardan en `test_pdf_images_web/pages`; se sirven en `GET /page/<upload_id>/<n>.png`, así que a la izquierda se ve la página del PDF y a la derecha su transcripción. Los tiles navegan y el panel sigue automáticamente la página que se está transcribiendo; solo deja de seguir si el usuario pincha un tile.
- El texto llega al terminar cada página, no carácter a carácter: Ollama responde de una vez y el OCR no da parciales útiles.

- **Pasos de la maqueta**: la revisión va como en la maqueta, con los thumbs de páginas a la izquierda, la página en el centro y el texto a la derecha (`contenteditable`); los cambios se guardan por página al navegar y el chip pasa a «editado».
- **Doble transcripción**: selector única/doble antes de subir. En doble se hace una segunda pasada con temperatura 0,3 y las palabras que no coinciden se marcan en rojo, con la 2ª lectura en el tooltip. El diff ignora espacios y saltos de línea: solo cuenta como duda lo que cambia el texto. Probado con un escaneo borroso: 7 tramos en rojo, y con un PDF limpio: 0.

- **Frontend en React**: la interfaz pasa a React 18 servido desde Flask (`static/app.js`, React/htm vendorizados en `static/vendor`, sin build ni CDN). Componentes de login, landing y espacio de trabajo; el flujo es login falso (cualquier credencial) → landing → subida → revisión.
- **Revisión como la maqueta**: thumbs, página y texto editable; cada página se marca «revisada» con el botón y solo entonces se avanza a la siguiente, con contador X/Y revisadas y banner al terminar.
- **Resaltado al pasar el ratón**: al pasar sobre una palabra en rojo, se dibuja su caja sobre la imagen. La caja sale de la capa de texto del PDF (`find_rects` con PyMuPDF, coordenadas normalizadas); en un escaneo sin capa de texto se enmarca la página entera y se avisa de que no se puede localizar (el modelo no devuelve coordenadas).

## Siguiente

- Decidir si la demo se prueba también en el servidor Arm64 o solo en local.
- Pasar el texto por el semáforo de calidad antes de usarlo con escaneos ilegibles: el modelo inventa texto cuando no lee bien.

- La segunda lectura usa temperatura 0,3 para que el modelo pueda discrepar. Si se prefiere hacer dos pasadas idénticas (deterministas), se cambia en una línea.
## Bloqueos / preguntas

- Ninguno.
