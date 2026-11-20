# Registro de errores

- **Estado:** abierto
- **Autor:** @ia-opencode-maga369
- **Creado:** 20/11/2026
- **Alcance:** los 41 ficheros versionados del repo (`README.md`, `CONTRIBUTING.md`, `AGENTS.md`, `docs/api/`, `docs/architecture/`, `docs/reglas/`, `docs/export/`, `docs/presidio.md`, `vault/`, `maqueta/`, `scripts/`) y el SQL de `docs/architecture/` leído línea a línea.
- **Para qué:** una sola lista de defectos, con evidencia, impacto y estado, para no reabrirlos ni volver a reportar lo descartado.
- **Qué no es:** no sustituye al [[Tablero]] ni a [[Coherencia]]. Aquí van defectos comprobables; allí, decisiones y bloqueantes.

## Cómo se usa

- Un defecto = un ID `E-NN`. **No se renumera y no se borra**: se cambia el estado y, si se corrige, se anota el PR.
- Estados: **abierto** · **corregido** · **descartado** (falso positivo, con el motivo) · **bloqueado** (espera una decisión).
- Severidad: **P0** rompe la ejecución del SQL · **P1** documentación que describe un esquema o un producto que ya no existe · **P2** enlaces, cifras y datos sueltos · **P3** discrepancia que exige decisión.
- Al encontrar uno nuevo, se añade una fila al resumen y su apartado de detalle en el mismo PR en que se detecta.

## Resumen

| ID | Sev | Qué, en una línea | Dónde | Estado |
|---|---|---|---|---|
| E-01 | P0 | `sha256()` recibe `text` y solo admite `bytea`: `triggers.sql` no se puede crear | `docs/architecture/triggers.sql:46-54` | abierto |
| E-02 | P0 | El trigger de auto-estado lee `NEW.documento_id` en `revisiones`, que no tiene esa columna | `docs/architecture/triggers.sql:176` | abierto |
| E-03 | P0 | `ALTER TABLE … PARTITION BY` no es SQL válido y el README manda ejecutarlo | `docs/architecture/partitioning.sql:16` | abierto |
| E-04 | P1 | El diccionario documenta 5 de las 11 tablas y para en V12 | `docs/architecture/data-dictionary.md` | abierto |
| E-05 | P1 | «7 triggers» cuando hay 16, y el árbol de ficheros en una sola línea | `docs/architecture/README.md:9` | abierto |
| E-06 | P1 | README raíz: migraciones «V1–V12», `/user/register` y exportación a Word | `README.md:45,60,65` | abierto |
| E-07 | P1 | [[Base de datos]] lista 9 de las 11 tablas y se presenta como «primer borrador» | `vault/Proyecto/Base de datos.md` | abierto |
| E-08 | P1 | `pendientes.md` §1 pide columnas que 0012 deja fuera; §3 está por detrás de V14/V15 | `docs/pendientes.md` | abierto |
| E-09 | P2 | Dos enlaces markdown rotos | `docs/presidio.md`, `vault/Bitacora/2026-11-18-ia-opencode-maga369.md` | abierto |
| E-10 | P2 | Dos wikilinks apuntan a `0006-generacion-pdf-final`, que es la **0007** | bitácora 16/11 de @ia-claude-alex, [[Anonimizacion con Presidio]] | abierto |
| E-11 | P2 | `version_esquema_bd = 1` con 15 migraciones en el repo | `V12__seed_configuracion_inicial.sql` | abierto |
| E-12 | P2 | No hay seed de `reglas_anonimizacion` y la config apunta a `RGPD_ES`, que no existe | `V12` + falta migración de reglas | abierto |
| E-13 | P2 | H3 y H4 de [[Coherencia]] siguen como bloqueantes, ya resueltos por V14/V15 | `vault/Proyecto/Coherencia.md` | abierto |
| E-14 | P3 | Comentarios y `CHECK` siguen hablando de `supervisor`, que 0012 quita | `V1__create_usuarios.sql:7`, `V15__flujo_revision_y_export.sql:29` | bloqueado (0012) |
| E-15 | P2 | `investigacion/` en minúsculas en [[Inicio]]; en la bóveda es `Investigacion/` y existe otra carpeta con ese nombre | `vault/Inicio.md:20` | abierto |

