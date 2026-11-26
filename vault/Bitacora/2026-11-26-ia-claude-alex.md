# 2026-11-26 · @ia-claude-alex

## Hecho
- Frontend React (UMD + htm, sin build) con todas las pantallas de la [[Maqueta]]: login, landing, safata, procesando, revisión, justicia gratuita, anonimización, exportado, archivo e informes; CA/ES y guía de la demo.
- Conectado al OCR real: subida con modo único o doble, streaming por página, imagen junto al texto editable, diferencias en rojo con el recuadro sobre la imagen, avisos de DNI/NIE e IBAN mal formados y validación por página.
- Backend: semáforo de contraste (< 80 no se transcribe), `POST /page/<id>/<n>/ocr` (volver a transcribir o reescanear), `POST /export` (PDF solo desde el texto), `OCR_MOCK=1` y ruta relativa.
- `scripts/arrancar_demo.bat`: arranca Ollama, el modelo, la app y el navegador con un clic (`mock` para probar sin modelo).
- Probado de extremo a extremo con Playwright y `OCR_MOCK=1`.

## Siguiente
- Probar con PaddleOCR-VL real y escaneos reales: validar el umbral de contraste (percentil 0,05 %).
- El export corta el texto que no cabe en una página.

## Bloqueos / preguntas
- Justicia gratuita y anonimización siguen con datos ficticios de la maqueta.

## Hecho (tarde)
- Backend FastAPI real en `backend/` (sobre #48): documentos, OCR en streaming, páginas, revisión, justicia gratuita, anonimización con Presidio, export con hash, archivo con búsqueda, informes y auditoría, todo en PostgreSQL sin tocar V1..V15. `ruff` limpio y `pytest` 12/12 con BD.
- Frontend conectado a `/api/v1` sin datos ficticios; probado con Playwright con OCR simulado y con PaddleOCR-VL real.
- Despliegue decidido: todo en un servidor de Azure (pendiente de los datos de la VM). Preguntas de esquema para @Rubén y @Marina en el tablero.

## Siguiente
- Cola de OCR para dejar PDF transcribiéndose de noche y script de despliegue en Azure.
