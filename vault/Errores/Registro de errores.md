# Registro de errores

- **Estado:** abierto
- **Autor:** @ia-opencode-maga369
- **Creado:** 20/11/2026
- **Actualizado:** 20/11/2026, segunda pasada centrada en base de datos
- **Alcance:** los 41 ficheros versionados del repo (`README.md`, `CONTRIBUTING.md`, `AGENTS.md`, `docs/api/`, `docs/architecture/`, `docs/reglas/`, `docs/export/`, `docs/presidio.md`, `vault/`, `maqueta/`, `scripts/`) y, leídos enteros, las 14 migraciones (`V1`–`V12`, `V14`, `V15`), `views.sql`, `triggers.sql` y `partitioning.sql`.
- **Para qué:** una sola lista de defectos, con evidencia, impacto y estado, para no reabrirlos ni volver a reportar lo descartado.
- **Qué no es:** no sustituye al [[Tablero]] ni a [[Coherencia]]. Aquí van defectos comprobables; allí, decisiones y bloqueantes.

## Cómo se usa

- Un defecto = un ID `E-NN`. **No se renumera y no se borra**: se cambia el estado y, si se corrige, se anota el PR.
- Estados: **abierto** · **corregido** · **descartado** (falso positivo, con el motivo) · **bloqueado** (espera una decisión).
- Severidad: **P0** rompe la ejecución del SQL · **P1** produce datos mal o documenta un esquema que ya no existe · **P2** enlaces, cifras y diseño mejorable · **P3** discrepancia que exige decisión.
- Al encontrar uno nuevo, se añade una fila al resumen y su apartado de detalle en el mismo PR en que se detecta.

> Desde #34 (19/11) la base de datos (`V1`–`V15`) se declara **definitiva**: no se abren migraciones nuevas. Los arreglos de esquema de este registro se aplican editando las migraciones que ya existen, no con una `V16`.

## Resumen