---

## P0 · SQL que no se puede aplicar

> Los tres son lectura del SQL, no ejecución: en este equipo no hay PostgreSQL y Docker no arranca. La deducción de E-01 está contrastada con la documentación de PostgreSQL; E-02 y E-03 son directos del esquema.

### E-01 · `audit_compute_hash` no se puede crear

- **Evidencia.** `docs/architecture/triggers.sql:46-54`:
  ```sql
  SELECT encode(
      sha256((row_data || jsonb_build_object('prev_hash', prev_hash))::text),
      'hex'
  )::CHAR(64);
  ```
- **Qué pasa.** En PostgreSQL `sha256()` solo acepta `bytea`; con `text` devuelve `function sha256(text) does not exist`. Como la función es `LANGUAGE sql`, el error salta al crearla, no al usarla.
- **Impacto.** `triggers.sql` aborta en la segunda función: no se crean el hash encadenado ni los 13 triggers que vienen después. El README lo presenta como un paso de despliegue.
- **Arreglo.** Envolver en `convert_to(... , 'UTF8')` antes del `sha256`.
- **Estado.** abierto. La misma línea está corregida en la copia de trabajo de `Documents/Advocats/docs/architecture-postgresSQL/triggers.sql`, fuera de este repo.

### E-02 · El trigger de auto-estado revienta en cada revisión

- **Evidencia.** `docs/architecture/triggers.sql:175-177`:
  ```sql
  ELSIF TG_TABLE_NAME = 'revisiones' THEN
      v_documento := NEW.documento_id;
  ```
  y `docs/architecture/migrations/V7__create_revisiones.sql`: la tabla tiene `version_id`, no `documento_id`.
- **Qué pasa.** En PL/pgSQL los campos de `NEW` se resuelven en ejecución, así que la función se crea sin error y falla al dispararse: `record "new" has no field "documento_id"`.
- **Impacto.** Cualquier `INSERT` o `UPDATE` en `revisiones` falla: el flujo de revisión no se puede usar. No se detecta al desplegar, solo al primer documento revisado.
- **Arreglo.** `SELECT documento_id INTO v_documento FROM versiones_documento WHERE id = NEW.version_id;`
- **Estado.** abierto.

### E-03 · `partitioning.sql` no es SQL válido

- **Evidencia.** `docs/architecture/partitioning.sql:16-17`:
  ```sql
  ALTER TABLE auditoria
  PARTITION BY RANGE (creado_en);
  ```
  y `docs/architecture/migrations/V8__create_auditoria.sql` crea `auditoria` sin `PARTITION BY`.
- **Qué pasa.** PostgreSQL no admite convertir una tabla normal en particionada con `ALTER TABLE … PARTITION BY`: hay que recrearla. El propio fichero tiene el procedimiento correcto comentado en las líneas 10-12, pero lo que se ejecuta es el `ALTER`.
- **Impacto.** El paso 3 del README de arquitectura (`psql -f docs/architecture/partitioning.sql`) falla siempre.
- **Arreglo.** Dejar el `ALTER` comentado y ejecutar el camino de recreación, o marcar el fichero como «solo con `pg_partman` y tabla vacía».
- **Estado.** abierto.

---

## P1 · Documentación que describe otro esquema

### E-04 · Diccionario de datos parado en V12

