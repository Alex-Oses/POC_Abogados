# Lo que queda del modelo y la integración

- **Estado:** actualizado · 26/11/2026
- **Autor:** @ia-opencode-ruben
- **Para qué:** el contrato, las reglas y el esquema ya describen autenticación, bloques de layout, cola de revisión y export; aquí queda solo lo que falta validar o pedir a terceros.
- **Qué no es:** no decide nada. Los bloqueantes se citan por su ID de [Coherencia](../vault/Proyecto/Coherencia.md) y las decisiones por su número; aquí solo se agrupa lo que hoy no se puede implementar.
- **Verificado el 24/11/2026** contra las migraciones `V1`-`V15`, `docs/api/endpoints.md`, `docs/reglas/` y las decisiones vigentes. **La BD sigue siendo `V1`-`V15`: no se abre `V13` ni `V16`.**
- **Modelo objetivo**: `Modelo-ER-POC-ICAT-v0.3` (24/11, [diagrama](../vault/Proyecto/Modelo%20de%20datos.md), [diccionario](architecture/data-dictionary.md)). `V15` ya crea sus 14 tablas; las columnas que aún faltan se recogen en E-53 (§3).

## 1. Identidad y sesiones (B1, B2 · [0009](../vault/Decisiones/0009-identidad.md))

**Dónde estamos.** `V15__flujo_revision_y_export.sql` ya añade `usuarios_roles`, `estado`, `sso_subject`, `password_hash` y `sesiones_usuario`; vista, trigger y diccionario están alineados. Falta validar la recreación de la base de desarrollo desde cero.

**Qué falta.** [0009](../vault/Decisiones/0009-identidad.md) está **aceptada (20/11)**: SSO del ICAT + admin local solo de desarrollo. Queda una dependencia externa: **el ICAT tiene que registrar la aplicación OIDC** (redirect URI, secreto, grupos). Son 1-2 semanas de terceros. **El SSO queda en pausa desde el 26/11**, con intención de retomarlo: mientras tanto el piloto arranca con el admin local de desarrollo, que lleva los tres roles.

**Ya implementado (26/11).** El backend de `backend/` tiene login local, `/user/me`, cierre de sesión, cambio de contraseña, administración de usuarios y auditoría encadenada. Falta ejecutarlo contra PostgreSQL: aquí no hay Docker ni `psql`, así que las pruebas de integración están escritas pero saltadas.

**Qué arrastra a la BD**

| Tabla | Qué se crea o cambia | Lo pide |
|---|---|---|
| `usuarios` | `usuarios_roles (usuario_id, rol)` con `CHECK` de tres valores y FK; `estado` sustituye a `activo`; `password_hash` (solo admin local de desarrollo), `motivo_baja` y `sso_subject` (UNIQUE) | U-01, U-04, U-08, contrato §1-2, 0009, 0012 |
| `tokens_usuario` (nueva) | **no se crea**: U-10 a U-15 retiradas (18/11) y la contraseña del admin de desarrollo viene de variable de entorno (U-21) | — |
| `sesiones_usuario` (nueva) | `usuario_id`, `token_hash`, `creado_en`, `expira_en`, `revocado_en`, `ip`, `user_agent`; tope de 3 con desalojo de la más antigua. Una de las **dos tablas nuevas** con `usuarios_roles` (opción B, 18/11) | U-16 a U-20, contrato §1, 0012 |
| `idx_usuarios_rol_activo` | se cae con `rol`/`activo`; entran `(estado)` e `idx_usuarios_roles_rol` | B1, 0012 |

Con SSO, `password_hash` queda **solo** para el admin de desarrollo y la invitación por email desaparece; `tokens_usuario` no se crea. Eso importa porque **no hay proveedor de correo elegido** (B2): sin invitaciones ni reset no hace falta SMTP.

**Qué no se puede escribir todavía:** el SSO en sí (alta por `sub`, callback OIDC) espera al registro del ICAT. El alta por invitación no existe (U-10 a U-15 retiradas); la cuenta local de desarrollo se siembra por entorno (U-21).

## 2. `bbox`, OCR y reconstrucción del PDF (B3, I5 · [0007](../vault/Decisiones/0007-generacion-pdf-final.md) y [pdf.md](export/pdf.md))

