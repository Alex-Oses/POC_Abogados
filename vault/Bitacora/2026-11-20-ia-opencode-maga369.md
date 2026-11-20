# 2026-11-20 · @ia-opencode-maga369

## Hecho

- **[[Registro de errores]]** nuevo en `vault/Errores/`: 15 defectos del repo con evidencia (fichero y línea), impacto, arreglo propuesto y estado, más los 4 falsos positivos descartados y lo que el registro no cubre. La tabla de resumen va arriba para poder escanearlo sin leerlo entero. Convención: ID `E-NN` que no se renumera y no se borra, solo cambia de estado.
- **Tres defectos P0 en el SQL.** `triggers.sql:49` pasa `text` a `sha256()`, que solo acepta `bytea`: la función no se crea y el fichero aborta. `triggers.sql:176` lee `NEW.documento_id` en `revisiones`, que tiene `version_id`: el trigger se crea pero falla en cada alta o cambio de revisión. `partitioning.sql:16` usa `ALTER TABLE … PARTITION BY`, que no es SQL válido, y el README lo manda ejecutar.
- **Documentación desfasada localizada**: `data-dictionary.md` documenta 5 de las 11 tablas y para en V12; el README de arquitectura dice «7 triggers» cuando hay 16; el README raíz sigue en «V1–V12», lista `/user/register` (que no está en el contrato) y promete Word; [[Base de datos]] lista 9 tablas; `pendientes.md` §1 contradice a [[0012-identidad-y-roles]].
- **Cuatro enlaces rotos** (dos markdown y dos wikilinks a `0006-generacion-pdf-final`, que es la 0007).
- **Corregidas dos afirmaciones mías del 19/11**: el README de arquitectura **no** está truncado, y el fallo de `NEW.creado_por` no existe en este repo (era de la copia de `Documents/Advocats`). Ambas quedan en el apartado «Descartados» para que nadie las vuelva a reportar.
- [[Inicio]] enlaza el registro y aclara que `vault/Investigacion/` (notas) y `investigacion/` (scripts) son cosas distintas. [[Tablero]] tiene la tarea de priorizar los 15 defectos.

## Siguiente

- Arreglar E-01 a E-03 en un PR aparte, cuando @Marina diga si entra también el diccionario y los README (P1) o solo el SQL.
- Reescribir `docs/architecture/data-dictionary.md` contra V1–V15: 11 tablas y las columnas de V14/V15.
- Cerrar E-13 en [[Coherencia]]: H3 y H4 ya no son bloqueantes.

## Bloqueos / preguntas

- **Nada ejecutado.** Sin PostgreSQL local y con Docker caído, E-01 a E-03 son lectura del SQL, no prueba en motor. En cuanto haya motor, se aplican migraciones, vistas y triggers, y el registro se actualiza con el resultado.
- **E-14 espera a 0012**: `supervisor` sigue en el `CHECK` de `usuarios.rol` (V1) y en un comentario de `V15`. No lo toco porque el `CHECK` lo cambia `V13` y 0012 sigue en Propuesta.
- **E-08 no se puede cerrar sin 0012**: `pendientes.md` §1 pide cuatro columnas de sesión que 0012 deja fuera.