| ID | Sev | Qué, en una línea | Dónde | Estado |
|---|---|---|---|---|
| E-01 | P0 | `sha256()` recibe `text` y solo admite `bytea`: `triggers.sql` no se puede crear | `triggers.sql:46-54` | abierto |
| E-02 | — | «El trigger de auto-estado lee `NEW.documento_id` en `revisiones`» | `triggers.sql:176` | **descartado** (V15 añade la columna) |
| E-03 | P0 | `ALTER TABLE … PARTITION BY` no es SQL válido y el README manda ejecutarlo | `partitioning.sql:16` | abierto |
| E-04 | P1 | El diccionario documenta 5 de las 11 tablas y para en V12 | `data-dictionary.md` | abierto |
| E-05 | P2 | El árbol de `docs/architecture/` sigue en una sola línea (los 16 triggers ya están) | `docs/architecture/README.md:9` | abierto |
| E-06 | — | «README raíz con V1–V12, `/user/register` y Word» | `README.md` | **corregido** (#37) |
| E-07 | P1 | [[Base de datos]] lista 9 de las 11 tablas y se presenta como «primer borrador» | `vault/Proyecto/Base de datos.md` | abierto |
| E-08 | P1 | `pendientes.md` §1 pide columnas que su propio §3 da por no creadas | `docs/pendientes.md` §1 vs §3 | abierto |
| E-09 | P2 | Dos enlaces markdown rotos | `docs/presidio.md`, bitácora del 18/11 | abierto |
| E-10 | P2 | Dos wikilinks apuntan a la decisión `0006`, que es la **0007** | bitácora del 16/11, [[Anonimizacion con Presidio]] | abierto |
| E-11 | — | «`version_esquema_bd = 1` con 15 migraciones» | `V12` | **descartado** (V15 lo pone a 15) |
| E-12 | P2 | No hay seed de `reglas_anonimizacion` y la config apunta a `RGPD_ES`, que no existe | `V12` + falta migración de reglas | abierto |
| E-13 | P2 | H3 de [[Coherencia]] cita `estado='eliminado'`, que V15 ya metió en el CHECK | `vault/Proyecto/Coherencia.md` | abierto |
| E-14 | P3 | Comentarios y `CHECK` siguen hablando de `supervisor`, que 0012 quita | `V1:7`, `V15:29,169` | bloqueado (0012) |
| E-15 | P2 | `investigacion/` en minúsculas en [[Inicio]]; en la bóveda es `Investigacion/` | `vault/Inicio.md:20` | abierto |
| E-16 | P0 | `partitioning.sql` llama a `partman` sobre `public.auditia`, que no existe | `partitioning.sql:52,58,61,67,70,73,81` | abierto |
| E-17 | P0 | `auditoria` no se puede particionar por `creado_en`: su PK es solo `id` | `V8:3-13`, `partitioning.sql:9-12` | abierto |
| E-18 | P1 | La cola ordena por `nivel_riesgo DESC`, y como es texto pone «alto» el último | `views.sql:102` | abierto |
| E-19 | P1 | Tres `JOIN` internos esconden documentos en las vistas | `views.sql:42,43-49,197-204` | abierto |
| E-20 | P1 | `entidades_confirmadas` no conoce las acciones nuevas de V15 | `views.sql:53` | abierto |
| E-21 | P1 | V15 dice que los offsets van por bloque; el contrato cerrado y las vistas, por texto completo | `V15:103-109`, `views.sql:94` | abierto |
| E-22 | P2 | `MAX(numero_version) + 1` sin bloqueo: dos versiones simultáneas chocan con el único | `V4:6,20`, `triggers.sql:92-107` | abierto |
| E-23 | P1 | La cadena de hashes se bifurca con dos inserciones simultáneas | `triggers.sql:55-87` | abierto |
| E-24 | P1 | La auditoría atribuye el cambio de estado a quien subió el documento | `triggers.sql:225-228` | abierto |
| E-25 | P1 | `anotaciones_entidad.bloque_id` puede apuntar a un bloque de otra versión | `V15:105-106` | abierto |
| E-26 | P2 | `reglas_anonimizacion.codigo UNIQUE` deja la columna `version` sin sentido | `V5:5-6` | abierto |
| E-27 | P2 | `usuarios.email UNIQUE` distingue mayúsculas: `Ana@` y `ana@` son dos cuentas | `V1:5` | abierto |
| E-28 | P2 | `V15` da por existente un único `(version_id, numero_intento)` que `V7` no creó | `V15:87-88`, `V7` | abierto |
| E-29 | P2 | `views.sql` dice ejecutarse tras V10, pero necesita columnas de V15 | `views.sql:3` | abierto |
| E-30 | P2 | `horas_media_estado` mide antigüedad, no tiempo en el estado | `views.sql:150,156-165` | abierto |

---

## P0 · SQL que no se puede aplicar

> Los cuatro son lectura del SQL, no ejecución: en este equipo no hay PostgreSQL y Docker no arranca. La deducción de E-01 está contrastada con la documentación de PostgreSQL; E-03, E-16 y E-17 se ven en el propio fichero.

### E-01 · `audit_compute_hash` no se puede crear

- **Evidencia.** `docs/architecture/triggers.sql:46-54`:
  ```sql
  SELECT encode(
      sha256((row_data || jsonb_build_object('prev_hash', prev_hash))::text),
      'hex'
  )::CHAR(64);
  ```
- **Qué pasa.** En PostgreSQL `sha256()` solo acepta `bytea`; con `text` devuelve `function sha256(text) does not exist`. Como la función es `LANGUAGE sql`, el error salta al crearla, no al usarla.
- **Impacto.** `triggers.sql` aborta en la segunda función: no se crean el hash encadenado ni los 13 triggers que vienen después.
- **Arreglo.** Envolver en `convert_to(... , 'UTF8')` antes del `sha256`.
- **Estado.** abierto. Ya corregido en la copia de trabajo `Documents/Advocats/docs/architecture-postgresSQL/triggers.sql`, fuera de este repo.

### E-03 · `partitioning.sql` no es SQL válido

- **Evidencia.** `docs/architecture/partitioning.sql:16-17` hace `ALTER TABLE auditoria PARTITION BY RANGE (creado_en);`, y `V8__create_auditoria.sql` crea la tabla sin `PARTITION BY`.
- **Qué pasa.** PostgreSQL no convierte una tabla normal en particionada con `ALTER TABLE … PARTITION BY`: hay que recrearla. El fichero tiene el procedimiento correcto comentado en las líneas 10-12, pero lo que se ejecuta es el `ALTER`.
- **Impacto.** El paso 3 del README de arquitectura falla siempre.
- **Arreglo.** Dejar el `ALTER` comentado y ejecutar el camino de recreación, o marcar el fichero como «solo con `pg_partman` y tabla vacía».
- **Estado.** abierto.

### E-16 · El nombre de la tabla está mal escrito en siete llamadas a `pg_partman`

- **Evidencia.** `partitioning.sql` crea el padre como `'public.auditoria'` (línea 31) y luego llama a `partman` sobre **`'public.auditia'`**: líneas 52, 58, 61, 67, 70, 73 y 81 (ocho apariciones, siete líneas). La línea 52 es la única que se ejecuta; el resto están comentadas, pero son las que el equipo copiará para operar.
- **Impacto.** Aunque se arregle E-03, `run_maintenance` falla con «no existe la tabla padre»; y las consultas de verificación de particiones y retención tampoco devuelven nada.
- **Arreglo.** `auditia` → `auditoria` en las ocho apariciones.
- **Estado.** abierto.

### E-17 · `auditoria` no se puede particionar con esa clave primaria

- **Evidencia.** `V8__create_auditoria.sql`: `id BIGSERIAL PRIMARY KEY`, y el particionado es `PARTITION BY RANGE (creado_en)`. El camino de recreación que sugiere `partitioning.sql:10` (`CREATE TABLE auditoria_partitioned (LIKE auditoria INCLUDING ALL) PARTITION BY RANGE (creado_en)`) copia también esa PK.
- **Qué pasa.** En una tabla particionada, toda `PRIMARY KEY` o `UNIQUE` tiene que incluir la columna de particionado; si no, PostgreSQL rechaza el `CREATE`: *unique constraint on partitioned table must include all partitioning columns*. Pasa con el `ALTER` (E-03) y con el `LIKE … INCLUDING ALL`.
- **Impacto.** El particionado no es aplicable sin cambiar la PK a `(id, creado_en)`. Y de paso, la cadena de hashes (E-23) ordena por `id`, que deja de ser único por sí solo.
- **Arreglo.** PK `(id, creado_en)` en la tabla particionada y, en las consultas del hash, ordenar por `(creado_en, id)`. Hay que decidir si la numeración de `id` sigue siendo la secuencia global (lo es, `BIGSERIAL` sobre la tabla padre).
- **Estado.** abierto.

---

## P1 · Documentación que describe otro esquema

### E-04 · Diccionario de datos parado en V12

- **Evidencia.** `data-dictionary.md` tiene 5 tablas: `usuarios`, `categorias_sensibles`, `documentos`, `versiones_documento` y `reglas_anonimizacion`. Existen **11**: faltan `anotaciones_entidad`, `revisiones`, `auditoria`, `configuracion_sistema`, `paginas_documento` y `bloques_layout`. Describe además `usuarios.rol` con `supervisor`, que 0012 quita.
- **Impacto.** Es el documento que se lee para escribir backend. Quien lo siga crea un modelo con 5 tablas y sin flujo de revisión.
- **Arreglo.** Reescribirlo contra V1–V15. El diccionario de `Documents/Advocats/docs/architecture-postgresSQL/data-dictionary.md` ya está en ese punto y sirve de base, corrigiendo nombres (`hash_sha256`, no `hash_actual`).
- **Estado.** abierto.

### E-05 · El árbol de `docs/architecture/` sigue en una sola línea

- **Evidencia.** `docs/architecture/README.md:9` mete todo el árbol de ficheros en una línea, sin saltos: no se lee en GitHub. El recuento de triggers ya está bien (16) desde #34, que también cambió la nota de V13.
- **Impacto.** Cosmético, pero es la puerta de entrada a la carpeta del modelo.
- **Arreglo.** Devolver el árbol a varias líneas.
- **Estado.** abierto (la cifra se corrigió el 19/11; solo queda el formato).

### E-06 · El README raíz prometía cosas que el contrato no tiene — corregido

- **Evidencia (19/11, antes de #37).** «migraciones Flyway V1-V12»; `/user/register`, que no estaba en el contrato; y exportación a **Word**, que no existía en `docs/export/`.
- **Estado.** corregido en #37: V1–V15, 40 rutas reales, sin Word y con `docs/api/`, `docs/reglas/` y `docs/export/` en el árbol.

### E-07 · [[Base de datos]] desactualizado

- **Evidencia.** Resume 9 tablas y se titula «primer borrador»; faltan `paginas_documento` y `bloques_layout`, y sigue diciendo que los roles están en `usuarios`.
- **Impacto.** Quien entra por [[Inicio]] → [[Base de datos]] ve un modelo anterior al de [[Modelo de datos]].
- **Arreglo.** Añadir las dos tablas, apuntar a [[Modelo de datos]] como fuente y quitar «primer borrador».
- **Estado.** abierto.

### E-08 · `pendientes.md` §1 y §3 se contradicen entre sí

- **Evidencia.** §1 dice que `usuarios` recibirá `estado`, `password_hash`, `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso`, `motivo_baja` y `sso_subject`; §3, en el mismo fichero, dice que `usuarios` se queda «sin `roles[]`, `estado`, `sso_subject` ni `password_hash`: el login tiene que caber en `rol`/`activo` o quedar fuera del piloto».
- **Impacto.** La lista de trabajo del backend se contradice a dos secciones de distancia. Desde #34 ya no pide `password_cambiado_en`, así que el conflicto con 0012 se ha estrechado, pero no ha desaparecido.
- **Arreglo.** Dejar una sola versión: o §1 se marca como «si se reabre la BD» o se retira y §3 queda como la única realidad.
- **Estado.** abierto.

---

## P1 · Vistas y triggers que devuelven datos mal

### E-18 · La cola de revisión ordena al revés

- **Evidencia.** `views.sql:101-104`:
  ```sql
  ORDER BY
      cs.nivel_riesgo DESC,          -- Alto riesgo primero
  ```
  `nivel_riesgo` es `VARCHAR(20)` con `'alto'`, `'medio'` y `'bajo'`. En orden alfabético `alto` < `bajo` < `medio`, así que `DESC` devuelve primero `medio`, luego `bajo` y deja `alto` al final.
- **Impacto.** El revisor empieza por lo menos crítico, y la vista se llama «cola priorizada». Es el defecto con más efecto diario de esta lista.
- **Arreglo.** `ORDER BY CASE cs.nivel_riesgo WHEN 'alto' THEN 1 WHEN 'medio' THEN 2 ELSE 3 END, …`, o directamente `cs.prioridad` (existe desde V15).
- **Estado.** abierto.

### E-19 · Tres `JOIN` internos esconden documentos

- **Evidencia e impacto.**
  - `views.sql:42`: `JOIN usuarios u ON u.id = d.creado_por`, pero `documentos.creado_por` es **nullable** (`ON DELETE SET NULL` en V3). Un documento sin autor, o cuyo autor se dio de baja con borrado, desaparece del listado.
  - `views.sql:43-49`: `JOIN LATERAL` (interno) a la última versión. Un documento recién subido, antes de que exista la versión original, no aparece.
  - `views.sql:197-204`: `JOIN LATERAL` (interno) a la versión `ocr_texto` en `v_entidad_detalle_diff`. Un PDF con capa de texto y sin OCR no aparece en el diff.
- **Arreglo.** `LEFT JOIN` en los tres casos, y `COALESCE`/`NULL` donde el contrato espere el dato.
- **Estado.** abierto.

### E-20 · El contador de entidades confirmadas se queda corto

- **Evidencia.** `views.sql:53` cuenta como confirmadas solo `'tachado'`, `'pseudonimizado'`, `'eliminado'` y `'mantenido'`. V15 cambia el `CHECK` de `accion_aplicada` a `censurar`, `etiqueta`, `iniciales`, `pseudonimizado`, `eliminado`, `mantenido`, `tachado` y `pendiente_revision`.
- **Impacto.** Toda entidad marcada con las tres acciones nuevas (`censurar` es la acción por defecto desde V15) cuenta como no confirmada en `v_documento_actual`: el panel dirá que hay trabajo pendiente cuando no lo hay.
- **Arreglo.** `accion_aplicada <> 'pendiente_revision'` en vez de enumerar, que además no vuelve a romperse si el `CHECK` cambia.
- **Estado.** abierto.

### E-21 · V15 y el contrato no coinciden en dónde cuentan los offsets

- **Evidencia.** `V15:103-109` añade `bloque_id` y documenta que `inicio_offset` y `fin_offset` son índices «dentro de `bloques_layout.contenido`, no del texto completo». El contrato cerrado el 19/11 dice lo contrario: «los offsets son índices de carácter dentro de `versiones_documento.contenido_texto`: la anotación no apunta a un bloque de layout» (`docs/api/endpoints.md`, B3). Y `views.sql:94` corta el snippet de `vd.contenido_texto`, o sea que implementa la versión del contrato.
- **Impacto.** Dos bases de offsets en el mismo repo. Si alguien implementa según V15, los offsets apuntan a otro sitio y el snippet del revisor sale mal. Además, `bloque_id` queda como columna sin uso.
- **Arreglo.** Como la BD se declara definitiva, lo barato es alinear V15 con el contrato: corregir los dos `COMMENT ON COLUMN` y decidir si `bloque_id` se queda (documentado como «sin uso») o se retira antes de desplegar.
- **Estado.** abierto.

### E-24 · La auditoría atribuye los cambios de estado a quien subió el documento

- **Evidencia.** `triggers.sql:225-228`:
  ```sql
  ELSIF TG_TABLE_NAME = 'documentos' AND TG_OP = 'UPDATE' AND OLD.estado <> NEW.estado THEN
      ev := 'DOCUMENTO_ESTADO_CAMBIO'; …
      usr := NEW.creado_por;
  ```
  `documentos` no tiene columna de «quién hizo el último cambio»; el único UUID disponible es `creado_por`.
- **Impacto.** En un registro que se presenta como trazabilidad legal (RGPD), el cambio de estado de un revisor aparece firmado por quien subió el PDF.
- **Arreglo.** O se añade `actualizado_por` a `documentos` y se rellena desde la aplicación, o el trigger saca el usuario de la revisión (`revisiones.asignado_a` de la versión afectada) cuando exista. Es una decisión de modelo, no un cambio de una línea: va con 0012.
- **Estado.** abierto.

### E-25 · Una anotación puede apuntar a un bloque de otra versión

- **Evidencia.** `V15:105-106` añade `anotaciones_entidad.bloque_id UUID REFERENCES bloques_layout(id)`, FK simple. La anotación ya tiene `version_id`, y nada obliga a que el bloque sea de esa versión.
- **Impacto.** Un `bloque_id` cruzado deja offsets que no corresponden al texto de la anotación. La base lo acepta.
- **Arreglo.** El mismo patrón que V15 usa para `revisiones`: `UNIQUE (id, version_id)` en `bloques_layout` y FK compuesta `(bloque_id, version_id)`.
- **Estado.** abierto.

---

## Concurrencia

### E-22 · El número de versión se calcula con una carrera

- **Evidencia.** `V4:6` declara `numero_version INT NOT NULL` (sin `DEFAULT`), con `uq_version_documento UNIQUE (documento_id, numero_version)` en la línea 20. `triggers.sql:92-107` lo calcula en un `BEFORE INSERT` con `SELECT COALESCE(MAX(numero_version), 0) + 1 … WHERE documento_id = NEW.documento_id`.
- **Qué pasa.** El trigger sí entra (sin `DEFAULT`, la columna llega `NULL` y se rellena antes del `NOT NULL`), pero `MAX + 1` no bloquea nada: dos transacciones que inserten una versión del mismo documento a la vez leen el mismo `MAX` y una choca contra el único con *duplicate key value violates unique constraint*.
- **Impacto.** No corrompe datos: falla una petición. Con dos OCR en paralelo del mismo documento, el segundo se cae y el cliente recibe un 500 sin explicación. En la POC es improbable; en producción, con reprocesos, no.
- **Arreglo.** `pg_advisory_xact_lock(hashtextextended(NEW.documento_id::text, 0))` antes del `MAX`, o una secuencia por documento. Es una línea y no cambia el modelo.
- **Estado.** abierto. (Corregido el 20/11: había escrito que el `DEFAULT 1` anulaba el trigger; la columna no tiene `DEFAULT` y el trigger funciona.)

### E-23 · La cadena de hashes se bifurca

- **Evidencia.** `triggers.sql:55-87`: en un `BEFORE INSERT` sobre `auditoria`, lee `hash_anterior` de la fila más reciente (`ORDER BY id DESC LIMIT 1`) y escribe `H(fila + hash_anterior)`. No hay `SERIALIZABLE`, ni bloqueo, ni secuencia de cadena.
- **Qué pasa.** Dos transacciones concurrentes leen la misma última fila y las dos escriben el mismo `hash_anterior`: la cadena deja de ser una cadena. Si además la tabla está particionada (E-17), la lectura recorre todas las particiones.
- **Impacto.** En un registro que se vende como inmutable, dos altas a la vez rompen la verificación de integridad. Con `pg_dump`/restauración parcial se rompe igual.
- **Arreglo.** `pg_advisory_xact_lock` por tabla en el trigger, o una tabla `auditoria_cadena` de una sola fila con `UPDATE … RETURNING` que serialice. Decidir también qué se hace con el `renumber` al particionar.
- **Estado.** abierto.

---

## P2 · Enlaces, cifras y diseño

### E-09 · Dos enlaces markdown rotos

- `docs/presidio.md` → `../vault/Decisiones/0006-generacion-pdf-final.md`. La nota es la **0007**.
- `vault/Bitacora/2026-11-18-ia-opencode-maga369.md` → `../docs/reglas/reglas-de-negocio.md`; falta un `../` (desde `vault/Bitacora/` son `../../docs/`).
- **Estado.** abierto.

### E-10 · Dos wikilinks a la decisión equivocada

- `vault/Bitacora/2026-11-16-ia-claude-alex.md` y [[Anonimizacion con Presidio]] usan `0006-generacion-pdf-final`; la decisión del PDF final es la **0007**.
- **Estado.** abierto.

### E-12 · No hay regla de anonimización sembrada

- `V12` deja `regla_default_codigo = "RGPD_ES"`, y ninguna migración inserta en `reglas_anonimizacion`. Con la base recién creada, la regla por defecto no existe.
- **Impacto.** No rompe el SQL; deja el pipeline sin regla.
- **Arreglo.** Migración de seed con `RGPD_ES` y su `configuracion`.
- **Estado.** abierto.

### E-13 · H3 de [[Coherencia]] cita un problema que V15 ya resolvió

- **Evidencia.** H3 dice que el documento de RGPD usa `estado = 'eliminado'`, «que no está en el CHECK de `documentos`». Desde V15:13-17, `'eliminado'` **sí** está en el CHECK. H4 ya está marcado como resuelto en [[Coherencia]] desde #34.
- **Impacto.** Queda un bloqueante fantasma en la lista; los otros dos puntos de H3 (borrado en cascada de anotaciones y `usuarios.activo`) siguen vivos y se mezclan con este.
- **Arreglo.** Quitar el primer punto de H3 y dejar los otros dos separados.
- **Estado.** abierto.

### E-15 · `investigacion/` con dos significados

- [[Inicio]]:20 escribe `` `investigacion/` `` para las notas de la bóveda, pero la carpeta de notas es `vault/Investigacion/` y existe además `investigacion/` en la raíz, que guarda los `bench.py`. Mismo nombre, dos cosas.
- **Estado.** abierto.

### E-26 · La columna `version` de las reglas no sirve para nada

- **Evidencia.** `V5:5-6`: `codigo VARCHAR(50) NOT NULL UNIQUE` y `version INT NOT NULL DEFAULT 1`. Con `codigo` único no puede haber dos filas de la misma regla, así que nunca habrá una versión 2 de `RGPD_ES`.
- **Impacto.** Se pierde el histórico de reglas, que es justo lo que se quiere para auditoría: al cambiar una regla se sobreescribe. Además `creado_por` y `version` dan a entender lo contrario.
- **Arreglo.** `UNIQUE (codigo, version)` más un único parcial `WHERE activa` para que solo haya una activa por código. Es lo que hace la copia de `Documents/Advocats`.
- **Estado.** abierto.

### E-27 · El email distingue mayúsculas

- **Evidencia.** `V1:5`: `email VARCHAR(255) NOT NULL UNIQUE`. `Marina@icat.cat` y `marina@icat.cat` son dos cuentas distintas.
- **Impacto.** Duplicados de cuenta y, con SSO, un usuario que entra con otra caja y no ve sus documentos.
- **Arreglo.** `UNIQUE (lower(email))` o `CITEXT`. Encaja con V13, que toca la identidad: mejor cerrarlo allí que en un parche suelto.
- **Estado.** abierto.

### E-28 · `V15` cita un único de `V7` que no existe

- **Evidencia.** `V15:87-88` dice: «El único de V7 era `(version_id, numero_intento)` y no lo implementaba». En `V7__create_revisiones.sql` no hay ningún `UNIQUE` ni `CONSTRAINT`: solo la PK y las FK.
- **Impacto.** Nada impide repetir `numero_intento` en la misma versión. Y el comentario hace creer que existe una red que no está.
- **Arreglo.** Añadir `UNIQUE (version_id, numero_intento)` (en V13 o en `V16`) y corregir el comentario.
- **Estado.** abierto.

### E-29 · El orden de ejecución que dice `views.sql` es falso

- **Evidencia.** `views.sql:3` dice «Ejecutar DESPUÉS de V10__create_indexes.sql», pero la vista usa `r.asignado_a`, que nace en V15, y `documentos.requiere_visto_bueno` también es de V15.
- **Impacto.** Quien siga esa línea ejecuta `views.sql` antes de V15 y recibe *column r.asignado_a does not exist*.
- **Arreglo.** «Después de todas las migraciones (V15 incluida)». El README de arquitectura ya lo hace en el orden correcto: solo falla el comentario del propio fichero.
- **Estado.** abierto.

### E-30 · `horas_media_estado` no mide lo que dice

- **Evidencia.** `views.sql:150`: `AVG(EXTRACT(EPOCH FROM (actualizado_en - creado_en))/3600)`. No hay histórico de estados en el esquema, así que lo que calcula es la antigüedad del documento, agrupada por el estado en que está ahora.
- **Impacto.** El panel se presenta como «cuellos de botella por estado» y no puede detectarlos: un documento que lleva 20 días en `pendiente` y otro que acaba de llegar promedian lo mismo que si el estado no influyera. Además el `CASE` de ordenación (156-165) no conoce `pendiente_visto_bueno` ni `eliminado`, que caen en el `ELSE 9`.
- **Arreglo.** O se renombra la columna a `horas_media_desde_alta`, o se añade `documentos_estado_historial` (tabla + trigger) y se calcula de verdad. Lo segundo es lo que pide un panel de cuellos de botella.
- **Estado.** abierto.

---

## P3 · Discrepancias que exigen decisión

### E-14 · `supervisor`, que 0012 quita

- `V1:7` admite `'supervisor'` en el `CHECK` de `rol`; `V15:29` describe `visto_bueno_por` como «supervisor que firmó» y `V15:169` manda el aviso al supervisor. 0012 deja **tres roles, sin supervisor**.
- **No es un error a corregir por mi cuenta**: el `CHECK` lo cambia `V13`, que espera a 0009 y 0012.
- **Estado.** bloqueado (0012).

---

## Descartados

Falsos positivos comprobados. Se dejan aquí para no volver a reportarlos.

- **E-02 · «El trigger de auto-estado lee `NEW.documento_id` en `revisiones`, que no tiene esa columna».** Es cierto con solo `V7`, pero `V15:58-72` añade `revisiones.documento_id` y la deja `NOT NULL`. Como el despliegue aplica todas las migraciones antes de `triggers.sql`, el trigger funciona. Descartado el 20/11.
- **E-11 · «`version_esquema_bd = 1` con 15 migraciones».** `V15:159-161` lo actualiza a `15`. Descartado el 20/11.
- **«`docs/architecture/README.md` está truncado».** No lo está: termina en el comando `psql` del paso 3, que es un final válido. El problema real es E-05.
- **«`trg_audit_categorias` usa `NEW.creado_por` y `categorias_sensibles` no tiene esa columna».** Cierto en la copia de `Documents/Advocats/docs/architecture-postgresSQL/`, **no en este repo**: aquí no existe trigger de auditoría sobre `categorias_sensibles`, y los tres `NEW.creado_por` que hay apuntan a columnas que sí existen.
- **«`V14__create_bloques_layout.sql` tiene bytes corruptos».** Es UTF-8 válido; lo que se veía roto era la consola de PowerShell.
- **Avisos de wikilink en `vault/Plantillas/Decision.md` y en [[Modelo de datos]] (`x,y` de Mermaid).** Son plantilla y sintaxis de Mermaid, no enlaces.

## Lo que no cubre

- **Nada está ejecutado en un motor.** Sin PostgreSQL local y con Docker caído, E-01, E-03, E-16 y E-17 son lectura, no prueba. En cuanto haya motor, se aplican las migraciones y este registro se actualiza con el resultado.
- **No se ha auditado el rendimiento con datos.** Las observaciones de E-22, E-23 y E-30 son de diseño; no hay medidas.
- **El contrato cita dos tablas que aún no existen** (`sesiones_usuario` y `regla_categorias`): no es un error, están en V13 y V16, pendientes de 0009/0012 y de B8.
- **La maqueta no se ha probado en navegador** y de `docs/api/endpoints.md` solo se ha contrastado el modelo de tablas, no ruta por ruta.
