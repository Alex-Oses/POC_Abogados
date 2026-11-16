# 0001 · OCR local con PaddleOCR-VL 1.6 sobre Ollama

- **Estado**: Aceptada
- **Fecha**: 2026-11-06
- **Autor**: equipo POC

## Contexto

El ICAT es sensible a la privacidad y los documentos (justicia gratuita) contienen datos personales y económicos. Ver [[Rendimiento OCR]].

## Decisión

Usar PaddleOCR-VL 1.6 (GGUF, 0,9B) en local con Ollama. Nada sale del servidor. Alternativas si hiciera falta cambiar: MinerU2.5-Pro o GLM-OCR.

## Consecuencias

- Hace falta GPU NVIDIA (≥ 4 GB) en el servidor del Colegio.
- Obligatorio el semáforo de calidad: el modelo inventa texto en páginas casi ilegibles.
