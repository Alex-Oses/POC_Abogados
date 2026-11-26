# Registro de errores

- **Estado:** abierto
- **Autor:** @ia-opencode-maga369
- **Creado:** 20/11/2026
- **Actualizado:** 20/11/2026, tercera pasada: contrato contra `V1`-`V15`, export, RGPD y maqueta. Arreglados E-31, E-32, E-35, E-37, E-40, E-41, E-45, E-46, E-48, E-49 y E-50
- **Actualizado (25/11/2026):** cerrados E-21, E-25 y E-52; offsets por bloque y correcciones del diseño del PDF final.
- **Actualizado (26/11/2026):** documentación de esquema alineada con el modelo v0.3; corregidos E-04, E-05, E-07, E-08 y E-13, parcial E-44, y abierto E-53 con las contradicciones del documento v0.3.
- **Actualizado (26/11/2026, segunda pasada):** cerrados los cuatro defectos P0 del SQL (E-01, E-03, E-16 y E-17); E-17 queda ligado a la decisión propuesta [[0017-particionado-auditoria]].
- **Actualizado (26/11/2026, tercera pasada):** documentado el port a MariaDB como segunda opción (`docs/architecture/mariadb/`, [[0018-mariadb-segunda-opcion]]). No abre defectos nuevos: E-23, E-51 y E-53 se heredan y se documentan como límites del port, sin ejecutar por falta de motor.
- **Alcance:** los ficheros versionados del repo (`README.md`, `CONTRIBUTING.md`, `AGENTS.md`, `docs/api/`, `docs/architecture/`, `docs/architecture/mariadb/`, `docs/reglas/`, `docs/export/`, `docs/presidio.md`, `vault/`, `maqueta/`, `scripts/`) y, leídos enteros, las 14 migraciones (`V1`–`V12`, `V14`, `V15`), `views.sql`, `triggers.sql` y `partitioning.sql`, además de sus 14 equivalentes MariaDB.
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
| E-01 | P0 | `sha256()` recibe `text` y solo admite `bytea`: `triggers.sql` no se puede crear | `triggers.sql:46-54` | **corregido** (26/11: `convert_to(..., 'UTF8')`) |
| E-02 | — | «El trigger de auto-estado lee `NEW.documento_id` en `revisiones`» | `triggers.sql:176` | **descartado** (V15 añade la columna) |
| E-03 | P0 | `ALTER TABLE … PARTITION BY` no es SQL válido y el README manda ejecutarlo | `partitioning.sql:16` | **corregido** (26/11: recreación idempotente en `partitioning.sql`) |
| E-04 | P1 | El diccionario documenta 5 de las 11 tablas y para en V12 | `data-dictionary.md` | **corregido** (26/11: 14 tablas + 19 relaciones) |
| E-05 | P2 | El árbol de `docs/architecture/` sigue en una sola línea (los 16 triggers ya están) | `docs/architecture/README.md:9` | **corregido** (26/11) |
| E-06 | — | «README raíz con V1–V12, `/user/register` y Word» | `README.md` | **corregido** (#37) |
| E-07 | P1 | [[Base de datos]] lista 9 de las 11 tablas y se presenta como «primer borrador» | `vault/Proyecto/Base de datos.md` | **corregido** (26/11: 14 tablas del modelo v0.3) |
| E-08 | P1 | `pendientes.md` §1 pide columnas que su propio §3 da por no creadas | `docs/pendientes.md` §1 vs §3 | **corregido** (26/11) |
| E-09 | P2 | Dos enlaces markdown rotos | `docs/presidio.md`, bitácora del 18/11 | abierto |
| E-10 | P2 | Dos wikilinks apuntan a la decisión `0006`, que es la **0007** | bitácora del 16/11, [[Anonimizacion con Presidio]] | abierto |
| E-11 | — | «`version_esquema_bd = 1` con 15 migraciones» | `V12` | **descartado** (V15 lo pone a 15) |
| E-12 | P2 | No hay seed de `reglas_anonimizacion` y la config apunta a `RGPD_ES`, que no existe | `V12` + falta migración de reglas | abierto |
| E-13 | P2 | H3 de [[Coherencia]] cita `estado='eliminado'`, que V15 ya metió en el CHECK | `vault/Proyecto/Coherencia.md` | **corregido** (26/11) |
| E-14 | P3 | Comentarios y `CHECK` siguen hablando de `supervisor`, que 0012 quita | `V1:7`, `V15:29,169` | bloqueado (0012) |
| E-15 | P2 | `investigacion/` en minúsculas en [[Inicio]]; en la bóveda es `Investigacion/` | `vault/Inicio.md:20` | abierto |
| E-16 | P0 | `partitioning.sql` llama a `partman` sobre `public.auditia`, que no existe | `partitioning.sql:52,58,61,67,70,73,81` | **corregido** (26/11: ocho apariciones) |
| E-17 | P0 | `auditoria` no se puede particionar por `creado_en`: su PK es solo `id` | `V8:3-13`, `partitioning.sql:9-12` | **corregido** (26/11: PK `(id, creado_en)` en la recreación; [[0017-particionado-auditoria]] en Propuesta) |
| E-18 | P1 | La cola ordena por `nivel_riesgo DESC`, y como es texto pone «alto» el último | `views.sql:102` | abierto |
| E-19 | P1 | Tres `JOIN` internos esconden documentos en las vistas | `views.sql:42,43-49,197-204` | abierto |
| E-20 | P1 | `entidades_confirmadas` no conoce las acciones nuevas de V15 | `views.sql:53` | abierto |
| E-21 | P1 | V15 dice que los offsets van por bloque; el contrato cerrado y las vistas, por texto completo | `V15:103-109`, `views.sql:94` | corregido (25/11): offsets por bloque; contrato, vistas y comentarios alineados |
| E-22 | P2 | `MAX(numero_version) + 1` sin bloqueo: dos versiones simultáneas chocan con el único | `V4:6,20`, `triggers.sql:92-107` | abierto |
| E-23 | P1 | La cadena de hashes se bifurca con dos inserciones simultáneas | `triggers.sql:55-87` | abierto |
| E-24 | P1 | La auditoría atribuye el cambio de estado a quien subió el documento | `triggers.sql:225-228` | abierto |
| E-25 | P1 | `anotaciones_entidad.bloque_id` puede apuntar a un bloque de otra versión | `V15:105-106` | corregido (25/11): FK compuesta `(bloque_id, version_id)` |
| E-26 | P2 | `reglas_anonimizacion.codigo UNIQUE` deja la columna `version` sin sentido | `V5:5-6` | abierto |
| E-27 | P2 | `usuarios.email UNIQUE` distingue mayúsculas: `Ana@` y `ana@` son dos cuentas | `V1:5` | abierto |
| E-28 | P2 | `V15` da por existente un único `(version_id, numero_intento)` que `V7` no creó | `V15:87-88`, `V7` | abierto |
| E-29 | P2 | `views.sql` dice ejecutarse tras V10, pero necesita columnas de V15 | `views.sql:3` | **corregido** (26/11: comprobado; también arreglada la cabecera de `triggers.sql`) |
| E-30 | P2 | `horas_media_estado` mide antigüedad, no tiempo en el estado | `views.sql:150,156-165` | abierto |
| E-31 | P1 | `versiones_documento.es_actual` no existe y el contrato lo usa para la versión vigente | `endpoints.md:210,428` vs `V4` | **corregido** (20/11) |
| E-32 | P1 | `pipeline_version` y `confianza_layout_promedio` no existen; la tabla solo tiene `confianza_promedio` | `endpoints.md:254-255,298` vs `V4:12` | **corregido** (20/11) |
| E-33 | P1 | `regla_categorias` no existe: `/rules` no puede guardar categorías | `endpoints.md:88-90,609` | corregido (24/11) |
| E-34 | P1 | Identidad y sesiones: faltan las columnas y tablas que usan el contrato y U-04/U-05/U-08 | `V1` vs `endpoints.md:143,163,176`; `Modelo de datos.md:233-237` | corregido (24/11) |
| E-35 | P1 | `paginas_documento.estado` vale `revisar/ilegible`, pero el contrato devuelve `aviso/error` | `endpoints.md:270,278` vs `V14:20-21` | **corregido** (20/11) |
| E-36 | P1 | La vista de métricas y el trigger de revisor asumen un rol único, no `usuarios_roles` | `views.sql:136`, `triggers.sql:134-136` vs 0012 | corregido (24/11) |
| E-37 | P1 | El export se dice idempotente sobre `exportado`, pero el mismo endpoint responde `409` si no está `aprobado` | `endpoints.md:472,474`; `pdf.md:148` | **corregido** (20/11) |
| E-38 | P1 | Se prometen seudónimos coherentes sin tabla ni mapa que los sostenga | `Modelo de datos.md:250`; `maqueta/index.html:156,188` | abierto |
| E-39 | P2 | `pdf.md` prohíbe PyMuPDF por AGPL y a la vez lo elige para leer la geometría | `pdf.md:102,156` | corregido (23/11): se elige `pypdf` BSD |
| E-40 | P2 | `pdf.md` atribuye la reconstrucción del PDF a la decisión 0006, que es Presidio | `pdf.md:12,188` | **corregido** (20/11) |
| E-41 | P2 | El README de arquitectura deja un bloque de código SQL sin cerrar | `docs/architecture/README.md:18-34` | **corregido** (20/11) |
| E-42 | P2 | `V15` siembra plazo, aviso y calendario de A-20, una regla retirada | `V15:163-172`; `README.md:9` | abierto |
| E-43 | P2 | `V12` activa notificaciones por email/Slack sin proveedor ni regla que las pida | `V12:21-22` | abierto |
| E-44 | P2 | El documento RGPD describe otro sistema: acción por defecto y borrado físico | `rgpd-considerations.md:11-13,48` vs `V15:151-153` | parcial (26/11: acción y PDF alineados; queda la retención) |
| E-45 | P2 | La maqueta promete borrar la imagen y la capa de texto de un PDF reconstruido | `maqueta/index.html:155-156,187-188`; `docs/maqueta.md` §3.7 | **corregido** (20/11) |
| E-46 | P2 | La documentación sigue mandando arreglos a `V13`/`V16`, que ya no existirán | `usuarios.md:98-101`; `pendientes.md:77,99`; `Modelo de datos.md:245,252` | **corregido** (20/11) |
| E-47 | P2 | La cabecera de `V15` describe un estado anterior: 0005 sin aceptar y B8 con migración | `V15:4-5,30,32` | corregido (24/11) |
| E-48 | P2 | El README dice que las reglas están «cerradas y auditadas» y varias siguen en propuesta o en pausa | `README.md:18` vs `reglas-de-negocio.md` | **corregido** (20/11) |
| E-49 | P2 | U-12 retirada dice que la ruta de recuperación «sigue existiendo»; el contrato la retiró | `reglas-de-negocio.md:193` vs `endpoints.md` §1 | **corregido** (20/11) |
| E-50 | P2 | [[Modelo de datos]] da por abiertos B5 y B8 y dice que `preservar_formato_pdf = false` contradice 0007 | `Modelo de datos.md:245,248-249` | **corregido** (20/11) |
| E-51 | P2 | `anotaciones_entidad` conserva `pagina_numero` y `bbox_*`, que no aparecen en el modelo ER vigente | `V6__create_anotaciones_entidad.sql` vs `Modelo de datos.md:147-165,247` | bloqueado: requiere decidir si se conservan como respaldo o se eliminan con plan de datos |
| E-52 | P1 | El diseño del PDF final tenía lagunas: geometría, semántica del texto, `falso_negativo`, sobrescritura, concurrencia y offsets | `pdf.md`, 0007, `endpoints.md` §5-6 | corregido (25/11) |
| E-53 | P3 | La v0.3 se contradice: `hash_export`, A-20, 0012, A-04, offsets, columnas de `revisiones` y columnas que el SQL no trae | `Modelo-ER-POC-ICAT-v0.3` (24/11) | abierto (documentado; decide el equipo) |

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
- **Arreglo (26/11).** Envuelto en `convert_to((row_data || jsonb_build_object('prev_hash', prev_hash))::text, 'UTF8')` antes del `sha256`, igual que hace `backend/app/db/queries/audit.sql:5`.
- **Estado.** corregido el 26/11 en este repo. Sigue vivo E-23: el trigger y el backend construyen la fila de forma distinta.

### E-03 · `partitioning.sql` no es SQL válido

- **Evidencia.** `docs/architecture/partitioning.sql:16-17` hace `ALTER TABLE auditoria PARTITION BY RANGE (creado_en);`, y `V8__create_auditoria.sql` crea la tabla sin `PARTITION BY`.
- **Qué pasa.** PostgreSQL no convierte una tabla normal en particionada con `ALTER TABLE … PARTITION BY`: hay que recrearla. El fichero tiene el procedimiento correcto comentado en las líneas 10-12, pero lo que se ejecuta es el `ALTER`.
- **Impacto.** El paso 3 del README de arquitectura falla siempre.
- **Arreglo (26/11).** `partitioning.sql` ya no ejecuta el `ALTER`: recrea `auditoria` como tabla particionada solo si no lo está, copiando las filas y conservando secuencia, FK, índices, comentarios y trigger. No se edita `V8` (BD cerrada, 0011 y 0015).
- **Estado.** corregido el 26/11. Sin motor local, la recreación está revisada solo por lectura.

### E-16 · El nombre de la tabla está mal escrito en siete llamadas a `pg_partman`

- **Evidencia.** `partitioning.sql` crea el padre como `'public.auditoria'` (línea 31) y luego llama a `partman` sobre **`'public.auditia'`**: líneas 52, 58, 61, 67, 70, 73 y 81 (ocho apariciones, siete líneas). La línea 52 es la única que se ejecuta; el resto están comentadas, pero son las que el equipo copiará para operar.
- **Impacto.** Aunque se arregle E-03, `run_maintenance` falla con «no existe la tabla padre»; y las consultas de verificación de particiones y retención tampoco devuelven nada.
- **Arreglo (26/11).** `auditia` → `auditoria` en las ocho apariciones, incluido el nombre del job de `pg_cron` y las consultas de verificación.
- **Estado.** corregido el 26/11.

### E-17 · `auditoria` no se puede particionar con esa clave primaria

- **Evidencia.** `V8__create_auditoria.sql`: `id BIGSERIAL PRIMARY KEY`, y el particionado es `PARTITION BY RANGE (creado_en)`. El camino de recreación que sugiere `partitioning.sql:10` (`CREATE TABLE auditoria_partitioned (LIKE auditoria INCLUDING ALL) PARTITION BY RANGE (creado_en)`) copia también esa PK.
- **Qué pasa.** En una tabla particionada, toda `PRIMARY KEY` o `UNIQUE` tiene que incluir la columna de particionado; si no, PostgreSQL rechaza el `CREATE`: *unique constraint on partitioned table must include all partitioning columns*. Pasa con el `ALTER` (E-03) y con el `LIKE … INCLUDING ALL`.
- **Impacto.** El particionado no es aplicable sin cambiar la PK a `(id, creado_en)`. Y de paso, la cadena de hashes (E-23) ordena por `id`, que deja de ser único por sí solo.
- **Arreglo (26/11).** La recreación de `partitioning.sql` define `PRIMARY KEY (id, creado_en)`; `triggers.sql` y `backend/app/db/queries/audit.sql` ordenan la cadena por `(creado_en DESC, id DESC)`. `id` sigue siendo `BIGSERIAL` con secuencia global. La propuesta [[0017-particionado-auditoria]] recoge el cambio de orden y queda a la espera de que una persona la acepte.
- **Estado.** corregido el 26/11 en el código; decisión **Propuesta**. Pendiente de validar en PostgreSQL 16.

---

## P1 · Documentación que describe otro esquema

### E-04 · Diccionario de datos parado en V12

- **Evidencia.** `data-dictionary.md` tiene 5 tablas: `usuarios`, `categorias_sensibles`, `documentos`, `versiones_documento` y `reglas_anonimizacion`. Existen **11**: faltan `anotaciones_entidad`, `revisiones`, `auditoria`, `configuracion_sistema`, `paginas_documento` y `bloques_layout`. Describe además `usuarios.rol` con `supervisor`, que 0012 quita.
- **Impacto.** Es el documento que se lee para escribir backend. Quien lo siga crea un modelo con 5 tablas y sin flujo de revisión.
- **Arreglo (26/11).** El diccionario describe las 14 tablas de `V1`–`V15` y se le añaden las 19 relaciones del modelo v0.3 y el desfase de columnas (E-53). Ya no cita `supervisor`.
- **Estado.** corregido el 26/11.

### E-05 · El árbol de `docs/architecture/` sigue en una sola línea

- **Evidencia.** `docs/architecture/README.md:9` mete todo el árbol de ficheros en una línea, sin saltos: no se lee en GitHub. El recuento de triggers ya está bien (16) desde #34, que también cambió la nota de V13.
- **Impacto.** Cosmético, pero es la puerta de entrada a la carpeta del modelo.
- **Arreglo (26/11).** Árbol en bloque `text`, una línea por fichero, con la nota de que `V15` incluye la identidad y las reglas. La cifra de 16 triggers ya estaba bien desde #34.
- **Estado.** corregido el 26/11.

### E-06 · El README raíz prometía cosas que el contrato no tiene — corregido

- **Evidencia (19/11, antes de #37).** «migraciones Flyway V1-V12»; `/user/register`, que no estaba en el contrato; y exportación a **Word**, que no existía en `docs/export/`.
- **Estado.** corregido en #37: V1–V15, 40 rutas reales, sin Word y con `docs/api/`, `docs/reglas/` y `docs/export/` en el árbol.

### E-07 · [[Base de datos]] desactualizado

- **Evidencia.** Resume 9 tablas y se titula «primer borrador»; faltan `paginas_documento` y `bloques_layout`, y sigue diciendo que los roles están en `usuarios`.
- **Impacto.** Quien entra por [[Inicio]] → [[Base de datos]] ve un modelo anterior al de [[Modelo de datos]].
- **Arreglo (26/11).** Ficha reescrita con las 14 tablas y las 19 relaciones de la v0.3, y una columna que indica qué hay en el SQL. Ya no se presenta como borrador.
- **Estado.** corregido el 26/11.

### E-08 · `pendientes.md` §1 y §3 se contradicen entre sí

- **Evidencia.** §1 dice que `usuarios` recibirá `estado`, `password_hash`, `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso`, `motivo_baja` y `sso_subject`; §3, en el mismo fichero, dice que `usuarios` se queda «sin `roles[]`, `estado`, `sso_subject` ni `password_hash`: el login tiene que caber en `rol`/`activo` o quedar fuera del piloto».
- **Impacto.** La lista de trabajo del backend se contradice a dos secciones de distancia. Desde #34 ya no pide `password_cambiado_en`, así que el conflicto con 0012 se ha estrechado, pero no ha desaparecido.
- **Arreglo (26/11).** §1 da por implementada la identidad en `V15` ([[0015-identidad-en-v15]]) y §3 recoge lo que falta, con E-53 como única lista de columnas pendientes. Ya no se contradicen.
- **Estado.** corregido el 26/11.

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

### E-21 · Offsets: el contrato y las vistas contaban sobre el texto completo

- **Evidencia histórica.** `V15:103-109` documentaba los offsets dentro de `bloques_layout.contenido`; el contrato de 19/11 decía `contenido_texto` y `views.sql` cortaba el snippet de la versión completa.
- **Arreglo aplicado (25/11).** Se adopta la base del modelo ER: `inicio_offset` y `fin_offset` cuentan sobre `bloques_layout.contenido` del bloque `bloque_id`. Contrato, diccionario, vistas, `pdf.md` y `pendientes.md` quedan alineados. Una anotación sin bloque no se exporta.
- **Estado.** corregido (25/11).

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

### E-25 · Una anotación podía apuntar a un bloque de otra versión

- **Evidencia histórica.** `V15:105-106` añadía `anotaciones_entidad.bloque_id` con FK simple a `bloques_layout(id)`; nada obligaba a que el bloque fuera de la misma versión.
- **Impacto.** Un `bloque_id` cruzado dejaba offsets que no corresponden al texto de la anotación. La base lo aceptaba.
- **Arreglo aplicado (25/11).** `V15` añade `UNIQUE (id, version_id)` en `bloques_layout` y la FK compuesta `(bloque_id, version_id)` en `anotaciones_entidad`.
- **Estado.** corregido (25/11).

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
- **Arreglo (26/11).** H3 tacha el punto del CHECK y el de `usuarios.activo`: el documento RGPD usa `eliminado_en`, roles de `usuarios_roles`, `cerrado_en` y la cadena de hash. Queda separado el borrado de `anotaciones_entidad` frente a A-18.
- **Estado.** corregido el 26/11.

### E-15 · `investigacion/` con dos significados

- [[Inicio]]:20 escribe `` `investigacion/` `` para las notas de la bóveda, pero la carpeta de notas es `vault/Investigacion/` y existe además `investigacion/` en la raíz, que guarda los `bench.py`. Mismo nombre, dos cosas.
- **Estado.** abierto.

### E-26 · La columna `version` de las reglas no sirve para nada

- **Evidencia.** `V5:5-6`: `codigo VARCHAR(50) NOT NULL UNIQUE` y `version INT NOT NULL DEFAULT 1`. Con `codigo` único no puede haber dos filas de la misma regla, así que nunca habrá una versión 2 de `RGPD_ES`.
- **Impacto.** Se pierde el histórico de reglas, que es justo lo que se quiere para auditoría: al cambiar una regla se sobreescribe. Además `creado_por` y `version` dan a entender lo contrario.
- **Arreglo.** `UNIQUE (codigo, version)` más un único parcial `WHERE activa` para que solo haya una activa por código. Es lo que hace la copia de `Documents/Advocats`.
- **Estado.** corregido (24/11): `V15` sustituye el único global por `(codigo, version)` y añade el único parcial de la versión activa.

### E-27 · El email distingue mayúsculas

- **Evidencia.** `V1:5`: `email VARCHAR(255) NOT NULL UNIQUE`. `Marina@icat.cat` y `marina@icat.cat` son dos cuentas distintas.
- **Impacto.** Duplicados de cuenta y, con SSO, un usuario que entra con otra caja y no ve sus documentos.
- **Arreglo.** `UNIQUE (lower(email))` o `CITEXT`. Encaja con el arreglo de identidad: mejor cerrarlo allí, editando la migración que se toque, que en un parche suelto.
- **Estado.** corregido (24/11): `V15` elimina el único sensible a mayúsculas y crea `uq_usuarios_email_lower`.

### E-28 · `V15` cita un único de `V7` que no existe

- **Evidencia.** `V15:87-88` dice: «El único de V7 era `(version_id, numero_intento)` y no lo implementaba». En `V7__create_revisiones.sql` no hay ningún `UNIQUE` ni `CONSTRAINT`: solo la PK y las FK.
- **Impacto.** Nada impide repetir `numero_intento` en la misma versión. Y el comentario hace creer que existe una red que no está.
- **Arreglo.** Añadir `UNIQUE (version_id, numero_intento)` editando `V7`, y corregir el comentario.
- **Estado.** corregido (24/11): `V15` crea `uq_revisiones_version_intento`.

### E-29 · El orden de ejecución que dice `views.sql` es falso

- **Evidencia.** `views.sql:3` dice «Ejecutar DESPUÉS de V10__create_indexes.sql», pero la vista usa `r.asignado_a`, que nace en V15, y `documentos.requiere_visto_bueno` también es de V15.
- **Impacto.** Quien siga esa línea ejecuta `views.sql` antes de V15 y recibe *column r.asignado_a does not exist*.
- **Arreglo (26/11).** `views.sql:3` ya decía «después de V15 y de los índices»; el registro no se había actualizado. La cabecera de `triggers.sql`, que sí seguía diciendo «V9 / antes de seeds», se alinea con el README.
- **Estado.** corregido el 26/11.

### E-30 · `horas_media_estado` no mide lo que dice

- **Evidencia.** `views.sql:150`: `AVG(EXTRACT(EPOCH FROM (actualizado_en - creado_en))/3600)`. No hay histórico de estados en el esquema, así que lo que calcula es la antigüedad del documento, agrupada por el estado en que está ahora.
- **Impacto.** El panel se presenta como «cuellos de botella por estado» y no puede detectarlos: un documento que lleva 20 días en `pendiente` y otro que acaba de llegar promedian lo mismo que si el estado no influyera. Además el `CASE` de ordenación (156-165) no conoce `pendiente_visto_bueno` ni `eliminado`, que caen en el `ELSE 9`.
- **Arreglo.** O se renombra la columna a `horas_media_desde_alta`, o se añade `documentos_estado_historial` (tabla + trigger) y se calcula de verdad. Lo segundo es lo que pide un panel de cuellos de botella.
- **Estado.** abierto.

---

## P3 · Discrepancias que exigen decisión

### E-14 · `supervisor`, que 0012 quita

- `V1:7` admite `'supervisor'` en el `CHECK` de `rol`; `V15:29` describe `visto_bueno_por` como «supervisor que firmó» y `V15:169` manda el aviso al supervisor. 0012 deja **tres roles, sin supervisor**.
- **No es un error a corregir por mi cuenta**: el `CHECK` se cambia editando `V1`, y espera a 0009 y 0012.
- **Estado.** bloqueado (0012).

### E-53 · Contradicciones internas del documento v0.3

El modelo del 24/11 es la fuente del [diagrama](../Proyecto/Modelo%20de%20datos.md), pero su texto se contradice en varios puntos. Se han documentado **sin copiar el error** a la documentación de esquema; cada uno necesita una decisión, no una corrección automática.

| # | Qué dice la v0.3 | Qué dice el repo | Cómo se ha reflejado |
|---|---|---|---|
| 1 | `hash_export` en `documentos` y B8 abierto | B8 cerrado el 19/11: el hash es de la versión, en `versiones_documento.metadatos_proceso->>'hash_export'` | Columna en el modelo por fidelidad a la v0.3, con aviso; [[Coherencia]] manda lo cerrado |
| 2 | A-20 «en pausa», con plazos en `revisiones` | A-20 **retirada** el 18/11; los campos siguen en el SQL sin uso (E-42) | `fecha_limite` y `aviso_24h_enviado_en` documentados sin uso |
| 3 | §5 de 0012: la propuesta sustituye `usuarios_roles` por una columna `roles` | @Marina decidió el 18/11 que los roles van en tabla, implementado en `V15` ([[0015-identidad-en-v15]]) | Prevalece la decisión: `usuarios_roles` con tres roles |
| 4 | Índice parcial de A-04 «por versión» | La regla aceptada es una revisión abierta **por documento** | Corregido en el diagrama y en el diccionario |
| 5 | `documento_id` y `actualizado_en` en `ANOTACIONES_ENTIDAD` | Son columnas de `revisiones` (A-04 y A-23, `docs/reglas/aprobacion.md`) | Corregido en el diagrama y en el diccionario |
| 6 | Offsets dentro de `bloques_layout.contenido` | E-21 y E-25 cerrados el 25/11: la edición de `V15` coincide con la v0.3 | Sin conflicto ya; el diagrama conserva la frase de la v0.3 |
| 7 | Campos de identidad que el SQL no trae (`intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso`, `password_cambiado_en`, `otorgado_en`, `otorgado_por`) y no trae `ultimo_uso_en` | `V15` sí añade `ultimo_uso_en` y no los otros seis | Diferencia documentada en [[Base de datos]], README y diccionario |

- **Impacto.** Quien lea solo la v0.3 montaría un hash en la tabla equivocada, un índice que permite dos revisiones abiertas y una tabla de usuarios con campos que no existen.
- **Arreglo.** Los puntos 4 y 5 ya están corregidos en la documentación; el 6 está resuelto en el SQL. Los puntos 1, 2, 3 y 7 exigen confirmación antes de editar `V15` otra vez.
- **Estado.** abierto (documentado; a la espera de decisión para los puntos 1, 2, 3 y 7).

---

## Tercera pasada (20/11)

> Contrato contra `V1`-`V15`, documentación del export, RGPD y maqueta. Sigue sin haber motor: todo es lectura del SQL y de los documentos.

### E-31 · `versiones_documento.es_actual` no existe

- **Evidencia.** `docs/api/endpoints.md:210` lee «la versión vigente (`es_actual = true`)» y `:428` crea `final_aprobado` «con `es_actual = true`». No hay ninguna aparición de `es_actual` en `docs/architecture/migrations/` ni en `views.sql`; `v_documento_actual` resuelve la vigente por `MAX(numero_version)`.
- **Impacto.** El contrato pide una bandera que la base no tiene. `POST /transform/plain-text` y el cierre de revisión no se pueden implementar tal como están escritos; el backend tendrá que usar la versión de mayor número y el contrato mentirá.
- **Arreglo.** Quitar `es_actual` del contrato y decir «la versión de mayor `numero_version`», como ya hace la vista. Si se quiere explícita, se edita `V4`/`V15`; no se crea una `V16`.
- **Estado.** corregido (20/11): el contrato ya dice «la de mayor `numero_version`» en las dos rutas.

### E-32 · `pipeline_version` y `confianza_layout_promedio` no existen

- **Evidencia.** `docs/api/endpoints.md:254-255` y `:298` devuelven `pipeline_version` y `confianza_layout_promedio`. `V4__create_versiones_documento.sql:12` solo tiene `confianza_promedio`; `pipeline_version` no aparece en ninguna migración.
- **Impacto.** Dos respuestas del contrato no se pueden servir desde el esquema. O se inventan en el backend o el cliente recibe campos distintos de los documentados.
- **Arreglo.** Devolver `confianza_promedio` y guardar la versión del pipeline en `metadatos_proceso` (que ya es JSONB), o añadir las columnas editando `V4`.
- **Estado.** corregido (24/11): `V15` crea `pipeline_version` y `confianza_layout_promedio`, y el contrato usa los nombres del modelo ER.

### E-33 · `regla_categorias` no existe

- **Evidencia.** `docs/api/endpoints.md:88-90` declara que `/rules` escribe en `reglas_anonimizacion` y `regla_categorias`, y `:609` repite la tabla. No hay ninguna migración que la cree; `[[Modelo de datos]]:246` lo reconoce: «no existen en `V1`-`V15`. Necesitan migración».
- **Impacto.** `POST /rules` y `PATCH /rules/{id}` no pueden guardar la lista de categorías de una regla. Si el backend usa `configuracion` JSONB, el contrato sigue prometiendo una tabla que no está.
- **Arreglo.** Usar `reglas_anonimizacion.configuracion` (ya guarda categorías y acciones) y quitar `regla_categorias` del contrato, o crear la tabla editando `V5`; no hay `V16`.
- **Estado.** corregido (24/11): `V15` crea `regla_categorias` con PK compuesta y FKs.

### E-34 · Identidad y sesiones: faltan columnas y tablas que el contrato ya usa

- **Evidencia histórica.** Antes de editar `V15`, `V1__create_usuarios.sql` solo tenía `email`, `nombre_completo`, `rol` y `activo`. El contrato devuelve `nombre`, `apellidos`, `roles` y `estado` (`endpoints.md:143,163`), escribe `eliminado_en` al dar de baja (`:176`) y usa `sesiones_usuario` (`:77` y todo §1).
- **Impacto.** Es B1 con nombres y apellidos: el alta por SSO, el estado de la cuenta, la baja, el tope de tres sesiones y la revocación no se pueden implementar sobre el esquema definitivo.
- **Arreglo aplicado (24/11).** `V15` añade la identidad completa sin abrir `V13`, y adapta nombres, email y sesión al modelo ER.
- **Estado.** corregido (24/11): `V15` añade `usuarios_roles`, `sesiones_usuario`, `nombre`, `apellidos`, `estado`, `sso_subject`, `password_hash`, `motivo_baja` y `eliminado_en`; además ajusta la sesión a `ip_origen` y `ultimo_uso_en`.

### E-35 · `paginas_documento.estado`: el contrato y la BD usan vocabularios distintos

- **Evidencia.** `V14__create_bloques_layout.sql:20-21` acepta `ok`, `revisar` e `ilegible`. El contrato devuelve `"estado": "aviso"` (`endpoints.md:270`) y documenta `ok | aviso | error` (`:278`).
- **Impacto.** La API promete estados que la base nunca guarda. Un cliente que filtre por `aviso` o `error` no recibe nada, y el semáforo de la bandeja pinta códigos distintos de los que persiste el OCR.
- **Arreglo.** Alinear el contrato con la BD (`ok | revisar | ilegible`) o cambiar el `CHECK` editando `V14`. Lo barato es el contrato.
- **Estado.** corregido (20/11): el contrato usa `ok | revisar | ilegible`, como `V14`.

### E-36 · La vista de métricas y el trigger de revisor asumen un rol único

- **Evidencia.** `views.sql:136`: `WHERE u.rol = 'revisor' AND u.activo = true`. `triggers.sql:134-136`: rechaza al asignado si `(SELECT rol FROM usuarios WHERE id = NEW.asignado_a) <> 'revisor'`. 0012 y U-01 ponen los roles en `usuarios_roles (usuario_id, rol)` (N:M) y eliminan `usuarios.rol`; U-04 sustituye `activo` por `estado`.
- **Impacto.** Un admin que también revisa desaparece de `v_metricas_revisor` y no puede ser asignado por el trigger. Si 0012 se acepta y `rol` desaparece, la vista y el trigger dejan de funcionar.
- **Arreglo.** `EXISTS (SELECT 1 FROM usuarios_roles ur WHERE ur.usuario_id = u.id AND ur.rol = 'revisor')` y `estado = 'activo'` en la vista; el trigger, la misma comprobación. Va con 0012.
- **Estado.** corregido (24/11): vista y trigger consultan `usuarios_roles` y `usuarios.estado`.

### E-37 · El export no puede ser idempotente y responder `409` a la vez

- **Evidencia.** `docs/api/endpoints.md:472`: «`409` si el documento no está `aprobado`». `:474`: «Un documento ya exportado devuelve el mismo PDF y el mismo hash: la operación es idempotente». `docs/export/pdf.md:148` repite que la segunda llamada devuelve el fichero guardado.
- **Impacto.** Un documento exportado está en `exportado`, no en `aprobado`, así que la segunda llamada recibe `409` y nunca devuelve el PDF ni el hash. La idempotencia que promete el contrato no existe, y no hay forma de volver a descargar lo exportado.
- **Arreglo.** Aceptar `aprobado` **o** `exportado` cuando ya hay `ruta_pdf` y hash; `409` solo para el resto. O retirar la frase de idempotencia.
- **Estado.** corregido (20/11): el export acepta `aprobado` y `exportado` con `ruta_pdf` y hash guardados.

### E-38 · Seudónimos «coherentes» sin tabla ni mapa

- **Evidencia.** `[[Modelo de datos]]:250` lo dice: «`pseudonimizado` guarda `texto_sustitucion` en la anotación, así que la misma persona puede salir con dos seudónimos distintos en el mismo documento». La maqueta promete lo contrario en `maqueta/index.html:156,188` (`g4`: «Pseudònims coherents dins del document, sense taula que guardar») y `docs/maqueta.md` §3.6. No hay tabla de seudónimos ni mapa en `metadatos_proceso`.
- **Impacto.** Dos apariciones de la misma persona pueden recibir letras distintas: se rompe la legibilidad del documento y la promesa de la demo, y el revisor no tiene forma de comprobarlo. En un documento anonimizado, la coherencia también es una propiedad de privacidad.
- **Arreglo.** Guardar el mapa persona → seudónimo en `versiones_documento.metadatos_proceso` (sin tabla nueva) o añadir la tabla editando `V6`/`V15`; decidir antes de la demo.
- **Estado.** abierto.

### E-39 · `pdf.md` no debe mezclar licencias

- **Evidencia histórica.** La versión anterior de `docs/export/pdf.md` proponía «`PyMuPDF` (`page.get_text("dict")`)» y a la vez lo prohibía por AGPL.
- **Impacto.** La fuente de cajas que el documento considera preferida está bajo la licencia que el propio documento descarta. Si el Colegio no acepta AGPL, la rama 1 del algoritmo no se puede usar, y con ella se cae el caso normal (PDF con capa de texto).
- **Arreglo aplicado (23/11).** Se usa `pypdf` con licencia BSD y se descarta PyMuPDF. Si no hay cajas suficientes, el export usa el modo secuencial.
- **Estado.** corregido (23/11).

### E-40 · `pdf.md` atribuye la reconstrucción a la decisión 0006

- **Evidencia.** `docs/export/pdf.md:12` remite el «modo imagen» a la decisión 0006 y `:188` dice «Aceptada en la decisión 0006». La reconstrucción del PDF es la 0007; la 0006 es Presidio. E-10 cubre los wikilinks, no estas dos frases.
- **Impacto.** Quien siga el documento acaba en la decisión equivocada y no encuentra la base de la reconstrucción.
- **Arreglo.** `0006` → `0007` en las dos líneas.
- **Estado.** corregido (20/11): `0006` pasó a `0007` en las dos líneas.

### E-41 · El README de arquitectura deja un bloque de código SQL sin cerrar

- **Evidencia.** `docs/architecture/README.md:18-34`: el bloque abierto en la línea 19 no se cierra; la línea 23 («Orden de Ejecución») y los comandos de `flyway`/`psql` quedan dentro del bloque.
- **Impacto.** GitHub renderiza toda la sección de despliegue como un único bloque SQL, sin encabezado, y el copiar-pegar incluye texto que no es SQL. Es la puerta de entrada a la carpeta del modelo.
- **Arreglo.** Cerrar el bloque tras la línea 22, poner `### Orden de ejecución` y abrir un bloque nuevo para los comandos.
- **Estado.** corregido (20/11): el bloque SQL se cierra y «Orden de ejecución» es un encabezado con su propio bloque.

### E-42 · `V15` siembra el plazo, el aviso y el calendario de A-20, una regla retirada

- **Evidencia.** `V15:163-172` inserta `revision_plazo_horas`, `revision_aviso_horas` y `calendario_laboral` con comentarios «A-20». `docs/reglas/aprobacion.md` §8 y `reglas-de-negocio.md` retiran A-20 el 18/11; `[[Coherencia]]` B4 deja `fecha_limite` y `aviso_24h_enviado_en` «sin uso». `docs/architecture/README.md:9` también describe V15 como «plazos».
- **Impacto.** La base define un plazo y un aviso que ninguna regla implementa, y el índice `idx_revisiones_plazo` barre columnas muertas. Quedan dos fuentes de verdad: la config y las reglas retiradas.
- **Arreglo.** Quitar los tres `INSERT` y el índice, o marcarlos como reservados para una A-20 futura; corregir los comentarios y el README.
- **Estado.** abierto.

### E-43 · `V12` activa notificaciones sin proveedor ni regla

- **Evidencia.** `V12:21-22` siembra `notificar_revisor_nuevas_pendientes` y `notificar_transcriptor_rechazo` en `true`. `docs/pendientes.md` §1 dice que no hay proveedor de correo (B2); A-20 retirada elimina el aviso de 24 h y A-21 no prevé notificaciones. V15 corrige otros seeds, pero no estos.
- **Impacto.** El backend puede construir un canal de email/Slack que nadie ha decidido, o dejar dos `true` que prometen avisos inexistentes. Es configuración que miente.
- **Arreglo.** Borrar las dos claves o ponerlas en `false` con una nota; si se retoman, van con una regla nueva.
- **Estado.** abierto.

### E-44 · El documento RGPD describe otro sistema (acción por defecto y borrado)

- **Evidencia.** `docs/architecture/rgpd-considerations.md:48` fija `accion_por_defecto="tachado"`; `V15:151-153` lo cambia a `"censurar"` (y la descripción de la clave). `rgpd-considerations.md:11-13` promete borrado físico del original a los 30 días y `Cascade delete` de versiones y anotaciones; `V15:31` y A-18 dicen que el borrado lógico «no borra versiones ni anotaciones» y A-21 deja el original sin caducidad; `:37` habla de 60 meses. H3 de [[Coherencia]] cubre parte de la cascada, pero no la acción por defecto ni el plazo de 30 días.
- **Impacto.** El ROPA/EIPD describe una acción y una retención que el sistema no aplica. En un documento legal, eso no es cosmético.
- **Arreglo (26/11).** Alineadas la acción por defecto (`censurar`) y la reconstrucción del PDF con 0007/V15. Queda decidir el plazo de conservación (U-08): el documento ya no afirma un borrado físico a 30 días como si estuviera acordado.
- **Estado.** parcialmente corregido el 26/11; abierto solo la retención.

### E-45 · La maqueta promete borrar imagen y capa de texto de un PDF reconstruido

- **Evidencia.** `maqueta/index.html:155,187` (`conf_1`): «el text original s'elimina de la capa de text, de la imatge i de les metadades». `:156,188` (`g2`): «Zones de la imatge esborrades». `docs/maqueta.md` §3.7: «borrado real (texto, imagen y metadatos)». La decisión 0007 reconstruye un PDF nuevo sin ningún píxel del escaneo: no hay capa de texto ni imagen que borrar. I2 solo cubrió el texto de `g2`.
- **Impacto.** La demo atribuye al producto una garantía que no ejecuta: no se borra nada porque no se copia nada. Quien vea la pantalla puede creer que el original se limpia y se conserva, justo lo contrario de 0007.
- **Arreglo.** Cambiar las tres frases por «PDF reconstruido desde el texto: no contiene el escaneo, su capa de texto ni sus metadatos».
- **Estado.** corregido (20/11): tres frases de `maqueta/index.html` y `docs/maqueta.md` §3.7.

### E-46 · La documentación sigue mandando arreglos a `V13`/`V16`

- **Evidencia.** `docs/reglas/usuarios.md:98-101` llama «tabla de `V13`» a `sesiones_usuario` y dice que «`V13` no se ha escrito». `docs/pendientes.md:77` pone `V13` como desbloqueo de 0009 y `:99` la lista como migración futura. `[[Modelo de datos]]:245` manda `hash_export` a `V16` y `:252` deja `V13` pendiente. El propio registro dice «en `V13` o en `V16`» en E-14, E-27 y E-28. `docs/pendientes.md:69` y [[Coherencia]] dicen lo contrario: no habrá `V13` ni `V16`.
- **Impacto.** El lector espera migraciones que no se van a escribir y los arreglos del registro apuntan a ficheros inexistentes. La premisa de la BD definitiva se cae en cuanto se sigue un enlace.
- **Arreglo.** Sustituir `V13`/`V16` por «editar la migración existente» o «fuera de alcance» en todos esos sitios, incluidos E-14, E-27 y E-28.
- **Estado.** corregido (20/11): `usuarios.md`, `pendientes.md`, [[Modelo de datos]] y las entradas E-14, E-27 y E-28.

### E-47 · La cabecera de `V15` describe un estado anterior

- **Evidencia.** `V15:4` dice «Depende de 0005 ... no aplicar antes de que se acepte»; 0005 está **Aceptada** desde el 19/11. `V15:5` dice que el hash del PDF «tendrá su migración»; B8 se cerró el 19/11 con el hash en `metadatos_proceso` y sin migración. `:32` sigue diciendo «pendiente de B8». `:30` describe `cerrado_en` como «cierre o reapertura», pero A-19 dice que lo escribe el export.
- **Impacto.** Un lector que despliegue por orden cree que V15 depende de una decisión no aceptada y que falta una migración que nunca llegará. El comentario de `cerrado_en` contradice la regla.
- **Arreglo.** Actualizar los cuatro comentarios; el SQL no cambia.
- **Estado.** corregido (24/11): cabecera, comentarios de `documentos`, dependencia de 0005 y estado de B8 actualizados en `V15`.

### E-48 · El README dice que las reglas están «cerradas y auditadas»

- **Evidencia.** `README.md:18` presenta «Reglas de negocio (U-01 a U-21, A-01 a A-24) | Cerradas y auditadas». En `docs/reglas/reglas-de-negocio.md`, U-01 y U-05 están «propuesta (0012)», A-06 «propuesta», A-15 «en pausa» y A-22 «sin efecto».
- **Impacto.** El estado que se enseña al cliente dice que todo está cerrado cuando la identidad y los roles siguen esperando votos. La auditoría que se promete no cubre las reglas en propuesta.
- **Arreglo.** «Propuestas y cerradas; el estado de cada una, en su fila».
- **Estado.** corregido (20/11): el README dice «propuestas y cerradas; el estado de cada una, en su fila».

### E-49 · U-12 retirada dice que la ruta de recuperación sigue existiendo

- **Evidencia.** `docs/reglas/reglas-de-negocio.md:193`: U-12, «Recuperación con enlace de un solo uso», se retira porque «la ruta sigue existiendo, sin regla que la gobierne». `docs/api/endpoints.md` §1 dice que «Invitación y recuperación de contraseña se retiran» y que no hay `tokens_usuario`; `docs/reglas/usuarios.md` §5 lo repite.
- **Impacto.** Una tabla de reglas retiradas afirma que hay una ruta que el contrato ya no tiene. Alguien puede implementarla o preguntar por ella en la demo.
- **Arreglo.** «La ruta también se retira con U-10 a U-15».
- **Estado.** corregido (20/11): U-12 dice que la ruta también se retira.

### E-50 · [[Modelo de datos]] da por abiertos B5 y B8 y se equivoca con `preservar_formato_pdf`

- **Evidencia.** `vault/Proyecto/Modelo de datos.md:245` dice que `hash_export` está «sin decidir» y que iría en `V16`; B8 se cerró el 19/11 en `metadatos_proceso`. `:248` dice que `GET /documents/{id}/pages` no tiene endpoint; existe desde el 19/11 (B5). `:249` dice que `preservar_formato_pdf = false` contradice 0007; es justo lo que 0007 pide (reconstruir sin formato original) y V15 lo pone en `false`.
- **Impacto.** El ER que se presenta como fuente de verdad contradice al contrato y a V15 en tres puntos, y manda a `V16` un hash que ya tiene dueño.
- **Arreglo.** Actualizar las tres viñetas; dejar solo lo que siga abierto (seudónimos, retención).
- **Estado.** corregido (20/11): las viñetas de [[Modelo de datos]] ya no contradicen al contrato ni a `V15`.

### E-51 · `anotaciones_entidad` conserva geometría legacy fuera del ER vigente

- **Evidencia.** `V6` conserva `pagina_numero` y `bbox_x/y/ancho/alto`, pero el modelo vigente relaciona la anotación con `bloques_layout` mediante `bloque_id` y deja esos campos fuera de la entidad.
- **Impacto.** El esquema tiene dos fuentes potenciales de geometría. El backend debe usar `bloque_id` y no leer los campos legacy; eliminarlos ahora podría destruir datos si ya se cargaron.
- **Bloqueo.** @Marina debe decidir si se conservan como respaldo o se eliminan con un plan de datos. No se toca el modelo ER.
- **Estado.** bloqueado.

### E-52 · El diseño del PDF final tenía lagunas que impedían implementarlo

- **Evidencia.** `pdf.md` y 0007 se contradecían sobre si PaddleOCR-VL devuelve cajas; no estaba definido si `final_aprobado` guarda texto sustituido o de origen; `falso_negativo` podía dejar visible el dato; el export podía sobrescribir un PDF ya exportado; no había bloqueo ni escritura atómica; la vida de `estructura.json` no estaba definida; tablas, Unicode y offsets no tenían regla; `es_actual` no se mantenía al insertar versiones.
- **Arreglo aplicado (25/11).** Se fija que PaddleOCR-VL 1.6 solo devuelve texto y que la geometría viene de la capa del PDF, de un detector de layout o de un bloque sintético por página. El texto de la versión es siempre el de origen y las sustituciones se aplican solo al generar salidas. `falso_negativo` exige `texto_sustitucion`. El export bloquea la fila, escribe de forma atómica, valida el hash y nunca regenera una versión exportada. La estructura se construye de forma perezosa y es regenerable. Se añaden reglas de tablas, Unicode NFC y offsets por bloque. `trg_version_auto_number` mantiene `es_actual`.
- **Estado.** corregido (25/11).

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

- **Nada está ejecutado en un motor.** Sin PostgreSQL local y con Docker ausente, E-01, E-03, E-16, E-17 y la nueva `V15` son lectura, no prueba. En cuanto haya motor, se aplican las migraciones y este registro se actualiza con el resultado.
- **No se ha auditado el rendimiento con datos.** Las observaciones de E-22, E-23 y E-30 son de diseño; no hay medidas.
- **La maqueta no se ha probado en navegador** y de `docs/api/endpoints.md` solo se ha contrastado el modelo de tablas, no ruta por ruta.
