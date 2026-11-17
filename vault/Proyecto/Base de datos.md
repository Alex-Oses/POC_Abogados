# Base de datos (primer borrador)

Detalle completo en [docs/architecture](../../docs/architecture/README.md): diccionario de datos, consideraciones RGPD, migraciones Flyway, vistas, triggers y particionado. Diagrama: `docs/architecture/diagrama-bbdd-borrador.png`.

## Resumen

PostgreSQL 14+ con `uuid-ossp`, `pgcrypto` y `pg_partman`.

| Tabla | Para qué |
|---|---|
| `usuarios` | Cuentas y roles (`transcriptor`, `revisor`…) |
| `categorias_sensibles` | Catálogo de categorías a anonimizar (seed V11) |
| `documentos` | Documento subido, hash SHA-256, estado, ruta a almacenamiento cifrado |
| `versiones_documento` | Versiones del texto hasta `final_aprobado` |
| `reglas_anonimizacion` | Reglas por tipo de documento |
| `anotaciones_entidad` | Cada dato detectado: motor, confianza y decisión humana |
| `revisiones` | Revisión humana con número de intento |
| `auditoria` | Registro con hash encadenado, particionado por mes |
| `configuracion_sistema` | Retención (documentos 60 meses, auditoría 120) y otros parámetros |

## Pendiente

- El modelo objetivo de @Marina, con su diagrama y la comparación con la decisión 0010: [[Modelo de datos]].
- `er-diagram.md` citado en el README de arquitectura pero no incluido; el diagrama de esa nota puede ser su punto de partida.