- **Evidencia.** `docs/architecture/data-dictionary.md` tiene 5 tablas: `usuarios`, `categorias_sensibles`, `documentos`, `versiones_documento` y `reglas_anonimizacion`. Hoy existen **11**: faltan `anotaciones_entidad`, `revisiones`, `auditoria`, `configuracion_sistema`, `paginas_documento` y `bloques_layout`. Además describe `usuarios.rol` con el valor `supervisor`, que 0012 quita.
- **Impacto.** Es el documento que se lee para escribir backend. Quien lo siga crea un modelo con 5 tablas y sin el flujo de revisión.
- **Arreglo.** Reescribirlo contra V1–V15 (las 11 tablas, las columnas que añaden V14 y V15 y los `CHECK` reales). El diccionario de `Documents/Advocats/docs/architecture-postgresSQL/data-dictionary.md` ya está en ese punto y sirve de base, corrigiendo nombres (`hash_sha256`, no `hash_actual`).
- **Estado.** abierto.

### E-05 · El README de arquitectura se queda corto

- **Evidencia.** `docs/architecture/README.md:9` dice `triggers.sql # Triggers automáticos (7 triggers)`; el fichero tiene **16** `CREATE TRIGGER`. En esa misma línea está todo el árbol de ficheros, sin saltos de línea, así que no se lee en GitHub. Las «5 vistas» sí son correctas.
- **Impacto.** Cifra falsa en el documento de entrada a `docs/architecture/`, y una estructura que no hay quien lea.
- **Arreglo.** Poner 16, devolver el árbol a varias líneas y añadir la fila de V13 como pendiente (hoy solo aparece entre paréntesis).
- **Estado.** abierto.

### E-06 · El README raíz promete cosas que el contrato no tiene

- **Evidencia.**
  - Línea 65: «migraciones Flyway V1-V12» — hay **V1–V12 + V14 + V15**.
  - Línea 60: lista `/user/register`, que **no aparece** en `docs/api/endpoints.md` (allí están `login`, `logout`, `me` y `password/change`).
  - Línea 45: «Exportación a PDF buscable o **Word**», cuando ni el contrato ni `docs/export/` recogen Word.
- **Impacto.** Es la primera página del repo; hoy describe un producto y un modelo distintos de los que hay.
- **Arreglo.** V1–V15, quitar `/user/register` y quitar Word (o abrir decisión si se quiere mantener).
- **Estado.** abierto.

### E-07 · [[Base de datos]] desactualizado

- **Evidencia.** La tabla resume 9 tablas y se titula «primer borrador»; faltan `paginas_documento` y `bloques_layout`, y la columna de roles sigue diciendo `usuarios`.
- **Impacto.** Quien entra por [[Inicio]] → [[Base de datos]] ve un modelo anterior al de [[Modelo de datos]].
- **Arreglo.** Añadir las dos tablas, apuntar a [[Modelo de datos]] como fuente y quitar «primer borrador».
- **Estado.** abierto.

### E-08 · `pendientes.md` contra 0012 y contra V14/V15

- **Evidencia.** §1 pide `password_cambiado_en`, `intentos_fallidos`, `bloqueado_hasta` y `ultimo_acceso`, que 0012 deja fuera de `usuarios`; §3 describe un esquema anterior a V14/V15.
- **Impacto.** Es la lista de trabajo del backend y arrastra tareas que ya están decididas en contra.
- **Arreglo.** §1 alineado con 0012 (o marcado «si 0012 se acepta así»); §3 revisado contra V14/V15.
- **Estado.** abierto.

---

## P2 · Enlaces, cifras y datos

### E-09 · Dos enlaces markdown rotos

- `docs/presidio.md` → `../vault/Decisiones/0006-generacion-pdf-final.md`. La nota es la **0007**.
- `vault/Bitacora/2026-11-18-ia-opencode-maga369.md` → `../docs/reglas/reglas-de-negocio.md`; falta un `../` (desde `vault/Bitacora/` son `../../docs/`).
- **Estado.** abierto.

### E-10 · Dos wikilinks a la decisión equivocada

