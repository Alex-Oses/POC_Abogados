# Servidor definitivo

- **Estado**: decidido el equipo; sin medir todavía
- **Responsable**: @Kevin (infraestructura) · @Alex (medición del OCR)
- **Dato de**: @Alex, 2026-11-16

## Equipo

**NVIDIA DGX Spark** (GB10 Grace Blackwell).

| | |
|---|---|
| CPU | 20 núcleos Arm (10 Cortex-X925 + 10 Cortex-A725) |
| GPU | Blackwell, 6.144 núcleos CUDA, Tensor de 5.ª generación |
| Memoria | 128 GB unificados (LPDDR5x) · **273 GB/s** |
| Potencia IA | hasta 1 PFLOP en FP4 |
| Consumo | 240 W |
| Sistema | DGX OS (Ubuntu sobre **Arm64**) |

## Qué implica para el POC

**A favor.** Los 128 GB unificados permiten tener a la vez el OCR (Ollama + PaddleOCR-VL), los modelos de spaCy de Presidio y la base de datos sin repartir memoria. Y el ancho de banda (273 GB/s) y la GPU (6.144 núcleos) están por encima del portátil de referencia con RTX 3050 (~192 GB/s, 2.048 núcleos): **debería ser más rápida, pero no está medido**. En [[Rendimiento OCR]] la fila del servidor sigue en «pendiente» hasta que se mida con `investigacion/paddleocr/bench.py`.

**Riesgo: es Arm64, no x86.** Todo el stack tiene que funcionar en esa arquitectura y eso se comprueba antes de dar el servidor por bueno:

- Ollama (hay build oficial para Linux Arm64) y el GGUF de PaddleOCR-VL.
- spaCy y Presidio: ruedas de Python para aarch64.
- PostgreSQL, Redis y los contenedores del despliegue: imágenes multiarquitectura.
- `numeros` de los modelos: si alguna versión fijada no trae rueda para aarch64, habrá que compilar o cambiar de versión.

**A tener en cuenta.** Es un equipo de escritorio (240 W), no un servidor de rack: sirve de sobra para el POC y para un Colegio, pero la concurrencia real (varios documentos a la vez) hay que medirla antes de prometer cifras.

## Siguiente

- [ ] Prueba de humo en el Spark: Ollama + PaddleOCR-VL, Presidio con los dos modelos y PostgreSQL.
- [ ] Repetir `investigacion/paddleocr/bench.py` y `investigacion/presidio/benchmark.py` allí y actualizar las tablas.
- [ ] Confirmar con @Kevin quién lo instala y dónde queda (red del Colegio o fuera).