**Decidido.** El PDF final se **reconstruye**: lienzo nuevo y texto nuevo, sin un píxel del escaneo. No es estética, es que el PDF es lo único que sale del despacho y no puede llevar capa oculta, metadatos ni una zona sin censurar. Se acepta la contrapartida: sellos, firmas manuscritas y textura no se reproducen.

**El hueco (corregido el 25/11).** `bloques_layout` ya existe en `V14` y `V15` añade `anotaciones_entidad.bloque_id` con FK compuesta por versión: los offsets se cuentan sobre `bloques_layout.contenido`, no sobre el texto completo. PaddleOCR-VL 1.6 devuelve **texto sin coordenadas**; la geometría se obtiene al principio, de la capa de texto del PDF o de un detector de layout. Si no hay ninguna, se crea un bloque sintético por página para que existan offsets y el render secuencial funcione.

**La salida acordada (17/11).** No se elige una fuente de geometría: se decide **por documento**, en este orden y quedándose con la primera que funcione.

1. **Capa de texto del PDF subido** (`pypdf`): caja y origen disponibles, sin OCR y sin licencia AGPL.
2. **Modelo de layout** (pipeline completo de PaddleOCR/PP-Structure, o `docling`): una pasada más por página.
3. **Modo secuencial**: mismo orden y jerarquía, sin posiciones; el texto se guarda en un bloque sintético por página.

Lo aplicado queda en `origen_geometria` para que el render sea reproducible.

**Lo que falta antes de implementar:**

1. **Medir el corpus real**: qué proporción de los documentos del Colegio llega como PDF con texto. Sin ese dato no se sabe si la rama 2 se paga.
2. ~~Crear `bloques_layout`~~: hecho en `V14`; los offsets se cuentan sobre `bloques_layout.contenido` de cada bloque.
3. **Decidir si el OCR es asíncrono por página** (I5). Las «dos lecturas» ya están decididas (A-24) y cuestan el doble de OCR (~1.375 pág/h en vez de 2.750).
4. ~~Semáforo por página (B5)~~: `paginas_documento` ya tiene lector (`GET /documents/{id}/pages`).

**Lo que no cambia:** 0007, el JSON de estructura y el render. Cuando llegue el `bbox`, se rellena el mismo JSON y no se toca el código de dibujo.

## 3. Todo lo que cambia en la BD

| Tabla | Qué queda | Lo pide | Depende de |
|---|---|---|---|
| `usuarios` | se añade al final de `V15` editada ([[0015-identidad-en-v15]]): fuera `rol`/`activo`; entran `estado`, `sso_subject`, `password_hash`, `motivo_baja` y `eliminado_en` | B1 | [[0015-identidad-en-v15]] |
| `sesiones_usuario` | tabla nueva al final de `V15` editada, con `token_hash` y `expira_en` ([[0015-identidad-en-v15]]) | B1, U-16 a U-20 | 0012, [[0015-identidad-en-v15]] |
| `documentos` | `hash_export` no existe: el hash vive en `versiones_documento.metadatos_proceso->>'hash_export'` (B8 cerrado 19/11) | B8 | 0007 |
| `anotaciones_entidad` | `bloque_id` con FK compuesta por versión en `V15`; los offsets se cuentan sobre `bloques_layout.contenido`. Queda E-51: los `bbox_*` legacy no se usan | B3, E-21 | — |
| `seudonimos` | no existe: la maqueta no puede prometer «taula de pseudònims xifrada i separada» | I2 | — |
| `reglas_anonimizacion` | `accion_por_defecto` sigue en `tachado`; las reglas no deben prometer otro defecto | I1 | 0005 |
| `configuracion_sistema` (seed) | motores OCR en cloud, `preservar_formato_pdf = true` y el timeout de 60 min siguen sembrados | H6 | — |
| `categorias_sensibles` (seed) | `NUSS` sigue marcado `rgpd_especial` | H8 | — |
| `auditoria` | **no cambia**: `evento` + `detalle` JSONB aguantan login, SSO, reapertura y export | — | — |
| Diferencias de columnas (E-53) | La v0.3 pide `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso`, `password_cambiado_en` y `usuarios_roles.otorgado_en`/`otorgado_por`; el SQL no los tiene, y sí añade `sesiones_usuario.ultimo_uso_en`, ausente en el modelo | EDICIÓN de `V15` | decisión nueva |

