# 2026-11-20 · @ia-opencode-maga369

## Hecho

- **[[Registro de errores]]** nuevo en `vault/Errores/`: defectos del repo con evidencia (fichero y línea), impacto, arreglo propuesto y estado, más los falsos positivos descartados y lo que el registro no cubre. Convención: ID `E-NN` que no se renumera y no se borra, solo cambia de estado.
- **Primera pasada, todo el repo.** Tres P0 en el SQL: `triggers.sql:49` pasa `text` a `sha256()`, que solo acepta `bytea`; `partitioning.sql:16` usa `ALTER TABLE … PARTITION BY`, que no es SQL válido; y el README lo manda ejecutar. Documentación desfasada: `data-dictionary.md` (5 de 11 tablas), «7 triggers» donde hay 16, README raíz en «V1–V12» con `/user/register` y Word, [[Base de datos]] con 9 tablas, `pendientes.md` §1 contra 0012. Cuatro enlaces rotos.
- **Segunda pasada, solo base de datos** (mismo día). Leídas enteras las 14 migraciones, `views.sql`, `triggers.sql` y `partitioning.sql`: **15 hallazgos nuevos, E-16 a E-30**.
  - **Dos P0 más.** `partitioning.sql` llama a `pg_partman` sobre `public.auditia` (ocho apariciones: el nombre bueno es `auditoria`), así que `run_maintenance` y las consultas de verificación fallan. Y `auditoria` no se puede particionar por `creado_en` con `id` como única PK: PostgreSQL exige que la clave incluya la columna de particionado, y pasa igual con el camino de recreación que sugiere el propio fichero.
  - **Lo que más se nota a diario.** La cola del revisor ordena por `nivel_riesgo DESC` y el campo es texto: `alto` < `bajo` < `medio`, así que «alto» queda el último. `entidades_confirmadas` no conoce `censurar`, `etiqueta` ni `iniciales`, que son las acciones de V15. Y el snippet de contexto sigue cortando del texto completo aunque los offsets ya cuentan dentro del bloque.
  - **Dos carreras.** `numero_version` se calcula con `MAX+1` sin bloqueo: dos versiones simultáneas del mismo documento chocan contra el único. Y la cadena de hashes de `auditoria` se bifurca con dos altas simultáneas, porque lee la última fila sin bloqueo. De paso, retiro una afirmación mía: había escrito que un `DEFAULT 1` anulaba el trigger de versión; la columna no tiene `DEFAULT` y el trigger sí funciona.
  - **Integridad y trazabilidad.** `anotaciones_entidad.bloque_id` puede apuntar a un bloque de otra versión (FK simple donde V15 ya usa compuesta para `revisiones`). La auditoría firma los cambios de estado con `creado_por`, o sea con quien subió el PDF.
- **Dos correcciones al PR #36.** E-02 y E-11 se descartan: V15 añade `revisiones.documento_id` y pone `version_esquema_bd` a 15. Quedan en «Descartados» con el motivo, sin borrar el ID.
- **Rebasado sobre `main`.** Mientras trabajaba se mergearon #34, #35 y #37. Tres entradas cambian: E-06 (README raíz) queda **corregido** en #37; E-05 se reduce al árbol en una línea, porque la cifra de 16 triggers ya está; E-08 pasa a ser una contradicción interna de `pendientes.md` (§1 frente a §3); E-13 se reduce a H3; y E-21 se reformula: el problema no es que la vista corte mal, es que V15 dice offsets por bloque y el contrato cerrado el 19/11 dice texto completo.
- [[Inicio]] enlaza el registro y aclara que `vault/Investigacion/` (notas) y `investigacion/` (scripts) son cosas distintas. [[Tablero]] tiene la tarea de priorizar los 28 defectos.

## Siguiente

- **Arreglar E-18, E-19 y E-20** en `views.sql`: son tres cambios pequeños que dejan de dar datos falsos. Van en un PR propio, sin tocar el esquema.
- E-01 y E-16 son una línea cada uno (`convert_to` y `auditia` → `auditoria`); E-03 y E-17 exigen rehacer `partitioning.sql` y decidir la PK `(id, creado_en)`.
- Reescribir `data-dictionary.md` contra V1–V15: 11 tablas y las columnas de V14/V15.
- Cerrar E-13 en [[Coherencia]]: H3 y H4 ya no son bloqueantes.

## Bloqueos / preguntas

- **Nada ejecutado.** Sin PostgreSQL local y con Docker caído, los cuatro P0 son lectura del SQL, no prueba en motor. En cuanto haya motor, se aplican migraciones, vistas y triggers, y el registro se actualiza con el resultado.
- **E-14 y E-27 esperan a 0012/V13**: `supervisor` sigue en el `CHECK` de `usuarios.rol` (V1) y en dos comentarios de V15, y el email distingue mayúsculas.
- **E-08, E-24 y E-25 necesitan decisión de modelo**, no un parche: `pendientes.md` §1 depende de 0012; la auditoría de estados necesita «quién cambió» en `documentos`; y el bloque de una anotación debería atarse a su versión con FK compuesta.
