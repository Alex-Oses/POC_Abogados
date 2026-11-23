# 0016 · Responsabilidades entre OCR, Presidio y PDF

- **Estado**: Propuesta
- **Fecha**: 2026-11-23
- **Autor**: @ia-copilot-ruben
- **Se decide con**: @Rubén (backend y PDF), @Alex (OCR), @Yaser (recorrido del dato), @Marina (modelo), @Kevin (despliegue)

## Contexto

La documentación anterior atribuía OCR, Presidio y composición del PDF al ETL. Eso no describe el reparto real: @Alex monta y mide PaddleOCR-VL; @Rubén implementa la lógica de backend, Presidio y el PDF final; @Yaser lleva el recorrido y la orquestación del dato.

## Decisión

Quedan fijas estas responsabilidades:

| Pieza | Responsable | Forma |
|---|---|---|
| PaddleOCR-VL, OCR y layout | @Alex | Servicio local y API propia |
| Semáforo de calidad del OCR | @Alex | Métricas y resultado por página |
| Presidio y configuración de detección/sustitución | @Rubén | Servicio Python local o contenedor aislado |
| Revisión humana y persistencia de decisiones | @Rubén | Backend, transacciones y modelo de datos |
| PDF reconstruido y su hash | @Rubén | ReportLab o motor equivalente según el stack |
| Recorrido/orquestación entre piezas | @Yaser | Contratos internos y datos, sin implementar los motores |

El backend conserva la API, los permisos, las sesiones, el estado del documento, la auditoría y la idempotencia del export. El OCR no cruza estado ni escribe tablas. Presidio devuelve propuestas y anotaciones; la decisión humana y el PDF final pasan por el backend.

## Consecuencias

- La carpeta `Infrastructure/Etl` o equivalente contiene clientes HTTP; no contiene OCR ni dependencias de Presidio.
- Si el API es C#, Java o .NET, Presidio se despliega como servicio Python independiente.
- Si el API es Python, se puede compartir el lenguaje con Presidio, pero sigue existiendo una frontera de proceso si se quiere aislar el modelo.
- La comparación C#/Java/Python de [[0014-stack-backend-c-sharp-java-python]] debe valorar el contenedor Python adicional de Presidio.