`documentos.num_paginas`, `bloques_layout`, `paginas_documento`, `revisiones.asignado_a`/`en_cola` y las columnas del visto bueno y del cierre **ya están en `V14`/`V15`**. Los offsets por bloque (B3, E-21) y la FK compuesta de `bloque_id` (E-25) también están cerrados desde el 25/11.

### Migraciones

**No hay migraciones nuevas.** La BD (`V1`-`V15`) es la definitiva desde el 19/11: `V13` no se escribe y `V16` no se abre. La identidad se añade al final de `V15` editada ([[0015-identidad-en-v15]]); lo demás se resuelve en el contrato, en las reglas o queda fuera del alcance.

Los once puntos revisados, las cinco preguntas contestadas y el orden están en [`vault/Decisiones/0011-ajustes-al-modelo-de-marina.md`](../vault/Decisiones/0011-ajustes-al-modelo-de-marina.md).

## 4. Qué espera a quién

| Decisión | Quién falta | Desbloquea |
|---|---|---|
| [0009](../vault/Decisiones/0009-identidad.md) identidad | **Aceptada (20/11)**; SSO **en pausa (26/11)** hasta que el ICAT registre la app OIDC | el alta de usuarios por `sub`; el piloto usa el admin local con tres roles |
| [0015](../vault/Decisiones/0015-identidad-en-v15.md) identidad en V15 | **Aceptada (24/11)**; falta validar desde cero | recrear la base de desarrollo y ejecutar las comprobaciones de vista, trigger y diccionario |
| [0008](../vault/Decisiones/0008-stack-backend.md) stack | **Resuelta (23/11)**: Python aceptado por @Rubén | [0014](../vault/Decisiones/0014-stack-backend-c-sharp-java-python.md): Python; C#/Java como alternativas |
| [0005](../vault/Decisiones/0005-reglas-usuarios-y-aprobacion.md) reglas de usuarios y aprobación | @Rubén | estados, cola de revisión, reglas (V15) |
| [0007](../vault/Decisiones/0007-generacion-pdf-final.md) PDF final | @Rubén | `bloques_layout` y el export |
| [0006](../vault/Decisiones/0006-presidio-anonimizacion-local.md) Presidio | @Rubén | acciones de anonimización (I1) |
| [0002](../vault/Decisiones/0002-postgresql.md) PostgreSQL + Flyway | equipo | ya se da por hecho en todo el repo |

## 5. Riesgos, por orden de lo que cuesta descubrir tarde

1. **Escribir el esquema antes de 0009** obliga a rehacer el alta y la sesión. Es el único punto donde esperar sale gratis.
2. **Arreglar los offsets después** de cargar anotaciones significa migrar datos y reescribir la revisión. `bloques_layout` va **antes** que el primer documento real.
3. **El `bbox` no es un problema de OCR**: se resuelve leyendo el PDF original. Lo caro sería dar por hecho que no hay capa de texto sin medirlo.
4. **El SSO es una dependencia externa**, no una tarea. Si el ICAT no registra la app, el piloto arranca con cuentas locales: la decisión 0009 ya lo contempla.
5. **Cada migración nueva toca los índices de V10** (`idx_usuarios_rol_activo` cae con `activo`). Los índices van en la misma migración que la columna, no en otra.

## 6. Cómo mantenerlo

Este informe **se queda obsoleto en cuanto entra una migración**, y una lista vieja es peor que ninguna. Se actualiza solo cuando pasa una de estas cuatro cosas; si no, no hace falta tocarlo:

| Cuándo | Qué hay que revisar |
|---|---|
| Se acepta una decisión (0005, 0007, 0009) | Las filas de §3 con «depende de» esa decisión pasan a tener respuesta |
| Se edita una migración existente (no hay `V13` ni `V16`) | Borra sus filas de §3; si la tabla ya existe, deja de ser una propuesta |
| Cambia `docs/api/endpoints.md` o `docs/reglas/` | La columna «lo pide» puede apuntar a una regla que ya no existe o a una nueva |
| Cambia la numeración de las decisiones | Los enlaces de §1, §2 y §4 |

La fuente de verdad no es este documento: son las migraciones, el contrato y las reglas. Esto es solo el índice de lo que falta. Si la tabla de §3 y el esquema se contradicen, manda el esquema y lo que está mal es este informe.
