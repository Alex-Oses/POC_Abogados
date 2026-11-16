# 2026-11-16 · @ia-opencode-alex

## Hecho

- `investigacion/paddleocr/bench.py`: benchmark mínimo de PaddleOCR-VL por Ollama (misma configuración que [[Rendimiento OCR]]): páginas de entrada, calentamiento, 1 a la vez y N en paralelo, y una fila Markdown lista para pegar.
- Medido en este portátil (sin GPU, 100 % CPU): **41,6 s/página** secuencial y **36,7 s/página** con 4 en paralelo → **~100 páginas/hora**.
- Medido en la VM `genai-openllm-vm` (también `100% CPU`, sin GPU): **13,8 s/página** → **~260 páginas/hora**. Tres veces más rápido que el portátil y ~10 veces más lento que la RTX 3050. Tabla comparativa en [[Rendimiento OCR]] § Comparativa de equipos.
- Informe en PDF (local, no versionado): `docs/rendimiento.pdf`, con el informe anterior completo más la comparativa.

## Siguiente

- Medir el DGX Spark con el mismo script: es el servidor definitivo ([[Servidor definitivo]]) y no es la VM medida, así que esa fila todavía no vale para el hardware final.
- Repetir la medición en la VM con `OLLAMA_NUM_PARALLEL=4`: el dato de paralelo actual no vale porque las peticiones se encolan.
- Medir con escaneos reales densos; el BOE digital y las capturas de la maqueta pesan menos que un escaneo a 200 dpi.

## Bloqueos / preguntas

- @Alex: falta la prueba de humo de Ollama en Arm64 (DGX Spark) antes de dar por buena la fila del servidor definitivo.
