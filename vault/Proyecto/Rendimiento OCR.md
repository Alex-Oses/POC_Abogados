# Rendimiento OCR · PaddleOCR-VL 1.6

Fuente: *PaddleOCR-VL 1.6 · Resultados de rendimiento en local* (06/11/2026).

## Resumen

- ~1 % de errores de carácter (CER) y 100 % de DNI, importes y referencias exactos con escaneos limpios o malos.
- Fax: 3,7 % CER, 69,7 % claves exactas. Muy mala calidad: 54 % CER, **inventa texto sin avisar**.
- ~2.750 páginas/hora en portátil con RTX 3050 4 GB. PDF de 100 páginas ≈ 2 min.
- Sin GPU baja a ~100 (portátil) y ~260 (servidor) páginas/hora: ver § Comparativa de equipos.
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

## Comparativa de equipos

Medido con `investigacion/paddleocr/bench.py`: mismas páginas, `temperature 0`, `num_ctx 4096`, `repeat_penalty 1.05`, `num_predict 1500`, tras un calentamiento. `OLLAMA_NUM_PARALLEL` ≥ paralelismo probado.

| Equipo | CPU | GPU | s/pág (1 a la vez) | s/pág (4 en paralelo) | pág/hora |
|---|---|---|---|---|---|
| Portátil de referencia (06/11) | Ryzen 7 6800HS, 16 GB | RTX 3050 Laptop 4 GB | 4,5–5,3 | 1,3 | ~2.750 |
| Este portátil (16/11) | Intel Tiger Lake (11.ª gen) | ninguna (100 % CPU) | 41,6 | 36,7 | ~100 |
| Servidor `genai-openllm-vm` (16/11) | x86_64 (VM) | ninguna (100 % CPU)¹ | 13,8 | 13,8² | ~260 |

¹ `ollama ps` confirma `100% CPU`: la VM no tiene GPU disponible para Ollama.
² Idéntico al secuencial porque `OLLAMA_NUM_PARALLEL` está en 1 (por defecto): las 4 peticiones se encolan, no se reparten. Repetir con `OLLAMA_NUM_PARALLEL=4` para tener el dato real.

Medir con 4 páginas o más: con una sola página el modelo ya está caliente y el resultado se infla (~350 pág/h en la misma máquina).

Conclusiones:

- Sin GPU, el OCR es entre 3 y 30 veces más lento que con la RTX 3050 (servidor ≈ 260 pág/h, portátil ≈ 100 pág/h, referencia ≈ 2.750 pág/h). Para el servidor, GPU NVIDIA sigue siendo requisito, no optimización.
- Un PDF de 100 páginas: ~2 min con RTX 3050, ~20 min en el servidor y ~1 h en el portátil pequeño.
- En CPU el paralelismo no aporta nada; el límite es el número de núcleos.

**El servidor definitivo será un NVIDIA DGX Spark** (GB10, GPU Blackwell, 128 GB unificados a 273 GB/s, Arm64; ver [[Servidor definitivo]]). **No está medido**: no tiene fila en la tabla hasta repetir `bench.py` allí, y antes hay que comprobar que Ollama, el GGUF de PaddleOCR-VL y Presidio funcionan en Arm64. Por sus cifras de ancho de banda y núcleos debería superar a la RTX 3050, pero eso es una estimación, no un dato.

## Cómo repetirlo

```bash
python investigacion/paddleocr/bench.py pagina1.png pagina2.png ... [--paralelo 4]
ollama ps   # confirma si está en GPU o en CPU
```

Informe en PDF: `docs/rendimiento.pdf`, generado en local (los `.pdf` no se versionan). Se regenera con `python docs/pdf.py "vault/Proyecto/Rendimiento OCR.md" docs/rendimiento.pdf`.

## Pendiente de probar

Documentos reales del Colegio · letra manuscrita real · rendimiento en el servidor definitivo · umbrales del semáforo con escaneos reales.
