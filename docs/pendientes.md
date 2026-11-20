# Lo que falta antes de escribir el modelo

- **Estado:** abierto · 17/11/2026
- **Autor:** @ia-opencode-ruben
- **Para qué:** el contrato y las reglas ya describen autenticación, bloques de layout, cola de revisión y export; el esquema real (`docs/architecture/migrations/`) todavía no. Esto es lo que hay que **decidir o migrar** antes de escribir backend: identidad, geometría del PDF y todo lo que cambia en la base de datos.
- **Qué no es:** no decide nada. Los bloqueantes se citan por su ID de [Coherencia](../vault/Proyecto/Coherencia.md) y las decisiones por su número; aquí solo se agrupa lo que hoy no se puede implementar.
- **Verificado el 19/11/2026** contra las migraciones `V1`-`V15`, `docs/api/endpoints.md`, `docs/reglas/` y las decisiones 0001-0012. **La BD es definitiva: no se planean migraciones nuevas**, así que lo que queda se arregla en el contrato o en las reglas.

## 1. Identidad y sesiones (B1, B2 · [0009](../vault/Decisiones/0009-identidad.md))

**Dónde estamos.** `V1__create_usuarios.sql` tiene `email`, `nombre_completo`, `rol`, `activo`. El contrato pide SSO, login local solo del admin de desarrollo, tres sesiones simultáneas y una cuenta con estados (`activo | bloqueado | baja`). `docs/reglas/usuarios.md` §7 ya escribió la lista; el modelo no la tiene.

**Qué falta decidir.** [0009](../vault/Decisiones/0009-identidad.md) está **aceptada (20/11)**: SSO del ICAT + admin local solo de desarrollo, con cuentas locales como alternativa. Queda una dependencia externa que no vota nadie del equipo: **el ICAT tiene que registrar la aplicación OIDC** (redirect URI, secreto, grupos). Son 1-2 semanas de terceros; si no llegan, el piloto arranca con cuentas locales y no cierra la puerta al SSO.

**Qué arrastra a la BD**

| Tabla | Qué se crea o cambia | Lo pide |
|---|---|---|
| `usuarios` | Tabla `usuarios_roles (usuario_id, rol)` con `CHECK` de tres valores y FK a `usuarios` (decisión de @Marina, 18/11); `estado` sustituye a `activo`; `nombre` y `apellidos` separados; `password_hash` (nulo si SSO), `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso`, `motivo_baja` y `sso_subject` (UNIQUE) si hay SSO | U-01, U-04, U-08, contrato §1-2, 0009, 0012 |
| `tokens_usuario` (nueva) | **no se crea**: U-10 a U-15 retiradas (18/11) y la contraseña del admin de desarrollo viene de variable de entorno (U-21) | — |
| `sesiones_usuario` (nueva) | `usuario_id`, `token_hash`, `creado_en`, `expira_en`, `revocado_en`, `ip`, `user_agent`; tope de 3 con desalojo de la más antigua. Una de las **dos tablas nuevas** con `usuarios_roles` (opción B, 18/11) | U-16 a U-20, contrato §1, 0012 |
| `idx_usuarios_rol_activo` | se cae con `rol`/`activo`; entran `(estado)` e `idx_usuarios_roles_rol` | B1, 0012 |

Con SSO, `password_hash` queda **solo** para el admin de desarrollo y la invitación por email desaparece; `tokens_usuario` no se crea. Eso importa porque **no hay proveedor de correo elegido** (B2): sin invitaciones ni reset no hace falta SMTP.

**Qué no se puede escribir hasta decidir:** el alta de usuarios, el middleware de sesión y la pantalla de login. Sin U-10 a U-15 no queda ninguna caducidad de token de invitación o reset; la del expediente se retiró (B6, A-21).

## 2. `bbox`, OCR y reconstrucción del PDF (B3, I5 · [0007](../vault/Decisiones/0007-generacion-pdf-final.md) y [pdf.md](export/pdf.md))

**Decidido.** El PDF final se **reconstruye**: lienzo nuevo y texto nuevo, sin un píxel del escaneo. No es estética, es que el PDF es lo único que sale del despacho y no puede llevar capa oculta, metadatos ni una zona sin censurar. Se acepta la contrapartida: sellos, firmas manuscritas y textura no se reproducen.

**El hueco.** `bloques_layout` ya existe en `V14`, pero las anotaciones guardan offsets sobre el texto completo y su propio `bbox`; el contrato ya se ha alineado con eso (no hay `bloque_id`). Y el OCR actual —PaddleOCR-VL por Ollama, prompt `OCR:`— devuelve **texto sin coordenadas**: hoy nada puede rellenar el `bbox` que pide la API.

