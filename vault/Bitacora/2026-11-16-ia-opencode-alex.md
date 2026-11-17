# 2026-11-16 · @ia-opencode-alex

## Hecho

- `investigacion/paddleocr/bench.py`: benchmark mínimo de PaddleOCR-VL por Ollama (misma configuración que [[Rendimiento OCR]]): páginas de entrada, calentamiento, 1 a la vez y N en paralelo, y una fila Markdown lista para pegar.
- Medido en este portátil (sin GPU, 100 % CPU): **41,6 s/página** secuencial y **36,7 s/página** con 4 en paralelo → **~100 páginas/hora**. Tabla comparativa en [[Rendimiento OCR]] § Comparativa de equipos.
- Medido en el servidor `genai-openllm-vm` (también `100% CPU`, sin GPU): **13,8 s/página** → **~260 páginas/hora**. Tres veces más rápido que el portátil y ~10 veces más lento que la RTX 3050.

## Siguiente

- Medir el DGX Spark ([[Servidor definitivo]]) con `bench.py`: la fila «servidor» es la VM `genai-openllm-vm`, no el hardware final. Antes, prueba de humo de Ollama en Arm64.

- Pedir GPU en el servidor: sin ella el POC se queda en ~260 páginas/hora (100 páginas ≈ 20 min).
- Repetir la medición del servidor con `OLLAMA_NUM_PARALLEL=4` para saber si el paralelismo ayuda en CPU (el dato actual no vale: las peticiones se encolan).
- Medir con páginas de escaneo real denso; las capturas de la maqueta y el BOE digital pesan menos que un escaneo de 200 dpi.

## Bloqueos / preguntas

- @Alex: ¿el servidor definitivo tendrá GPU? Hoy es una VM sin acelerador y el POC no pasa de ~260 páginas/hora.
