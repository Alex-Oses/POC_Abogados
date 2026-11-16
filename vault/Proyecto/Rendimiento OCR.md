# Rendimiento OCR · PaddleOCR-VL 1.6

Fuente: *PaddleOCR-VL 1.6 · Resultados de rendimiento en local* (06/11/2026).

## Resumen

- ~1 % de errores de carácter (CER) y 100 % de DNI, importes y referencias exactos con escaneos limpios o malos.
- Fax: 3,7 % CER, 69,7 % claves exactas. Muy mala calidad: 54 % CER, **inventa texto sin avisar**.
- ~2.750 páginas/hora en portátil con RTX 3050 4 GB. PDF de 100 páginas ≈ 2 min.
- OmniDocBench v1.6: 96,3 (primero, publicado por el propio equipo de PaddleOCR; sin réplica independiente).

## Entorno de prueba

Ryzen 7 6800HS, 16 GB RAM, RTX 3050 Laptop 4 GB, Windows 11, Ollama 0.40.14, GGUF oficial (0,9B, 1,8 GB). 12 páginas jurídicas sintéticas + BOE real (LAU 1994) + manuscritos, tablas, sellos y catalán, en 16 calidades.

## Velocidad

| Modo | s/página |
|---|---|
| 1 a la vez | ~4,5-5,3 |
| 4 en paralelo | 1,3 |
| Solo CPU | ~30 |

## Por tipo de documento

BOE 1994: 97-98 % palabras correctas · Tablas: 99 % celdas (prompt «OCR:») · Sellos y notas a mano no empeoran · Catalán: pierde el punto de «l·l» y el apóstrofo sale recto · Manuscrito: solo probado con letra simulada.

## Semáforo (páginas casi ilegibles)

- Antes del OCR: contraste de la imagen. Ilegibles ≈ 46, resto ≥ 110. **< 80 → volver a escanear.**
- Después: página casi vacía, otros alfabetos o mucha repetición. Detecta 66 % de páginas malas sin falsas alarmas.
- Segunda pasada a temperatura 0,4: marca el 42 % de errores con 83 % de precisión.

## Configuración recomendada

| Parámetro | Valor |
|---|---|
| Servidor | Ollama, un único modelo en GPU |
| `num_ctx` | 4096 |
| Llamada | `POST /api/generate`, prompt `OCR:`, imagen base64, `temperature 0` |
| Bucles | `repeat_penalty 1.05`, `num_predict 1500`; al tope, reintento con 1.2 |
| Paralelismo | `OLLAMA_NUM_PARALLEL=4` |
| Entrada PDF | Extraer la imagen original, sin renderizar ni preprocesar |
| Mínimo | GPU NVIDIA 4 GB, 16 GB RAM |

Estimación (no medida): RTX 4090 / L40S → 12.000-24.000 páginas/hora.

## Pendiente de probar

Documentos reales del Colegio · letra manuscrita real · rendimiento en el servidor definitivo · umbrales del semáforo con escaneos reales.