**La salida acordada (17/11).** No se elige una fuente de geometría: se decide **por documento**, en este orden y quedándose con la primera que funcione.

1. **Capa de texto del PDF subido** (PyMuPDF `page.get_text("dict")`): caja, tamaño y origen reales, sin OCR y en milisegundos.
2. **Modelo de layout** (pipeline completo de PaddleOCR/PP-Structure, o `docling`): una pasada más por página.
3. **Modo secuencial**: mismo orden y jerarquía, sin posiciones.

Lo aplicado queda en `origen_geometria` para que el render sea reproducible.

**Lo que falta antes de implementar:**

1. **Medir el corpus real**: qué proporción de los documentos del Colegio llega como PDF con texto. Sin ese dato no se sabe si la rama 2 se paga.
2. ~~Crear `bloques_layout`~~: hecho en `V14`; los offsets se cuentan sobre `contenido_texto`.
3. **Decidir si el OCR es asíncrono por página** (I5). Las «dos lecturas» ya están decididas (A-24) y cuestan el doble de OCR (~1.375 pág/h en vez de 2.750).
4. ~~Semáforo por página (B5)~~: `paginas_documento` ya tiene lector (`GET /documents/{id}/pages`).

**Lo que no cambia:** 0007, el JSON de estructura y el render. Cuando llegue el `bbox`, se rellena el mismo JSON y no se toca el código de dibujo.

## 3. Todo lo que cambia en la BD

| Tabla | Qué queda | Lo pide | Depende de |
|---|---|---|---|
| `usuarios` | sin `roles[]`, `estado`, `sso_subject` ni `password_hash`: el login tiene que caber en `rol`/`activo` o quedar fuera del piloto | B1 | 0009 |
| `sesiones_usuario` | no existe: sin sesión propia hay que decidir cómo se guarda el token y si hay más de una sesión | B1, U-16 a U-20 | 0009, 0012 |
| `documentos` | `hash_export` no existe: el hash vive en `versiones_documento.metadatos_proceso->>'hash_export'` (B8 cerrado 19/11) | B8 | 0007 |
| `anotaciones_entidad` | sin `bloque_id`: el contrato ya cuenta los offsets sobre `contenido_texto` y usa el `bbox` de la detección | B3 | — |
| `seudonimos` | no existe: la maqueta no puede prometer «taula de pseudònims xifrada i separada» | I2 | — |
| `reglas_anonimizacion` | `accion_por_defecto` sigue en `tachado`; las reglas no deben prometer otro defecto | I1 | 0005 |
| `configuracion_sistema` (seed) | motores OCR en cloud, `preservar_formato_pdf = true` y el timeout de 60 min siguen sembrados | H6 | — |
| `categorias_sensibles` (seed) | `NUSS` sigue marcado `rgpd_especial` | H8 | — |
| `auditoria` | **no cambia**: `evento` + `detalle` JSONB aguantan login, SSO, reapertura y export | — | — |

`documentos.num_paginas`, `bloques_layout`, `paginas_documento`, `revisiones.asignado_a`/`en_cola` y las columnas del visto bueno y del cierre **ya están en `V14`/`V15`**.

### Migraciones

**No hay migraciones nuevas.** La BD (`V1`-`V15`) es la definitiva desde el 19/11: `V13` no se escribe y `V16` no se abre. Lo que quede se resuelve en el contrato, en las reglas o queda fuera del alcance.

Los once puntos revisados, las cinco preguntas contestadas y el orden están en [`vault/Decisiones/0011-ajustes-al-modelo-de-marina.md`](../vault/Decisiones/0011-ajustes-al-modelo-de-marina.md).

## 4. Qué espera a quién

| Decisión | Quién falta | Desbloquea |
|---|---|---|
| [0009](../vault/Decisiones/0009-identidad.md) identidad | **Aceptada (20/11)**; falta el registro OIDC del ICAT | el alta de usuarios (editando una migración existente; no hay `V13`) |
| [0008](../vault/Decisiones/0008-stack-backend.md) stack | **Reabierta (20/11)**: la decide @Rubén | [0014](../vault/Decisiones/0014-stack-backend-c-sharp-java-python.md): C#, Java o Python |
| [0005](../vault/Decisiones/0005-reglas-usuarios-y-aprobacion.md) reglas de usuarios y aprobación | @Rubén | estados, cola de revisión, reglas (V15) |
| [0007](../vault/Decisiones/0007-generacion-pdf-final.md) PDF final | @Rubén | `bloques_layout` y el export |
| [0006](../vault/Decisiones/0006-presidio-anonimizacion-local.md) Presidio | @Alex | acciones de anonimización (I1) |
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
