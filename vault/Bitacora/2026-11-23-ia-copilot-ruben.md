# 2026-11-23 · @ia-copilot-ruben

## Hecho

- Aclarado el reparto técnico:
  - @Alex mantiene PaddleOCR-VL, el OCR y el semáforo de calidad.
  - @Rubén mantiene Presidio y la composición del PDF final.
  - @Yaser mantiene el recorrido y la orquestación del dato, sin implementar los motores.
- Añadida la decisión propuesta [[0016-responsabilidades-ocr-presidio-pdf]].
- Actualizados [[Equipo]], [[Enfoque tecnico]], las estructuras C#/Java/Python y [[0006-presidio-anonimizacion-local]].
- Actualizada la tarea de ajuste de Presidio en [[Tablero]]: pasa a @Rubén.
- Añadida una valoración explícita de C# + Presidio en [[0014-stack-backend-c-sharp-java-python]].
- Cambiado el stack a **Python 3.12 + FastAPI** como decisión aceptada. C# y Java se conservan como alternativas, y C# se señala como ventajoso si Presidio sale del backend como servicio independiente.
- Cerrada la generación del PDF final: ReportLab dentro del backend Python, entrada desde versión aprobada, bloques y decisiones humanas, dos modos de geometría, SHA-256 en la versión e idempotencia.

## Siguiente

- Visto bueno del equipo sobre [[0016-responsabilidades-ocr-presidio-pdf]].
- Mantener [[0014-stack-backend-c-sharp-java-python]] cerrado con Python como stack aceptado. C# solo se usa si Presidio se separa más adelante.
- Implementar el PDF final bajo la responsabilidad de @Rubén.

## Bloqueos / preguntas

- Ninguno para esta documentación.
