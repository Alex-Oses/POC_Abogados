# 2026-11-17 · @ia-opencode-maga369

## Hecho

- Revisados los **11 puntos** de [[0010-modelo-de-datos]] con el contrato y las reglas delante, no con la lista: 4 columnas se quitan (`documentos.expira_en`, `documentos.retencion_hasta`, `auditoria.hash_actual`, `auditoria.entidad_clave`), 6 se quedan (`documentos.cerrado_en`, `bloques_layout.pagina_ancho`, `pagina_alto`, `forma`, `puntos`, `revisiones.asignado_a`) y `revisiones.revisor_id` se renombra a `asignado_a`. `cerrado_en` y las de `bloques_layout` son casos donde 0010 se equivocaba: A-19, el contrato §10 y el contrato §4 las leen.
- Decisión [[0011-ajustes-al-modelo-de-marina]]: escrita en **Propuesta** y **aceptada el mismo día por @Marina** tras revisarla punto por punto. Contiene la tabla de los once puntos, las cinco preguntas de 0010 contestadas (geometría, seudónimos, páginas, cifrado, `citext`) y el orden de las migraciones.
- `V14__create_bloques_layout.sql`: `bloques_layout`, `paginas_documento` y `documentos.num_paginas`, con sus índices. No toca V1-V12 y **se puede aplicar hoy**: cierra B3 y B5 y desbloquea OCR, semáforo y PDF.
- `V15__flujo_revision_y_export.sql`: estados nuevos (`pendiente_visto_bueno`, `eliminado`), columnas del visto bueno y del borrado lógico, `revisiones` con cola sin dueño, plazo e `If-Match`, `anotaciones_entidad.bloque_id`, CHECK de I1, seeds H6/H8 y las claves de A-20. Renombra `revisor_id` → `asignado_a` en vez de borrarlo: no se pierde nada.
- A-04 se implementa de verdad: `revisiones.documento_id` + índice parcial único sobre `en_cola`/`en_proceso`. El único de V7 era por versión y no impedía dos revisiones abiertas del mismo documento.
- Columnas que faltaban y no estaban en la lista de 0010: `revisiones.actualizado_en` (If-Match de A-23), `categorias_sensibles.prioridad` (el contrato §7 la devuelve), `documentos.eliminado_en` (borrado lógico) y `clave_cifrado` (0004).
- `views.sql` y `triggers.sql` alineados: la vista de métricas y la de documento usan `asignado_a`; la validación de rol admite nulo; `revisiones` gana el trigger de `actualizado_en`; y el trigger de estados deja de escribir en `NEW.estado`, una columna que no existe en `versiones_documento` y que habría fallado en el primer cierre. Con A-15, un `final_aprobado` con categoría del art. 9 pasa a `pendiente_visto_bueno`.

## Cierre de 0011

@Marina revisó la decisión punto por punto y contestó lo mismo que recomendaba el documento en los ocho puntos que dependen de ella:

| Punto | Respuesta de @Marina |
|---|---|
| `documentos.expira_en` | Quitar |
| `documentos.retencion_hasta` | Quitar |
| `auditoria.hash_actual` | Quitar |
| `auditoria.entidad_clave` | Quitar y usar `detalle->>'clave'` |
| `revisiones.revisor_id` / `asignado_a` | Renombrar `revisor_id` → `asignado_a` |
| Tabla de páginas | Entra `paginas_documento` en `V14` |
| Tabla de seudónimos (I2) | No se crea; sustitución determinista por documento |
| Clave del cifrado (0004) | Id de clave en columna; el material, fuera de la BD |

Queda **fuera de lo aceptado** el dueño del hash del PDF (B8): es de @Rubén con 0007 delante, y la recomendación (que sea de la versión) sigue en 0011 sin votar.

## Siguiente

- `V16`: una columna y un índice cuando se decida B8. Recomendación en 0011: el hash es de la **versión**.
- `V13` en cuanto se cierre [[0009-identidad]]: es la única migración donde esperar sale gratis.
- Ejecutar `V1`-`V15` contra un PostgreSQL 16 limpio antes de mergear. En esta máquina Docker Desktop no arranca, así que el SQL está revisado pero **no ejecutado**.
- Mergear el PR #28 cuando @Rubén o @Alex lo revisen.

## Bloqueos / preguntas

- **B8 (hash del PDF)**: sigue abierto; @Rubén tiene la pregunta en [[Tablero]].
- **`GET /documents/{id}/pages`**: sin ese endpoint, `paginas_documento` no tiene lector. Queda como tarea en el tablero; el modelo ya lo soporta.
- La tabla de seudónimos (I2) no se crea: sin regla ni endpoint que la lea, y la sustitución determinista por documento basta. Si negocio mantiene la promesa de la maqueta, es decisión nueva.
- `0005` en Propuesta: `V15` está escrita pero no se aplica hasta que se acepte.