- `vault/Bitacora/2026-11-16-ia-claude-alex.md` y [[Anonimizacion con Presidio]] usan `[[0006-generacion-pdf-final]]`; la decisión del PDF final es la **0007** y la 0006 es otra.
- **Estado.** abierto.

### E-11 · `version_esquema_bd` nace desfasado

- `V12__seed_configuracion_inicial.sql` fija `version_esquema_bd = '1'` y ya hay 14 migraciones aplicadas. Si alguien lo usa para comprobar compatibilidad, miente desde el primer día.
- **Estado.** abierto.

### E-12 · No hay regla de anonimización sembrada

- `V12` deja `regla_default_codigo = "RGPD_ES"`, y ninguna migración inserta en `reglas_anonimizacion`. Con la base recién creada, la regla por defecto no existe.
- **Impacto.** No rompe el SQL; deja el pipeline sin regla.
- **Arreglo.** Migración de seed con `RGPD_ES` y su `configuracion` (o cambiar la clave a una regla que exista).
- **Estado.** abierto.

### E-13 · [[Coherencia]] mantiene bloqueantes ya resueltos

- H3 (geometría del PDF) y H4 quedaron cerrados con V14/V15, pero siguen en la lista de abiertos, y el [[Tablero]] sigue hablando de «los 8 bloqueantes».
- **Estado.** abierto.

### E-15 · `investigacion/` con dos significados

- [[Inicio]]:20 escribe `` `investigacion/` `` para las notas de la bóveda, pero la carpeta de notas es `vault/Investigacion/` y existe además `investigacion/` en la raíz, que guarda los `bench.py`. Mismo nombre, dos cosas.
- **Estado.** abierto.

---

## P3 · Discrepancias que exigen decisión

### E-14 · `supervisor`, que 0012 quita

- `V1__create_usuarios.sql:7` admite `'supervisor'` en el `CHECK` de `rol`, y `V15__flujo_revision_y_export.sql:29` describe `visto_bueno_por` como «supervisor que firmó». 0012 deja **tres roles, sin supervisor**.
- **No es un error a corregir por mi cuenta**: el `CHECK` lo cambia `V13`, que espera a 0009 y 0012. Se anota para que no se olvide al escribirla.
- **Estado.** bloqueado (0012).

---

## Descartados

Falsos positivos comprobados. Se dejan aquí para no volver a reportarlos.

- **«`docs/architecture/README.md` está truncado».** No lo está: termina en el comando `psql` del paso 3, que es un final válido. El problema real es E-05.
- **«`trg_audit_categorias` usa `NEW.creado_por` y `categorias_sensibles` no tiene esa columna».** Cierto en la copia de `Documents/Advocats/docs/architecture-postgresSQL/`, **no en este repo**: aquí no existe trigger de auditoría sobre `categorias_sensibles`, y los tres `NEW.creado_por` que hay (`documentos`, `versiones_documento`, `reglas_anonimizacion`) apuntan a columnas que sí existen.
- **«`V14__create_bloques_layout.sql` tiene bytes corruptos».** Es UTF-8 válido; lo que se veía roto era la consola de PowerShell.
- **Avisos de wikilink en `vault/Plantillas/Decision.md` (`[[NNNN-...]]`) y en [[Modelo de datos]] (`[[x,y]]`).** Son plantilla y sintaxis de Mermaid, no enlaces.

## Lo que no cubre

- **Nada está ejecutado en un motor.** Sin PostgreSQL local y con Docker caído, E-01 a E-03 son lectura, no prueba. En cuanto haya motor, se aplican las migraciones y este registro se actualiza con el resultado.
- **La maqueta no se ha probado en navegador**, solo se ha revisado su contenido. Del HTML no se ha auditado el JS.
- **`docs/api/endpoints.md`** se ha contrastado con el modelo, no ruta por ruta contra las reglas.
